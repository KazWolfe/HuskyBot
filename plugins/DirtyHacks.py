import logging
import os
import re
import uuid

import discord
import requests
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfUtils
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class DirtyHacks:
    """
    A series of dirty hacks used to bypass Discord's stupidity.

    Discord is dumb.
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()

        LOG.info("Loaded plugin!")

    async def on_message(self, message: discord.Message):
        try:
            await self.kill_crashing_gifs(message)
        except:
            return

    async def kill_crashing_gifs(self, message: discord.Message):
        matches = re.findall(Regex.URL_REGEX, message.content, re.IGNORECASE)

        for attach in message.attachments:  # type: discord.Attachment
            matches.append(attach.proxy_url)
            matches.append(attach.url)

        # If a message has no links, abort right now.
        if matches is None or len(matches) == 0:
            return

        print(matches)

        for match in matches:  # type: str
            match = ''.join(match)

            if not match.endswith('.gif'):
                return

            image_name = '/tmp/{}.gif'.format(str(uuid.uuid4()))
            img_data = requests.get(match).content

            with open(image_name, 'wb') as handler:
                handler.write(img_data)

            (width, height) = WolfUtils.get_image_size(image_name)

            # Image is larger than 5000 px * 5000 px but *less* than 1 MB
            if (width > 5000) and (height > 5000) and os.path.getsize(image_name) < 1_000_000:
                await message.delete()


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(DirtyHacks(bot))
