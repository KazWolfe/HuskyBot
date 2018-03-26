#!/usr/bin/env python3

import datetime
import logging
import os
import sys
import traceback

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfUtils
from WolfBot.WolfStatics import Colors, ChannelKeys

BOT_CONFIG = WolfConfig.getConfig()
LOCAL_STORAGE = WolfConfig.getSessionStore()

initialized = False

# Determine restart reason (pretty mode) - HACK FOR BOT INIT
restart_reason = BOT_CONFIG.get("restartReason", "start")
start_status = discord.Status.idle
if restart_reason == "admin":
    start_game = discord.Activity(name="Restarting...", type=discord.ActivityType.playing)
elif restart_reason == "update":
    start_game = discord.Game(name="Updating...", type=discord.ActivityType.playing)
else:
    start_game = discord.Game(name="Starting...", type=discord.ActivityType.playing)

bot = commands.Bot(command_prefix=BOT_CONFIG.get('prefix', '/'))

# LOCAL_STORAGE.set('logPath', 'logs/log-' + str(datetime.datetime.now()).split('.')[0] + ".log")
LOCAL_STORAGE.set('logPath', 'logs/wolfbot-' + str(datetime.datetime.now()).split(' ')[0] + '.log')
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    handlers=[logging.FileHandler(LOCAL_STORAGE.get('logPath'), 'a'),
                              logging.StreamHandler(sys.stdout)])
LOG = logging.getLogger("DiyBot.Core")


async def initialize():
    global restart_reason
    global start_game
    global initialized

    # Delete temporary restart configs
    if restart_reason != "start":
        BOT_CONFIG.delete("restartReason")
        del start_game
        restart_reason = "start"

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

    initialized = True


@bot.event
async def on_ready():
    if not initialized:
        await initialize()

    bot_presence = BOT_CONFIG.get('presence', {"game": "DiyBot", "type": 2, "status": "dnd"})

    await bot.change_presence(activity=discord.Activity(name=bot_presence['game'], type=bot_presence['type']),
                              status=discord.Status[bot_presence['status']])


@bot.event
async def on_guild_join(guild):
    if not BOT_CONFIG.get("developerMode", False):
        if guild.id != BOT_CONFIG.get("guildId"):
            guild.leave()


@bot.event
async def on_command_error(ctx, error):
    command_name = ctx.message.content.split(' ')[0][1:]

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/" + command_name
                        + "` does not exist.** See `/help` for valid commands.",
            color=Colors.DANGER
        ))
        LOG.error("Encountered permission error when attempting to run command %s: %s", command_name, str(error))
        return

    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/" + command_name + "` may not be run in a DM.** "
                        + "See `/help` for valid commands.",
            color=Colors.DANGER
        ))
        LOG.error("Command %s may not be run in a direct message!", command_name)
        return

    if isinstance(error, commands.DisabledCommand):
        embed = discord.Embed(
            title="Command Handler",
            description="**The command `/" + command_name
                        + "` does not exist.** See `/help` for valid commands.",
            color=Colors.DANGER
        )

        if ctx.message.author.guild_permissions.administrator:
            embed.set_footer(text="E_DISABLED_COMMAND")

        await ctx.send(embed=embed)

        LOG.error("Command %s is disabled.", command_name)
        return

    if isinstance(error, commands.CommandNotFound):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/" + command_name
                        + "` does not exist.** See `/help` for valid commands.",
            color=Colors.DANGER
        ))
        LOG.error("Command %s does not exist to the system.", command_name)
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
async def on_error(event_method, *args, **kwargs):
    LOG.error('Exception in method %s:\n%s', event_method, traceback.format_exc())

    try:
        channel = BOT_CONFIG.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

        if channel is None:
            LOG.warn('A logging channel is not set up! Error messages will not be forwarded to Discord.')
            return

        channel = bot.get_channel(channel)

        embed = discord.Embed(
            title="Bot Exception Handler",
            description=WolfUtils.trim_string(
                "Exception in method `" + event_method + "`:\n```" + traceback.format_exc() + "```", 2048, True),
            color=Colors.DANGER
        )

        await channel.send(embed=embed)
    except Exception as e:
        LOG.critical("There was an error sending an error to the error channel.\n " + str(e))


@bot.event
async def on_message(message):
    if not WolfUtils.should_process_message(message):
        return

    if message.content.startswith(bot.command_prefix):
        if message.content.lower().split(' ')[0][1:] in BOT_CONFIG.get('ignoredCommands', []):
            LOG.info("User %s ran an ignored command %s", message.author, message.content)
            return

        if message.content.lower().split(' ')[0].startswith('/r/'):
            LOG.info("User %s linked to subreddit %s, ignoring command", message.author, message.content)
            return

        LOG.info("User %s ran %s", message.author, message.content)
        await bot.process_commands(message)


if __name__ == '__main__':
    bot.run(BOT_CONFIG['apiKey'])

    # Auto restart if a reason is present
    if BOT_CONFIG.get("restartReason") is not None:
        print("READY FOR RESTART!")
        os.execl(sys.executable, *([sys.executable] + sys.argv))
