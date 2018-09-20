import datetime
import logging
import math
import re

import discord
from discord.ext import commands

from WolfBot import WolfConfig, WolfUtils
from WolfBot.WolfStatics import *
from WolfBot.antispam import AntiSpamModule

LOG = logging.getLogger("DakotaBot.Plugin.AntiSpam." + __name__.split('.')[-1])

defaults = {
    'banLimit': 5,  # Number of warnings before banning the user
    'linkWarnLimit': 5,  # The number of links in a single message before banning
    'minutes': 30,  # Cooldown timer (reset)
    'totalBeforeBan': 100  # Total links in cooldown period before ban
}


class LinkFilter(AntiSpamModule):
    def __init__(self, plugin):
        super().__init__(name="linkFilter", callback=self.base, brief="Control the link filter's settings",
                         checks=[super().has_permissions(manage_guild=True)], aliases=["lf"])

        self.bot = plugin.bot
        self._config = WolfConfig.get_config()

        self._events = {}

        self.add_command(self.set_link_cooldown)
        self.add_command(self.clear_cooldown)
        self.add_command(self.clear_all_cooldowns)

        LOG.info("Filter initialized.")

    def cleanup(self):
        # Purge expired events/cooldowns.
        for user_id in self._events.keys():
            if self._events[user_id]['expiry'] < datetime.datetime.utcnow():
                LOG.info("Cleaning up expired cooldown for user %s", user_id)
                del self._events[user_id]

    def clear_for_user(self, user: discord.Member):
        if user.id not in self._events.keys():
            raise KeyError("The user requested does not have a record for this filter.")

        del self._events[user.id]

    def clear_all(self):
        self._events = {}

    async def on_message(self, message: discord.Message):
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
        COOLDOWN_CONFIG = ANTISPAM_CONFIG.get('LinkFilter', {}).get('config', defaults)

        # gen the embed here
        link_warning = discord.Embed(
            title=Emojis.STOP + " Hey! Listen!",
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
        if message.author.id in self._events \
                and self._events[message.author.id]['expiry'] < datetime.datetime.utcnow():
            del self._events[message.author.id]

        # Users with MANAGE_MESSAGES are allowed to send as many links as they want.
        if message.author.permissions_in(message.channel).manage_messages:
            return

        regex_matches = re.findall(Regex.URL_REGEX, message.content, re.IGNORECASE)

        # If a message has no links, abort right now.
        if regex_matches is None or len(regex_matches) == 0:
            return

        LOG.info(f"Found a message from {message.author} containing {len(regex_matches)} links. Processing.")

        # We have at least one link now, make the cooldown record.
        cooldown_record = self._events.setdefault(message.author.id, {
            'expiry': datetime.datetime.utcnow() + datetime.timedelta(minutes=COOLDOWN_CONFIG['minutes']),
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
                                          f"{cooldown_record['expiry'].strftime(DATETIME_FORMAT)}")

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
                del self._events[message.author.id]
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
                                      f"resets {cooldown_record['expiry'].strftime(DATETIME_FORMAT)}")

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
                del self._events[message.author.id]

    @commands.command(name="configure", brief="Configure thresholds for LinkFilter")
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
        link_config = as_config.setdefault('LinkFilter', {}).setdefault('config', defaults)

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

    @commands.command(name="clear", brief="Clear a cooldown record for a specific user")
    async def clear_cooldown(self, ctx: commands.Context, user: discord.Member):
        """
        Clear a user's cooldown record for this filter.

        This command allows moderators to override the antispam expiry system, and clear a user's cooldowns/strikes/
        warnings early. Any accrued warnings for the selected user are discarded and the user starts with a clean slate.

        Parameters:
            user - A user object (ID, mention, etc) to target for clearing.

        See also:
            /as <filter_name> clearAll - Clear all cooldowns for all users for a single filter.
            /as clear - Clear cooldowns on all filters for a single user.
            /as clearAll - Clear all cooldowns globally for all users (reset).
        """

        try:
            self.clear_for_user(user)
            LOG.info(f"Th link filter cooldown record for {user} was cleared by {ctx.author}.")
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Link Filter",
                description=f"There is no cooldown record present for {user.mention}. Either this user does not exist, "
                            f"they do not have a cooldown record, or it has already been cleared.",
                color=Colors.DANGER
            ))
            return

        await ctx.send(embed=discord.Embed(
            title=Emojis.SPARKLES + " Link Filter | Cooldown Record Cleared!",
            description=f"The cooldown record for {user.mention} has been cleared. There are now no warnings on this "
                        f"user's record.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="clearAll", brief="Clear all cooldown records for this filter.")
    @commands.has_permissions(administrator=True)
    async def clear_all_cooldowns(self, ctx: commands.Context):
        """
        Clear cooldown records for all users for this filter.

        This command will clear all cooldowns for the current filter, effectively resetting its internal state. No users
        will have any warnings for this filter after this command is executed.

        See also:
            /as <filter_name> clear - Clear cooldowns on a single filter for a single user.
            /as clear - Clear cooldowns on all filters for a single user.
            /as clearAll - Clear all cooldowns globally for all users (reset).
        """

        record_count = len(self._events)

        self.clear_all()
        LOG.info(f"{ctx.author} cleared {record_count} cooldown records from the link filter.")

        await ctx.send(embed=discord.Embed(
            title=Emojis.SPARKLES + " Link Filter | Cooldown Records Cleared!",
            description=f"All cooldown records for the link filter have been successfully cleared. No warnings "
                        f"currently exist in the system.",
            color=Colors.SUCCESS
        ))
