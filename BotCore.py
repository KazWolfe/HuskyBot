#!/usr/bin/env python3

import datetime
import logging
import os
import sys
import time

import discord
from discord.ext import commands

from WolfBot import WolfUtils
from WolfBot.WolfConfig import WolfConfig
from WolfBot.WolfEmbed import Colors

BOT_CONFIG = WolfConfig("config/config.json")
LOCAL_STORAGE = WolfConfig()

# Determine restart reason (pretty mode)
restart_reason = BOT_CONFIG.get("restartReason", "start")
start_status = discord.Status.idle
if restart_reason == "admin":
    start_game = discord.Game(name="Restarting...", type=0)
elif restart_reason == "update":
    start_game = discord.Game(name="Updating...", type=0)
else:
    start_game = discord.Game(name="Starting...", type=0)

bot = commands.Bot(command_prefix=BOT_CONFIG.get('prefix', '/'), game=start_game, status=start_status)

# LOCAL_STORAGE.set('logPath', 'logs/log-' + str(datetime.datetime.now()).split('.')[0] + ".log")
LOCAL_STORAGE.set('logPath', 'logs/wolfbot-' + str(datetime.datetime.now()).split(' ')[0] + '.log')
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    handlers=[logging.FileHandler(LOCAL_STORAGE.get('logPath'), 'a'),
                              logging.StreamHandler(sys.stdout)])
LOG = logging.getLogger("DiyBot.Core")


@bot.event
async def on_ready():
    if restart_reason != "start":
        BOT_CONFIG.delete("restartReason")

    time.sleep(5)
    bot_presence = BOT_CONFIG.get('presence', {"game": "DiyBot", "type": 2, "status": "dnd"})

    await bot.change_presence(game=discord.Game(name=bot_presence['game'], type=bot_presence['type']),
                              status=discord.Status[bot_presence['status']])
    LOG.info("DiyBot is online, running discordpy " + discord.__version__)

    # Lock the bot to a single guild
    if not BOT_CONFIG.get("developerMode", False):
        if BOT_CONFIG.get("guildId") is None:
            LOG.error("No Guild ID specified! Quitting.")
            exit(127)

        for guild in bot.guilds:
            if guild.id != BOT_CONFIG.get("guildId"):
                guild.leave()

    # Load plugins
    sys.path.insert(1, os.getcwd() + "/plugins/")

    bot.load_extension('BotAdmin')

    if BOT_CONFIG.get("developerMode", False):
        bot.load_extension('Debug')

    for extension in BOT_CONFIG.get('plugins', []):
        bot.load_extension(extension)

    # Inform on restart
    if BOT_CONFIG.get("restartNotificationChannel") is not None:
        channel = bot.get_channel(BOT_CONFIG.get("restartNotificationChannel"))
        await channel.send(embed=discord.Embed(
            title="Bot Manager",
            description="The bot has been successfully restarted, and is now online.",
            color=Colors.SUCCESS
        ))
        BOT_CONFIG.delete("restartNotificationChannel")


@bot.event
async def on_guild_join(guild):
    if not BOT_CONFIG.get("developerMode", False):
        if guild.id != BOT_CONFIG.get("guildId"):
            guild.leave()


@bot.event
async def on_command_error(ctx, error):
    command_name = ctx.message.content.split(' ')[0].replace('/', '')

    if isinstance(error, commands.MissingPermissions):
        # fail silently on permission error
        LOG.error("Encountered permission error when attempting to run command %s: %s", command_name, str(error))
        return

    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/" + command_name + "` may not be run in a DM.** "
                        + "See `/help` for valid commands.",
            color=Colors.DANGER
        ))
        LOG.error("Command %s may only be run in a direct message!", command_name)
        return

    if isinstance(error, commands.CommandNotFound) or isinstance(error, commands.DisabledCommand):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/" + command_name
                        + "` does not exist.** See `/help` for valid commands.",
            color=Colors.DANGER
        ))
        LOG.error("Command %s does not exist to the system, or is disabled.", command_name)
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/" + command_name + "` could not run, because it is missing arguments.**\n"
                        + " See `/help " + command_name + "` for the arguments required.",
            color=Colors.DANGER
        ).add_field(name="Missing Parameter", value="`" + str(error).split(" ")[0] + "`", inline=True))
        LOG.error("Command %s was called with the wrong parameters.", command_name)
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/" + command_name + "` could not understand the arguments given.**\n"
                        + "See `/help " + command_name + "` and the error below to fix this issue.",
            color=Colors.DANGER
        ).add_field(name="Error Log", value="```" + str(error) + "```", inline=False))
        LOG.error("Command %s was unable to parse arguments: %s.", command_name, str(error))
        return

    # Handle all other errors
    await ctx.send(embed=discord.Embed(
        title="Bot Error Handler",
        description="The bot has encountered a fatal error running the command given. Logs are below.",
        color=Colors.DANGER
    ).add_field(name="Error Log", value="```" + str(error) + "```", inline=False))
    LOG.error("Error running command %s: %s", ctx.message.content, error)


@bot.event
async def on_message(message):
    if not WolfUtils.should_process_message(message):
        return

    if message.content.startswith(bot.command_prefix):
        LOG.info("User %s ran %s", message.author, message.content)
        await bot.process_commands(message)


if __name__ == '__main__':
    bot.run(BOT_CONFIG['apiKey'])
