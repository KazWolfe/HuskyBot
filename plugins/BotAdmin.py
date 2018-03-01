import logging
import os
import sys

import discord
import git
from discord.ext import commands

from BotCore import BOT_CONFIG
from BotCore import LOCAL_STORAGE
from WolfBot import WolfUtils
from WolfBot.WolfEmbed import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)

class BotAdmin:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot

    async def on_ready(self):
        LOG.info("Enabled plugin!")

    @commands.command(name="version", brief="Get version information for the bot")
    async def version_cmd(self, ctx: discord.ext.commands.Context):
        repo = git.Repo(search_parent_directories = True)
        sha = repo.head.object.hexsha
    
        await ctx.send(embed=discord.Embed(
                title="DiyBot",
                description="This is DIYBot, a fork of the WolfBot core Discord bot platform. It is responsible for managing"
                + " and assisting the moderators on the DIY Tech subreddit.",
                color = Colors.INFO
            )
            .add_field(name="Authors", value="KazWolfe, Clover", inline=False)
            .add_field(name="Bot Version", value="[`" + sha[:8] + "`](https://www.github.com/KazWolfe/diy_tech-bot/commit/" + sha + ")", inline=True)
            .add_field(name="Library Version", value=discord.__version__, inline=True)
            .set_thumbnail(url="https://cdn.discordapp.com/avatars/" + str(ctx.bot.user.id) + "/" + str(ctx.bot.user.avatar) + ".png")
            .set_footer(text="MIT License, © 2018 KazWolfe", icon_url="https://avatars3.githubusercontent.com/u/5192145")
        )

    @commands.group(pass_context=True, brief="Administrative bot control commands.", hidden=True)
    @commands.has_permissions(administrator=True)
    async def admin(self, ctx: discord.ext.commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The command you have requested is not available.",
                color = Colors.DANGER
            ))
            return

    @admin.command(name="reloadConfig", brief="Reload the bot's configuration files from disk.")
    async def reloadConfig(self, ctx: discord.ext.commands.Context):
        BOT_CONFIG.load()
        LOG.info("Bot configuration reloaded.")
        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description="The bot configuration has been reloaded.",
            color = Colors.INFO
        ))

    @admin.command(name="load", brief="Temporarily load a plugin into the bot.")
    async def load(self, ctx: discord.ext.commands.Context, plugin_name: str):
        try:
            self.bot.load_extension(plugin_name)
        except (AttributeError, ImportError) as e:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The plugin `" + plugin_name + "` has failed to load. The following error is available:\n ```{}: {}```".format(type(e).__name__, str(e)),
                color = Colors.DANGER
            ))
            return
        LOG.info("Loaded plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description="The plugin `" + plugin_name + "` has been loaded.",
            color = Colors.INFO
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
            color = Colors.INFO
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
                description="The plugin `" + plugin_name + "` has failed to reload. The following error is available:\n ```{}: {}```".format(type(e).__name__, str(e)),
                color = Colors.DANGER
            ))
            return
        LOG.info("Reloaded plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description="The plugin `" + plugin_name + "` has been reloaded.",
            color = Colors.INFO
        ))

    @admin.command(name="enable", brief="Enable a plugin to run now and at bot load.")
    async def enable(self, ctx: discord.ext.commands.Context, plugin_name: str):
        config = BOT_CONFIG.get('plugins', [])

        if plugin_name in config:
            await ctx.send("Plugin {} is already enabled.".format(plugin_name))
            return

        try:
            self.bot.load_extension(plugin_name)
        except (AttributeError, ImportError) as e:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The plugin `" + plugin_name + "` has failed to enable. The following error is available:\n ```{}: {}```".format(type(e).__name__, str(e)),
                color = Colors.DANGER
            ))
            return
        LOG.info("Loaded plugin %s for enable", plugin_name)

        config.append(plugin_name)
        BOT_CONFIG.set('plugins', config)
        LOG.info("Enabled plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description="The plugin `" + plugin_name + "` has been enabled and will run automatically.",
            color = Colors.SUCCESS
        ))

    @admin.command(name="disable", brief="Disable a plugin from running at bot load. Also stops the plugin.")
    async def disable(self, ctx: discord.ext.commands.Context, plugin_name: str):
        if plugin_name == "BotAdmin":
            await ctx.send("ERROR: Can not disable BotAdmin! It is marked as a critical module.")
            return

        config = BOT_CONFIG.get('plugins', [])

        if plugin_name not in config:
            await ctx.send("Plugin {} is already disabled.".format(plugin_name))
            return

        self.bot.unload_extension(plugin_name)
        LOG.info("Unloaded plugin %s for disable", plugin_name)

        config.remove(plugin_name)
        BOT_CONFIG.set('plugins', config)
        LOG.info("Disabled plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description="The plugin `" + plugin_name + "` has been disabled and will no longer run automatically.",
            color = Colors.WARNING
        ))
        
    @admin.command(name="log", aliases=["logs"], brief="See the bot's current log.")
    async def log(self, ctx: discord.ext.commands.Context, lines: int = 10):
        logFile = LOCAL_STORAGE.get('logPath')
        logs = None
        
        if logFile is None:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="A log file was expected, but was not found or configured. This suggests a *serious* problem with the bot.",
                color = Colors.DANGER
            ))
            return
            
        with open(logFile, 'r') as diskLog:
            logs = WolfUtils.tail(diskLog, lines)

        await ctx.send(embed=discord.Embed(
            title="Log Entries from " + logFile,
            description="```" + logs + "```",
            color = Colors.SECONDARY
        ))
        
    @admin.command(name="presence", brief="Set the bot's presence mode.")
    async def presence(self, ctx: discord.ext.commands.Context, game: str, presenceType: int, status: str):
        newStatus = None
    
        if status.lower() == "invisible" or status.lower() == "offline":
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The bot status can not be set to invisible or offline.",
                color = Colors.DANGER
            ))
            return
            
        if not 0 <= presenceType <= 2:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The presence type must be **`0`** (\"Playing\"), **`1`** (\"Streaming\"), or **`2`** (\"Listening to\").",
                color = Colors.DANGER
            ))
            return
            
        try:
            newStatus = discord.Status[status.lower()]
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="Valid values for status are: **`ONLINE`**, **`IDLE`**, **`DND`**.",
                color = Colors.DANGER
            ))
            return
            
        BOT_CONFIG.set('presence', {"game": game, "type": presenceType, "status": status})
        await ctx.bot.change_presence(game=discord.Game(name=game, type=presenceType), status=newStatus)
        await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The bot's presence was updated.",
                color = Colors.SUCCESS
            ))
            
    @admin.command(name="restart", brief="Restart the bot.")
    async def restart(self, ctx: discord.ext.commands.Context):
        await ctx.bot.change_presence(game=discord.Game(name="Restarting...", type=0), status=discord.Status.idle)
        LOG.info("Bot is going down for admin requested restart!")
        os.execl(sys.executable, *([sys.executable]+sys.argv))
            
def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(BotAdmin(bot))
