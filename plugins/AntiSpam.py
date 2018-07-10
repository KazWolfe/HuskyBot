import asyncio
import datetime
import logging
import math
import re

import discord
from discord.ext import commands
from discord.http import Route

from WolfBot import WolfConfig
from WolfBot import WolfUtils
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)

F_EXPIRY = "cooldownExpiry"

# Default configuration values for the AntiSpam features.
DEFAULTS = {
    "multiPing": {
        "soft": 6,  # Number of unique pings in a message before deleting the message
        "hard": 15  # Number of unique pings in a message before banning the user
    },
    "invites": {
        'minutes': 30,  # Cooldown timer (reset)
        'banLimit': 5  # Number of warnings before ban
    },
    'attach': {
        'seconds': 15,  # Cooldown timer (reset)
        'warnLimit': 3,  # Number of attachment messages before warning the user
        'banLimit': 5  # Number of attachment messages before banning the user
    },
    'link': {
        'banLimit': 5,  # Number of warnings before banning the user
        'linkWarnLimit': 5,  # The number of links in a single message before banning
        'minutes': 30,  # Cooldown timer (reset)
        'totalBeforeBan': 100  # Total links in cooldown period before ban
    },
    'nonAscii': {
        'minMessageLength': 40,  # Minimum length of messages to check
        'nonAsciiThreshold': 0.5,  # Threshold (0 to 1) before marking the message as spam
        'banLimit': 3,  # Number of spam messages before banning
        'minutes': 5  # Cooldown timer (minutes)
    }
}


# noinspection PyMethodMayBeStatic
class AntiSpam:
    """
    The AntiSpam plugin is responsible for maintaining and running advanced logic-based moderation tasks on behalf of
    the moderator team.

    It, alongside Censor, ModTools, and the UBL help form the moderative backbone and power of the bot platform.
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()

        # Statics
        self.INVITE_COOLDOWNS = {}
        self.ATTACHMENT_COOLDOWNS = {}
        self.LINK_COOLDOWNS = {}
        self.NONASCII_COOLDOWNS = {}

        # Tasks
        self.__cleanup_task__ = self.bot.loop.create_task(self.cleanup_expired_cooldowns())

        LOG.info("Loaded plugin!")

    def __unload(self):
        self.__cleanup_task__.cancel()

    async def cleanup_expired_cooldowns(self):
        """
        Iterates through each field every four hours to check for expired cooldowns.

        Ugly as fuck.
        """
        while not self.bot.is_closed():
            for d in [self.INVITE_COOLDOWNS, self.LINK_COOLDOWNS, self.ATTACHMENT_COOLDOWNS]:
                for user_id in d.keys():
                    if d[user_id][F_EXPIRY] < datetime.datetime.utcnow():
                        LOG.info("Cleaning up expired cooldown for user %s", user_id)
                        del d[user_id]

            await asyncio.sleep(60 * 60 * 4)  # sleep for four hours

    async def on_message(self, message):
        if not WolfUtils.should_process_message(message):
            return

        events = [
            self.multi_ping_check(message),
            self.prevent_discord_invites(message),
            self.attachment_cooldown(message),
            self.prevent_link_spam(message),
            self.block_nonascii_spam(message)
        ]

        for event in events:
            asyncio.ensure_future(event)

    async def multi_ping_check(self, message):
        PING_WARN_LIMIT = self._config.get('antiSpam', {}).get('pingSoftLimit', DEFAULTS['multiPing']['soft'])
        PING_BAN_LIMIT = self._config.get('antiSpam', {}).get('pingHardLimit', DEFAULTS['multiPing']['hard'])

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_ALERTS.value, None)
        if alert_channel is not None:
            alert_channel = message.guild.get_channel(alert_channel)

        if message.author.permissions_in(message.channel).mention_everyone:
            return

        if PING_WARN_LIMIT is not None and len(message.mentions) >= PING_WARN_LIMIT:
            try:
                await message.delete()
            except discord.NotFound:
                LOG.warning("Message already deleted before AS could handle it (censor?).")

            # ToDo: Issue actual warning through Punishment (once made available)
            await message.channel.send(embed=discord.Embed(
                title=Emojis.NO_ENTRY + " Mass Ping Blocked",
                description="A mass-ping message was blocked in the current channel.\n"
                            "Please reduce the number of pings in your message and try again.",
                color=Colors.WARNING
            ))

            if alert_channel is not None:
                await alert_channel.send(embed=discord.Embed(
                    description=f"User {message.author} has pinged {len(message.mentions)} users in a single message "
                                f"in channel {message.channel.mention}.",
                    color=Colors.WARNING
                ).set_author(name="Mass Ping Alert", icon_url=message.author.avatar_url))

            LOG.info(f"Got message from {message.author} containing {len(message.mentions)} pings.")

        if PING_BAN_LIMIT is not None and len(message.mentions) >= PING_BAN_LIMIT:
            await message.author.ban(delete_message_days=0, reason="[AUTOMATIC BAN - AntiSpam Module] "
                                                                   "Multi-pinged over guild ban limit.")

    async def prevent_discord_invites(self, message: discord.Message):
        ANTISPAM_CONFIG = self._config.get('antiSpam', {})

        ALLOWED_INVITES = ANTISPAM_CONFIG.get('allowedInvites', [message.guild.id])
        COOLDOWN_SETTINGS = ANTISPAM_CONFIG.get('cooldowns', {}).get('invites', DEFAULTS['invites'])

        # Prepare the logger
        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is not None:
            log_channel = message.guild.get_channel(log_channel)

        # Prevent memory abuse by deleting expired cooldown records for this member
        if message.author.id in self.INVITE_COOLDOWNS \
                and self.INVITE_COOLDOWNS[message.author.id][F_EXPIRY] < datetime.datetime.utcnow():
            del self.INVITE_COOLDOWNS[message.author.id]
            LOG.info(f"Cleaned up stale invite cooldowns for user {message.author}")

        # Users with MANAGE_MESSAGES are allowed to send unauthorized invites.
        if message.author.permissions_in(message.channel).manage_messages:
            return

        # Determine if this is a "new user"
        is_new_user = (message.author.joined_at > datetime.datetime.utcnow() - datetime.timedelta(seconds=60))

        regex_matches = re.finditer(Regex.INVITE_REGEX, message.content, flags=re.IGNORECASE)

        for regex_match in regex_matches:
            fragment = regex_match.group('fragment')

            # Attempt to validate the invite, deleting invalid ones
            invite_data = None
            invite_guild = None
            try:
                # discord py doesn't let us do this natively, so let's do it ourselves!
                invite_data = await self.bot.http.request(
                    Route('GET', '/invite/{invite_id}?with_counts=true', invite_id=fragment))
                invite_guild = discord.Guild(state=self.bot, data=invite_data['guild'])
            except discord.errors.NotFound:
                LOG.warning(f"Couldn't resolve invite key {fragment}. Either it's invalid or the bot was banned.")

            # This guild is allowed to have invites on our guild, so we can ignore them.
            if (invite_guild is not None) and (invite_guild.id in ALLOWED_INVITES):
                continue

            # The guild either is invalid or not on the whitelist - delete the message.
            try:
                await message.delete()
            except discord.NotFound:
                # Message not found, let's log this
                LOG.warning(f"The message I was trying to delete does not exist! ID: {message.id}")

            # Grab the existing cooldown record, or make a new one if it doesn't exist.
            record = self.INVITE_COOLDOWNS.setdefault(message.author.id, {
                F_EXPIRY: datetime.datetime.utcnow() + datetime.timedelta(minutes=COOLDOWN_SETTINGS['minutes']),
                'offenseCount': 0
            })

            # Warn the user on their first offense only.
            if not is_new_user and record['offenseCount'] == 0:
                await message.channel.send(embed=discord.Embed(
                    title=Emojis.STOP + " Discord Invite Blocked",
                    description=f"Hey {message.author.mention}! It looks like you posted a Discord invite.\n\n"
                                f"Here on DIY Tech, we have a strict no-invites policy in order to prevent spam "
                                f"and advertisements. If you would like to post an invite, you may contact the "
                                f"admins to request an invite code be whitelisted.\n\n"
                                f"We apologize for the inconvenience.",
                    color=Colors.WARNING
                ), delete_after=90.0)

            # And we increment the offense counter here, and extend their expiry
            record['offenseCount'] += 1
            record[F_EXPIRY] = datetime.datetime.utcnow() + datetime.timedelta(minutes=COOLDOWN_SETTINGS['minutes'])

            #  Log their offense to the server log (if it exists)
            if log_channel is not None:
                # We've a valid invite, so let's log that with invite data.
                log_embed = discord.Embed(
                    description=f"An invite with key `{fragment}` by user {message.author} (ID `{message.author.id}`) "
                                f"was caught and filtered.",
                    color=Colors.INFO
                )
                log_embed.set_author(name=f"Invite from {message.author} intercepted!",
                                     icon_url=message.author.avatar_url)

                if invite_guild is not None:
                    log_embed.add_field(name="Invited Guild Name", value=invite_guild.name, inline=True)

                    ch_type = {0: "#", 2: "[VC] ", 4: "[CAT] "}
                    log_embed.add_field(name="Invited Channel Name",
                                        value=ch_type[invite_data['channel']['type']] + invite_data['channel']['name'],
                                        inline=True)
                    log_embed.add_field(name="Invited Guild ID", value=invite_guild.id, inline=True)

                    log_embed.add_field(name="Invited Guild Creation",
                                        value=invite_guild.created_at.strftime(DATETIME_FORMAT),
                                        inline=True)

                    if invite_data.get('approximate_member_count', -1) != -1:
                        log_embed.add_field(name="Invited Guild User Count",
                                            value=f"{invite_data.get('approximate_member_count', -1)} "
                                                  f"({invite_data.get('approximate_presence_count', -1)} online)",
                                            )

                    if invite_data.get('inviter') is not None:
                        inviter: dict = invite_data.get('inviter', {})
                        log_embed.add_field(
                            name="Invite Creator",
                            value=f"{inviter['username']}#{inviter['discriminator']}"
                        )

                    log_embed.set_thumbnail(url=invite_guild.icon_url)

                log_embed.set_footer(text=f"Strike {record['offenseCount']} "
                                          f"of {COOLDOWN_SETTINGS['banLimit']}, "
                                          f"resets {record[F_EXPIRY].strftime(DATETIME_FORMAT)}")

                await log_channel.send(embed=log_embed)

            # If the user is at the offense limit, we're going to ban their ass. In this case, this means that on
            # their fifth invalid invite, we ban 'em.
            if COOLDOWN_SETTINGS['banLimit'] > 0 and (record['offenseCount'] >= COOLDOWN_SETTINGS['banLimit']):
                try:
                    del self.INVITE_COOLDOWNS[message.author.id]

                    await message.author.ban(
                        reason=f"[AUTOMATIC BAN - AntiSpam Plugin] User sent {COOLDOWN_SETTINGS['banLimit']} "
                               f"unauthorized invites in a {COOLDOWN_SETTINGS['minutes']} minute period.",
                        delete_message_days=0)
                    LOG.info(f"User {message.author} was banned for exceeding set invite thresholds.")
                except KeyError:
                    LOG.warning("Attempted to delete cooldown record for user %s (ban over limit), but failed as the "
                                "record count not be found.", message.author.id)
            elif is_new_user:
                # If we have a new user, we kick them now because they're probably a spammer.
                await message.author.kick(reason="New user (less than 60 seconds old) posted invite.")
                LOG.info(f"User {message.author} kicked for posting invite within 60 seconds of joining.")
            else:
                LOG.info(f"User {message.author} was issued an invite warning ({record['offenseCount']} / "
                         f"{COOLDOWN_SETTINGS['banLimit']}, resetting at {record[F_EXPIRY].strftime(DATETIME_FORMAT)})")

            # We don't need to process anything anymore.
            break

    async def attachment_cooldown(self, message: discord.Message):
        ANTISPAM_CONFIG = self._config.get('antiSpam', {})
        COOLDOWN_CONFIG = ANTISPAM_CONFIG.get('cooldowns', {}).get('attach', DEFAULTS['attach'])

        # Prepare the logger
        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is not None:
            log_channel = message.guild.get_channel(log_channel)

        # Clear expired cooldown record for this user, if it exists.
        if message.author.id in self.ATTACHMENT_COOLDOWNS \
                and self.ATTACHMENT_COOLDOWNS[message.author.id][F_EXPIRY] < datetime.datetime.utcnow():
            del self.ATTACHMENT_COOLDOWNS[message.author.id]
            LOG.info(f"Cleaned up stale attachment cooldowns for user {message.author}")

        # Users with MANAGE_MESSAGES are allowed to bypass attachment rate limits.
        if message.author.permissions_in(message.channel).manage_messages:
            return

        if len(message.attachments) > 0:
            # User posted an attachment, and is not in the cache. Let's add them, on strike 0.
            cooldown_record = self.ATTACHMENT_COOLDOWNS.setdefault(message.author.id, {
                F_EXPIRY: datetime.datetime.utcnow() + datetime.timedelta(seconds=COOLDOWN_CONFIG['seconds']),
                'offenseCount': 0
            })

            # And we increment the offense counter here.
            cooldown_record['offenseCount'] += 1

            # Give them a fair warning on attachment #3
            if COOLDOWN_CONFIG['warnLimit'] != 0 and cooldown_record['offenseCount'] == COOLDOWN_CONFIG['warnLimit']:
                await message.channel.send(embed=discord.Embed(
                    title=Emojis.STOP + " Whoa there, pardner!",
                    description=f"Hey there {message.author.mention}! You're sending files awfully fast. Please help "
                                f"us keep this chat clean and readable by not sending lots of files so quickly. "
                                f"Thanks!",
                    color=Colors.WARNING
                ), delete_after=90.0)

                if log_channel is not None:
                    await log_channel.send(embed=discord.Embed(
                        description=f"User {message.author} has sent {cooldown_record['offenseCount']} attachments in "
                                    f"a {COOLDOWN_CONFIG['seconds']}-second period in channel "
                                    f"{message.channel.mention}.",
                        color=Colors.WARNING
                    ).set_author(name="Possible Attachment Spam", icon_url=message.author.avatar_url))
                    return

                LOG.info(f"User {message.author} has been warned for posting too many attachments in a short while.")
            elif cooldown_record['offenseCount'] >= COOLDOWN_CONFIG['banLimit']:
                await message.author.ban(reason=f"[AUTOMATIC BAN - AntiSpam Module] User sent "
                                                f"{cooldown_record['offenseCount']} attachments in a "
                                                f"{COOLDOWN_CONFIG['seconds']} second period.",
                                         delete_message_days=1)
                del self.ATTACHMENT_COOLDOWNS[message.author.id]
                LOG.info(f"User {message.author} has been banned for posting over {COOLDOWN_CONFIG['banLimit']} "
                         f"attachments in a {COOLDOWN_CONFIG['seconds']} period.")
            else:
                LOG.info(f"User {message.author} posted a message with {len(message.attachments)} attachments, "
                         f"incident logged. User on warning {cooldown_record['offenseCount']} of "
                         f"{COOLDOWN_CONFIG['banLimit']}.")

        else:
            # They sent a message containing text. Clear their cooldown.
            if message.author.id in self.ATTACHMENT_COOLDOWNS:
                LOG.info(f"User {message.author} previously on file cooldown warning list has sent a file-less "
                         f"message. Deleting cooldown entry.")
                del self.ATTACHMENT_COOLDOWNS[message.author.id]

    async def prevent_link_spam(self, message: discord.Message):
        """
        Prevent link spam by scanning messages for anything that looks link-like.

        If a link is found, we will attempt to kill it if it has more than [linkWarnLimit] links inside of it. After a
        number of warnings determined by [warningsBeforeBan], the system will ban the account automatically. This
        cooldown will automatically expire after [cooldownMinutes] from the first message.

        Alternatively, if a user posts [totalBeforeBan] links in [minutes] from their initial link message, they will
        also be banned.

        :param message: The discord Message object to process.
        :return: Does not return.
        """

        ANTISPAM_CONFIG = self._config.get('antiSpam', {})
        COOLDOWN_CONFIG = ANTISPAM_CONFIG.get('cooldowns', {}).get('link', DEFAULTS['link'])

        # gen the embed here
        link_warning = discord.Embed(
            title=Emojis.STOP + "Hey! Listen!",
            description=f"Hey {message.author.mention}! It looks like you posted a lot of links.\n\n"
                        f"In order to cut down on server spam, we have a limitation on the number of links "
                        f"you are allowed to have in a time period. Generally, you won't exceed this limit "
                        f"normally, but I'd like to give you a friendly warning to calm down on the number of "
                        f"links you have. Thanks!",
            color=Colors.WARNING
        ).set_thumbnail(url="https://i.imgur.com/Z3l78Dh.gif")

        # Prepare the logger
        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is not None:
            log_channel = message.guild.get_channel(log_channel)

        # We can lazily delete link cooldowns on messages, instead of checking.
        if message.author.id in self.LINK_COOLDOWNS \
                and self.LINK_COOLDOWNS[message.author.id][F_EXPIRY] < datetime.datetime.utcnow():
            del self.LINK_COOLDOWNS[message.author.id]

        # Users with MANAGE_MESSAGES are allowed to send as many links as they want.
        if message.author.permissions_in(message.channel).manage_messages:
            return

        regex_matches = re.findall(Regex.URL_REGEX, message.content, re.IGNORECASE)

        # If a message has no links, abort right now.
        if regex_matches is None or len(regex_matches) == 0:
            return

        LOG.info(f"Found a message from {message.author} containing {len(regex_matches)} links. Processing.")

        # We have at least one link now, make the cooldown record.
        cooldown_record = self.LINK_COOLDOWNS.setdefault(message.author.id, {
            F_EXPIRY: datetime.datetime.utcnow() + datetime.timedelta(minutes=COOLDOWN_CONFIG['minutes']),
            'offenseCount': 0,
            'totalLinks': 0
        })

        # We also want to track individual link posting
        if COOLDOWN_CONFIG['linkWarnLimit'] > 0:

            # Increment the record
            cooldown_record['totalLinks'] += len(regex_matches)

            # if a member is closely approaching their link cap (75% of max), warn them.
            warn_limit = math.floor(COOLDOWN_CONFIG['totalBeforeBan'] * 0.75)
            if cooldown_record['totalLinks'] >= warn_limit and cooldown_record['offenseCount'] == 0:
                await message.channel.send(embed=link_warning, delete_after=90.0)
                cooldown_record['offenseCount'] += 1

                if log_channel is not None:
                    embed = discord.Embed(
                        description=f"User {message.author} has sent {cooldown_record['totalLinks']} links recently, "
                                    f"and as a result has been warned. If they continue to post links to the currently "
                                    f"configured value of {COOLDOWN_CONFIG['totalBeforeBan']} links, they will "
                                    f"be automatically banned.",
                    )

                    embed.set_footer(text=f"Cooldown resets "
                                          f"{cooldown_record[F_EXPIRY].strftime(DATETIME_FORMAT)}")

                    embed.set_author(name="Link spam from {message.author} detected!",
                                     icon_url=message.author.avatar_url)

                    await log_channel.send(embed=embed)

            # And then ban at max
            if cooldown_record['totalLinks'] >= COOLDOWN_CONFIG['totalBeforeBan']:
                await message.author.ban(reason=f"[AUTOMATIC BAN - AntiSpam Module] User sent "
                                                f"{COOLDOWN_CONFIG['totalBeforeBan']} or more links in a "
                                                f"{COOLDOWN_CONFIG['minutes']} minute period.",
                                         delete_message_days=1)

                # And purge their record, it's not needed anymore
                del self.LINK_COOLDOWNS[message.author.id]
                return

        # And now process warning counters
        if COOLDOWN_CONFIG['linkWarnLimit'] > 0 and (len(regex_matches) > COOLDOWN_CONFIG['linkWarnLimit']):

            # First and foremost, delete the message
            try:
                await message.delete()
            except discord.NotFound:
                LOG.warning("Message was deleted before AS could handle it.")

            # Add the user to the warning table if they're not already there
            if cooldown_record['offenseCount'] == 0:
                # Inform the user of what happened, on their first time only.
                await message.channel.send(embed=link_warning, delete_after=90.0)

            # Get the offender's cooldown record, and increment it.
            cooldown_record['offenseCount'] += 1

            # Post something to logs
            if log_channel is not None:
                embed = discord.Embed(
                    description=f"User {message.author} has sent a message containing over "
                                f"{COOLDOWN_CONFIG['linkWarnLimit']} links to a public channel.",
                    color=Colors.WARNING
                )

                embed.add_field(name="Message Text", value=WolfUtils.trim_string(message.content, 1000, False),
                                inline=False)

                embed.add_field(name="Message ID", value=message.id, inline=True)
                embed.add_field(name="Channel", value=message.channel.mention, inline=True)

                embed.set_footer(text=f"Strike {cooldown_record['offenseCount']} "
                                      f"of {COOLDOWN_CONFIG['banLimit']}, "
                                      f"resets {cooldown_record[F_EXPIRY].strftime(DATETIME_FORMAT)}")

                embed.set_author(name=f"Link spam from {message.author} blocked.",
                                 icon_url=message.author.avatar_url)

                await log_channel.send(embed=embed)

            # If the user is over the ban limit, get rid of them.
            if cooldown_record['offenseCount'] >= COOLDOWN_CONFIG['banLimit']:
                await message.author.ban(reason=f"[AUTOMATIC BAN - AntiSpam Module] User sent "
                                                f"{COOLDOWN_CONFIG['banLimit']} messages containing "
                                                f"{COOLDOWN_CONFIG['linkWarnLimit']} or more links in a "
                                                f"{COOLDOWN_CONFIG['minutes']} minute period.",
                                         delete_message_days=1)

                # And purge their record, it's not needed anymore
                del self.LINK_COOLDOWNS[message.author.id]

    async def block_nonascii_spam(self, message: discord.Message):
        ANTISPAM_CONFIG = self._config.get('antiSpam', {})
        CHECK_CONFIG = ANTISPAM_CONFIG.get('cooldowns', {}).get('link', DEFAULTS['nonAscii'])

        # Prepare the logger
        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is not None:
            log_channel = message.guild.get_channel(log_channel)

        # We can lazily delete link cooldowns on messages, instead of checking.
        if message.author.id in self.NONASCII_COOLDOWNS \
                and self.NONASCII_COOLDOWNS[message.author.id][F_EXPIRY] < datetime.datetime.utcnow():
            del self.NONASCII_COOLDOWNS[message.author.id]

        # Disable if min length is 0 or less
        if CHECK_CONFIG['minMessageLength'] <= 0:
            return

        # Users with MANAGE_MESSAGES are allowed to send as many links as they want.
        if message.author.permissions_in(message.channel).manage_messages:
            return

        # Message is too short, just ignore it.
        if len(message.content) < CHECK_CONFIG['minMessageLength']:
            return

        nonascii_characters = re.sub('[ -~]', '', message.content)

        # Message doesn't have enough non-ascii characters, we can ignore it.
        if len(nonascii_characters) < (len(message.content) * CHECK_CONFIG['nonAsciiThreshold']):
            return

        # Message is now over threshold, get/create their cooldown record.
        cooldown_record = self.NONASCII_COOLDOWNS.setdefault(message.author.id, {
            F_EXPIRY: datetime.datetime.utcnow() + datetime.timedelta(minutes=CHECK_CONFIG['minutes']),
            'offenseCount': 0
        })

        if cooldown_record['offenseCount'] == 0:
            await message.channel.send(embed=discord.Embed(
                title=Emojis.SHIELD + " Oops! Non-ASCII Message!",
                description=f"Hey {message.author.mention}!\n\nIt looks like you posted a message containing a lot of "
                            f"non-ascii characters. In order to cut down on spam, we are a bit strict with this. We "
                            f"won't delete your message, but please keep ASCII spam off the server.\n\nContinuing to "
                            f"spam ASCII messages may result in a ban. Thank you for keeping DIY Tech clean!"
            ), delete_after=90.0)

        cooldown_record['offenseCount'] += 1

        if log_channel is not None:
            embed = discord.Embed(
                description=f"User {message.author} has sent a message with {len(nonascii_characters)} non-ASCII "
                            f"characters (out of {len(message.content)} total).",
                color=Colors.WARNING
            )

            embed.add_field(name="Message Text", value=WolfUtils.trim_string(message.content, 1000, False),
                            inline=False)

            embed.add_field(name="Message ID", value=message.id, inline=True)
            embed.add_field(name="Channel", value=message.channel.mention, inline=True)

            embed.set_footer(text=f"Strike {cooldown_record['offenseCount']} of {CHECK_CONFIG['banLimit']}, "
                                  f"resets {cooldown_record[F_EXPIRY].strftime(DATETIME_FORMAT)}")

            embed.set_author(name=f"Non-ASCII spam from {message.author} detected!",
                             icon_url=message.author.avatar_url)

            await log_channel.send(embed=embed)

        if cooldown_record['offenseCount'] >= CHECK_CONFIG['banLimit']:
            await message.author.ban(reason=f"[AUTOMATIC BAN - AntiSpam Module] User sent {CHECK_CONFIG['banLimit']} "
                                            f"messages over the non-ASCII threshold in a {CHECK_CONFIG['minutes']} "
                                            f"minute period.",
                                     delete_message_days=1)

            # And purge their record, it's not needed anymore
            del self.NONASCII_COOLDOWNS[message.author.id]

    @commands.group(name="antispam", aliases=['as'], brief="Manage the Antispam configuration for the bot")
    @commands.has_permissions(manage_messages=True)
    async def asp(self, ctx: commands.Context):
        """
        This is the parent command for the AntiSpam module.

        It does nothing on its own, but it does grant the ability for administrators to change spam filter settings on
        the fly.
        """
        pass

    @asp.command(name="setPingLimit", brief="Set the number of pings required before AntiSpam takes action")
    @commands.has_permissions(mention_everyone=True)
    async def set_ping_limit(self, ctx: commands.Context, warn_limit: int, ban_limit: int):
        """
        Set the warning and ban limits for the maximum number of pings permitted in a single message.

        This command takes two arguments - warn_limit and ban_limit. Both of these are integers.

        Once a user exceeds the warning limit of pings in a single message, their message will be automatically deleted
        and a warning will be issued to the user.

        If a user surpasses the ban limit of pings in a single message, the message will be deleted and the user will
        be immediately banned.

        Setting a value to zero or any negative number will disable that specific limit.

        Example commands:
            /as setPingLimit 6 15 - Set warn limit to 6, ban limit to 15
            /as setPingLimit 6 0  - Set warn limit to 6, remove the ban limit
        """
        if warn_limit < 1:
            warn_limit = None

        if ban_limit < 1:
            ban_limit = None

        as_config = self._config.get('antiSpam', {})
        as_config['pingSoftLimit'] = warn_limit
        as_config['pingHardLimit'] = ban_limit
        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description=f"Ping limits have been successfully updated. Warn in `{warn_limit}` pings, "
                        f"ban in `{ban_limit}`.",
            color=Colors.SUCCESS
        ))

    @asp.command(name="allowInvite", brief="Allow an invite from the guild ID given")
    @commands.has_permissions(manage_guild=True)
    async def allow_invite(self, ctx: commands.Context, guild: int):
        """
        Add a guild to the AntiSpam Invite Whitelist.

        By default, AntiSpam will block all guild invites not posted by authorized members (or invites that are not to
        this guild). This may be overridden on a case-by-case basis using this command. Once a guild is added to the
        whitelist, their invites will not be touched on this guild.

        This command expects a single argument - a guild ID.

        Example commands:
            /as allowInvite 11223344 - Allow invites from guild ID 11223344

        See also:
            /help as blockInvite    - Remove a guild from the invite whitelist
            /help as inviteCooldown - Edit cooldown settings for the invite limiter.
        """
        as_config = self._config.get('antiSpam', {})

        allowed_invites = as_config.setdefault('allowedInvites', [ctx.guild.id])

        if guild in allowed_invites:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Plugin",
                description=f"The guild with ID `{guild}` is already whitelisted!",
                color=Colors.WARNING
            ))
            return

        allowed_invites.append(guild)
        self._config.set("antiSpam", as_config)
        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description=f"The invite to guild `{guild}` has been added to the whitelist.",
            color=Colors.SUCCESS
        ))
        return

    @asp.command(name="blockInvite", brief="Remove an invite from the whitelist.")
    @commands.has_permissions(manage_guild=True)
    async def block_invite(self, ctx: commands.Context, guild: int):
        """
        Remove a guild from the AntiSpam Invite Whitelist.

        If a guild was added to the AntiSpam whitelist, this command may be used to remove the whitelist entry. See
        /help antispam allowInvite for more information on this command.

        This command expects a single argument - a guild ID.

        This command will return an error if a guild not on the whitelist is removed.

        Example Commands:
            /as blockInvite 11223344 - No longer allow invites from guild ID 11223344

        See also:
            /help as allowInvite    - Add a guild to the invite whitelist
            /help as inviteCooldown - Edit cooldown settings for the invite limiter.
        """
        as_config = self._config.get('antiSpam', {})
        allowed_invites = as_config.setdefault('allowedInvites', [ctx.guild.id])

        if guild == ctx.guild.id:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Plugin",
                description=f"This guild may not be removed from the whitelist!",
                color=Colors.WARNING
            ))
            return

        if guild not in allowed_invites:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Plugin",
                description=f"The guild `{guild}` is not whitelisted!",
                color=Colors.WARNING
            ))
            return

        allowed_invites.pop(guild)
        self._config.set("antiSpam", as_config)
        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description=f"The guild with ID `{guild}` has been removed from the whitelist.",
            color=Colors.SUCCESS
        ))

    @asp.command(name="inviteCooldown", brief="Set invite cooldown and ban limits")
    @commands.has_permissions(manage_guild=True)
    async def set_invite_cooldown(self, ctx: commands.Context, cooldown_minutes: int, ban_limit: int):
        """
        Set cooldowns/ban thresholds for guild invite spam.

        The bot will automatically ban a user after posting a certain number of invites in a defined time period. This
        command allows those limits to be altered.

        The command takes two arguments: cooldown_minutes, and ban_limit.

        If a user posts `ban_limit` or more guild invites in the span of `cooldown_minutes` minutes, they will be
        automatically banned from the guild.

        See also:
            /help as blockInvite    - Remove a guild from the invite whitelist
            /help as blockInvite    - Add a guild to the invite whitelist
        """
        as_config = self._config.get('antiSpam', {})
        invite_cooldown = as_config.setdefault('cooldowns', {}).setdefault('invites', DEFAULTS['invites'])

        invite_cooldown['minutes'] = cooldown_minutes
        invite_cooldown['banLimit'] = ban_limit

        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description=f"The invite module of AntiSpam has been set to allow a max of **`{ban_limit}`** unauthorized "
                        f"invites in a **`{cooldown_minutes}` minute** period.",
            color=Colors.SUCCESS
        ))

    @asp.command(name="attachmentCooldown", brief="Set attachment cooldown and ban limits")
    @commands.has_permissions(manage_guild=True)
    async def set_attach_cooldown(self, ctx: commands.Context, cooldown_seconds: int, warn_limit: int, ban_limit: int):
        """
        Set cooldowns/ban thresholds on attachment spam.

        AntiSpam will log and ban users that go over a set amount of attachments in a second. This command allows those
        limits to be altered on the fly.

        If a user sends `warn_limit` announcements in a `cooldown_seconds` second period, they will be issued a warning
        message to cool on the spam. If they persist to `ban_limit` attachments in the same period, they will be
        automatically banned from the guild.

        A message not containing attachments will reset the cooldown period.
        """

        as_config = self._config.get('antiSpam', {})
        attach_config = as_config.setdefault('cooldowns', {}).setdefault('attach', DEFAULTS['attach'])

        attach_config['seconds'] = cooldown_seconds
        attach_config['warnLimit'] = warn_limit
        attach_config['banLimit'] = ban_limit

        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description=f"The attachments module of AntiSpam has been set to allow a max of **`{ban_limit}`** "
                        f"attachments in a **`{cooldown_seconds}` second** period, warning after **`{warn_limit}`** "
                        f"attachments",
            color=Colors.SUCCESS
        ))

    @asp.command(name="linkCooldown", brief="Set cooldowns for link posting", aliases=["zelda"])
    @commands.has_permissions(manage_guild=True)
    async def set_link_cooldown(self, ctx: commands.Context, cooldown_minutes: int, links_before_warn: int,
                                ban_limit: int, total_link_limit: int):

        """
        Set cooldowns/ban thresholds for link spam.

        AntiSpam will attempt to log users who post links excessively to chat. This command allows these settings to be
        updated on the fly.

        If a user sends a message containing `links_before_warn` messages in a single message, the message will be
        deleted and the user will be issued a warning. If a user accrues `ban_limit` warnings in a period of time
        `cooldown_minutes` minutes from the initial warning, they will be banned.

        Alternatively, if a user posts `total_link_limit` links in a `minutes` period, they will be automatically
        banned as well. A warning will be issued at 75% of links.

        Setting links_before_warn to 0 disables this feature entirely, and setting `ban_limit` to 0 will disable the
        autoban feature.

        Cooldowns are not reset by anything other than time.

        Default values:
            cooldown_minutes: 30 minutes
            links_before_warn: 5 links
            ban_limit: 5 warnings
            total_link_limit: 75 links
        """

        as_config = self._config.get('antiSpam', {})
        link_config = as_config.setdefault('cooldowns', {}).setdefault('link', DEFAULTS['link'])

        link_config['banLimit'] = ban_limit
        link_config['linkWarnLimit'] = links_before_warn
        link_config['minutes'] = cooldown_minutes
        link_config['totalBeforeBan'] = total_link_limit

        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description=f"The links module of AntiSpam has been set to allow a max of {links_before_warn} links in a "
                        f"single message. If a user posts more than {ban_limit} illegal messages in a "
                        f"{cooldown_minutes} minute period, they will additionally be banned. If a user posts "
                        f"{total_link_limit} links in the same time period, they will also be banned.",
            color=Colors.SUCCESS
        ))

    @asp.command(name="nonAsciiCooldown", brief="Set non-ASCII cooldown and ban limits")
    @commands.has_permissions(manage_guild=True)
    async def set_ascii_cooldown(self, ctx: commands.Context, cooldown_minutes: int, ban_limit: int, min_length: int,
                                 threshold: int):
        """
        Set cooldowns/ban thresholds on non-ASCII spam.

        AntiSpam will attempt to detect and ban uses who excessively post non-ASCII characters. These are defined as
        symbols that can not be typed on a normal keyboard such as emoji and box art. Effectively, this command will
        single-handedly kill ASCII art spam on the guild.

        If a user posts a message with at least `min_length` characters which contains at least `length * threshold`
        non-ASCII characters, the bot will log a warning and warn the user on the first offense. If a user exceeds
        `ban_limit` warnings, they will be automatically banned. This feature does NOT delete messages pre-ban.

        Setting min_length to 0 or less will disable this feature.

        Parameters:
            cooldown_minutes - The number of minutes before a given cooldown expires (default: 5)
            ban_limit - The number of warnings before a user is autobanned (default: 3)
            min_length - The minimum total number of characters to process a message (default: 40)
            threshold - A value (between 0 and 1) that represents the percentage of characters that need to be
                       non-ASCII before a warning is fired. (default: 0.5)
        """

        as_config = self._config.get('antiSpam', {})
        nonascii_config = as_config.setdefault('cooldowns', {}).setdefault('nonAscii', DEFAULTS['nonAscii'])

        if not 0 <= threshold <= 1:
            await ctx.send(embed=discord.Embed(
                title="Configuration Error",
                description="The `threshold` value must be between 0 and 1!",
                color=Colors.DANGER
            ))

        nonascii_config['minutes'] = cooldown_minutes
        nonascii_config['banLimit'] = ban_limit
        nonascii_config['minMessageLength'] = min_length
        nonascii_config['nonAsciiThreshold'] = threshold

        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description=f"The non-ASCII module of AntiSpam has been set to scan messages over **{min_length} "
                        f"characters** for a non-ASCII **threshold of {threshold}**. Users will be automatically "
                        f"banned for posting **{ban_limit} messages** in a **{cooldown_minutes} minute** period.",
            color=Colors.SUCCESS
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(AntiSpam(bot))
