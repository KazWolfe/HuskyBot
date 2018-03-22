import logging

import discord
import traceback

from datetime import datetime
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfUtils
from WolfBot.WolfStatics import Colors, ChannelKeys

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


class Fun:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()
        LOG.info("Loaded plugin!")


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Fun(bot))
