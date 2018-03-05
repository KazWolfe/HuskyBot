import logging
import os
import sys
import time

import discord
import git
from discord.ext import commands

from BotCore import BOT_CONFIG
from WolfBot.WolfEmbed import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Updater:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot

    async def on_ready(self):
        LOG.info("Enabled plugin!")

    @commands.command(name="update", brief="Pull the latest version of code from Git.", hidden=True)
    @commands.has_permissions(administrator=True)
    async def updateBot(self, ctx: discord.ext.commands.Context):
        repo = git.Repo(search_parent_directories=True)
        remote = repo.remotes.origin

        current_sha = repo.head.object.hexsha

        fetch_info = remote.fetch()[0]
        LOG.info("Got update fetch to " + str(fetch_info))

        if fetch_info.commit.hexsha == current_sha:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The bot is already up-to-date at version [`"
                            + current_sha[:8] + "`](https://www.github.com/KazWolfe/diy_tech-bot/commit/"
                            + current_sha + ")",
                color=Colors.INFO
            ))
            return

        if fetch_info.flags != 64:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The bot's code can not be fast-forwarded to the latest version. Please manually "
                            + "update the bot.",
                color=Colors.DANGER
            ))
            return

        # we're clear to update. let's do it!
        LOG.info("All update sanity checks passed. Pulling...")
        await ctx.bot.change_presence(game=discord.Game(name="Updating...", type=0), status=discord.Status.idle)
        time.sleep(5)
        remote.pull()
        new_sha = repo.head.object.hexsha
        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description="The bot's code has been updated from `" + current_sha[:8]
                        + "`to [`" + new_sha[:8] + "`](https://www.github.com/KazWolfe/diy_tech-bot/commit/" + new_sha
                        + ") Please wait while the bot restarts...",
            color=Colors.SUCCESS
        ))

        LOG.info("Bot is going down for update restart!")
        BOT_CONFIG.set("restartNotificationChannel", ctx.channel.id)
        await ctx.bot.logout()
        os.execl(sys.executable, *([sys.executable] + sys.argv))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Updater(bot))
