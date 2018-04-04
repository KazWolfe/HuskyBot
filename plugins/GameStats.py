import logging
import re

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


class GameStats:
    """
    Query various game services for statistics.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()
        LOG.info("Loaded plugin!")

    @commands.command(name="summonerstats", brief="Get Leagoue of Legends stats for a Summoner")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def summoner_stats(self, ctx: commands.Context, summoner: str):
        if not re.match(r'^[0-9\p{L} _.]+$', summoner):
            await ctx.send(embed=discord.Embed(
                title="Invalid Summoner Name!",
                description="The summoner name you have entered appears to be invalid.",
                color=Colors.DANGER
            ))
            return


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(GameStats(bot))
