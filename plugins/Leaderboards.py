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
        processed_bans = []
        banned_uids = []

        # old : new
        lb_conf = self._config.get('leaderboard', {})
        user_map = lb_conf.get('userMap', {})

        def process_ban(banned_user_id: int, ban_reason: str, banning_user: discord.User = None):
            if banned_user_id in processed_bans:
                return

            if banned_user_id not in banned_uids:
                return

            if (ban_reason is None) or (ban_reason == ""):
                ban_reason = "<No ban reason provided>"

            if banning_user is None or banning_user == self.bot.user:
                if not re.match(r'\[.*By .*] .*', ban_reason):
                    responsible_user = "Unknown"

                    if ("AUTOMATIC BAN" in ban_reason) or ("AutoBan" in ban_reason):
                        responsible_user = "DakotaBot AutoBan"

                    ban_count = cache.setdefault(responsible_user, 0)
                    ban_count += 1
                    cache[responsible_user] = ban_count
                else:
                    responsible_user = ban_reason.split("By ", 1)[1].split("] ", 1)[0]

                    ban_count = cache.setdefault(responsible_user, 0)
                    ban_count += 1
                    cache[responsible_user] = ban_count
            elif banning_user is not None:
                ban_count = cache.setdefault(str(banning_user), 0)
                ban_count += 1
                cache[str(banning_user)] = ban_count

            processed_bans.append(banned_user_id)

        async with ctx.typing():
            banned_members = await ctx.guild.bans()
            banned_uids = [bo.user.id for bo in banned_members]

            async for entry in ctx.guild.audit_logs(action=discord.AuditLogAction.ban,
                                                    limit=None):  # type: discord.AuditLogEntry
                process_ban(entry.target.id, entry.reason, entry.user)

            for ban in banned_members:
                process_ban(ban.user.id, ban.reason)

            # process mappings
            new_cache = {}
            for user in cache.keys():
                mapped_user = user_map.get(user, user)

                new_cache[mapped_user] = new_cache.get(mapped_user, 0) + cache[user]

            cache = new_cache

            # out of ban loop now
            board = sorted(cache.items(), key=lambda x: x[1], reverse=True)[:10]

            lc = ""

            for record in board:
                lc += " - `{}` with **{} bans**\n".format(record[0], record[1])

            embed = discord.Embed(
                title="Top 10 Mods (By Bans)",
                description="The mods with the top bans are: \n{}".format(lc),
                color=Colors.INFO
            )

            embed.set_footer(text="Σ={} | listed={}".format(sum(cache.values()), len(banned_uids)))

            await ctx.send(embed=embed)

    @commands.command(name="lbmap", brief="Map one userstring to another")
    @commands.has_permissions(administrator=True)
    async def lbmap(self, ctx: commands.Context, map_from: str, map_to: str):
        lb_conf = self._config.get('leaderboard', {})
        user_map = lb_conf.get('userMap', {})

        if map_to.lower() == "none":
            del user_map[map_from]
        else:
            user_map[map_from] = map_to

        self._config.set('leaderboard', lb_conf)

        await ctx.send("Mapped `{}` -> `{}`".format(map_from, map_to))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Leaderboards(bot))
