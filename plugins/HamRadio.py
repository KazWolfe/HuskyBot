import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


class HamRadio:
    def __init__(self, bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()
        LOG.info("Loaded plugin!")

    @commands.group(pass_context=True)
    async def ham(self, ctx: discord.ext.commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid HamRadio command.")
            return

    @ham.command(name="register")
    async def registerCallsign(self, ctx: discord.ext.commands.Context, callsign: str):
        config = self._config.get('ham_radio', {})

        if config.get('callsigns') is None:
            config['callsigns'] = {}

        config['callsigns'][str(ctx.author.id)] = callsign

        self._config.set('ham_radio', config)

        await ctx.send("Set your callsign to {}!".format(callsign))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(HamRadio(bot))
