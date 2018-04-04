import asyncio
import logging
import random
from datetime import datetime

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


class Fun:
    """
    Useless plugin.

    // ToDo: Delete this.
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()
        LOG.info("Loaded plugin!")

    @commands.command(name="slap", brief="Slap a user silly!")
    async def slap(self, ctx: commands.Context, user: discord.Member = None):
        """
        Give a user a hearty slap with a trout (?)

        This command allows you to slap a specified user (by ping, user ID, etc.) with a trout of varying size depending
        on whichever is nearest the top of the fish pile.

        It is recommended that one does not slap the bot or the bot's developer.
        """

        if user is None:
            await ctx.send("\uD83D\uDC1F  ***{}*** *tried to slap someone with a large trout, but missed and hit "
                           "themselves!*".format(ctx.author.mention))
            return

        if user.id in [self.bot.user.id, 142494680158961664]:
            await(ctx.send(Emojis.WOLF + " *I slap {} around with a wolf. The wolf bites, dealing critical damage!*"
                           .format(ctx.author.mention)))
            return

        victim = user.mention

        if user == ctx.author:
            victim = "themselves"

        slap = random.randint(1, 40)

        if slap == 40:
            await ctx.send("\uD83D\uDC1F ***{}*** *slaps* ***{}*** *around with a rainbow trout!*"
                           .format(ctx.author.mention, victim))
        elif slap > 30:
            await ctx.send("\uD83D\uDC1F ***{}*** *bludgeons* ***{}*** *with a rather large trout!*"
                           .format(ctx.author.mention, victim))
        elif slap > 20:
            await ctx.send("\uD83D\uDC1F ***{}*** *slaps* ***{}*** *around with a large trout!*"
                           .format(ctx.author.mention, victim))
        elif slap > 10:
            await ctx.send("\uD83D\uDC1F ***{}*** *slaps* ***{}*** *around with a trout!*"
                           .format(ctx.author.mention, victim))
        elif slap > 1:
            await ctx.send("\uD83D\uDC1F ***{}*** *slaps* ***{}*** *around with a small trout!*"
                           .format(ctx.author.mention, victim))
        else:
            await ctx.send("\uD83D\uDC1F ***{}*** *annoys* ***{}*** *by waving a minnow in their face!*"
                           .format(ctx.author.mention, victim))

    @commands.command(name="hug", brief="Get a hug from the bot, or give a hug!")
    async def hug(self, ctx: commands.Context, target: discord.Member = None):
        """
        Hug a user in need of a hug.

        This command allows you to hug a user of their choice (provided you have permission to hug that user).

        If you hug yourself or do not specify a user to hug, the bot will attempt to hug you instead.
        """
        if target is None:
            target = ctx.author

        if target == ctx.author:
            await ctx.send("*Attempting to upload hug to {}. Please wait...*".format(target.mention))
            await ctx.trigger_typing()
            await asyncio.sleep(5)
            await ctx.send(embed=discord.Embed(
                title="Bot Error Handler",
                description="The bot has encountered a fatal error running the command given. Logs are below.",
                color=Colors.DANGER
            ).add_field(name="Error Log", value="```Command raised an exception: SentienceError: Bot does not have the "
                                                "required emotional capability to give hugs.```", inline=False))
            return

        if target.id == 336301511942340608 and ctx.author.id == 323365398546481154 \
                or target.id in [142494680158961664, 84374504964358144]:  # Anyone hugging kaz or clover
            await ctx.send(embed=discord.Embed(
                title="Hug Manager",
                description="You are not permitted to hug this user.",
                color=Colors.DANGER
            ))
            return

        if target == self.bot.user:
            await ctx.send("Sorry, I don't like hugs. Perhaps ear scritches instead?")
            return

        await ctx.send("*{} gives {} a hug. Aww!*".format(ctx.author.mention, target.mention))

    @commands.command(name="rate", brief="Rate another user based on attractiveness, craziness, and intelligence")
    @commands.has_permissions(view_audit_log=True)
    async def rate_user(self, ctx: commands.Context, member: discord.User):
        """
        The ultimate command for narcissists! Rate yourself or another member of the server!

        This command uses advanced math, coding, and algorithms to determine a user's Relative Hotness based on three
        metrics: Attractiveness, Craziness, and Intelligence.

        These three scores are then summed up (with craziness being inverted) into an Overall Hotness Score.

        Please note that this algorithm is very complicated and results may not be 100% accurate.
        """

        seed = 736580  # A certain wolfgirl...
        master_rng = random.Random((member.id + seed + datetime.utcnow().toordinal()) % seed)

        def get_value(user_value: int, imin: int, imax: int, dev: float):
            rng = random.Random(user_value - seed)

            result = round(rng.randint(imin, imax) + master_rng.gauss(0, dev), 2)

            if result > 10:
                return 10.00

            if result < 0:
                return 0.00

            return result

        attractiveness = 0.25

        if member.avatar is not None:
            attractiveness = get_value(int(member.avatar[2:], 16) % seed, 1, 10, 0.2575)

        craziness = get_value(int(member.discriminator), 1, 10, 0.2575)
        intelligence = get_value(member.id % seed, 1, 10, 0.2575)

        average_score = round((attractiveness + (10.0 - craziness) + intelligence) / 3, 2)

        if member == self.bot.user:
            attractiveness = 11.27
            craziness = 0
            intelligence = 16
            average_score = "HAWT AF"

        embed = discord.Embed(
            title="{} has an overall rating of {}!".format(member.display_name, average_score),
            description="The rating for for {} is ready!".format(member.mention),
            color=Colors.INFO
        )

        embed.add_field(name="Attractiveness",
                        value=str(Emojis.FIRE * round(attractiveness / 2)) + " ({})".format(attractiveness),
                        inline=False)
        embed.add_field(name="Craziness",
                        value=str(Emojis.SKULL * round(craziness / 2)) + " ({})".format(craziness),
                        inline=False)
        embed.add_field(name="Intelligence",
                        value=str(Emojis.BOOK * round(intelligence / 2)) + " ({})".format(intelligence),
                        inline=False)

        embed.set_thumbnail(url=member.avatar_url)

        await ctx.send(embed=embed)


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Fun(bot))
