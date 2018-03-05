import logging

import discord
from discord.ext import commands

LOG = logging.getLogger("DiyBot.Plugin." + __name__)

class ServerLog:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot

    async def on_member_ban(self, guild, user):
        pass


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(ServerLog(bot))
    LOG.info("Loaded plugin!")