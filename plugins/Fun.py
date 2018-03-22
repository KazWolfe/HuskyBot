import logging

import discord
import random

from datetime import datetime
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfUtils
from WolfBot.WolfStatics import Colors, ChannelKeys

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


class Fun:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()
        LOG.info("Loaded plugin!")

    @commands.command(name="slap", brief="Slap a user!")
    async def slap(self, ctx: commands.Context, user: discord.Member = None):
        if user is None:
            await ctx.send("***{}*** *tried to slap someone with a large trout, but missed and hit themselves!*"
                           .format(ctx.author.mention))
            return

        slap = random.randint(1, 40)

        if slap == 40:
            await ctx.send("***{}*** *slaps* ***{}*** *around with a rainbow trout!*"
                           .format(ctx.author.mention, user.mention))
        elif slap > 30:
            await ctx.send("***{}*** *slaps* ***{}*** *around with a rather large trout!*"
                           .format(ctx.author.mention, user.mention))
        elif slap > 20:
            await ctx.send("***{}*** *slaps* ***{}*** *around with a large trout!*"
                           .format(ctx.author.mention, user.mention))
        elif slap > 10:
            await ctx.send("***{}*** *slaps* ***{}*** *around with a trout!*"
                           .format(ctx.author.mention, user.mention))
        else:
            await ctx.send("***{}*** *slaps* ***{}*** *around with a rather small trout!*"
                           .format(ctx.author.mention, user.mention))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Fun(bot))
