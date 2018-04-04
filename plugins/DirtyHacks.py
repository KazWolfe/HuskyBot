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

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class DirtyHacks:
    """
    A series of dirty hacks used to bypass Discord's stupidity.

    Discord is dumb.
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot  # type: commands.Bot
        self._config = WolfConfig.get_config()

        LOG.info("Loaded plugin!")

    async def on_message(self, message: discord.Message):
        # noinspection PyBroadException
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
            if (width > 5000) and (height > 5000) and os.path.getsize(image_name) < 1000000:
                await message.delete()

            os.remove(image_name)

    @commands.command(name="disableHacks", brief="Disable DirtyHacks")
    @commands.has_permissions(manage_messages=True)
    async def disable_hacks(self, ctx: commands.Context):
        config = self._config.get('plugins', [])  # type: list

        if "DirtyHacks" in config:
            config.remove("DirtyHacks")
            self._config.set('plugins', config)

        self.bot.remove_cog("DirtyHacks")
        await ctx.send("DirtyHacks has been unloaded and disabled. "
                       "Paging <@142494680158961664> and <@84374504964358144>.")

    @commands.command(name="testHacks", brief="Test DirtyHacks")
    @commands.has_permissions(manage_messages=True)
    async def test_hacks(self, ctx: commands.Context):
        await ctx.send("DirtyHacks is running.")


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(DirtyHacks(bot))
