import asyncio
import datetime
import logging
import os
import sys

import discord
import tortoise
from discord.ext import commands

from libhusky.HuskyStatics import *
from libhusky.discordpy import ErrorHandler, ShardManager
from libhusky.discordpy.HuskyHelpFormatter import HuskyHelpFormatter
from libhusky.helpers import DatabaseHelper, RedisHelper, LoggingHelper, HTTPServerHelper
from libhusky.util import HuskyConfig, SuperuserUtil
from libhusky.util.UtilClasses import InitializationState

LOG = logging.getLogger("HuskyBot.Core")


class HuskyBot(commands.AutoShardedBot):
    def __init__(self):
        # the loop needs to be initialized early
        _loop = asyncio.get_event_loop()

        self.init_stage = InitializationState.NOT_INITIALIZED

        self.developer_mode = os.environ.get('HUSKYBOT_DEVMODE', False)
        self.superusers = None

        self.session_store = HuskyConfig.get_session_store()

        # initialize logging subsystem
        self.__log_path = "logs/huskybot.log"
        self.logger = LoggingHelper.initialize_logger(self, self.__log_path)
        LOG.info("The bot's log path is: {}".format(self.__log_path))

        # datastore initialization and connection
        DatabaseHelper.initialize_database(_loop)
        self.redis = RedisHelper.initialize_redis()

        # shard controller and logic
        self.__shard_manager = ShardManager.ShardManager(self)
        shard_ids, shard_count = self.__shard_manager.register()

        # API server
        self.api_server = HTTPServerHelper.initialize_webserver(self, _loop)

        # todo: bring sharding logic in to redis, hook redis for this data.
        super().__init__(
            shard_count=shard_count,
            shard_ids=shard_ids,
            command_prefix="/",
            status=discord.Status.idle,
            activity=self.__build_stage0_activity(),
            command_not_found="**Error:** The bot could not find the command `/{}`.",
            command_has_no_subcommands="**Error:** The command `/{}` has no subcommands.",
            help_command=HuskyHelpFormatter(),
            loop=_loop
        )

        self.db = DatabaseHelper.block_wait_for_database(_loop)

        self.init_stage = InitializationState.INSTANTIATED

    def __build_stage0_activity(self):
        # ToDo: [PARITY] Add support for different types
        return discord.Activity(
            name=f"Starting HuskyBot...",
            type=discord.ActivityType.playing
        )

    def __load_plugins(self):
        # Add plugins to path, giving precedence to custom_plugins.
        sys.path.insert(1, os.getcwd() + "/custom_plugins/")
        sys.path.insert(2, os.getcwd() + "/plugins/")

        # load in key plugins (*guaranteed* to exist)
        self.load_extension('Base')
        if self.developer_mode:
            self.load_extension('Debug')

    def entrypoint(self):
        if os.environ.get('DISCORD_TOKEN'):
            LOG.debug("Loading API key from environment variable DISCORD_TOKEN.")
        else:
            LOG.critical("The API key for HuskyBot must be loaded via the DISCORD_TOKEN environment variable.")
            exit(1)

        if self.developer_mode:
            LOG.warning("!!! The bot is running in DEVELOPER MODE !!!")

        # load in plugins and everything else
        LOG.info(f"HuskyBot loading, running discord.py {discord.__version__}. Loading plugins...")
        self.__load_plugins()
        LOG.info(f"Plugins loaded.")

        # mark initialization state
        self.init_stage = InitializationState.LOADED

        # pass over to discord.py
        self.run(os.getenv('DISCORD_TOKEN'))

        LOG.info("Shutting down HuskyBot...")

    async def on_ready(self):
        # LOG.debug("HuskyBot.on_ready()")
        if self.init_stage == InitializationState.READY_RECEIVED:
            LOG.warning("The bot attempted to re-run on_ready() - did the network die or similar?")
            return

        # Generate any schemas that the system deems necessary
        await tortoise.Tortoise.generate_schemas(safe=True)

        # Load in application information
        if not self.session_store.get('appInfo'):
            app_info = await self.application_info()
            self.session_store.set("appInfo", app_info)
            LOG.debug("Loaded application info into local cache")

            # Load in superusers
            if not self.superusers:
                self.superusers = await SuperuserUtil.get_superusers(app_info)
                LOG.info(f"Superusers loaded: {self.superusers}")

        # We consider the initialization time to be the first execution
        if not self.session_store.get('initTime'):
            self.session_store.set('initTime', datetime.datetime.now())
            LOG.debug("Initialization time recorded to local cache")

        LOG.info("=== HuskyBot is online and ready to process events! ===")
        self.init_stage = InitializationState.READY_RECEIVED

        if StaticFeatureFlags.FF_SHIM_BOT_INIT:
            await self.change_presence(
                activity=discord.Activity(name="Discord", type=discord.ActivityType.listening),
                status=discord.Status.online
            )

    async def on_shard_ready(self, shard_id):
        # LOG.debug(f"HuskyBot.on_shard_ready({shard_id})")
        LOG.info(f"Shard ID {shard_id} online and receiving events. Target shard count is {self.shard_count}.")

        # ToDo: [PARITY] Better presence handler.
        await self.change_presence(
            activity=discord.Activity(name="/ commands", type=discord.ActivityType.listening),
            status=discord.Status.online,
            shard_id=shard_id
        )

    async def on_command_error(self, ctx, error: commands.CommandError):
        await ErrorHandler.get_instance().handle_command_error(ctx, error)

    async def on_error(self, event_method, *args, **kwargs):
        exception = sys.exc_info()

        if isinstance(exception, discord.HTTPException) and exception.code == 502:
            LOG.error(f"Got HTTP status code {exception.code} for method {event_method} - Discord is "
                      f"likely broken right now.")
        else:
            LOG.error('Exception in method %s!', event_method, exc_info=exception)

    async def close(self):
        if self.db:
            await tortoise.Tortoise.close_connections()
            LOG.debug("DB connection(s) shut down")

        await super().close()

        # Redis needs to be shut down _after_ the host goes down. Otherwise, we risk multiple responses for a single
        # event.
        if self.redis:
            self.__shard_manager.remove_host()
            self.redis.close()
            LOG.debug("Redis connection shut down")


if __name__ == '__main__':
    if os.name != "posix":
        # Critical logging isn't the best way to do this, as this is (technically) before the logger is initialized,
        # but it's still somewhat there. We just haven't hooked in our fancy features yet.
        LOG.critical("This application may only run on POSIX-compliant operating systems such as Linux or macOS.")
        exit(1)

    bot = HuskyBot()
    bot.entrypoint()
    LOG.info("Left entrypoint, bot has shut down. Goodbye, everybody!")
