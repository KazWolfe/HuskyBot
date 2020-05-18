from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from HuskyBot import HuskyBot

import logging
import sys

from libhusky.util import UtilClasses

LOG = logging.getLogger("HuskyBot." + __name__)

LOG_FILE_SIZE_BYTES = 5 * (1024 ** 2)  # 5 MB
LOG_FILE_BACKUPS = 5

DEBUG_DPY = False


def initialize_logger(bot: HuskyBot, log_path: str):
    # Build the to-file log handler
    file_log_handler = UtilClasses.CompressingRotatingFileHandler(log_path,
                                                                  maxBytes=LOG_FILE_SIZE_BYTES,
                                                                  backupCount=LOG_FILE_BACKUPS,
                                                                  encoding='utf-8')
    file_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    # Build the to-stream (stdout) log handler
    stream_log_handler = logging.StreamHandler(sys.stdout)

    # ToDo: Build the logstash log handler

    # noinspection PyArgumentList
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[file_log_handler, stream_log_handler]
    )

    bot_logger = logging.getLogger("HuskyBot")
    bot_logger.setLevel(logging.INFO)

    if bot.developer_mode:
        bot_logger.setLevel(logging.DEBUG)
        LOG.setLevel(logging.DEBUG)

    if DEBUG_DPY:
        discord_logger = logging.getLogger("discord")
        discord_logger.setLevel(logging.DEBUG)

    return bot_logger
