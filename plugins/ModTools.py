import logging

import discord
from discord.ext import commands

from BotCore import BOT_CONFIG
from WolfBot.WolfEmbed import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)

# PUNISHMENTS = sqlite3.connect("config/punishments.db")


# noinspection PyMethodMayBeStatic
class ModTools:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
#       self.pCursor = PUNISHMENTS.cursor()

    # Prevent users from becoming bot role if they're not actually bots.
    async def on_member_update(self, before, after):
        if before.roles == after.roles:
            return

        special_roles = BOT_CONFIG.get("specialRoles", {})

        if special_roles.get('bots') is None:
            return

        bot_role = discord.utils.get(after.roles, id=int(special_roles.get('bots')))

        if (bot_role is not None) and (bot_role not in before.roles) and (not before.bot):
            await after.remove_roles(bot_role, reason="User is not an authorized bot.")
            LOG.info("User " + after.display_name + " was granted bot role, but was not a bot. Removing.")

    # AutoBan support
    async def on_member_join(self, member):
        autobans = BOT_CONFIG.get("autobans", [])

        if member.id in autobans:
            await member.ban(reason="User was on autoban list.")
            autobans.remove(member.id)
            BOT_CONFIG.set("autobans", autobans)

    @commands.command(name="autoban", aliases=["hackban"], brief="Ban a non-member online (preemptive)")
    @commands.has_permissions(ban_members=True)
    async def autoban(self, ctx: discord.ext.commands.Context, target: int):
        autobans = BOT_CONFIG.get("autobans", [])

        if target in autobans:
            await ctx.send(embed=discord.Embed(
                title="Autoban Command Error",
                description="Could not autoban user `" + str(target) + "` as they are already autobanned.",
                color=Colors.DANGER
            ))
            return

        autobans.append(target)
        BOT_CONFIG.set("autobans", autobans)
        await ctx.send(embed=discord.Embed(
            title="Autoban Utility",
            description="User `" + str(target) + "` was successfully autobanned.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="autopardon", aliases=["hackpardon"], brief="Pardon a member on the autoban list.")
    @commands.has_permissions(ban_members=True)
    async def autopardon(self, ctx: discord.ext.commands.Context, target: int):
        autobans = BOT_CONFIG.get("autobans", [])

        if target not in autobans:
            await ctx.send(embed=discord.Embed(
                title="Autoban Command Error",
                description="Could not pardon user `" + str(target) + "` as they are not autobanned.",
                color=Colors.DANGER
            ))
            return

        autobans.remove(target)
        BOT_CONFIG.set("autobans", autobans)
        await ctx.send(embed=discord.Embed(
            title="Autoban Utility",
            description="User `" + str(target) + "` was successfully pardoned.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="warn", brief="Issue an official warning to a user.", disabled=True)
    @commands.has_permissions(ban_members=True)
    async def warn(self, ctx: discord.ext.commands.Context, target: discord.Member, *, reason: str):
        pass

    @commands.command(name="mute", brief="Temporarily mute a user from the current channel", disabled=True)
    @commands.has_permissions(manage_messages=True)
    async def mute(self, ctx: discord.ext.commands.Context, target: discord.Member, time: str=None, * reason: str):
        pass

    @commands.command(name="globalmute", aliases=["gmute"],
                      brief="Temporarily mute a user from the server", disabled=True)
    @commands.has_permissions(ban_members=True)
    async def globalmute(self, ctx: discord.ext.commands.Context, target: discord.Member, time: str=None, *,
                         reason: str):
        pass


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(ModTools(bot))
    LOG.info("Loaded plugin!")
