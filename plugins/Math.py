import json
import logging

import aiohttp
import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Math:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()

        self._http_session = aiohttp.ClientSession()

        LOG.info("Loaded plugin!")

    def __unload(self):
        self._http_session.close()

    @commands.command(name="latex", brief="Generate and render some LaTeX code")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def render_tex(self, ctx: commands.Context, *, latex: str):
        """
        Send off some LaTeX for rendering. [EXPERIMENTAL]

        Take some LaTeX code (assuming a document), render it, and send it back to the chat. This command uses the rtex
        renderer by DXSmiley: https://github.com/DXsmiley/rtex.
        """

        api_url = "http://rtex.probablyaweb.site/api/v2"

        if latex.startswith('```') and latex.endswith("```"):
            latex = latex[3:-3]

            if latex.startswith('tex'):
                latex = latex[3:]

        latex_wrapped = f"\\documentclass{{article}}\n" \
                        f"\\usepackage{{color}}\n" \
                        f"\\color{{white}}\n" \
                        f"\\begin{{document}}\n" \
                        f"{latex}\n" \
                        f"\\pagenumbering{{gobble}}\n" \
                        f" \\end{{document}}"

        response = await self._http_session.post(api_url, data={
            "code": latex_wrapped,
            "format": "png"
        })

        response_data = json.loads(await response.text())
        was_successful = response.status == 200 and response_data.get('status') == 'success'

        embed = discord.Embed(
            title="Rendered LaTeX",
            color=Colors.INFO if was_successful else Colors.DANGER
        )

        if was_successful:
            embed.set_footer(text="LaTeX rendered by rTEX: rtex.probablyaweb.site")
            embed.set_image(url=api_url + "/" + response_data['filename'])
        else:
            embed.add_field(name="Rendering Error", value=response_data['description'])

        await ctx.send(embed=embed)


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Math(bot))
