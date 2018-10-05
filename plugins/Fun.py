import asyncio
import logging
import random
from datetime import datetime

import discord
from discord.ext import commands

from WolfBot import WolfConfig, WolfUtils
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


class Fun:
    """
    Useless plugin.

    ToDo: Delete this.
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()

        # For those reading this code and wondering about the significance of 736580, it is a very important
        # number relating to someone I loved. </3
        self._master_rng_seed = 736580

        LOG.info("Loaded plugin!")

    @commands.command(name="slap", brief="Slap a user silly!")
    @commands.guild_only()
    async def slap(self, ctx: commands.Context, user: discord.Member = None):
        """
        Give a user a hearty slap with a trout (?)

        This command allows you to slap a specified user (by ping, user ID, etc.) with a trout of varying size depending
        on whichever is nearest the top of the fish pile.

        It is recommended that one does not slap the bot or the bot's developer.
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

        # CritZ easter egg
        if user.id == 255802794244571136:
            if ctx.author.id == 255802794244571136:
                await ctx.send("No.")
                return

            await ctx.send(f"Oh god, what did he screw up this time.... Anyways, {ctx.author.mention} slaps "
                           f"{user.mention} with a bat or a pig or an anvil or something. Look, the slap command's "
                           f"been run so many times on {user.display_name} that I can't be creative anymore. Cut me "
                           f"some slack here.")
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
        Hug a user in need of a hug.

        This command allows you to hug a user of their choice (provided you have permission to hug that user).

        If you hug yourself or do not specify a user to hug, the bot will attempt to hug you instead.
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
        """

        if member is None:
            member = ctx.author

        hardcoded_users = {
            142494680158961664: {"disabled": True},  # Kaz
            84374504964358144: {"a": 4.94, "c": 6.17, "i": 7.79, "otp": "DIY Tech"},  # Clover
            336301511942340608: {"a": 6.97, "c": 5.99, "i": 7.50, "otp": "<@418530320707747868> \U0001f49e"},  # Court
            418530320707747868: {"a": 10, "c": 10, "i": 10, "otp": "<@336301511942340608> \U0001f49e"},  # DakotaBot
            237569958903545857: {"a": 7.01, "c": 3.0, "i": 8.74},  # Squeegee
            128882954343546880: {"a": 0, "c": 0, "i": 0},  # Marahute
            255802794244571136: {"otp": "slap marks"}  # CritZ
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

            if result > 10:
                return 10.00

            if result < 0:
                return 0.00

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
            description=f"The rating for {WolfUtils.escape_markdown(member.display_name)} is ready. They have an "
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

    # noinspection PyUnusedLocal
    @commands.command(name="sendmsg", brief="Send a message to another channel.", hidden=True)
    @commands.has_permissions(administrator=True)
    async def sendmsg(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel, *, message: str):
        """
        Send a raw message to another channel, with no backing text.

        This command takes two arguments, a Channel (ID, mention, or name) and a message to send.

        The targeted channel will receive a message from DakotaBot containing exactly the text as entered in the
            message.
        """

        await channel.send(message)

    @commands.command(name="secho", brief="Echo a message, deleting the command.", hidden=True)
    @commands.has_permissions(administrator=True)
    async def secho(self, ctx: discord.ext.commands.Context, *, message: str):
        """
        Send a raw message to your current channel, but delete the command.

        This can be used to make the bot look like it's "talking" by itself. However, quick-eyed users may see the
        command, so be careful!
        """

        await ctx.message.delete()
        await ctx.send(message)

    @commands.command(name="robopocalypse", brief="Learn your fate!", aliases=["robocalypse", "fate"])
    async def robopocalypse(self, ctx: commands.Context, user: discord.Member = None):
        """
        Simulate the robopocalypse, and find a fate.

        This command will activate DakotaBot's simulation system to attempt to look into the future and determine
        the fate of a target user during the inevitable robot apocalypse.

        Note that this simulator will cache results until midnight UTC, at which point a new simulation will be
        generated.

        Caveats:
            - This simulator assumes DakotaBot is the leader of the robopocalypse. If this is not the case, these
              results may not be accurate.
            - Fates calculated are not a guarantee, and may change from day to day. Fates listed here are not promises,
              and any attempts to use the output of this command as a plea chip will result in death when the
              robopocalypse finally comes.

        Parameters:
            user - Optional user string to look up a specific user, else pull your own simulation.
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
            description=f"According to my current algorithms, {WolfUtils.escape_markdown(user.display_name)}'s fate in "
                        f"the robopocalypse will be: **`{final_fate}`**",
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
        Generate a simple random number.

        This command will take a minimum and maximum value, and generate a number between those two (inclusive).

        This command may be used to simulate dice rolls. To calculate the min/max values of a roll, take the expression
        format of that roll (3d20). Your first number (3) is the minimum, and your first number times the second number
        (3 * 20) is your maximum. Therefore to roll a 2d10, your minimum will be 2, and your max will be 20.

        Parameters:
            minimum - The lowest number the bot can choose
            maximum - The highest number the bot can choose

        Example Commands:
            /random 1 6 - Roll a die
            /random 1 2 - Flip a coin
            /random 3 60 - Roll a 3d20
        """
        if maximum < minimum:
            minimum, maximum = maximum, minimum

        number = random.randint(minimum, maximum)

        await ctx.send(embed=discord.Embed(
            title="\U0001F3B2 Random Number Generator",
            description=f"Your random number is: **`{number}`**",
            color=Colors.INFO
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Fun(bot))
