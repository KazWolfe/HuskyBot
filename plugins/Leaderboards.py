import logging

from discord.ext import commands

from HuskyBot import HuskyBot

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Leaderboards(commands.Cog):
    def __init__(self):
        raise Exception("Module borked. DISABLE ME.")


def setup(bot: HuskyBot):
    bot.add_cog(Leaderboards())
