from __future__ import annotations

import asyncio
import ssl
from typing import TYPE_CHECKING

from aiohttp import web

from libhusky import HuskyHTTP

if TYPE_CHECKING:
    from HuskyBot import HuskyBot

import logging

LOG = logging.getLogger("HuskyBot." + __name__)


async def __initialize_webserver(application: web.Application, bot: HuskyBot):
    # todo: load from somewhere else?
    http_config = {
        "host": "127.0.0.1",
        "port": "9339",
        "ssl_cert": None
    }

    ssl_context = None
    if http_config.get('ssl_cert', None) is not None:
        with open(http_config.get('ssl_cert', 'certs/cert.pem'), 'r') as cert:
            ssl_context = ssl.SSLContext()
            ssl_context.load_cert_chain(cert.read())

    # Abuse the hell out of aiohttp's own router to load in HuskyRouter.
    application.router.add_route('*', '/{tail:.*}', HuskyHTTP.get_router().handle(bot))

    runner = web.AppRunner(application)
    await runner.setup()
    site = web.TCPSite(runner, host=http_config['host'], port=http_config['port'], ssl_context=ssl_context)
    await site.start()
    LOG.info(f"Started {'HTTPS' if ssl_context is not None else 'HTTP'} server at "
             f"{http_config['host']}:{http_config['port']}, now listening...")


def initialize_webserver(bot: HuskyBot, loop: asyncio.AbstractEventLoop):
    application = web.Application()

    asyncio.ensure_future(__initialize_webserver(application, bot), loop=loop)

    return application
