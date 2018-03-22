import logging
import os
import sys
import time
from datetime import datetime

import discord
import git
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfUtils
from WolfBot.WolfStatics import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Updater:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()
        self.repo = git.Repo(search_parent_directories=True)
        LOG.info("Loaded plugin!")

    @commands.command(name="update", brief="Pull the latest version of code from Git.", hidden=True)
    @commands.has_permissions(administrator=True)
    async def updateBot(self, ctx: discord.ext.commands.Context):
        remote = self.repo.remotes.origin

        current_sha = self.repo.head.object.hexsha

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
        new_sha = self.repo.head.object.hexsha
        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description="The bot's code has been updated from `" + current_sha[:8]
                        + "`to [`" + new_sha[:8] + "`](https://www.github.com/KazWolfe/diy_tech-bot/commit/" + new_sha
                        + ") Please wait while the bot restarts...",
            color=Colors.SUCCESS
        ))

        LOG.info("Bot is going down for update restart!")
        self._config.set("restartNotificationChannel", ctx.channel.id)
        self._config.set("restartReason", "update")
        await ctx.bot.logout()

    @commands.command(name="changelog", brief="Get the changelog for the most recent bot version.")
    @commands.has_permissions(administrator=True)
    async def changelog(self, ctx: discord.ext.commands.Context):
        lastCommit = self.repo.head.commit

        embed = discord.Embed(
            title="Changlog for version `" + str(lastCommit.hexsha)[:8] + "`",
            description="```" + lastCommit.message + "```",
            color=Colors.PRIMARY
        )

        embed.add_field(name="Author", value=lastCommit.author, inline=True)
        embed.add_field(name="Author Date", value=datetime
                        .fromtimestamp(lastCommit.authored_date).strftime('%Y-%m-%d %H:%M:%S') + " UTC", inline=True)
        embed.add_field(name="GitHub", value="[See Commit >](https://www.github.com/KazWolfe/"
                                             + "diy_tech-bot/commit/" + lastCommit.hexsha + ")", inline=False)

        await ctx.send(embed=embed)


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Updater(bot))
