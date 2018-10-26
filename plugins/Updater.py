import logging
import time
from datetime import datetime

import discord
import git
from discord.ext import commands

from HuskyBot import HuskyBot
from libhusky.HuskyStatics import *

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Updater:
    """
    Core class for bot update management.

    This is an administrative non-critical plugin designed to assist in bot development by facilitating an easy way to
    upgrade the bot's code without manually connecting to servers. While this plugin attempts to be smart with updates,
    its capability for intelligence is rather limited. This plugin should not be relied upon to be a completely reliable
    and bulletproof way of updating the bot.
    """

    def __init__(self, bot: HuskyBot):
        self.bot = bot
        self._config = bot.config
        self.repo = git.Repo(search_parent_directories=True)
        LOG.info("Loaded plugin!")

    @commands.command(name="update", brief="Pull the latest version of code from Git")
    @commands.has_permissions(administrator=True)
    async def update_bot(self, ctx: discord.ext.commands.Context):
        """
        This command will attempt to fast-forward the bot's code to the latest version (as present in GitHub). Once it
        successfully pulls the latest version of the code, it will log itself out (triggering the restart loop in
        BotCore). This updater does not alter the config files or run any configuration migrations, so care must be
        taken to make sure changes don't break things.

        This command also does *no checks* of the code to ensure it's runnable. This must be done client-side before
        pushing.
        """

        remote = self.repo.remotes.origin

        current_sha = self.repo.head.object.hexsha

        fetch_info = remote.fetch()[0]
        LOG.info("Got update fetch to %s", fetch_info)

        if fetch_info.commit.hexsha == current_sha:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description=f"The bot is already up-to-date at version "
                            f"[`{current_sha[:8]}`]({GIT_URL}/commit/{current_sha})",
                color=Colors.INFO
            ))
            return

        if fetch_info.flags != 64:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The bot's code can not be fast-forwarded to the latest version. Please manually "
                            "update the bot.",
                color=Colors.DANGER
            ))
            return

        # we're clear to update. let's do it!
        LOG.info("All update sanity checks passed. Pulling...")
        await ctx.bot.change_presence(activity=discord.Activity(name="Updating...", type=0), status=discord.Status.idle)
        time.sleep(5)
        remote.pull()
        new_sha = self.repo.head.object.hexsha
        await ctx.send(embed=discord.Embed(
            title=Emojis.INBOX + " Bot Update Utility",
            description=f"The bot's code has been updated from `{current_sha[:8]}` "
                        f"to [`{new_sha[:8]}`]({GIT_URL}/commit/{new_sha}) Please wait while the bot restarts...",
            color=Colors.SUCCESS
        ))

        LOG.info("Bot is going down for update restart!")
        self._config.set("restartNotificationChannel", ctx.channel.id)
        self._config.set("restartReason", "update")
        await ctx.trigger_typing()
        await ctx.bot.logout()

    @commands.command(name="changelog", brief="Get the Git changelog for the bot's current version")
    @commands.has_permissions(administrator=True)
    async def changelog(self, ctx: discord.ext.commands.Context):
        """
        This will pull a changelog from the Git log. Specifically, this exposes the last commit to users for
        verification and change notification.

        Git changelogs should not contain sensitive information, so this command is safe to run in public channels,
        but admin discretion is advised.
        """
        last_commit = self.repo.head.commit

        embed = discord.Embed(
            title=Emojis.MEMO + f" Changelog for version `{last_commit.hexsha[:8]}`",
            description=f"```{last_commit.message}```",
            color=Colors.PRIMARY
        )

        embed.add_field(name="Author", value=last_commit.author, inline=True)
        embed.add_field(name="Author Date", value=datetime
                        .fromtimestamp(last_commit.authored_date).strftime(DATETIME_FORMAT), inline=True)
        embed.add_field(name="GitHub",
                        value=f"[See Commit >]({GIT_URL}/commit/{last_commit.hexsha})",
                        inline=False)

        await ctx.send(embed=embed)


def setup(bot: HuskyBot):
    bot.add_cog(Updater(bot))
