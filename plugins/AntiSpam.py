import logging
import re
import datetime

import discord
from discord.ext import commands

from WolfBot import WolfUtils
from WolfBot import WolfConfig
from WolfBot.WolfStatics import Colors, ChannelKeys

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class AntiSpam:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()

        # Statics
        self.INVITE_COOLDOWNS = {}

        LOG.info("Loaded plugin!")

    async def on_message(self, message):
        if not WolfUtils.should_process_message(message):
            return

        await self.multi_ping_check(message)
        await self.prevent_discord_invites(message)

    async def multi_ping_check(self, message):
        PING_WARN_LIMIT = self._config.get('antiSpam', {}).get('pingSoftLimit', 6)
        PING_BAN_LIMIT = self._config.get('antiSpam', {}).get('pingHardLimit', 15)

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

        if PING_BAN_LIMIT is not None and len(message.mentions) >= PING_BAN_LIMIT:
            await message.author.ban(delete_message_days=0, reason="[AUTOMATIC BAN - AntiSpam Module] "
                                                                   "Multi-pinged over server ban limit.")
            # ToDo: Integrate with ServerLog to send custom ban message to staff logs.

    async def prevent_discord_invites(self, message):
        ALLOWED_INVITES = self._config.get('antiSpam', {}).get('allowedInvites', [message.guild.id])

        # Prepare the logger
        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is None:
            return
        log_channel = message.guild.get_channel(log_channel)

        # Prevent memory abuse by deleting expired cooldown records
        if message.author.id in self.INVITE_COOLDOWNS \
                and self.INVITE_COOLDOWNS[message.author.id]['cooldownExpiry'] < datetime.datetime.now():
            del self.INVITE_COOLDOWNS[message.author.id]

        # Users with MANAGE_MESSAGES are allowed to send unauthorized invites.
        if message.author.permissions_in(message.channel).manage_messages:
            return

        regex_matches = re.findall('discord\.gg/.+', message.content, flags=re.IGNORECASE)

        # Handle messages without any invites in them (by ignoring them)
        if regex_matches is None or regex_matches == []:
            return

        for regex_match in regex_matches:
            fragment = re.split("discord\.gg/", regex_match, flags=re.IGNORECASE)[1]

            # Attempt to validate the invite, deleting invalid ones
            try:
                invite_data = await self.bot.get_invite("https://discord.gg/{}".format(fragment))
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

            # This guild is allowed to have invites on this server, so we can ignore them.
            if invite_data.guild.id in ALLOWED_INVITES:
                continue

            # We have an invite from a non-whitelisted server. Delete it.
            await message.delete()

            # Add the user to the cooldowns table - we're going to use this to prevent DIYBot's spam and to ban the user
            # if they go over 5 deleted invites in a 30 minute period.
            if message.author.id not in self.INVITE_COOLDOWNS.keys():
                self.INVITE_COOLDOWNS[message.author.id] = {
                    'cooldownExpiry': datetime.datetime.now() + datetime.timedelta(minutes=30),
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

            # We've a valid invite, so let's log that with invite data.
            invite_embed = discord.Embed(
                description="An invite with key `{}` by user {} (ID `{}`) was caught and filtered. Invite information "
                            "below.".format(fragment, str(message.author), str(message.author.id)),
                color=Colors.INFO
            )
            invite_embed.set_author(name="Invite from {} intercepted!".format(str(message.author)),
                                    icon_url=message.author.avatar_url)

            invite_embed.add_field(name="Invited Guild Name", value=invite_data.guild.name, inline=True)
            invite_embed.add_field(name="Invited Channel Name", value="#" + invite_data.channel.name, inline=True)
            invite_embed.add_field(name="Invited Guild ID", value=invite_data.guild.id, inline=True)

            invite_embed.add_field(name="Invited Guild Creation Date",
                                   value=str(invite_data.guild.created_at).split('.')[0],
                                   inline=True)

            invite_embed.set_footer(text="Strike {} of 5, resets {}"
                                    .format(cooldownRecord['offenseCount'],
                                            str(cooldownRecord['cooldownExpiry']).split('.')[0]))

            await log_channel.send(embed=invite_embed)

            # If the user is over the offense limit, we're going to ban their ass. In this case, this means that on
            # their sixth invalid invite, we ban 'em.
            if cooldownRecord['offenseCount'] > 5:
                await message.author.ban(reason="[AUTOMATIC BAN - AntiSpam Module] User sent over 5 unauthorized "
                                                "invites in a 30 minute period.", delete_message_days=0)
                del self.INVITE_COOLDOWNS[message.author.id]

            break

    @commands.group(name="antispam", aliases=['as'], brief="Manage the Antispam configuration for the bot")
    @commands.has_permissions(manage_messages=True)
    async def asp(self, ctx: commands.Context):
        pass

    @asp.command(name="setPingWarnLimit", brief="Set the number of pings required before delete/warn")
    @commands.has_permissions(mention_everyone=True)
    async def setWarnLimit(self, ctx: commands.Context, new_limit: int):
        if new_limit < 1:
            new_limit = None

        as_config = self._config.get('antiSpam', {})
        as_config['pingSoftLimit'] = new_limit
        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Module",
            description="The warning limit for pings has been set to " + str(new_limit) + ".",
            color=Colors.SUCCESS
        ))

    @asp.command(name="setPingBanLimit", brief="Set the number of pings required before user ban")
    @commands.has_permissions(mention_everyone=True)
    async def setBanLimit(self, ctx: commands.Context, new_limit: int):
        if new_limit < 1:
            new_limit = None

        as_config = self._config.get('antiSpam', {})
        as_config['pingHardLimit'] = new_limit
        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Module",
            description="The ban limit for pings has been set to " + str(new_limit) + ".",
            color=Colors.SUCCESS
        ))

    @asp.command(name="allowInvite", brief="Allow an invite from the server ID given")
    @commands.has_permissions(manage_guild=True)
    async def allow_invite(self, ctx: commands.Context, guild: int):
        as_config = self._config.get('antiSpam', {})
        allowed_invites = as_config.setdefault('allowedInvites', [ctx.guild.id])

        if guild in allowed_invites:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Module",
                description="The guild with ID `{}` is already whitelisted!".format(guild),
                color=Colors.WARNING
            ))
            return

        allowed_invites.append(guild)
        self._config.set("antiSpam", as_config)
        await ctx.send(embed=discord.Embed(
            title="AntiSpam Module",
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
                title="AntiSpam Module",
                description="This guild may not be removed from the whitelist!".format(guild),
                color=Colors.WARNING
            ))
            return

        if guild not in allowed_invites:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Module",
                description="The guild `{}` is not whitelisted!".format(guild),
                color=Colors.WARNING
            ))
            return

        allowed_invites.pop(guild)
        self._config.set("antiSpam", as_config)
        await ctx.send(embed=discord.Embed(
            title="AntiSpam Module",
            description="The guild with ID `{}` has been removed from the whitelist."
                .format(guild),
            color=Colors.SUCCESS
        ))
        return


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(AntiSpam(bot))
