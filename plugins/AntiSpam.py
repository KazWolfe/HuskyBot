import datetime
import logging
import re

import discord
from discord.ext import commands
from discord.http import Route

from WolfBot import WolfConfig
from WolfBot import WolfUtils
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class AntiSpam:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()

        # Statics
        self.INVITE_COOLDOWNS = {}
        self.ATTACHMENT_COOLDOWNS = {}

        LOG.info("Loaded plugin!")

    async def on_message(self, message):
        if not WolfUtils.should_process_message(message):
            return

        # AS can't do anything in DMs, so just ignore em.
        if message.guild is None:
            return

        await self.multi_ping_check(message)
        await self.prevent_discord_invites(message)
        await self.attachment_cooldown(message)

    async def multi_ping_check(self, message):
        PING_WARN_LIMIT = self._config.get('antiSpam', {}).get('pingSoftLimit', 6)
        PING_BAN_LIMIT = self._config.get('antiSpam', {}).get('pingHardLimit', 15)

        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is not None:
            log_channel = message.guild.get_channel(log_channel)

        if message.author.permissions_in(message.channel).mention_everyone:
            return

        if PING_WARN_LIMIT is not None and len(message.mentions) >= PING_WARN_LIMIT:
            await message.delete()
            # ToDo: Issue actual warning through Punishment (once made available)
            await message.channel.send(embed=discord.Embed(
                title="Mass Ping Blocked",
                description="A mass-ping message was blocked in the current channel.\n"
                            + "Please reduce the number of pings in your message and try again.",
                color=Colors.WARNING
            ))

            if log_channel is not None:
                await log_channel.send(embed=discord.Embed(
                    description="User {} has pinged {} users in a single in channel {}."
                        .format(message.author, str(len(message.mentions)), message.channel),
                    color=Colors.WARNING
                ).set_author(name="Mass Ping Alert", icon_url=message.author.avatar_url))
                return

        if PING_BAN_LIMIT is not None and len(message.mentions) >= PING_BAN_LIMIT:
            await message.author.ban(delete_message_days=0, reason="[AUTOMATIC BAN - AntiSpam Module] "
                                                                   "Multi-pinged over guild ban limit.")

    async def prevent_discord_invites(self, message):
        ANTISPAM_CONFIG = self._config.get('antiSpam', {})

        ALLOWED_INVITES = ANTISPAM_CONFIG.get('allowedInvites', [message.guild.id])
        COOLDOWN_SETTINGS = ANTISPAM_CONFIG.get('cooldowns', {}).get('invites', {'minutes': 30, 'banLimit': 5})

        # Prepare the logger
        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is not None:
            log_channel = message.guild.get_channel(log_channel)

        # Prevent memory abuse by deleting expired cooldown records
        if message.author.id in self.INVITE_COOLDOWNS \
                and self.INVITE_COOLDOWNS[message.author.id]['cooldownExpiry'] < datetime.datetime.utcnow():
            del self.INVITE_COOLDOWNS[message.author.id]

        # Users with MANAGE_MESSAGES are allowed to send unauthorized invites.
        if message.author.permissions_in(message.channel).manage_messages:
            return

        regex_matches = re.findall('discord\.gg/[0-9a-z\-]+', message.content, flags=re.IGNORECASE)

        # Handle messages without any invites in them (by ignoring them)
        if regex_matches is None or regex_matches == []:
            return

        for regex_match in regex_matches:
            fragment = regex_match.split('/', maxsplit=1)[1]

            # Attempt to validate the invite, deleting invalid ones
            try:
                # discordpy doesn't let us do this natively, so let's do it ourselves!
                invite_data = await self.bot.http.request(
                    Route('GET', '/invite/{invite_id}?with_counts=true', invite_id=fragment))
                invite_guild = discord.Guild(state=self.bot, data=invite_data['guild'])
            except discord.errors.NotFound:
                await message.delete()

                invalid_embed = discord.Embed(
                    description="An invalid invite with key `{}` by user {} (ID `{}`) was caught and filtered."
                        .format(fragment, str(message.author), str(message.author.id)),
                    color=Colors.INFO
                )
                invalid_embed.set_author(name="Invite from {} intercepted in {}!"
                                         .format(str(message.author), "#" + str(message.channel)),
                                         icon_url=message.author.avatar_url)

                await log_channel.send(embed=invalid_embed)
                break

            # This guild is allowed to have invites on our guild, so we can ignore them.
            if invite_guild.id in ALLOWED_INVITES:
                continue

            # If we reached here, we have an invite from a non-whitelisted guild. Delete it.
            await message.delete()

            # Add the user to the cooldowns table - we're going to use this to prevent DIYBot's spam and to ban the user
            # if they go over a defined number of invites in a period
            if message.author.id not in self.INVITE_COOLDOWNS.keys():
                self.INVITE_COOLDOWNS[message.author.id] = {
                    'cooldownExpiry': datetime.datetime.utcnow() + datetime.timedelta(
                        minutes=COOLDOWN_SETTINGS['minutes']),
                    'offenseCount': 0
                }

                # We're also going to be nice and inform the user on their *first offense only*. The message will
                # self-destruct after 90 seconds.
                await message.channel.send(embed=discord.Embed(
                    title="Discord Invite Blocked",
                    description="Hey {}! It looks like you posted a Discord invite.\n\n"
                                "Here on DIY Tech, we have a strict no-invites policy in order to prevent spam and "
                                "advertisements. If you would like to post an invite, you may contact the admins to "
                                "request an invite code be whitelisted.\n\n"
                                "We apologize for the inconvenience.".format(message.author.mention),
                    color=Colors.WARNING
                ), delete_after=90.0)

            cooldownRecord = self.INVITE_COOLDOWNS[message.author.id]

            # And we increment the offense counter here.
            cooldownRecord['offenseCount'] += 1

            if log_channel is not None:
                # We've a valid invite, so let's log that with invite data.
                log_embed = discord.Embed(
                    description="An invite with key `{}` by user {} (ID `{}`) was caught and filtered. Invite "
                                "information below.".format(fragment, str(message.author), str(message.author.id)),
                    color=Colors.INFO
                )
                log_embed.set_author(name="Invite from {} intercepted!".format(str(message.author)),
                                     icon_url=message.author.avatar_url)

                log_embed.add_field(name="Invited Guild Name", value=invite_guild.name, inline=True)

                ch_type = {0: "#", 2: "[VC] ", 4: "[CAT] "}
                log_embed.add_field(name="Invited Channel Name", value=ch_type[invite_data['channel']['type']]
                                                                       + invite_data['channel']['name'], inline=True)
                log_embed.add_field(name="Invited Guild ID", value=invite_guild.id, inline=True)

                log_embed.add_field(name="Invited Guild Creation Date",
                                    value=invite_guild.created_at.strftime(DATETIME_FORMAT),
                                    inline=True)

                if invite_data.get('approximate_member_count', -1) != -1:
                    log_embed.add_field(name="Invited Guild User Count",
                                        value="{} ({} online)".format(invite_data.get('approximate_member_count', -1),
                                                                      invite_data.get('approximate_presence_count',
                                                                                      -1)))

                log_embed.set_footer(text="Strike {} of {}, resets {}"
                                     .format(cooldownRecord['offenseCount'],
                                             COOLDOWN_SETTINGS['banLimit'],
                                             cooldownRecord['cooldownExpiry'].strftime(DATETIME_FORMAT)))

                log_embed.set_thumbnail(url=invite_guild.icon_url)

                await log_channel.send(embed=log_embed)

            # If the user is at the offense limit, we're going to ban their ass. In this case, this means that on
            # their fifth invalid invite, we ban 'em.
            if cooldownRecord['offenseCount'] >= COOLDOWN_SETTINGS['banLimit']:
                await message.author.ban(reason="[AUTOMATIC BAN - AntiSpam Module] User sent {} unauthorized invites "
                                                "in a {} minute period.".format(COOLDOWN_SETTINGS['banLimit'],
                                                                                COOLDOWN_SETTINGS['minutes']),
                                         delete_message_days=0)
                del self.INVITE_COOLDOWNS[message.author.id]

            break

    async def attachment_cooldown(self, message: discord.Message):
        ANTISPAM_CONFIG = self._config.get('antiSpam', {})
        COOLDOWN_CONFIG = ANTISPAM_CONFIG.get('cooldowns', {}).get('attach', {'seconds': 15,
                                                                              'warnLimit': 3,
                                                                              'banLimit': 5})

        # Prepare the logger
        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is not None:
            log_channel = message.guild.get_channel(log_channel)

        # Clear
        if message.author.id in self.ATTACHMENT_COOLDOWNS \
                and self.ATTACHMENT_COOLDOWNS[message.author.id]['cooldownExpiry'] < datetime.datetime.utcnow():
            del self.ATTACHMENT_COOLDOWNS[message.author.id]

        # Users with MANAGE_MESSAGES are allowed to bypass attachment rate limits.
        if message.author.permissions_in(message.channel).manage_messages:
            return

        if len(message.attachments) > 0:
            # User posted an attachment, and is not in the cache. Let's add them, on strike 0.
            if message.author.id not in self.ATTACHMENT_COOLDOWNS.keys():
                self.ATTACHMENT_COOLDOWNS[message.author.id] = {
                    'cooldownExpiry': datetime.datetime.utcnow() + datetime.timedelta(
                        seconds=COOLDOWN_CONFIG['seconds']),
                    'offenseCount': 0
                }

            cooldownRecord = self.ATTACHMENT_COOLDOWNS[message.author.id]

            # And we increment the offense counter here.
            cooldownRecord['offenseCount'] += 1

            # Give them a fair warning on attachment #3
            if COOLDOWN_CONFIG['warnLimit'] != 0 and cooldownRecord['offenseCount'] == COOLDOWN_CONFIG['warnLimit']:
                await message.channel.send(embed=discord.Embed(
                    title="\uD83D\uDED1 Whoa there, pardner!",
                    description="Hey there {}! You're sending files awfully fast. Please help us keep this chat clean "
                                "and readable by not sending lots of files so quickly. Thanks!"
                        .format(message.author.mention),
                    color=Colors.WARNING
                ), delete_after=90.0)
                if log_channel is not None:
                    await log_channel.send(embed=discord.Embed(
                        description="User {} has sent {} attachments in a {}-second period in channel {}."
                            .format(message.author, cooldownRecord['offenseCount'], COOLDOWN_CONFIG['seconds'],
                                    message.channel),
                        color=Colors.WARNING
                    ).set_author(name="Possible Attachment Spam", icon_url=message.author.avatar_url))
                    return

            # And ban their sorry ass at #5.
            if cooldownRecord['offenseCount'] >= COOLDOWN_CONFIG['banLimit']:
                await message.author.ban(reason="[AUTOMATIC BAN - AntiSpam Module] User sent {} attachments in a {} "
                                                "second period.".format(cooldownRecord['offenseCount'],
                                                                        COOLDOWN_CONFIG['banLimit']),
                                         delete_message_days=1)
                del self.ATTACHMENT_COOLDOWNS[message.author.id]

        else:
            # They sent a message containing text. Clear their cooldown.
            if message.author.id in self.ATTACHMENT_COOLDOWNS:
                LOG.info("User {} previously on file cooldown warning list has sent a file-less message. Deleting "
                         "cooldown entry.".format(message.author))
                del self.ATTACHMENT_COOLDOWNS[message.author.id]

    @commands.group(name="antispam", aliases=['as'], brief="Manage the Antispam configuration for the bot")
    @commands.has_permissions(manage_messages=True)
    async def asp(self, ctx: commands.Context):
        pass

    @asp.command(name="setPingWarnLimit", brief="Set the number of pings required before delete/warn")
    @commands.has_permissions(mention_everyone=True)
    async def set_ping_warn_limit(self, ctx: commands.Context, new_limit: int):
        if new_limit < 1:
            new_limit = None

        as_config = self._config.get('antiSpam', {})
        as_config['pingSoftLimit'] = new_limit
        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description="The warning limit for pings has been set to " + str(new_limit) + ".",
            color=Colors.SUCCESS
        ))

    @asp.command(name="setPingBanLimit", brief="Set the number of pings required before user ban")
    @commands.has_permissions(mention_everyone=True)
    async def set_ping_ban_limit(self, ctx: commands.Context, new_limit: int):
        if new_limit < 1:
            new_limit = None

        as_config = self._config.get('antiSpam', {})
        as_config['pingHardLimit'] = new_limit
        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description="The ban limit for pings has been set to " + str(new_limit) + ".",
            color=Colors.SUCCESS
        ))

    @asp.command(name="allowInvite", brief="Allow an invite from the guild ID given")
    @commands.has_permissions(manage_guild=True)
    async def allow_invite(self, ctx: commands.Context, guild: int):
        as_config = self._config.get('antiSpam', {})
        allowed_invites = as_config.setdefault('allowedInvites', [ctx.guild.id])

        if guild in allowed_invites:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Plugin",
                description="The guild with ID `{}` is already whitelisted!".format(guild),
                color=Colors.WARNING
            ))
            return

        allowed_invites.append(guild)
        self._config.set("antiSpam", as_config)
        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description="The invite to guild `{}` has been added to the whitelist."
                .format(guild),
            color=Colors.SUCCESS
        ))
        return

    @asp.command(name="blockInvite", brief="Remove an invite from the whitelist.")
    @commands.has_permissions(manage_guild=True)
    async def block_invite(self, ctx: commands.Context, guild: int):
        as_config = self._config.get('antiSpam', {})
        allowed_invites = as_config.setdefault('allowedInvites', [ctx.guild.id])

        if guild == ctx.guild.id:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Plugin",
                description="This guild may not be removed from the whitelist!".format(guild),
                color=Colors.WARNING
            ))
            return

        if guild not in allowed_invites:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Plugin",
                description="The guild `{}` is not whitelisted!".format(guild),
                color=Colors.WARNING
            ))
            return

        allowed_invites.pop(guild)
        self._config.set("antiSpam", as_config)
        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description="The guild with ID `{}` has been removed from the whitelist."
                .format(guild),
            color=Colors.SUCCESS
        ))

    @asp.command(name="inviteCooldown", brief="Set invite cooldown and ban limits")
    @commands.has_permissions(manage_guild=True)
    async def set_invite_cooldown(self, ctx: commands.Context, cooldown_minutes: int, ban_limit: int):
        as_config = self._config.get('antiSpam', {})
        invite_cooldown = as_config.setdefault('cooldowns', {}).setdefault('invites', {'minutes': 30, 'banLimit': 5})

        invite_cooldown['minutes'] = cooldown_minutes
        invite_cooldown['banLimit'] = ban_limit

        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description="The invite module of AntiSpam has been set to allow a max of **`{}`** unauthorized invites "
                        "in a **`{}` minute** period.".format(ban_limit, cooldown_minutes),
            color=Colors.SUCCESS
        ))

    @asp.command(name="attachmentCooldown", brief="Set attachment cooldown and ban limits")
    @commands.has_permissions(manage_guild=True)
    async def set_attach_cooldown(self, ctx: commands.Context, cooldown_seconds: int, warn_limit: int, ban_limit: int):
        as_config = self._config.get('antiSpam', {})
        attach_config = as_config.setdefault('cooldowns', {}).setdefault('attach', {'seconds': 15,
                                                                                    'warnLimit': 3, 'banLimit': 5})

        attach_config['seconds'] = cooldown_seconds
        attach_config['warnLimit'] = warn_limit
        attach_config['banLimit'] = ban_limit

        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description="The attachments module of AntiSpam has been set to allow a max of **`{}`** attachments in a "
                        "**`{}` second** period, warning after **`{}`** attachments"
                .format(ban_limit, cooldown_seconds, warn_limit),
            color=Colors.SUCCESS
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(AntiSpam(bot))
