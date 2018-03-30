import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Giveaway:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()
        self._session_store = WolfConfig.getSessionStore()
        LOG.info("Loaded plugin!")


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Giveaway(bot))
