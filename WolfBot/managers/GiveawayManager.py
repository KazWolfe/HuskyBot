import asyncio
import datetime
import logging
import random

import discord
from discord.ext import commands

from WolfBot import WolfConfig, WolfData, WolfUtils
from WolfBot.WolfStatics import *

GIVEAWAY_CONFIG_KEY = 'giveaways'
LOG = logging.getLogger("DiyBot.Managers." + __name__)


class GiveawayManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()
        self._giveaway_config = WolfConfig.WolfConfig('config/giveaways.json', create_if_nonexistent=True)

        self.__cache__ = []

        self.load_giveaways_from_file()

        self.__task__ = self.bot.loop.create_task(self.process_giveaways())

        LOG.info("Loaded GiveawayManager!")

    def load_giveaways_from_file(self):
        giveaway_list = self._giveaway_config.get(GIVEAWAY_CONFIG_KEY, [])

        for giveaway_raw in giveaway_list:
            giveaway = WolfData.GiveawayObject()
            giveaway.load_dict(giveaway_raw)

            self.__cache__.append(giveaway)

    async def process_giveaways(self):
        while not self.bot.is_closed():
            for giveaway in self.__cache__:
                if giveaway.is_over():
                    LOG.info("Found a scheduled giveaway for {} ending. Triggering...".format(giveaway.name))
                    await self.finish_giveaway(giveaway)

                # Because giveaways are sorted by finish date, if we encounter a giveaway that *isn't* over, we can
                # assume there's nothing more to do, so we can exit the for loop entirely.
                else:
                    break

            # Check again every half second
            await asyncio.sleep(0.5)

    async def finish_giveaway(self, giveaway: WolfData.GiveawayObject):
        wcl = "\n\nWinners will be contacted shortly."

        channel = self.bot.get_channel(giveaway.register_channel_id)  # type: discord.TextChannel
        message = await channel.get_message(giveaway.register_message_id)  # type: discord.Message

        contending_users = []

        for reaction in message.reactions:
            if reaction.emoji != Emojis.GIVEAWAY:
                continue

            contending_users += await reaction.users().flatten()

        # Remove the bot
        contending_users.remove(self.bot.user)

        winning_users = random.sample(contending_users, min(giveaway.winner_count, len(contending_users)))

        if len(winning_users) == 1:
            win_text = "Congratulations to our winner, {}!".format(winning_users[0].mention) + wcl
        elif len(winning_users) == 2:
            win_text = "Congratulations to our winners, " \
                       "{} and {}!".format(winning_users[0].mention, winning_users[1].mention) + wcl
        elif len(winning_users) > 2:
            win_csb = [u.mention for u in winning_users]

            win_text = "Congratulations to our winners: {}, and {}!".format(' ,'.join(win_csb[:-1]), win_csb[-1:][0]) \
                       + wcl
        else:
            win_text = "Unfortunately, nobody entered this giveaway... :sob:"

        embed = discord.Embed(
            title=Emojis.GIVEAWAY + " Giveaway over!",
            description="Woo! The giveaway for **{}** has ended!\n\n{}".format(giveaway.name, win_text),
            color=Colors.PRIMARY
        )

        await message.delete()
        await channel.send(embed=embed)

        if giveaway in self.__cache__:
            self.__cache__.remove(giveaway)

        self._giveaway_config.set(GIVEAWAY_CONFIG_KEY, self.__cache__)

    async def start_giveaway(self, ctx: commands.Context, title: str, end_time: datetime.datetime, winners: int):
        channel = ctx.channel

        if winners == 1:
            winner_str = "1 winner"
        else:
            winner_str = "{} winners".format(winners)

        giveaway_embed = discord.Embed(
            title="{} New Giveaway: {}!".format(Emojis.GIVEAWAY, title),
            description="A giveaway has been started for **{}**!\n\nAnyone may enter, and up to {} will be selected "
                        "for the final prize. React with the {} emoji to enter.\n\nThis giveaway will end at "
                        "{} UTC.".format(title, winner_str, Emojis.GIVEAWAY, end_time.strftime(DATETIME_FORMAT)),
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

        self.__cache__.insert(pos, giveaway)
        self.__cache__.sort(key=lambda g: g.count if g.count else 10 * 100)
        self._giveaway_config.set(GIVEAWAY_CONFIG_KEY, self.__cache__)

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
