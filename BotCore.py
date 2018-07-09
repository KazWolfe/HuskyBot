#!/usr/bin/env python3

import logging
import os
import sys
import re
import traceback

import discord
from discord.ext import commands
import discord.ext.commands.bot as BotClass

from aiohttp import web
import ssl

from WolfBot import WolfConfig
from WolfBot import WolfStatics
from WolfBot import WolfUtils
from WolfBot import WolfHTTP
from WolfBot.WolfStatics import Colors, ChannelKeys

BOT_CONFIG = WolfConfig.get_config()
LOCAL_STORAGE = WolfConfig.get_session_store()

initialized = False

# Determine restart reason (pretty mode) - HACK FOR BOT INIT
restart_reason = BOT_CONFIG.get("restartReason", "start")
start_status = discord.Status.idle

if restart_reason == "admin":
    start_activity = discord.Activity(name="Restarting...", type=discord.ActivityType.playing)
elif restart_reason == "update":
    start_activity = discord.Activity(name="Updating...", type=discord.ActivityType.playing)
else:
    start_activity = discord.Activity(name="Starting...", type=discord.ActivityType.playing)

# initialize our bot here
bot = commands.Bot(command_prefix=BOT_CONFIG.get('prefix', '/'),
                   activity=start_activity,
                   status=start_status,
                   command_not_found="**Error:** The bot could not find the command `/{}`.")

webapp = web.Application()

# set up logging
LOCAL_STORAGE.set('logPath', 'logs/dakotabot-{}.log'.format(WolfUtils.get_timestamp().split(' ', 1)[0]))
logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    handlers=[logging.FileHandler(LOCAL_STORAGE.get('logPath'), 'a'),
                              logging.StreamHandler(sys.stdout)])
# WolfUtils.configure_loggers()
MASTER_LOGGER = logging.getLogger("DakotaBot")
MASTER_LOGGER.setLevel(logging.INFO)
LOG = MASTER_LOGGER.getChild('Core')


async def initialize():
    global restart_reason
    global start_activity
    global initialized

    # Delete temporary restart configs
    if restart_reason != "start":
        BOT_CONFIG.delete("restartReason")
        del start_activity
        restart_reason = "start"

    LOG.info("DakotaBot is online, running discord.py {}. "
             "Initializing and loading modules...".format(discord.__version__))

    # Lock the bot to a single guild
    if not BOT_CONFIG.get("developerMode", False):
        if BOT_CONFIG.get("guildId") is None:
            LOG.error("No Guild ID specified! Quitting.")
            exit(127)

        for guild in bot.guilds:
            if guild.id != BOT_CONFIG.get("guildId"):
                guild.leave()

    # Disable help, and register our own
    bot.remove_command("help")
    bot.add_command(commands.Command(name="help",
                                     brief="Get help with the bot",
                                     aliases=["?"],
                                     callback=help_command))

    # Initialize our HTTP server
    await start_webserver()

    # Load plugins
    sys.path.insert(1, os.getcwd() + "/plugins/")

    bot.load_extension('BotAdmin')

    plugin_list = BOT_CONFIG.get('plugins', [])

    if BOT_CONFIG.get("developerMode", False):
        plugin_list = ["Debug"] + plugin_list

    for plugin in plugin_list:
        # noinspection PyBroadException
        try:
            bot.load_extension(plugin)
        except:  # This is a very hacky way to do this, but we need to persist module loading through a failure
            await on_error('initialize/load_plugin/' + plugin)

    # Inform on restart
    if BOT_CONFIG.get("restartNotificationChannel") is not None:
        channel = bot.get_channel(BOT_CONFIG.get("restartNotificationChannel"))
        await channel.send(embed=discord.Embed(
            title=Emojis.REFRESH + " Bot Manager",
            description="The bot has been successfully restarted, and is now online.",
            color=Colors.SUCCESS
        ))
        BOT_CONFIG.delete("restartNotificationChannel")

    initialized = True


@bot.event
async def on_ready():
    if not initialized:
        await initialize()
        LOG.info("The bot has been initialized. Ready to process commands and events.")
    else:
        LOG.warning("A new on_ready() was called after initialization. Did the network die?")

    bot_presence = BOT_CONFIG.get('presence', {"game": "DakotaBot", "type": 2, "status": "dnd"})

    await bot.change_presence(
        activity=discord.Activity(name=bot_presence['game'], type=bot_presence['type']),
        status=discord.Status[bot_presence['status']]
    )


@bot.event
async def on_guild_join(guild):
    if not BOT_CONFIG.get("developerMode", False):
        if guild.id != BOT_CONFIG.get("guildId"):
            guild.leave()


@bot.event
async def on_command_error(ctx, error: commands.CommandError):
    command_name = ctx.message.content.split(' ')[0][1:]

    error_string = WolfUtils.trim_string(str(error).replace('```', '`\u200b`\u200b`'), 128)

    # Handle cases where the calling user is missing a required permission.
    if isinstance(error, commands.MissingPermissions):
        if BOT_CONFIG.get("developerMode", False):
            await ctx.send(embed=discord.Embed(
                title="Command Handler",
                description="**You are not authorized to run `/{}`:**\n```{}```\n\nPlease ask a staff member for "
                            "assistance".format(command_name, error_string),
                color=Colors.DANGER
            ))

        LOG.error("Encountered permission error when attempting to run command %s: %s", command_name, str(error))

    # Handle cases where the command is disabled.
    elif isinstance(error, commands.DisabledCommand):
        if BOT_CONFIG.get("developerMode", False):
            embed = discord.Embed(
                title="Command Handler",
                description="**The command `/{}` does not exist.** See `/help` for valid "
                            "commands.".format(command_name),
                color=Colors.DANGER
            )

            await ctx.send(embed=embed)

        LOG.error("Command %s is disabled.", command_name)

    # Handle cases where the command does not exist.
    elif isinstance(error, commands.CommandNotFound):
        if BOT_CONFIG.get("developerMode", False):
            await ctx.send(embed=discord.Embed(
                title="Command Handler",
                description="**The command `/{}` does not exist.** See `/help` for valid "
                            "commands.".format(command_name),
                color=Colors.DANGER
            ))

        LOG.error("Command %s does not exist to the system.", command_name)

    # Handle cases where a prerequisite command check failed to execute
    elif isinstance(error, commands.CheckFailure):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/{}` failed an execution check.** "
                        "Additional information may be provided below.".format(command_name),
            color=Colors.DANGER
        ).add_field(name="Error Log", value="```" + error_string + "```", inline=False))

        LOG.error("Encountered check failure when attempting to run command %s: %s", command_name, str(error))

    # Handle cases where a command is run over a Direct Message without working over DMs
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/{}` may not be run in a DM.** See `/help` for valid "
                        "commands.".format(command_name),
            color=Colors.DANGER
        ))

        LOG.error("Command %s may not be run in a direct message!", command_name)

    # Handle cases where a command is run missing a required argument
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/{}` could not run, because it is missing arguments.**\n"
                        "See `/help {}` for the arguments required.".format(command_name, command_name),
            color=Colors.DANGER
        ).add_field(name="Missing Parameter", value="`" + error_string.split(" ")[0] + "`", inline=True))
        LOG.error("Command %s was called with the wrong parameters.", command_name)
        return

    # Handle cases where an argument can not be parsed properly.
    elif isinstance(error, commands.BadArgument):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/{}` could not understand the arguments given.**\n"
                        "See `/help {}` and the error below to fix this issue.".format(command_name, command_name),
            color=Colors.DANGER
        ).add_field(name="Error Log", value="```" + error_string + "```", inline=False))

        LOG.error("Command %s was unable to parse arguments: %s.", command_name, str(error))

    # Handle cases where the bot is missing a required execution permission.
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/{}` could not execute successfully, as the bot does not have a required"
                        "permission.**\nPlease make sure that the bot has the following permissions: "
                        "`{}`".format(command_name, ', '.join(error.missing_perms)),
            color=Colors.DANGER
        ))

        LOG.error("Bot is missing permissions %s to execute command %s", error.missing_perms, command_name)

    # Handle commands on cooldown
    elif isinstance(error, commands.CommandOnCooldown):
        seconds = round(error.retry_after)
        tx = "{} {}".format(seconds, "second" if seconds == 1 else "seconds")

        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description="**The command `/{}` has been run too much recently!**\nPlease wait **{}** until trying "
                        "again.".format(command_name, tx),
            color=Colors.DANGER
        ))

        LOG.error("Command %s was on cooldown, and is unable to be run for %s seconds. Cooldown: %s", command_name,
                  round(error.retry_after, 0), error.cooldown)

    # Handle any and all other error cases.
    else:
        await ctx.send(embed=discord.Embed(
            title="Bot Error Handler",
            description="The bot has encountered a fatal error running the command given. Logs are below.",
            color=Colors.DANGER
        ).add_field(name="Error Log", value="```" + error_string + "```", inline=False))
        LOG.error("Error running command %s. See below for trace.\n%s",
                  ctx.message.content, ''.join(traceback.format_exception(type(error), error, error.__traceback__)))

        # Send it over to the main error logger as well.
        raise error


# noinspection PyUnusedLocal
@bot.event
async def on_error(event_method, *args, **kwargs):
    LOG.error('Exception in method %s:\n%s', event_method, traceback.format_exc())

    try:
        channel = BOT_CONFIG.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

        if channel is None:
            LOG.warning('A logging channel is not set up! Error messages will not be forwarded to Discord.')
            return

        channel = bot.get_channel(channel)

        embed = discord.Embed(
            title="Bot Exception Handler",
            description="Exception in method `{}`:\n```{}```".format(
                event_method,
                WolfUtils.trim_string(traceback.format_exc().replace('```', '`\u200b`\u200b`'), 1500)
            ),
            color=Colors.DANGER
        )

        await channel.send("<@{}>, an error has occurred with the bot. See attached "
                           "embed.".format(WolfStatics.DEVELOPERS[0]),
                           embed=embed)
    except Exception as e:
        LOG.critical("There was an error sending an error to the error channel.\n " + str(e))


@bot.event
async def on_message(message):
    author = message.author
    if not WolfUtils.should_process_message(message):
        return

    if message.content.startswith(bot.command_prefix):
        if (author.id in BOT_CONFIG.get('userBlacklist', [])) and (author.id not in WolfStatics.DEVELOPERS):
            LOG.info("Blacklisted user %s attempted to run command %s", message.author, message.content)
            return

        if message.content.lower().split(' ')[0][1:] in BOT_CONFIG.get('ignoredCommands', []):
            LOG.info("User %s ran an ignored command %s", message.author, message.content)
            return

        if message.content.lower().split(' ')[0].startswith('/r/'):
            LOG.info("User %s linked to subreddit %s, ignoring command", message.author, message.content)
            return

        if LOCAL_STORAGE.get('lockdown', False) and (author.id not in WolfStatics.DEVELOPERS):
            LOG.info("Lockdown mode is enabled for the bot. Command blocked.")
            return

        LOG.info("User %s ran %s", author, message.content)

        await bot.process_commands(message)


async def help_command(ctx: commands.Context, *command: str):
    """
    Get help information from the bot database.

    This command takes a string (command) as an argument to look up. If a command does not exist, the bot will throw
    an error.
    """
    content = ctx.message.content

    # Evil parse magic is evil, I hate this code.
    if len(command) == 0:
        command = ''
    elif len(command) > 0:
        content = content.split(None, 1)[1]
        command = re.sub(r'[_*`~]', '', content, flags=re.M)
        command = command.split()

    # noinspection PyProtectedMember
    await BotClass._default_help_command(ctx, *command)


def get_developers():
    """
    Get a list of all registered bot developers.
    """
    return WolfStatics.DEVELOPERS


async def start_webserver():
    http_config = BOT_CONFIG.get('httpConfig', {
        "host": "localhost",
        "port": "9339",
        "ssl_cert": None
    })

    ssl_context = None
    if http_config.get('ssl_cert', None) is not None:
        with open(http_config.get('ssl_cert', 'certs/cert.pem'), 'rb') as cert:
            ssl_context = ssl.SSLContext()
            ssl_context.load_cert_chain(cert)

    for method in ["GET", "HEAD", "POST", "PATCH", "PUT", "DELETE", "VIEW"]:
        webapp.router.add_route(method, '/{tail:.*}', WolfHTTP.get_router().handle(bot))
    runner = web.AppRunner(webapp)
    await runner.setup()
    site = web.TCPSite(runner, host=http_config['host'], port=http_config['port'], ssl_context=ssl_context)
    await site.start()
    LOG.info("Started {} server at {}:{}, now listening...".format("HTTPS" if ssl_context is not None else "HTTP",
                                                                   http_config['host'], http_config['port']))


if __name__ == '__main__':
    LOG.info("Set log path to {}".format(LOCAL_STORAGE.get('logPath')))
    bot.run(BOT_CONFIG['apiKey'])

    # Auto restart if a reason is present
    if BOT_CONFIG.get("restartReason") is not None:
        print("READY FOR RESTART!")
        os.execl(sys.executable, *([sys.executable] + sys.argv))
