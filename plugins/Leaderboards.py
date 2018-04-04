import logging
import re

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Leaderboards:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()
        self._session_store = WolfConfig.get_session_store()

        LOG.info("Loaded plugin!")

    @commands.group(name="leaderboards", brief="Get leaderboards for various server stats", aliases=['lb'])
    async def leaderboard(self, ctx: commands.Context):
        pass

    @leaderboard.command(name="bans", brief="Get banningest moderators")
    @commands.has_permissions(ban_members=True)
    async def ban_leaderboard(self, ctx: commands.Context):
        # "username": banCount
        cache = {}

        async with ctx.typing():
            banned_members = [bo.user.id for bo in await ctx.guild.bans()]

            async for entry in ctx.guild.audit_logs(action=discord.AuditLogAction.ban,
                                                    limit=None):  # type: discord.AuditLogEntry
                banned_user = entry.target  # discord.User

                # Only count users still banned.
                if banned_user.id not in banned_members:
                    continue

                if entry.user != self.bot.user:
                    bans = cache.setdefault(str(entry.user), 0)
                    bans += 1
                    cache[str(entry.user)] = bans
                else:
                    reason = entry.reason  # type: str

                    if not re.match(r'\[.*By .*] .*', reason):
                        username = "Unknown"

                        if ("AUTOMATIC BAN" in reason) or ("AutoBan" in reason):
                            username = "DakotaBot AutoBan"

                        bans = cache.setdefault(username, 0)
                        bans += 1
                        cache[username] = bans
                    else:
                        ruser = reason.split("By ", 1)[1].split("] ", 1)[0]

                        bans = cache.setdefault(ruser, 0)
                        bans += 1
                        cache[ruser] = bans

            # out of ban loop now
            cache = sorted(cache.items(), key=lambda x: x[1], reverse=True)[:10]

            lc = ""

            for record in cache:
                lc += " - `{}` with **{} bans**\n".format(record[0], record[1])

            embed = discord.Embed(
                title="Top 10 Mods (By Bans)",
                description="The mods with the top bans are: \n{}".format(lc),
                color=Colors.INFO
            )

            await ctx.send(embed=embed)


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Leaderboards(bot))
