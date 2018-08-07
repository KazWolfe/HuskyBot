import asyncio
import datetime
import logging
import random

import discord
from discord.ext import commands

from WolfBot import WolfConfig, WolfData, WolfUtils
from WolfBot.WolfStatics import *

GIVEAWAY_CONFIG_KEY = 'giveaways'
LOG = logging.getLogger("DakotaBot.Managers.GiveawayManager")


class GiveawayManager:
    """
    The Giveaway Manager is a centralized management location for Giveaways (see the Giveaway plugin).

    Because Giveaways need to be persistent between sessions/bot executions, this class exists. Similarly, the
    scheduler needs some registered class.
    """

    def __init__(self, bot: commands.Bot):
        """
        Initialize a new GiveawayManager for the bot.
        :param bot: The Bot we use to initialize everything.
        """

        self.bot = bot
        self._config = WolfConfig.get_config()
        self._giveaway_config = WolfConfig.get_config('giveaways', create_if_nonexistent=True)

        # Random number generator
        self._rng = random.SystemRandom()

        # We store all giveaways in a time-ordered cache list. Reading and working with the file directly is
        # *generally* a bad idea.
        self.__cache__ = []

        self.load_giveaways_from_file()

        self.__task__ = self.bot.loop.create_task(self.process_giveaways())

        LOG.info("Manager load complete.")

    def load_giveaways_from_file(self) -> None:
        """
        Initialize the giveaways cache from the file.
        :return: Doesn't return.
        """
        giveaway_list = self._giveaway_config.get(GIVEAWAY_CONFIG_KEY, [])

        for giveaway_raw in giveaway_list:
            giveaway = WolfData.GiveawayObject(data=giveaway_raw)

            self.__cache__.append(giveaway)

    async def process_giveaways(self) -> None:
        """
        Process all pending giveaways.

        Iterate through the cache looking for any expired giveaway. This method will run about once every 0.5 seconds
        as part of the bot's event loop. As a result, care must be taken to make sure this code exits quickly if nothing
        needs to be done.
        :return: Doesn't return.
        """

        while not self.bot.is_closed():
            # This is what peak performance looks like, kids.
            for giveaway in self.__cache__:
                if giveaway.is_over():
                    LOG.info(f"Found a scheduled giveaway for {giveaway.name} ending. Triggering...")
                    await self.finish_giveaway(giveaway)

                # Because giveaways are sorted by finish date, if we encounter a giveaway that *isn't* over, we can
                # assume there's nothing more to do, so we can exit the for loop entirely.
                else:
                    break

            # Check again every half second
            await asyncio.sleep(0.5)

    async def finish_giveaway(self, giveaway: WolfData.GiveawayObject) -> None:
        """
        Finish an arbitrary giveaway.

        This method contains all the logic to stop a giveaway, remove it from the cache/file, and notify the winner(s)
        of the giveaway. This method may be called manually to prematurely end a giveaway *while* declaring a winner.

        :param giveaway: Any giveaway to cancel/end.
        :return: Doesn't return.
        """

        wcl = "\n\nWinners will be contacted shortly."

        channel: discord.TextChannel = self.bot.get_channel(giveaway.register_channel_id)
        message: discord.Message = await channel.get_message(giveaway.register_message_id)

        contending_users = []

        for reaction in message.reactions:
            if reaction.emoji != Emojis.GIVEAWAY:
                continue

            async for user in reaction.users():
                if user == self.bot.user:
                    continue

                contending_users += user

        winning_users = self._rng.sample(contending_users, min(giveaway.winner_count, len(contending_users)))

        if len(winning_users) == 1:
            win_text = f"{f'Congratulations to our winner, {winning_users[0].mention}!'}{wcl}"
        elif len(winning_users) == 2:
            message = f'Congratulations to our winners, {winning_users[0].mention} and {winning_users[1].mention}!'
            win_text = f"{message}{wcl}"
        elif len(winning_users) > 2:
            win_csb = [u.mention for u in winning_users]

            win_text = f"Congratulations to our winners: {', '.join(win_csb[:-1])}, and {win_csb[-1:][0]}! {wcl}"
        else:
            win_text = "Unfortunately, nobody entered this giveaway... :sob:"

        embed = discord.Embed(
            title=Emojis.GIVEAWAY + " Giveaway over!",
            description=f"Woo! The giveaway for **{giveaway.name}** has ended!\n\n{win_text}",
            color=Colors.PRIMARY
        )

        await message.delete()
        await channel.send(embed=embed)

        if giveaway in self.__cache__:
            self.__cache__.remove(giveaway)

        self._giveaway_config.set(GIVEAWAY_CONFIG_KEY, self.__cache__)

    async def start_giveaway(self, ctx: commands.Context, title: str, end_time: datetime.datetime,
                             winners: int) -> WolfData.GiveawayObject:

        """
        Begin a new Giveaway.

        This command will build a new Giveaway, register it with the event loop and cache, and store it in the
        persistent file. If a giveaway is to be executed, it ***must*** be created with this method.

        :param ctx: The Context responsible for creating the giveaway.
        :param title: The title/name of the giveaway (usually the object people will win)
        :param end_time: A DateTime to end the giveaway
        :param winners: A number of winners (greater than zero) to choose from.
        :return: Returns the created GiveawayObject
        """
        channel = ctx.channel

        if winners == 1:
            winner_str = "1 winner"
        else:
            winner_str = f"{winners} winners"

        giveaway_embed = discord.Embed(
            title=f"{Emojis.GIVEAWAY} New Giveaway: {title}!",
            description=f"A giveaway has been started for **{title}**!\n\nAnyone may enter, and up to {winner_str} "
                        f"will be selected for the final prize. React with the {Emojis.GIVEAWAY} emoji to enter."
                        f"\n\nThis giveaway will end at {end_time.strftime(DATETIME_FORMAT)} UTC",
            color=Colors.INFO
        )

        message = await ctx.send(embed=giveaway_embed)
        await message.add_reaction(Emojis.GIVEAWAY)

        giveaway = WolfData.GiveawayObject()
        giveaway.name = title
        giveaway.end_time = end_time.timestamp()  # All timestamps are UTC.
        giveaway.winner_count = winners
        giveaway.register_channel_id = channel.id
        giveaway.register_message_id = message.id

        pos = WolfUtils.get_sort_index(self.__cache__, giveaway, 'end_time')

        # note, we insert the giveaway, and sort. this is a rare operation, so a sort is "acceptable"
        # Null-ending giveaways (usually impossible) will be placed at the very end.
        self.__cache__.insert(pos, giveaway)
        self.__cache__.sort(key=lambda g: g.end_time if g.end_time else 10 * 100)
        self._giveaway_config.set(GIVEAWAY_CONFIG_KEY, self.__cache__)

        return giveaway

    def get_giveaways(self):
        """
        Return a list of all active giveaways currently registered *in cache*.

        Note that this command will not return giveaways (somehow) in the config but not the cache.

        NOTE: DO NOT TRUST THE ORDERING OF THIS RETURN! While indexes will be persistent throughout the session, they
              may change at *any time* and are not necessarily sorted in start or end times.

        :return: A list of `GiveawayObject`s currently in cache.
        """

        return self.__cache__

    def kill_giveaway(self, giveaway: WolfData.GiveawayObject):
        """
        Kill a giveaway non-gracefully, immediately purging it from cache.

        This command will terminate a giveaway without ending it. This means it will not execute, and there will not be
        a "winner" to the giveaway.

        Depending on the time to giveaway end, this method may cause unexpected behavior. Use carefully.

        :param giveaway: The GiveawayObject to terminate.
        """

        self.__cache__.remove(giveaway)
        self._giveaway_config.set(GIVEAWAY_CONFIG_KEY, self.__cache__)

    async def cleanup(self):
        if self.__task__ is not None:
            self.__task__.cancel()
