from __future__ import annotations

# ToDo: This file has gotten very ugly and is in dire need of a refactor.

import contextvars
import json
import traceback
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

# weirdness, but this needs to be out of all closures.
LOG_CTX_O = contextvars.ContextVar('log_ctx', default={})


class ContextFilter(logging.Filter):
    def filter(self, record):
        current_context = LOG_CTX_O.get()

        if current_context:
            record.context = current_context
        else:
            record.context = ""

        return True


class JSONFormatter(logging.Formatter):
    def exception_processor(self, exc_info):
        exceptions = []  # list of dict of exceptions

        cur_exception = exc_info[1]
        while cur_exception:
            trace = []
            for frame in traceback.extract_tb(cur_exception.__traceback__):
                trace.append({
                    "file": frame.filename,
                    "lineno": frame.lineno,
                    "name": frame.name,
                    "line": frame.line
                })

            exceptions.append({
                "type": type(cur_exception).__name__,
                "message": traceback._some_str(cur_exception),
                "stacktrace": trace
            })

            cur_exception = cur_exception.__cause__

        exceptions.reverse()  # top of the chain is the first

        return exceptions

    def format(self, record: logging.LogRecord) -> str:
        r_dict: dict = record.__dict__

        my_record = {
            "timestamp": record.created,
            "levelname": record.levelname,
            "name": record.name,
            "message": record.message,
            "_python": {
                "pathname": record.pathname,
                "funcname": record.funcName,
                "line": record.lineno
            }
        }

        if r_dict.get("context"):
            my_record['context'] = r_dict.get('context')

        # ToDo: Fix this so it's more sane - exception should be a list of exceptions in the chain, or something.
        #       Traceback should be better too, something like each entry should be a list of dicts or at least a list
        #       of (sanely) formatted strings.
        if record.exc_info:
            my_record['exception'] = self.exception_processor(record.exc_info)

        return json.dumps(my_record)



def initialize_logger(bot: HuskyBot, log_path: str):
    # Build the to-file log handler
    file_log_handler = UtilClasses.CompressingRotatingFileHandler(log_path,
                                                                  maxBytes=LOG_FILE_SIZE_BYTES,
                                                                  backupCount=LOG_FILE_BACKUPS,
                                                                  encoding='utf-8')
    file_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    json_handler = logging.FileHandler("logs/huskylog.json")
    json_handler.setFormatter(JSONFormatter())

    # Build the to-stream (stdout) log handler
    stream_log_handler = logging.StreamHandler(sys.stdout)
    stream_log_handler.addFilter(ContextFilter())

    # ToDo: Build the logstash log handler

    # noinspection PyArgumentList
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(context)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[file_log_handler, stream_log_handler, json_handler]
    )

    bot_logger = logging.getLogger("HuskyBot")
    bot_logger.setLevel(logging.INFO)

    if bot.developer_mode:
        bot_logger.setLevel(logging.DEBUG)
        LOG.setLevel(logging.DEBUG)

    if DEBUG_DPY:
        discord_logger = logging.getLogger("discord")
        discord_logger.addFilter(ContextFilter())
        discord_logger.setLevel(logging.DEBUG)

    return bot_logger, LOG_CTX_O
