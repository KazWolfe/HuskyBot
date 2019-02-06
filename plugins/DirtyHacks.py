import json
import logging
import os
import random
import re
import tempfile

import aiohttp
import discord
from PIL import Image, ImageSequence
from discord.ext import commands

from HuskyBot import HuskyBot
from libhusky import HuskyUtils
from libhusky.HuskyStatics import *

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class DirtyHacks:
    """
    A series of dirty hacks used to bypass Discord's stupidity.

    Discord is dumb.
    """

    def __init__(self, bot: HuskyBot):
        self.bot = bot
        self._config = bot.config

        self._http_session = aiohttp.ClientSession(loop=bot.loop)

        LOG.info("Loaded plugin!")

    def __unload(self):
        self.bot.loop.create_task(self._http_session.close())

    async def on_message(self, message: discord.Message):
        if not HuskyUtils.should_process_message(message):
            return

        await self.kill_abusive_gifs(message)
        # await self.calculate_entropy(message)

    async def kill_abusive_gifs(self, message: discord.Message):
        def undersized_gif_check(file) -> bool:
            # Try to see if this gif is too big for its size (over 5000px^2, but less than 1mb)
            (width, height) = HuskyUtils.get_image_size(file.name)

            if (width > 5000) and (height > 5000) and os.path.getsize(file.name) < 1000000:
                LOG.info("Found a GIF that exceeds sane size limits (over 5000px^2, but under 1mb)")
                return True

            return False

        def too_large_frame_check(file) -> bool:
            # Try to see if this gif has a too big frame
            im = Image.open(file.name)
            frames = ImageSequence.Iterator(im)
            mx, my = im.size
            for frame in frames:
                x, y = frame.tile[0][1][2:]

                if (mx + my) > 0 and ((x > 2 * mx) or (y > 2 * my)):
                    # We found a frame that's way too big
                    LOG.info("Found a GIF with an obscenely large frame.")
                    return True

            return False

        matches = re.findall(Regex.URL_REGEX, message.content, re.IGNORECASE)

        for attach in message.attachments:  # type: discord.Attachment
            matches.append(attach.proxy_url)
            matches.append(attach.url)

        # If a message has no links, abort right now.
        if matches is None or len(matches) == 0:
            return

        # deduplicate the list
        matches = list(set(matches))

        for match in matches:  # type: str
            match = ''.join(match)

            if not match.endswith('.gif'):
                return

            with tempfile.NamedTemporaryFile(suffix=".gif") as f:
                async with self._http_session.get(match) as r:  # type: aiohttp.ClientResponse
                    if r.status != 200:
                        LOG.warning("Failed to check GIF, because status code was not 200")
                        return

                    if not r.headers.get('content-type', 'application/octet-stream').startswith('image'):
                        LOG.warning("Failed to check GIF, because content type was not image")
                        return

                    img_data = await r.read()

                f.write(img_data)
                f.flush()

                LOG.info(f"Found potentially dangerous GIF, saved at {f.name}")
                if undersized_gif_check(f) or too_large_frame_check(f):
                    await message.delete()
                    break

                f.delete()

    async def calculate_entropy(self, message: discord.Message):
        if message.content is None or message.content == "":
            return

        # run on about 20% of messages
        if random.randint(1, 5) != 3:
            return

        entropy = HuskyUtils.calculate_str_entropy(message.content)

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


def setup(bot: HuskyBot):
    bot.add_cog(DirtyHacks(bot))
