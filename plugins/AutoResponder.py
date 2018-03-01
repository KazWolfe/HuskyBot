import discord
from discord.ext import commands

from BotCore import BOT_CONFIG
from BotCore import LOCAL_STORAGE

from WolfBot import WolfUtils
from WolfBot.WolfEmbed import Colors
import logging

import git
import os

LOG = logging.getLogger("DiyBot.Plugin." + __name__)

class AutoResponder:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot

    async def on_ready(self):
        LOG.info("Enabled plugin!")
        
#   responses: {
#       "someString": {
#           "requiredRoles": [],             // Any on the list, *or* MANAGE_MESSAGES
#           "allowedChannels": [],           // If none, global.
#           "isEmbed": False                 // Determine whether to treat as embed or whatever
#           "response": "my response"
#       }
#   }
        
    async def on_message(message):
        responses = BOT_CONFIG.get("responses", {})
        
        
def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(AutoResponder(bot))
