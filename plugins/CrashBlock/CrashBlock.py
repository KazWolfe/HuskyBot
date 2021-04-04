import logging

from discord.ext import commands

from HuskyBot import HuskyBot

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


class CrashBlock(commands.Cog):
    """
    Internal HuskyBot debugging toolkit.

    This plugin provides a number of internal debugging commands useful for development and low-level maintenance of
    the bot. This plugin (typically) should not be loaded on production Husky servers. However, certain functionality
    may be useful in certain use cases, so it is made available.

    The Debug plugin is automatically loaded in Developer Mode.
    """

    # ToDo: Add some stuff to test the database and redis, make sure it's working.

    def __init__(self, bot: HuskyBot):
        self.bot = bot

        raise NotImplementedError()