import logging
import random

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Dakota:

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()

        self.reactions = ["Rooooo!", "Woof!", "Bork!", "Aaaaooo!", "Awooo!"]

        self.pet_state = {
            "health": 100.00,
            "hunger": 100.00,
            "energy": 100.00,
            "happiness": 100.00
        }

        LOG.info("Loaded plugin!")

    def get_title(self, title: str):
        return "{} {}".format(''.join(random.sample(self.reactions, 1)), title)

    def edit_stat(self, stat_name: str, diff: float):
        old_stat = self.pet_state[stat_name]
        new_stat = old_stat + round(diff, 2)

        if new_stat > 100:
            new_stat = 100
        elif new_stat < 0:
            new_stat = 0

        self.pet_state[stat_name] = round(new_stat, 2)

        return {"old": old_stat, "new": new_stat}

    def get_stat_embed(self, title, description, color=discord.Embed.Empty, deltas=None):
        if deltas is None or not isinstance(deltas, dict):
            deltas = {}

        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )

        hedstr = "({})".format(round(deltas['health'], 2)) if deltas.get('health') is not None else ''
        embed.add_field(name="Health",
                        value=Emojis.HEART + " {} / 100 {}".format(self.pet_state['health'], hedstr),
                        inline=True)

        hudstr = "({})".format(round(deltas['hunger'], 2)) if deltas.get('hunger') is not None else ''
        embed.add_field(name="Hunger",
                        value=Emojis.MEAT + " {} / 100 {}".format(self.pet_state['hunger'], hudstr),
                        inline=True)

        endstr = "({})".format(round(deltas['energy'], 2)) if deltas.get('energy') is not None else ''
        embed.add_field(name="Energy",
                        value=Emojis.BATTERY + " {} / 100 {}".format(self.pet_state['energy'], endstr),
                        inline=True)

        hadstr = "({})".format(round(deltas['happiness'], 2)) if deltas.get('happiness') is not None else ''
        embed.add_field(name="Happiness",
                        value=Emojis.STAR + " {} / 100 {}".format(self.pet_state['happiness'], hadstr),
                        inline=True)

        embed.set_thumbnail(url=self.bot.user.avatar_url)

        return embed

    async def on_message(self, message: discord.Message):
        self.edit_stat('hunger', -1 * random.gauss(0.15, 0.05))
        self.edit_stat('happiness', -1 * random.gauss(0.05, 0.03))
        self.edit_stat('energy', -1 * random.gauss(0.15, 0.05))

    @commands.command(name="feed", brief="Give Dakota a bowl of food")
    @commands.cooldown(1, 90, commands.BucketType.guild)
    async def feed(self, ctx: commands.Context):
        food_types = {
            "kibble": 15.0,
            "steak": 25.0,
            "chicken": 20.0,
            "peanut butter": 5.0,
            "dog treats": 2.0
        }

        food_name = ''.join(random.sample(food_types.keys(), 1))
        food_add = food_types[food_name]

        self.edit_stat('energy', 2 * food_add)

        stat = self.edit_stat('hunger', food_add)

        await ctx.send(embed=self.get_stat_embed(
            title=self.get_title("Food!"),
            description="{} has fed Dakota some {}!".format(ctx.author.mention, food_name),
            deltas={'hunger': stat['new'] - stat['old']}
        ))

    @commands.command(name="pet", brief="Give Dakota a pet")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def pet(self, ctx: commands.Context):
        stat = self.edit_stat('happiness', random.gauss(3, 0.1225))

        await ctx.send(embed=self.get_stat_embed(
            title=self.get_title("Scritches!"),
            description="{} has pet Dakota!".format(ctx.author.mention),
            deltas={'happiness': stat['new'] - stat['old']}
        ))

    @commands.command(name="walk", brief="Take Dakota for walkies")
    @commands.cooldown(1, 300, commands.BucketType.guild)
    async def walkies(self, ctx: commands.Context):
        energy = self.edit_stat('energy', -1 * random.gauss(35, 3.525))
        energy_delta = energy['new'] - energy['old']

        hunger = self.edit_stat('hunger', -1 * random.gauss(35, 3.525))
        hunger_delta = hunger['new'] - hunger['old']

        happiness = self.edit_stat('happiness', 1 * random.gauss(60, 5))
        happiness_delta = happiness['new'] - happiness['old']

        await ctx.send(embed=self.get_stat_embed(
            title=self.get_title("Walkies!"),
            description="{} has taken Dakota for a walk.".format(ctx.author.mention),
            deltas={
                'energy': energy_delta,
                'hunger': hunger_delta,
                'happiness': happiness_delta
            }
        ))

    @commands.command(name="petstats", brief="Check up on Dakota")
    async def stats(self, ctx: commands.Context):
        await ctx.send(embed=self.get_stat_embed(
            title="Stats for Dakota",
            description="Current statistics report for the resident server husky. {}".format(self.get_title(""))
        ))


def setup(bot: commands.Bot):
    bot.add_cog(Dakota(bot))
