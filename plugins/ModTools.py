import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot.WolfEmbed import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class ModTools:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        LOG.info("Loaded plugin!")

    # Prevent users from becoming bot role if they're not actually bots.
    async def on_member_update(self, before, after):
        if before.roles == after.roles:
            return

        special_roles = WolfConfig.getConfig().get("specialRoles", {})

        if special_roles.get('bots') is None:
            return

        bot_role = discord.utils.get(after.roles, id=int(special_roles.get('bots')))

        if (bot_role is not None) and (bot_role not in before.roles) and (not before.bot):
            await after.remove_roles(bot_role, reason="User is not an authorized bot.")
            LOG.info("User " + after.display_name + " was granted bot role, but was not a bot. Removing.")

    # AutoBan support
    async def on_member_join(self, member):
        autobans = WolfConfig.getConfig().get("autobans", [])

        if member.id in autobans:
            await member.ban(reason="User was on autoban list.")
            autobans.remove(member.id)
            WolfConfig.getConfig().set("autobans", autobans)

    @commands.command(name="autoban", aliases=["hackban"], brief="Ban a non-member online (preemptive)")
    @commands.has_permissions(ban_members=True)
    async def autoban(self, ctx: discord.ext.commands.Context, target: int):
        autobans = WolfConfig.getConfig().get("autobans", [])

        if target in autobans:
            await ctx.send(embed=discord.Embed(
                title="Autoban Command Error",
                description="Could not autoban user `" + str(target) + "` as they are already autobanned.",
                color=Colors.DANGER
            ))
            return

        autobans.append(target)
        WolfConfig.getConfig().set("autobans", autobans)
        await ctx.send(embed=discord.Embed(
            title="Autoban Utility",
            description="User `" + str(target) + "` was successfully autobanned.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="autopardon", aliases=["hackpardon"], brief="Pardon a member on the autoban list.")
    @commands.has_permissions(ban_members=True)
    async def autopardon(self, ctx: discord.ext.commands.Context, target: int):
        autobans = WolfConfig.getConfig().get("autobans", [])

        if target not in autobans:
            await ctx.send(embed=discord.Embed(
                title="Autoban Command Error",
                description="Could not pardon user `" + str(target) + "` as they are not autobanned.",
                color=Colors.DANGER
            ))
            return

        autobans.remove(target)
        WolfConfig.getConfig().set("autobans", autobans)
        await ctx.send(embed=discord.Embed(
            title="Autoban Utility",
            description="User `" + str(target) + "` was successfully pardoned.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="warn", brief="Issue an official warning to a user.", enabled=False)
    @commands.has_permissions(ban_members=True)
    async def warn(self, ctx: discord.ext.commands.Context, target: discord.Member, *, reason: str):
        pass

    @commands.command(name="mute", brief="Temporarily mute a user from the current channel", enabled=False)
    @commands.has_permissions(manage_messages=True)
    async def mute(self, ctx: discord.ext.commands.Context, target: discord.Member, time: str = None, *, reason: str):
        pass

    @commands.command(name="globalmute", aliases=["gmute"],
                      brief="Temporarily mute a user from the server", enabled=False)
    @commands.has_permissions(ban_members=True)
    async def globalmute(self, ctx: discord.ext.commands.Context, target: discord.Member, time: str = None, *,
                         reason: str):
        pass

    @commands.command(name="roleping", brief="Ping all users with a certain role")
    @commands.has_permissions(manage_roles=True)
    async def roleping(self, ctx: commands.Context, target: discord.Role, *, message: str):
        is_role_mentionable = target.mentionable

        if not is_role_mentionable:
            await target.edit(reason="Role Ping requested by " + str(ctx.message.author), mentionable=True)

        await ctx.send(target.mention + " <" + ctx.message.author.display_name + "> " + message)

        if not is_role_mentionable:
            await target.edit(reason="Role Ping requested by " + str(ctx.message.author)
                                     + " completed", mentionable=False)


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(ModTools(bot))
