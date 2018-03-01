import discord
from discord.ext import commands

from BotCore import BOT_CONFIG
from BotCore import LOCAL_STORAGE

from WolfBot import WolfUtils
from WolfBot.WolfEmbed import Colors
import logging

import git
import os
import sys

LOG = logging.getLogger("DiyBot.Plugin." + __name__)

class Updater:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot

    async def on_ready(self):
        LOG.info("Enabled plugin!")
        
    @commands.command(name="update", brief="Pull the latest version of code from Git.", hidden=True)
    @commands.has_permissions(administrator=True)
    async def updateBot(self, ctx: discord.ext.commands.Context):
        repo = git.Repo(search_parent_directories = True)
        remote = repo.remotes.origin
        
        currentSha = repo.head.object.hexsha
        
        fetch_info = remotes.fetch('master:master')[0]
        LOG.info("Got update fetch to " + str(fetch_info)
        
        if (fetch_info.commit.hexsha == currentSha):
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The bot is already up-to-date at version [`" + currentSha "`](https://www.github.com/KazWolfe/diy_tech-bot/commit/" + currentSha + ")",
                color = Colors.INFO
            ))
            return
            
        if (fetch_info.flags != 64):
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The bot's code can not be fast-forwarded to the latest version. Please manually update the bot.",
                color = Colors.DANGER
            ))
            return
            
        # we're clear to update. let's do it!
        LOG.info("All update sanity checks passed. Pulling...")
        remote.pull()
        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description="The bot's code has been updated! Please wait while the bot restarts...",
            color = Colors.SUCCESS
        ))
        
        LOG.info("Bot is going down for update restart!")
        os.execl(sys.executable, *([sys.executable]+sys.argv))
        
        
def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Updater(bot))
