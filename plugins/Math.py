import json
import logging

import aiohttp
import discord
from discord.ext import commands

from HuskyBot import HuskyBot
from libhusky.HuskyStatics import *

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Math:
    def __init__(self, bot: HuskyBot):
        self.bot = bot
        self._config = bot.config

        self._http_session = aiohttp.ClientSession(loop=bot.loop)

        LOG.info("Loaded plugin!")

    def __unload(self):
        self.bot.loop.create_task(self._http_session.close())

    @commands.command(name="latex", brief="Generate and render some LaTeX code [EXPERIMENTAL]")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def render_tex(self, ctx: commands.Context, *, latex: str):
        """
        The LaTeX command allows you to write descriptive/advanced mathematical equations and information, and have the
        bot display it as an image in a response.

        All LaTeX code is wrapped in the following template before being sent:

            \\documentclass{article}

            \\usepackage{color} \\color{white}
            \\begin{document}

            <your latex here>

            \\pagenumbering{gobble}
            \\end{document}

        TeX rendering is handled by DXSmiley's rtex (https://github.com/DXsmiley/rtex) - http://rtex.probablyaweb.site/
        """

        api_url = "http://rtex.probablyaweb.site/api/v2"

        if latex.startswith('```') and latex.endswith("```"):
            latex = latex[3:-3]

            if latex.startswith('tex'):
                latex = latex[3:]

        latex_wrapped = f"\\documentclass{{article}}\n\n" \
                        f"\\usepackage{{color}} \\color{{white}}\n" \
                        f"\\begin{{document}}\n\n" \
                        f"{latex}\n\n" \
                        f"\\pagenumbering{{gobble}}\n" \
                        f" \\end{{document}}"

        response = await self._http_session.post(api_url, data={
            "code": latex_wrapped,
            "format": "png"
        })

        response_data = json.loads(await response.text())
        was_successful = response.status == 200 and response_data.get('status') == 'success'

        response.close()

        embed = discord.Embed(
            title="Rendered LaTeX",
            color=Colors.INFO if was_successful else Colors.DANGER
        )

        if was_successful:
            embed.set_footer(text="Rendered by rTEX API",
                             icon_url="http://rtex.probablyaweb.site/static/favicon.png")
            embed.set_image(url=api_url + "/" + response_data['filename'])
        else:
            embed.add_field(
                name="Rendering Error",
                value="There was an issue rendering your TeX. Please check your code to ensure that it is error-free. "
                      "You may use [the online implementation](http://rtex.probablyaweb.site/) to try out your TeX "
                      "code.\n\nThe rendering service may also be offline or experiencing difficulties.")

        await ctx.send(embed=embed)


def setup(bot: HuskyBot):
    bot.add_cog(Math(bot))
