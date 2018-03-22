import logging
import re

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
            await message.author.ban(delete_message_days=1, reason="[AUTOMATIC BAN - AntiSpam Module] "
                                                                   "Multi-pinged over server ban limit.")
            # ToDo: Integrate with ServerLog to send custom ban message to staff logs.

    async def prevent_discord_invites(self, message):
        ALLOWED_INVITES = self._config.get('antiSpam', {}).get('allowedInvites', ['diytech'])

        regex_matches = re.findall('discord\.gg/\w+', message.content, flags=re.IGNORECASE)

        if message.author.permissions_in(message.channel).manage_messages:
            return

        if regex_matches is None or regex_matches == []:
            # No invite links detected. Move on.
            return

        for regex_match in regex_matches:
            fragment = re.split("discord\.gg/", regex_match, flags=re.IGNORECASE)[1]

            if fragment in ALLOWED_INVITES:
                # Permitted fragment
                continue

            await message.delete()
            await message.channel.send(embed=discord.Embed(
                title="Discord Invite Blocked",
                description="Hey! It looks like you posted a Discord invite.\n\n"
                            "Here on DIY Tech, we have a strict no-invites policy in order to prevent spam and "
                            "advertisements. If you would like to post an invite, you may contact the admins to "
                            "request an invite code be whitelisted.\n\n"
                            "We apologize for the inconvenience.",
                color=Colors.WARNING
            ), delete_after=30.0)

            # Send a message to the server log, too
            log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
            if log_channel is None:
                return
            log_channel = message.guild.get_channel(log_channel)

            try:
                invite_data = await self.bot.get_invite("https://discord.gg/{}".format(fragment))
            except discord.errors.NotFound:
                invalid_embed = discord.Embed(
                    description="An invalid invite with key `{}` by user {} (ID `{}`) was caught and filtered."
                                .format(fragment, str(message.author), str(message.author.id)),
                    color=Colors.INFO
                )
                invalid_embed.set_author(name="Invite from {} intercepted!".format(str(message.author)),
                                         icon_url=message.author.avatar_url)

                await log_channel.send(embed=invalid_embed)
                break

            invite_embed = discord.Embed(
                description="An invite with key `{}` by user {} (ID `{}`) was caught and filtered. Invite information "
                            "below.".format(fragment, str(message.author), str(message.author.id)),
                color=Colors.INFO
            )
            invite_embed.set_author(name="Invite from {} intercepted!".format(str(message.author)),
                                    icon_url=message.author.avatar_url)
            invite_embed.add_field(name="Guild Name", value=invite_data.guild.name, inline=True)
            invite_embed.add_field(name="Channel Name", value="#" + invite_data.channel.name, inline=True)
            invite_embed.add_field(name="Guild ID", value=invite_data.guild.id, inline=True)
            invite_embed.add_field(name="Guild Creation Date", value=str(invite_data.guild.created_at).split('.')[0],
                                   inline=True)

            await log_channel.send(embed=invite_embed)
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

    @asp.command(name="allowInvite", brief="Allow a specific invite slug (case sensitive!)")
    @commands.has_permissions(manage_guild=True)
    async def allow_invite(self, ctx: commands.Context, fragment: str):
        as_config = self._config.get('antiSpam', {})
        allowed_invites = as_config.setdefault('allowedInvites', ['diytech'])

        try:
            invite_data = await self.bot.get_invite("https://discord.gg/{}".format(fragment))
        except discord.errors.NotFound:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Module",
                description="The invite with fragment `{}` is invalid!".format(fragment),
                color=Colors.ERROR
            ))
            return

        if fragment in allowed_invites:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Module",
                description="The invite with fragment `{}` is already whitelisted!".format(fragment),
                color=Colors.WARNING
            ))
            return

        allowed_invites.append(fragment)
        self._config.set("antiSpam", as_config)
        await ctx.send(embed=discord.Embed(
            title="AntiSpam Module",
            description="The invite to **{}** with fragment `{}` has been added to the whitelist."
                        .format(invite_data.guild.name, fragment),
            color=Colors.SUCCESS
        ))
        return

    @asp.command(name="blockInvite", brief="Remove an invite from the whitelist.")
    @commands.has_permissions(manage_guild=True)
    async def block_invite(self, ctx: commands.Context, fragment: str):
        as_config = self._config.get('antiSpam', {})
        allowed_invites = as_config.setdefault('allowedInvites', ['diytech'])

        try:
            invite_data = await self.bot.get_invite("https://discord.gg/{}".format(fragment))
        except discord.errors.NotFound:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Module",
                description="The invite with fragment `{}` is invalid!".format(fragment),
                color=Colors.ERROR
            ))
            return

        if fragment not in allowed_invites:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Module",
                description="The invite with fragment `{}` is not whitelisted!".format(fragment),
                color=Colors.WARNING
            ))
            return

        allowed_invites.pop(fragment)
        self._config.set("antiSpam", as_config)
        await ctx.send(embed=discord.Embed(
            title="AntiSpam Module",
            description="The invite to **{}** with fragment `{}` has been removed from the whitelist."
                        .format(invite_data.guild.name, fragment),
            color=Colors.SUCCESS
        ))
        return


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(AntiSpam(bot))
