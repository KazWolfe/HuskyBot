#!/usr/bin/env python3

# System imports
import logging
import os
import ssl
import sys
import traceback

# discord.py imports
import discord
# aiohttp/web api support
from aiohttp import web
from discord.ext import commands

# HuskyBot related imports
from libhusky import HuskyConfig
from libhusky import HuskyHTTP
from libhusky import HuskyStatics
from libhusky import HuskyUtils
from libhusky.HuskyStatics import *

LOG = logging.getLogger("HuskyBot.Core")


class HuskyBot(commands.Bot, metaclass=HuskyUtils.Singleton):
    def __init__(self):
        self.init_stage = -1

        # Load in configuration and other important things here.
        self.config = HuskyConfig.get_config()
        self.session_store = HuskyConfig.get_session_store()

        self.developer_mode = self.config.get('developerMode', False)

        # Private variables used for init only
        self.__daemon_mode = (os.getppid() == 1)
        self.session_store.set("daemonMode", self.__daemon_mode)

        self.__log_path = 'logs/huskybot.log'
        self.session_store.set('logPath', self.__log_path)

        # Load in HuskyBot's logger
        self.logger = self.__initialize_logger()

        # Load in HuskyBot's API
        self.webapp = web.Application()

        super().__init__(
            command_prefix=self.config.get('prefix', '/'),
            status=discord.Status.idle,
            activity=self.__build_stage0_activity(),
            command_not_found="**Error:** The bot could not find the command `/{}`.",
            command_has_no_subcommands="**Error:** The command `/{}` has no subcommands."
        )

        self.init_stage = 0

    def entrypoint(self):
        if self.config.get('apiKey') is None:
            if self.__daemon_mode:
                LOG.critical("The bot does not have an API key assigned to it. Please run the bot without a "
                             "daemon to set the API key.")
                exit(1)
            else:
                print("The bot does not have an API key defined. Please enter one below...")
                key = input("Discord API Key? ")

                self.config.set('apiKey', key)
                print("The API key has been set!")

        LOG.info("The bot's log path is: {}".format(self.__log_path))

        if self.__daemon_mode:
            LOG.info("The bot is currently loaded in Daemon Mode. In Daemon Mode, certain functionalities are "
                     "slightly altered to better utilize the headless environment.")

        self.run(self.config['apiKey'])

        if self.config.get("restartReason") is not None:
            print("READY FOR RESTART!")
            os.execl(sys.executable, *([sys.executable] + sys.argv))

    def __build_stage0_activity(self):
        mapping = {
            "admin": "Restarting...",
            "update": "Updating...",
            None: "Starting"
        }

        restart_reason = self.config.get("restartReason")

        if restart_reason is not None:
            self.config.delete("restartReason")

        return discord.Activity(
            name=mapping.get(restart_reason, "Starting..."),
            type=discord.ActivityType.playing
        )

    def __initialize_logger(self):
        # Build the to-file logger HuskyBot uses.
        file_log_handler = HuskyUtils.CompressingRotatingFileHandler(self.session_store.get('logPath'),
                                                                     maxBytes=(1024 ** 2) * 5,
                                                                     backupCount=5,
                                                                     encoding='utf-8')
        file_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

        # Build the to-stream logger
        stream_log_handler = logging.StreamHandler(sys.stdout)
        if self.__daemon_mode:
            stream_log_handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))

        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[file_log_handler, stream_log_handler]
        )

        bot_logger = logging.getLogger("HuskyBot")
        bot_logger.setLevel(logging.INFO)

        return bot_logger

    async def __init_guild_lock(self):
        if self.config.get('guildId') is not None:
            for guild in self.guilds:  # type: discord.Guild
                if guild.id != self.config.get('guildId'):
                    LOG.warning(f"Bot was in unauthorized guild {guild.name} ({guild.id}). "
                                f"Leaving the guild.")
                    await guild.leave()

        elif len(self.guilds) > 0:
            LOG.critical("Bot account is in multiple guilds without being in developer mode or "
                         "having a guild set. Please remove this account from all guilds, or specify "
                         "a guild ID in the config.")
            exit(127)

    async def __initialize_webserver(self):
        http_config = self.config.get('httpConfig', {
            "host": "localhost",
            "port": "9339",
            "ssl_cert": None
        })

        ssl_context = None
        if http_config.get('ssl_cert', None) is not None:
            with open(http_config.get('ssl_cert', 'certs/cert.pem'), 'r') as cert:
                ssl_context = ssl.SSLContext()
                ssl_context.load_cert_chain(cert.read())

        for method in ["GET", "HEAD", "POST", "PATCH", "PUT", "DELETE", "VIEW"]:
            self.webapp.router.add_route(method, '/{tail:.*}', HuskyHTTP.get_router().handle(self))

        runner = web.AppRunner(self.webapp)
        await runner.setup()
        site = web.TCPSite(runner, host=http_config['host'], port=http_config['port'], ssl_context=ssl_context)
        await site.start()
        LOG.info(f"Started {'HTTPS' if ssl_context is not None else 'HTTP'} server at "
                 f"{http_config['host']}:{http_config['port']}, now listening...")

    async def __init_load_plugins(self):
        sys.path.insert(1, os.getcwd() + "/plugins/")

        self.load_extension('Base')
        self.load_extension('BotAdmin')

        plugin_list = self.config.get('plugins', [])

        if self.config.get("developerMode", False):
            LOG.setLevel(logging.DEBUG)
            plugin_list = ["Debug"] + plugin_list

        for plugin in plugin_list:
            # noinspection PyBroadException
            try:
                self.load_extension(plugin)
            except Exception:
                await self.on_error('initialize/load_plugin/' + plugin)

    async def __init_inform_restart(self):
        if self.config.get("restartNotificationChannel") is not None:
            channel = self.get_channel(self.config.get("restartNotificationChannel"))
            await channel.send(embed=discord.Embed(
                title=Emojis.REFRESH + " Bot Manager",
                description="The bot has been successfully restarted, and is now online.",
                color=Colors.SUCCESS
            ))
            self.config.delete("restartNotificationChannel")

    async def init_stage1(self):
        """
        Initialize the bot logger and other critical services. Init stage 1 will *not* re-run if it has executed.
        """

        if self.init_stage >= 1:
            LOG.warning("The system attempted to re-run initialization stage 1. Did the network or "
                        "similar die?")
            return

        LOG.info(f"HuskyBot is online, running discord.py {discord.__version__}. Initializing and "
                 f"loading modules...")

        if not self.developer_mode:
            await self.__init_guild_lock()

        await self.__initialize_webserver()
        await self.__init_load_plugins()

        await self.__init_inform_restart()

        self.init_stage = 1
        LOG.info("The bot has been initialized. Ready to process commands and events.")

    async def on_ready(self):
        # Attempt to initialize the bot
        await self.init_stage1()

        ready_presence = self.config.get('presence', {"game": "HuskyBot", "type": 2, "status": "dnd"})

        await self.change_presence(
            activity=discord.Activity(name=ready_presence['game'], type=ready_presence['type']),
            status=discord.Status[ready_presence['status']]
        )

    async def on_guild_join(self, guild: discord.Guild):
        if self.config.get('guildId') is None:
            self.config.set('guildId', guild.id)
            LOG.info(f"This bot has been locked to {guild.name} (ID {guild.id})!")
            return

        if not self.developer_mode:
            if guild.id != self.config.get("guildId"):
                LOG.warning(f"The bot has joined an unauthorized guild {guild.name} ({guild.id}). "
                            f"The bot is leaving the guild...")
                await guild.leave()

    async def on_message(self, message: discord.Message):
        author = message.author
        if not HuskyUtils.should_process_message(message):
            return

        if message.content.startswith(self.command_prefix):
            if (author.id in self.config.get('userBlacklist', [])) and (author.id not in HuskyStatics.DEVELOPERS):
                LOG.info("Blacklisted user %s attempted to run command %s", message.author, message.content)
                return

            if message.content.lower().split(' ')[0][1:] in self.config.get('ignoredCommands', []):
                LOG.info("User %s ran an ignored command %s", message.author, message.content)
                return

            if message.content.lower().split(' ')[0].startswith('/r/'):
                LOG.info("User %s linked to subreddit %s, ignoring command", message.author, message.content)
                return

            if self.session_store.get('lockdown', False) and (author.id not in HuskyStatics.DEVELOPERS):
                LOG.info("Lockdown mode is enabled for the bot. Command blocked.")
                return

            LOG.info("User %s ran %s", author, message.content)

            await self.process_commands(message)

    async def on_error(self, event_method, *args, **kwargs):
        exception = sys.exc_info()

        channel = self.config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

        if channel is None:
            LOG.warning('A logging channel is not set up! Error messages will not be forwarded to '
                        'Discord.')
            raise exception

        channel = self.get_channel(channel)

        if isinstance(exception, discord.HTTPException) and exception.code == 502:
            LOG.error(f"Got HTTP status code {exception.code} for method {event_method} - Discord is "
                      f"likely borked now.")
        else:
            LOG.error('Exception in method %s:\n%s', event_method, traceback.format_exc())

            try:
                embed = discord.Embed(
                    title="Bot Exception Handler",
                    description="Exception in method `{}`:\n```{}```".format(
                        event_method,
                        HuskyUtils.trim_string(traceback.format_exc().replace('```', '`\u200b`\u200b`'), 1500)
                    ),
                    color=Colors.DANGER
                )

                dev_ping = self.config.get("specialRoles", {}).get(SpecialRoleKeys.BOT_DEVS.value)

                if dev_ping is not None:
                    dev_ping = f"&{dev_ping}"
                else:
                    dev_ping = HuskyStatics.DEVELOPERS[0]

                await channel.send("<@{}>, an error has occurred with the bot. See attached "
                                   "embed.".format(dev_ping),
                                   embed=embed)
            except Exception as e:
                LOG.critical("There was an error sending an error to the error channel.\n " + str(e))
                raise e

    async def on_command_error(self, ctx, error: commands.CommandError):
        command_name = ctx.message.content.split(' ')[0][1:]

        error_string = HuskyUtils.trim_string(str(error).replace('```', '`\u200b`\u200b`'), 128)

        # Handle cases where the calling user is missing a required permission.
        if isinstance(error, commands.MissingPermissions):
            if self.config.get("developerMode", False):
                await ctx.send(embed=discord.Embed(
                    title="Command Handler",
                    description=f"**You are not authorized to run `/{command_name}`:**\n```{error_string}```\n\n"
                                f"Please ask a staff member for assistance.",
                    color=Colors.DANGER
                ))

            LOG.error("Encountered permission error when attempting to run command %s: %s",
                      command_name, str(error))

        # Handle cases where the command is disabled.
        elif isinstance(error, commands.DisabledCommand):
            if self.config.get("developerMode", False):
                embed = discord.Embed(
                    title="Command Handler",
                    description=f"**The command `/{command_name}` does not exist.** See `/help` for valid commands.",
                    color=Colors.DANGER
                )

                await ctx.send(embed=embed)

            LOG.error("Command %s is disabled.", command_name)

        # Handle cases where the command does not exist.
        elif isinstance(error, commands.CommandNotFound):
            if self.config.get("developerMode", False):
                await ctx.send(embed=discord.Embed(
                    title="Command Handler",
                    description=f"**The command `/{command_name}` does not exist.** See `/help` for valid commands.",
                    color=Colors.DANGER
                ))

            LOG.error("Command %s does not exist to the system.", command_name)

        # Handle cases where a prerequisite command check failed to execute
        elif isinstance(error, commands.CheckFailure):
            await ctx.send(embed=discord.Embed(
                title="Command Handler",
                description=f"**The command `/{command_name}` failed an execution check.** Additional information may "
                            f"be provided below.",
                color=Colors.DANGER
            ).add_field(name="Error Log", value="```" + error_string + "```", inline=False))

            LOG.error("Encountered check failure when attempting to run command %s: %s",
                      command_name, str(error))

        # Handle cases where a command is run over a Direct Message without working over DMs
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send(embed=discord.Embed(
                title="Command Handler",
                description=f"**The command `/{command_name}` may not be run in a DM.** See `/help` for valid "
                            f"commands.",
                color=Colors.DANGER
            ))

            LOG.error("Command %s may not be run in a direct message!", command_name)

        # Handle cases where a command is run missing a required argument
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=discord.Embed(
                title="Command Handler",
                description=f"**The command `/{command_name}` could not run, because it is missing arguments.**\n"
                            f"See `/help {command_name}` for the arguments required.",
                color=Colors.DANGER
            ).add_field(name="Missing Parameter", value="`" + error_string.split(" ")[0] + "`", inline=True))
            LOG.error("Command %s was called with the wrong parameters.", command_name)
            return

        # Handle cases where an argument can not be parsed properly.
        elif isinstance(error, commands.BadArgument):
            await ctx.send(embed=discord.Embed(
                title="Command Handler",
                description=f"**The command `/{command_name}` could not understand the arguments given.**\n"
                            f"See `/help {command_name}` and the error below to fix this issue.",
                color=Colors.DANGER
            ).add_field(name="Error Log", value="```" + error_string + "```", inline=False))

            LOG.error("Command %s was unable to parse arguments: %s", command_name, str(error))
            LOG.error(''.join(traceback.format_exception(type(error), error, error.__traceback__)))

        # Handle cases where the bot is missing a required execution permission.
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(embed=discord.Embed(
                title="Command Handler",
                description=f"**The command `/{command_name}` could not execute successfully, as the bot does not have "
                            f"a required permission.**\nPlease make sure that the bot has the following permissions: " +
                            "`{}`".format(', '.join(error.missing_perms)),
                color=Colors.DANGER
            ))

            LOG.error("Bot is missing permissions %s to execute command %s", error.missing_perms, command_name)

        # Handle commands on cooldown
        elif isinstance(error, commands.CommandOnCooldown):
            seconds = round(error.retry_after)
            tx = "{} {}".format(seconds, "second" if seconds == 1 else "seconds")

            await ctx.send(embed=discord.Embed(
                title="Command Handler",
                description=f"**The command `/{command_name}` has been run too much recently!**\nPlease wait **{tx}** "
                            f"until trying again.",
                color=Colors.DANGER
            ))

            LOG.error("Command %s was on cooldown, and is unable to be run for %s seconds. Cooldown: %s",
                      command_name, round(error.retry_after, 0), error.cooldown)

        # Handle any and all other error cases.
        else:
            await ctx.send(embed=discord.Embed(
                title="Bot Error Handler",
                description="The bot has encountered a fatal error running the command given. Logs are below.",
                color=Colors.DANGER
            ).add_field(name="Error Log", value="```" + error_string + "```", inline=False))
            LOG.error("Error running command %s. See below for trace.\n%s",
                      ctx.message.content,
                      ''.join(traceback.format_exception(type(error), error, error.__traceback__)))

            if command_name.lower() in ["eval", "feval", "requestify"]:
                LOG.info(f"Suppressed critical error reporting for command {command_name}")
                return

            # Send it over to the main error logger as well.
            raise error


if __name__ == '__main__':
    bot = HuskyBot()
    bot.entrypoint()
