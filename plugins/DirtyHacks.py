import json
import logging
import os
import random
import re
import tempfile

import aiohttp
import discord
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
        self.bot = bot
        self._config = WolfConfig.get_config()

        self._http_session = aiohttp.ClientSession()

        LOG.info("Loaded plugin!")

    def __unload(self):
        self._http_session.close()

    async def on_message(self, message: discord.Message):
        if not WolfUtils.should_process_message(message):
            return

        await self.kill_crashing_gifs(message)
        # await self.calculate_entropy(message)

    async def kill_crashing_gifs(self, message: discord.Message):
        matches = re.findall(Regex.URL_REGEX, message.content, re.IGNORECASE)

        for attach in message.attachments:  # type: discord.Attachment
            matches.append(attach.proxy_url)
            matches.append(attach.url)

        # If a message has no links, abort right now.
        if matches is None or len(matches) == 0:
            return

        for match in matches:  # type: str
            match = ''.join(match)

            if not match.endswith('.gif'):
                return

            with tempfile.NamedTemporaryFile() as f:
                async with self._http_session.get(match) as r:  # type: aiohttp.ClientResponse
                    if r.status != 200:
                        return

                    if not r.headers.get('content-type', 'application/octet-stream').startswith('image'):
                        return

                    img_data = await r.read()

                f.write(img_data)
                f.flush()

                (width, height) = WolfUtils.get_image_size(f.name)

                # Image is larger than 5000 px * 5000 px but *less* than 1 MB
                if (width > 5000) and (height > 5000) and os.path.getsize(f.name) < 1000000:
                    await message.delete()

    async def calculate_entropy(self, message: discord.Message):
        if message.content is None or message.content == "":
            return

        # run on about 20% of messages
        if random.randint(1, 5) != 3:
            return

        entropy = WolfUtils.calculate_str_entropy(message.content)

        clean_content = message.content.replace('\n', ' // ')
        s = clean_content if len(clean_content) < 20 else f"{clean_content[:20]}..."

        LOG.info(f"[EntropyCalc] Message {message.id} in #{message.channel.name} ({s}) has "
                 f"length={len(message.content)} and entropy {entropy}.")

        with open("logs/entropy.log", 'a') as f:
            f.write(json.dumps({
                "text": message.content,
                "entropy": entropy,
                "length": len(message.content)
            }) + "\n")

    @commands.command(name="disableHacks", brief="Disable DirtyHacks")
    @commands.has_permissions(manage_messages=True)
    async def disable_hacks(self, ctx: commands.Context):
        config: list = self._config.get('plugins', [])

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
