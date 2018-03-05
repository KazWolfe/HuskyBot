import logging
import os
import sys

import discord
import git
from discord.ext import commands

from WolfBot import WolfUtils
from WolfBot import WolfConfig
from WolfBot.WolfEmbed import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class BotAdmin:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        LOG.info("Loaded plugin!")

    @commands.command(name="version", brief="Get version information for the bot")
    async def version_cmd(self, ctx: discord.ext.commands.Context):
        repo = git.Repo(search_parent_directories=True)
        sha = repo.head.object.hexsha

        await ctx.send(embed=discord.Embed(
            title="DiyBot",
            description="This is DIYBot, a fork of the WolfBot core Discord bot platform. It is responsible for "
                        "managing and assisting the moderators on the DIY Tech subreddit.",
            color=Colors.INFO
        )
                       .add_field(name="Authors", value="KazWolfe, Clover", inline=False)
                       .add_field(name="Bot Version", value="[`" + sha[:8]
                                                            + "`](https://www.github.com/KazWolfe/diy_tech-bot/commit/"
                                                            + sha + ")", inline=True)
                       .add_field(name="Library Version", value=discord.__version__, inline=True)
                       .set_thumbnail(url="https://cdn.discordapp.com/avatars/" + str(ctx.bot.user.id) + "/"
                                          + str(ctx.bot.user.avatar) + ".png")
                       .set_footer(text="MIT License, © 2018 KazWolfe",
                                   icon_url="https://avatars3.githubusercontent.com/u/5192145")
                       )

    @commands.group(pass_context=True, brief="Administrative bot control commands.", hidden=True)
    @commands.has_permissions(administrator=True)
    async def admin(self, ctx: discord.ext.commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The command you have requested is not available.",
                color=Colors.DANGER
            ))
            return

    @admin.command(name="reloadConfig", brief="Reload the bot's configuration files from disk.")
    async def reloadConfig(self, ctx: discord.ext.commands.Context):
        WolfConfig.getConfig().load()
        LOG.info("Bot configuration reloaded.")
        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description="The bot configuration has been reloaded.",
            color=Colors.INFO
        ))

    @admin.command(name="load", brief="Temporarily load a plugin into the bot.")
    async def load(self, ctx: discord.ext.commands.Context, plugin_name: str):
        try:
            self.bot.load_extension(plugin_name)
        except (AttributeError, ImportError) as e:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The plugin `" + plugin_name
                            + "` has failed to load. The following "
                            + "error is available:\n ```{}: {}```".format(type(e).__name__, str(e)),
                color=Colors.DANGER
            ))
            LOG.error("Could not load plugin %s. Error: %s", plugin_name, e)
            return
        LOG.info("Loaded plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description="The plugin `" + plugin_name + "` has been loaded.",
            color=Colors.INFO
        ))

    @admin.command(name="unload", brief="Temporarily unload a plugin from the bot.")
    async def unload(self, ctx: discord.ext.commands.Context, plugin_name: str):
        if plugin_name == "BotAdmin":
            await ctx.send("ERROR: Can not unload BotAdmin! It is marked as a critical module.")
            return

        """Unloads an extension."""
        self.bot.unload_extension(plugin_name)
        LOG.info("Unloaded plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description="The plugin `" + plugin_name + "` has been unloaded.",
            color=Colors.INFO
        ))

    @admin.command(name="reload", brief="Unload and reload a plugin.")
    async def reload(self, ctx: discord.ext.commands.Context, plugin_name: str):
        self.bot.unload_extension(plugin_name)
        LOG.info("Unloaded plugin %s for reload.", plugin_name)
        try:
            self.bot.load_extension(plugin_name)
        except (AttributeError, ImportError) as e:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The plugin `" + plugin_name
                            + "` has failed to reload. The following "
                            + "error is available:\n ```{}: {}```".format(type(e).__name__, str(e)),
                color=Colors.DANGER
            ))
            LOG.error("Could not reload plugin %s. Error: %s", plugin_name, e)
            return
        LOG.info("Reloaded plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description="The plugin `" + plugin_name + "` has been reloaded.",
            color=Colors.INFO
        ))

    @admin.command(name="enable", brief="Enable a plugin to run now and at bot load.")
    async def enable(self, ctx: discord.ext.commands.Context, plugin_name: str):
        config = WolfConfig.getConfig().get('plugins', [])

        if plugin_name in config:
            await ctx.send("Plugin {} is already enabled.".format(plugin_name))
            return

        try:
            self.bot.load_extension(plugin_name)
        except (AttributeError, ImportError) as e:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The plugin `" + plugin_name + "` has failed to enable. The following error is "
                            + "available:\n ```{}: {}```".format(type(e).__name__, str(e)),
                color=Colors.DANGER
            ))
            LOG.error("Could not enable plugin %s. Error: %s", plugin_name, e)
            return
        LOG.info("Loaded plugin %s for enable", plugin_name)

        config.append(plugin_name)
        WolfConfig.getConfig().set('plugins', config)
        LOG.info("Enabled plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description="The plugin `" + plugin_name + "` has been enabled and will run automatically.",
            color=Colors.SUCCESS
        ))

    @admin.command(name="disable", brief="Disable a plugin from running at bot load. Also stops the plugin.")
    async def disable(self, ctx: discord.ext.commands.Context, plugin_name: str):
        if plugin_name == "BotAdmin":
            await ctx.send("ERROR: Can not disable BotAdmin! It is marked as a critical module.")
            LOG.warning("The BotAdmin module was requested to be disabled.")
            return

        config = WolfConfig.getConfig().get('plugins', [])

        if plugin_name not in config:
            await ctx.send("Plugin {} is already disabled.".format(plugin_name))
            return

        self.bot.unload_extension(plugin_name)
        LOG.info("Unloaded plugin %s for disable", plugin_name)

        config.remove(plugin_name)
        WolfConfig.getConfig().set('plugins', config)
        LOG.info("Disabled plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description="The plugin `" + plugin_name + "` has been disabled and will no longer run automatically.",
            color=Colors.WARNING
        ))

    @admin.command(name="log", aliases=["logs"], brief="See the bot's current log.")
    async def log(self, ctx: discord.ext.commands.Context, lines: int = 10):
        log_file = WolfConfig.getSessionStore().get('logPath')

        if log_file is None:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="A log file was expected, but was not found or configured. This suggests a *serious* "
                            + "problem with the bot.",
                color=Colors.DANGER
            ))
            return

        logs = WolfUtils.tail(log_file, lines)

        await ctx.send(embed=discord.Embed(
            title="Log Entries from " + log_file,
            description="```" + logs + "```",
            color=Colors.SECONDARY
        ))

    @admin.command(name="presence", brief="Set the bot's presence mode.")
    async def presence(self, ctx: discord.ext.commands.Context, game: str, presence_type: int, status: str):
        if status.lower() == "invisible" or status.lower() == "offline":
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The bot status can not be set to invisible or offline.",
                color=Colors.DANGER
            ))
            return

        if not 0 <= presence_type <= 3:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The presence type must be **`0`** (\"Playing\"), **`1`** (\"Streaming\"), "
                            + "**`2`** (\"Listening to\"), or **`3`** (\"Watching\").",
                color=Colors.DANGER
            ))
            return

        try:
            new_status = discord.Status[status.lower()]
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="Valid values for status are: **`ONLINE`**, **`IDLE`**, **`DND`**.",
                color=Colors.DANGER
            ))
            return

        WolfConfig.getConfig().set('presence', {"game": game, "type": presence_type, "status": status.lower()})
        await ctx.bot.change_presence(game=discord.Game(name=game, type=presence_type), status=new_status)
        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description="The bot's presence was updated.",
            color=Colors.SUCCESS
        ))

    @admin.command(name="reloadpresence", brief="Reload a Presence from the config file", aliases=["rpresence"])
    async def reloadPresence(self, ctx: discord.ext.commands.Context):
        bot_presence = WolfConfig.getConfig().get('presence', {"game": "DiyBot", "type": 2, "status": "dnd"})

        await ctx.bot.change_presence(game=discord.Game(name=bot_presence['game'], type=bot_presence['type']),
                                      status=discord.Status[bot_presence['status']])

    @admin.command(name="restart", brief="Restart the bot.")
    async def restart(self, ctx: discord.ext.commands.Context):
        await ctx.bot.change_presence(game=discord.Game(name="Restarting...", type=0), status=discord.Status.idle)
        LOG.info("Bot is going down for admin requested restart!")
        WolfConfig.getConfig().set("restartNotificationChannel", ctx.channel.id)
        WolfConfig.getConfig().set("restartReason", "admin")
        await ctx.bot.logout()


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(BotAdmin(bot))
