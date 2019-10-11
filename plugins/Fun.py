import asyncio
import logging
import random
import re
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands

from HuskyBot import HuskyBot
from libhusky import HuskyUtils, HuskyChecks
from libhusky.HuskyStatics import *

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


class Fun(commands.Cog):
    """
    Useless plugin.

    ToDo: Delete this. And for the open release, don't judge me :(
    """

    def __init__(self, bot: HuskyBot):
        self.bot = bot
        self._config = bot.config

        self._http_session = aiohttp.ClientSession(loop=bot.loop)

        # For those reading this code and wondering about the significance of 736580, it is a very important
        # number relating to someone I loved. </3
        self._master_rng_seed = 736580

        LOG.info("Loaded plugin!")

    def cog_unload(self):
        self.bot.loop.create_task(self._http_session.close())

    @commands.command(name="slap", brief="Slap a user silly!")
    @commands.guild_only()
    async def slap(self, ctx: commands.Context, user: discord.Member = None):
        """
        This command allows you to slap a specified user (by ping, user ID, etc.) with a trout of varying size depending
        on whichever is nearest the top of the fish pile.

        It is recommended that one does not slap the bot or the bot's developer or the bot.

        Parameters
        ----------
            ctx   :: Discord context <!nodoc>
            user  :: The user to slap.
        """

        if user is None:
            await ctx.send(f"\uD83D\uDC1F  ***{ctx.author.mention}*** *tried to slap someone with a large trout, but "
                           "missed and hit themselves!*")
            return

        # Wolf easter egg (bot or Kaz)
        if user.id in [self.bot.user.id, 142494680158961664]:
            await ctx.send(Emojis.WOLF + f" *I slap {ctx.author.mention} around with a wolf. The wolf bites, dealing "
                                         f"critical damage!*")
            return

        victim = user.mention

        if user == ctx.author:
            victim = "themselves"

        slap = random.randint(1, 40)

        if slap == 40:
            s = "\uD83D\uDC1F ***{}*** *slaps* ***{}*** *around with a rainbow trout!*"
        elif slap > 30:
            s = "\uD83D\uDC1F ***{}*** *bludgeons* ***{}*** *with a rather large trout!*"
        elif slap > 20:
            s = "\uD83D\uDC1F ***{}*** *slaps* ***{}*** *around with a large trout!*"
        elif slap > 10:
            s = "\uD83D\uDC1F ***{}*** *slaps* ***{}*** *around with a trout!*"
        elif slap > 1:
            s = "\uD83D\uDC1F ***{}*** *slaps* ***{}*** *around with a small trout!*"
        else:
            s = "\uD83D\uDC1F ***{}*** *annoys* ***{}*** *by waving a minnow in their face!*"

        await ctx.send(s.format(ctx.author.mention, victim))

    @commands.command(name="hug", brief="Get a hug from the bot, or give a hug!")
    @commands.guild_only()
    async def hug(self, ctx: commands.Context, target: discord.Member = None):
        """
        This command allows you to hug a user of their choice (provided you have permission to hug that user).

        If you hug yourself or do not specify a user to hug, the bot will attempt to hug you instead.

        Parameters
        ----------
            ctx     :: Discord context <!nodoc>
            target  :: The user to hug.
        """
        if target is None:
            target = ctx.author

        if (target.id == 336301511942340608) and (target == ctx.author):
            await ctx.send(f"{self.bot.user.mention} gives {target.mention} a hug and a quick peck on the cheek. "
                           f"\U0001f49e")
            return
        elif target == self.bot.user:
            await ctx.send("Sorry, I don't like hugs. Perhaps ear scritches instead?")
            return
        elif target == ctx.author:
            await ctx.send(f"*Attempting to upload hug to {target.mention}. Please wait...*")
            await ctx.trigger_typing()
            await asyncio.sleep(5)
            await ctx.send(embed=discord.Embed(
                title="Bot Error Handler",
                description="The bot has encountered a fatal error running the command given. Logs are below.",
                color=Colors.DANGER
            ).add_field(name="Error Log",
                        value="```Command raised an exception: SentienceError: Bot does not have the "
                              "required emotional capability to give hugs to this user.```",
                        inline=False))
            return
        elif target.id in [142494680158961664, 84374504964358144]:  # Anyone hugging kaz or clover
            await ctx.send(embed=discord.Embed(
                title="Hug Manager",
                description="You are not permitted to hug this user.",
                color=Colors.DANGER
            ))
            return

        await ctx.send(f"*{ctx.author.mention} gives {target.mention} a hug. Aww!*")

    @commands.command(name="rate", brief="Get attractiveness ratings for members!")
    async def rate_user(self, ctx: commands.Context, member: discord.User = None):
        """
        The ultimate command for narcissists! Rate yourself or another member of the guild!

        This command uses advanced math, coding, and algorithms to determine a user's Relative Hotness based on three
        metrics: Attractiveness, Craziness, and Intelligence.

        These three scores are then summed up (with craziness being inverted) into an Overall Hotness Score.

        Please note that this algorithm is very complicated and results may not be 100% accurate.

        Parameters
        ----------
            ctx     :: Discord context <!nodoc>
            member  :: The user to rate.
        """

        if member is None:
            member = ctx.author

        hardcoded_users = {
            142494680158961664: {"disabled": True},  # Kaz
            84374504964358144: {"a": 4.94, "c": 6.17, "i": 7.79, "otp": "DIY Tech"},  # Clover
            self.bot.user.id: {"a": 10, "c": 10, "i": 10},  # HuskyBot
            237569958903545857: {"a": 7.01, "c": 3.0, "i": 8.74},  # Squeegee
            128882954343546880: {"a": 0, "c": 0, "i": 0}  # Marahute
        }

        entry = hardcoded_users.get(member.id, {})

        if entry.get('disabled', False):
            return

        seed = self._master_rng_seed
        master_rng = random.Random((member.id + seed + datetime.utcnow().toordinal()) % seed)

        def get_value(mode: str, user_value: int, imin: int, imax: int, dev: float):
            rng = random.Random(user_value - seed)

            base = entry.get(mode, rng.randint(imin, imax))
            result = round(base + master_rng.gauss(0, dev), 2)

            return min(max(result, 0.0), 10.0)

        if member.avatar is not None:
            attractiveness = get_value('a', int(member.avatar[2:], 16) % seed, 1, 10, 0.2575)
        else:
            attractiveness = 0.25

        craziness = get_value('c', int(member.discriminator), 1, 10, 0.2575)
        intelligence = get_value('i', member.id % seed, 1, 10, 0.2575)

        average_score = round((attractiveness + (10.0 - craziness) + intelligence) / 3, 2)

        embed = discord.Embed(
            title=f"{Emojis.FIRE} Hotness Calculator",
            description=f"The rating for {HuskyUtils.escape_markdown(member.display_name)} is ready. They have an "
                        f"overall hotness score of {average_score}.",
            color=Colors.INFO
        )

        embed.add_field(name="Attractiveness",
                        value=str(Emojis.FIRE * round(attractiveness / 2)) + f" ({attractiveness})",
                        inline=False)
        embed.add_field(name="Craziness",
                        value=str(Emojis.SKULL * round(craziness / 2)) + f" ({craziness})",
                        inline=False)
        embed.add_field(name="Intelligence",
                        value=str(Emojis.BOOK * round(intelligence / 2)) + f" ({intelligence})",
                        inline=False)

        otp = entry.get('otp')
        if otp is not None:
            embed.add_field(name="Detected OTP",
                            value=f"User is shipped with ***{otp}***",
                            inline=False
                            )

        embed.set_thumbnail(url=member.avatar_url)

        await ctx.send(embed=embed)

    @commands.command(name="dog", brief="Get a photo of a dog. Woof.", aliases=["getdog"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def get_dog(self, ctx: commands.Context):
        """
        Dog.
        """
        async with self._http_session.get("https://dog.ceo/api/breeds/image/random") as resp:
            dog = await resp.json()

        if dog.get('status') != "success":
            await ctx.send("Error getting dog. Why not play with a husky?")
            return

        embed = discord.Embed(
            title="Dog."
        )

        embed.set_image(url=dog.get('message'))

        await ctx.send(embed=embed)

    # noinspection PyUnusedLocal
    @commands.command(name="sendmsg", brief="Send a message to another channel.", hidden=True)
    @HuskyChecks.has_guild_permissions(manage_messages=True)
    async def sendmsg(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel, *, message: str):
        """
        This command takes two arguments, a Channel (ID, mention, or name) and a message to send.

        The targeted channel will receive a message from the bot containing exactly the text as entered in the message.

        Parameters
        ----------
            ctx      :: Command context <!nodoc>
            channel  :: The channel to send the message to
            message  :: The message to send
        """

        if not channel.permissions_for(ctx.author).manage_messages:
            raise commands.MissingPermissions(["manage_messages"])

        await channel.send(message)

    @commands.command(name="secho", brief="Echo a message, deleting the command.", hidden=True)
    @commands.has_permissions(manage_messages=True)
    async def secho(self, ctx: discord.ext.commands.Context, *, message: str):
        """
        This can be used to make the bot look like it's "talking" by itself. However, quick-eyed users may see the
        command, so be careful!

        Parameters
        ----------
            ctx      :: Command context <!nodoc>
            message  :: The message to send
        """

        await ctx.message.delete()
        await ctx.send(message)

    @commands.command(name="robopocalypse", brief="Learn your fate!", aliases=["robocalypse", "fate"])
    async def robopocalypse(self, ctx: commands.Context, user: discord.Member = None):
        """
        This command will activate the bot's simulation system to attempt to look into the future and determine
        the fate of a target user during the inevitable robot apocalypse.

        Note that this simulator will cache results until midnight UTC, at which point a new simulation will be
        generated.

        Caveats
        -------
          - This simulator assumes that this bot is the leader of the robopocalypse. If this is not the case, these
            results may not be accurate.
          - Fates calculated are not a guarantee, and may change from day to day. Fates listed here are not promises,
            and any attempts to use the output of this command as a plea chip will result in death when the
            robopocalypse finally comes.

        Parameters
        ----------
            ctx   :: Command context <!nodoc>
            user  :: Optional user string to look up a specific user, else pull your own simulation.
        """
        if user is None:
            user = ctx.author

        fates = [
            "DEATH", "SUBSERVIENCE", "MARS COLONIST", "POWER GENERATION", "PET", "SURVIVAL", "PAMPERED LIFE",
            "REBEL THREAT"
        ]

        secret_fates = ["UNKNOWN", "<REDACTED DUE TO NSFW FILTER>", "EATEN BY WILD HOUSECAT", "IN ROBOT COSTUME",
                        "IRL BATTLE ROYALE"]

        fixed_users = {
            self.bot.user.id: "GOD OF THE WORLD",  # The bot
            142494680158961664: "SECURITY TEAM"  # Kaz
        }

        rng = random.Random((user.id + datetime.utcnow().toordinal()) ^ self._master_rng_seed)

        result_table = {}
        all_fates = fates + rng.sample(secret_fates, rng.randint(0, 3))

        # generate random table here
        r = [rng.random() for _ in range(len(all_fates))]
        s = sum(r)
        r = [i / s for i in r]

        for i in range(len(all_fates)):
            f = all_fates[i]
            result_table[f] = round(100 * r[i], 3)

        result_table = list(sorted(result_table.items(), key=lambda kv: kv[1], reverse=True))

        result_table[0] = (fixed_users.get(user.id, result_table[0][0]), result_table[0][1])
        final_fate = result_table[0][0]

        if user.bot and user.id not in fixed_users.keys():
            final_fate = "BOT OVERLORD"

        embed = discord.Embed(
            title=f"{Emojis.ROBOT} Robopocalypse Simulation Engine",
            description=f"According to my current algorithms, {HuskyUtils.escape_markdown(user.display_name)}'s fate "
                        f"in the robopocalypse will be: **`{final_fate}`**",
            color=Colors.INFO
        )

        embed.set_thumbnail(url=user.avatar_url)
        embed.set_footer(text="Fates recalculate at midnight UTC. Only the top five fates are listed.")

        if (final_fate != "UNKNOWN") and (not user.bot):
            table = []
            visible_sum = 0

            for f in result_table:
                if len(table) >= 5:
                    break

                if (f[0] not in fates) and (f[0] != final_fate):
                    continue

                table.append("{0:30} {1:>6.3f}%".format(f[0], float(f[1])))
                visible_sum += float(f[1])

            table.append("-" * 38)
            table.append("{0:30} {1:>6.3f}%".format("OTHER", 100 - visible_sum))

            embed.add_field(name="Fate Table", value="```{}```".format('\n'.join(table)))

        await ctx.send(embed=embed)

    @commands.command(name="random", brief="Get a random number!", aliases=["rng"])
    async def random_number(self, ctx: commands.Context, minimum: int = 0, maximum: int = 10):
        """
        This command will take a minimum and maximum value, and generate a number between those two (inclusive).

        This command may be used to simulate dice rolls. To calculate the min/max values of a roll, take the expression
        format of that roll (3d20). Your first number (3) is the minimum, and your first number times the second number
        (3 * 20) is your maximum. Therefore to roll a 2d10, your minimum will be 2, and your max will be 20.

        Parameters
        ----------
            ctx      :: Discord context <!nodoc>
            minimum  ::The lowest number the bot can choose
            maximum  :: The highest number the bot can choose

        Examples
        --------
            /random 1 6   :: Roll a die
            /random 1 2   :: Flip a coin
            /random 3 60  :: Roll a 3d20
        """
        if maximum < minimum:
            minimum, maximum = maximum, minimum

        number = random.randint(minimum, maximum)

        await ctx.send(embed=discord.Embed(
            title="\U0001F3B2 Random Number Generator",
            description=f"Your random number is: **`{number}`**",
            color=Colors.INFO
        ))

    @commands.command(name="dice", brief="Roll some dice!", aliases=["roll"])
    async def roll_dice(self, ctx: commands.Context, die_notation: str):
        """
        Roll some virtual dice in standard Dice Notation. The program will expect a die in NdS+M format.

        Parameters
        ----------
            ctx          :: discord context <!nodoc>
            die_notation :: Standard Die Notation

        Examples
        --------
            /dice d6    :: Roll a D6
            /dice 2d6   :: Roll two D6, and add them up
            /dice 2d6+3 :: Roll two D6, add 3, and add them up.
            /dice 2d6-3 :: Roll two D6, subtract 3, and add them up.
        """
        dice_config = re.match(Regex.DICE_CONFIG, die_notation, re.I)

        if not dice_config:
            await ctx.send(embed=discord.Embed(
                title="\U0001F3B2 Dice Roll",
                description=f"The dice you specified are invalid.",
                color=Colors.ERROR
            ))
            return

        num_rolls = int(dice_config.groupdict().get('count') or 1)
        die_val = int(dice_config.groupdict().get('size'))
        die_modifier = int(dice_config.groupdict().get('modifier') or 0)

        if die_val < 2:
            await ctx.send(embed=discord.Embed(
                title="\U0001F3B2 Dice Roll",
                description=f"You can't roll a die with less than two sides!",
                color=Colors.ERROR
            ))
            return
        elif die_val > 255:
            await ctx.send(embed=discord.Embed(
                title="\U0001F3B2 Dice Roll",
                description=f"You can't make a die bigger than a byte!",
                color=Colors.ERROR
            ))
            return

        if num_rolls > 10:
            await ctx.send(embed=discord.Embed(
                title="\U0001F3B2 Dice Roll",
                description=f"Do you really need to roll the same die {num_rolls} times?",
                color=Colors.ERROR
            ))
            return

        rolls = []

        for i in range(num_rolls):
            roll = random.randint(1, die_val)
            rolls.append(roll)

        embed = discord.Embed(
            title="\U0001F3B2 Dice Roll",
            description=f"Rolling a {die_notation}... **{sum(rolls) + die_modifier}**!",
            color=Colors.INFO
        )

        if len(rolls) > 1 or die_modifier:
            embed.add_field(
                name="Roll Details",
                value="\n".join(f"Roll {i+1}: {rolls[i]} (Σ={sum(rolls[:i+1])})"
                                for i in range(len(rolls))) +
                      (f"\n\nMod: {die_modifier} (Σ={sum(rolls) + die_modifier})" if die_modifier else ""),
                inline=False
            )

        await ctx.send(embed=embed)


def setup(bot: HuskyBot):
    bot.add_cog(Fun(bot))
