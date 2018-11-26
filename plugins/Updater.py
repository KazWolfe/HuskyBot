import asyncio
import logging
import sys
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

        update_result, old_sha, new_sha = await self.perform_upgrade()

        if update_result == UpdateResult.UPDATED:
            await ctx.send(embed=discord.Embed(
                title=Emojis.INBOX + " Bot Update Utility",
                description=f"The bot's code has been updated from `{old_sha[:8]}` "
                            f"to [`{new_sha[:8]}`]({GIT_URL}/commit/{new_sha}). Please wait while the bot restarts...",
                color=Colors.SUCCESS
            ))
        elif update_result == UpdateResult.UPDATED_WITH_DEPS:
            await ctx.send(embed=discord.Embed(
                title=Emojis.INBOX + " Bot Update Utility",
                description=f"The bot's code has been updated from `{old_sha[:8]}` "
                            f"to [`{new_sha[:8]}`]({GIT_URL}/commit/{new_sha}). The bot's dependencies have "
                            f"additionally been updated to the latest version. Please wait while the bot restarts...",
                color=Colors.SUCCESS
            ))
        elif update_result == UpdateResult.DEPS_UPDATE_FAILED:
            await ctx.send(embed=discord.Embed(
                title=Emojis.INBOX + " Bot Update Utility",
                description=f"The bot's code could not be updated successfully, as an error was encountered while "
                            f"attempting to update the bot's dependencies. The bot's code has not been updated.",
                color=Colors.DANGER
            ))
            return
        elif update_result == UpdateResult.ALREADY_UP_TO_DATE:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description=f"The bot is already up-to-date at version "
                            f"[`{old_sha[:8]}`]({GIT_URL}/commit/{old_sha})",
                color=Colors.INFO
            ))
            return
        elif update_result == UpdateResult.CANNOT_FAST_FORWARD:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The bot's code can not be fast-forwarded to the latest version. Please manually "
                            "update the bot.",
                color=Colors.DANGER
            ))
            return

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

    async def perform_upgrade(self):
        remote = self.repo.remotes.origin

        current_sha = self.repo.head.object.hexsha

        fetch_info = remote.fetch()[0]
        LOG.info("Updater fetched %s from upstream.", fetch_info)

        if fetch_info.commit.hexsha == current_sha:
            return UpdateResult.ALREADY_UP_TO_DATE, current_sha, current_sha

        if fetch_info.flags != 64:
            return UpdateResult.CANNOT_FAST_FORWARD, current_sha, current_sha

        LOG.info("Update sanity checks complete. The bot is ready for upgrade.")
        await self.bot.change_presence(
            activity=discord.Activity(name="Updating...", type=0),
            status=discord.Status.idle
        )

        await asyncio.sleep(5)
        remote.pull()

        new_sha = self.repo.head.object.hexsha
        LOG.info(f"The bot's update succeeded. Now at git revision {new_sha[:8]}.")

        # Dependency upgrade requested
        if "--update-deps" in self.repo.head.object.message:
            LOG.info("Git requested a dependency upgrade. Performing...")

            pip_process = await asyncio.create_subprocess_exec(
                [sys.executable, "-m", "pip", "install", "-r", "./requirements.txt"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await pip_process.communicate()

            if pip_process.returncode != 0:
                LOG.error("Dependencies failed to upgrade. Output below.")
                LOG.error(f'[stdout]\n{stdout.decode()}')
                LOG.error(f'[stderr]\n{stderr.decode()}')

                LOG.info("Reverting last commit to code...")
                self.repo.head.reset(commit=current_sha, index=True, working_tree=True)
                LOG.info(f"Code hard-reset to {current_sha[:8]}.")

                return UpdateResult.DEPS_UPDATE_FAILED, current_sha, current_sha

            return UpdateResult.UPDATED_WITH_DEPS, current_sha, new_sha

        return UpdateResult.UPDATED, current_sha, new_sha


class UpdateResult:
    # Success
    UPDATED = 0
    UPDATED_WITH_DEPS = 1

    # Failure
    ALREADY_UP_TO_DATE = 100
    CANNOT_FAST_FORWARD = 101
    DEPS_UPDATE_FAILED = 110


def setup(bot: HuskyBot):
    bot.add_cog(Updater(bot))
