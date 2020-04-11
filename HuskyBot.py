import datetime
import logging
import os
import sys
import time

import discord
import redis
import sqlalchemy
from discord.ext import commands
from sqlalchemy import orm
from sqlalchemy.exc import DatabaseError

from libhusky.discordpy import ErrorHandler, ShardManager
from libhusky.discordpy.HuskyHelpFormatter import HuskyHelpFormatter
from libhusky.util import UtilClasses, HuskyConfig, SuperuserUtil

LOG = logging.getLogger("HuskyBot.Core")


class HuskyBot(commands.AutoShardedBot, metaclass=UtilClasses.Singleton):
    def __init__(self):
        self.developer_mode = os.environ.get('HUSKYBOT_DEVMODE', False)
        self.__daemon_mode = (os.getppid() == 1)
        self.superusers = None

        self.session_store = HuskyConfig.get_session_store()

        # initialize logging subsystem
        self.__log_path = "logs/huskybot.log"
        self.logger = self.__initialize_logger()
        LOG.info("The bot's log path is: {}".format(self.__log_path))

        # datastore initialization and connection
        self.__initialize_database()
        self.redis = self.__initialize_redis()

        # shard controller and logic
        self.__shard_manager = ShardManager.ShardManager(self)
        shard_ids, shard_count = self.__shard_manager.register()

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
        )

    async def close(self):
        LOG.info("Shutting down HuskyBot...")

        await super().close()

    def __build_stage0_activity(self):
        # ToDo: [PARITY] Add support for different types
        return discord.Activity(
            name="Starting...",
            type=discord.ActivityType.playing
        )

    def __initialize_database(self):
        try:
            c = f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}" \
                f"@db:5432/{os.environ['POSTGRES_DB']}"
            self.db = sqlalchemy.create_engine(c)
        except KeyError as e:
            LOG.critical("No database configuration was set for Husky!")
            raise e
        except DatabaseError as s:
            LOG.critical(f"Could not connect to the database! The error is as follows: \n{s}")
            raise s

        self.session_factory = sqlalchemy.orm.sessionmaker(bind=self.db)

    def __initialize_redis(self):
        conn = redis.Redis(
            host=os.environ['REDIS_HOST'],
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            password=os.getenv('REDIS_PASSWORD')
        )

        max_wait_time = 30

        LOG.debug("Waiting 30s for Redis to come online...", )
        for t in range(max_wait_time):
            if conn.ping():
                break
            time.sleep(1)
        else:
            LOG.critical("Redis didn't come up in 30 seconds!")
            raise ConnectionError("Redis hit timeout!")

        LOG.debug("Redis is online.")
        return conn

    def __initialize_logger(self):
        # Build the to-file logger HuskyBot uses.
        file_log_handler = UtilClasses.CompressingRotatingFileHandler(self.__log_path,
                                                                      maxBytes=(1024 ** 2) * 5,
                                                                      backupCount=5,
                                                                      encoding='utf-8')
        file_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

        # Build the to-stream logger
        stream_log_handler = logging.StreamHandler(sys.stdout)
        if self.__daemon_mode:
            stream_log_handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))

        # noinspection PyArgumentList
        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[file_log_handler, stream_log_handler]
        )

        bot_logger = logging.getLogger("HuskyBot")
        bot_logger.setLevel(logging.INFO)

        if self.developer_mode:
            bot_logger.setLevel(logging.DEBUG)
            LOG.setLevel(logging.DEBUG)

        return bot_logger

    def __load_modules(self):
        # Add modules to path, giving precedence to custom_modules.
        sys.path.insert(1, os.getcwd() + "/custom_plugins/")
        sys.path.insert(2, os.getcwd() + "/plugins/")

        # load in key modules (*guaranteed* to exist)
        self.load_extension('Base')
        if self.developer_mode:
            self.load_extension('Debug')

    def entrypoint(self):
        if os.environ.get('DISCORD_TOKEN'):
            LOG.debug("Loading API key from environment variable DISCORD_TOKEN.")
        else:
            LOG.critical("The API key for HuskyBot must be loaded via the DISCORD_TOKEN environment variable.")
            exit(1)

        if self.__daemon_mode:
            LOG.info("The bot is currently loaded in Daemon Mode. In Daemon Mode, certain functionalities are "
                     "slightly altered to better utilize the headless environment.")

        if self.developer_mode:
            LOG.info("The bot is running in DEVELOPER MODE! Some features may behave in unexpected ways or may "
                     "otherwise break. Some bot safety checks are disabled with this mode on.")

        # load in modules and everything else
        LOG.info(f"HuskyBot is online, running discord.py {discord.__version__}. Loading plugins...")
        self.__load_modules()
        LOG.info(f"Modules loaded.")

        # pass over to discord.py
        self.run(os.getenv('DISCORD_TOKEN'))

        LOG.info("Shutting down HuskyBot...")

        if self.db:
            self.db.dispose()
            LOG.debug("DB connection shut down")

        if self.redis:
            self.__shard_manager.remove_host()
            self.redis.close()
            LOG.debug("Redis shut down")

    async def on_ready(self):
        # Load in application information
        if not self.session_store.get('appInfo'):
            app_info = await self.application_info()
            self.session_store.set("appInfo", app_info)
            LOG.debug("Loaded application info into local cache.")

            # Load in superusers
            if not self.superusers:
                self.superusers = await SuperuserUtil.get_superusers(app_info)
                LOG.info(f"Superusers loaded: {self.superusers}")

        # We consider the initialization time to be the first execution
        if not self.session_store.get('initTime'):
            self.session_store.set('initTime', datetime.datetime.now())
            LOG.debug("Initialization time recorded to local cache!")

    async def on_shard_ready(self, shard_id):
        LOG.info(f"Shard ID {shard_id} online and receiving events. Target shard count is {self.shard_count}.")

        # ToDo: [PARITY] Better presence handler.
        await self.change_presence(
            activity=discord.Activity(name="/ commands", type=discord.ActivityType.listening),
            status=discord.Status.online,
            shard_id=shard_id
        )

    async def on_command_error(self, ctx, error: commands.CommandError):
        await ErrorHandler.CommandErrorHandler().handle_command_error(ctx, error)

    async def on_error(self, event_method, *args, **kwargs):
        exception = sys.exc_info()

        if isinstance(exception, discord.HTTPException) and exception.code == 502:
            LOG.error(f"Got HTTP status code {exception.code} for method {event_method} - Discord is "
                      f"likely borked now.")
        else:
            LOG.error('Exception in method %s!', event_method, exc_info=exception)


if __name__ == '__main__':
    if os.name != "posix":
        # Critical logging isn't the best way to do this, as this is (technically) before the logger is initialized,
        # but it's still somewhat there. We just haven't hooked in our fancy features yet.
        LOG.critical("This application may only run on POSIX-compliant operating systems such as Linux or macOS.")
        exit(1)

    bot = HuskyBot()
    bot.entrypoint()
    LOG.info("Left entrypoint, bot has shut down. Goodbye, everybody!")
