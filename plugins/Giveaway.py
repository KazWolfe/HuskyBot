import datetime
import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfConverters
from WolfBot.WolfData import GiveawayObject
from WolfBot.WolfStatics import *
from WolfBot.managers.GiveawayManager import GiveawayManager

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)

GIVEAWAY_CONFIG_KEY = "giveaways"


# noinspection PyMethodMayBeStatic
class Giveaway:
    """
    The Giveaway plugin allows server moderators to schedule and execute fair giveaways determined by a random number
    generator.

    Giveaways may run indefinitely, and are handled completely by the bot. Note that the bot does not handle reward
    distribution - this is the responsibility of the staff member running the giveaway.
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()
        self._session_store = WolfConfig.get_session_store()
        self.giveaway_manager = GiveawayManager(bot)
        LOG.info("Loaded plugin!")

    # noinspection PyUnresolvedReferences
    def __unload(self):
        # super.__cleanup()
        self.giveaway_manager.cleanup()

    @commands.group(name="giveaways", brief="Control the giveaway plugin", aliases=["giveaway", "ga"])
    @commands.has_permissions(manage_messages=True)
    async def ga(self, ctx: commands.Context):
        """
        Manage the Giveaway plugin.

        This command, by itself, does nothing. Please refer to the below *actual* commands:
        """

        pass

    @ga.command(name="list", brief="List all active giveaways in the guild")
    async def list_giveaways(self, ctx: commands.Context):
        """
        Get a list of all currently active giveaways in the current guild.

        This command will iterate over the "active giveaways" list and attempt to find all Giveaways queued for
        execution. This allows staff members to get an overview (and, if necessary, stop) of server giveaways.
        """

        pretty_list = ""

        giveaways = self.giveaway_manager.get_giveaways()

        for i in range(len(giveaways)):
            g = giveaways[i]

            end_time = datetime.datetime.utcfromtimestamp(g.end_time).strftime(DATETIME_FORMAT)
            channel = self.bot.get_channel(g.register_channel_id)

            pretty_list += f"\n{i + 1}. {g.name} (in {channel.mention}, ending {end_time}, {g.winner_count} winners)"

        if len(giveaways) == 0:
            await ctx.send(embed=discord.Embed(
                title="No giveaways running!",
                description="There are currently no giveaways running on this guild.",
                color=Colors.WARNING
            ))
            return

        await ctx.send(embed=discord.Embed(
            title=f"{len(giveaways)} giveaways running!",
            description=f"The following giveaways are currently running: \n{pretty_list}",
            color=Colors.INFO
        ))

    @ga.command(name="start", brief="Start a new Giveaway on the guild")
    async def start(self, ctx: commands.Context, name: str, timedelta: WolfConverters.DateDiffConverter, winners: int):
        """
        Start a new Giveaway on the guild.

        This command allows a moderator to start a giveaway in the current channel. Giveaway winners are chosen by a
        cryptographically secure random number generator, as determined by the number of entrants.

        The giveaway will take place in the current channel, and will require every user willing to participate to
        react with the specified emoji (see Emojis.GIVEAWAY in code).

        Giveaways will end at most 60 seconds after the specified time, depending on server load and other factors.

        Parameters:
            name      - The giveaway name, as a text string. A giveaway with spaces in names must be "quoted".
            timedelta - The time (in standard ##d##h##m##s format) before this giveaway ends.
            winners   - A count of total winners to be chosen and listed in the final message.
        """

        end_time = datetime.datetime.utcnow() + timedelta

        if not (winners > 0):
            await ctx.send(embed=discord.Embed(
                title="Error making giveaway!",
                description="A giveaway requires at least one winner. Please double-check your command.",
                color=Colors.DANGER
            ))
            return

        await self.giveaway_manager.start_giveaway(ctx, name, end_time, winners)

    @ga.command(name="end", brief="End a giveaway early (defining a winner)", aliases=["stop"])
    async def stop(self, ctx: commands.Context, giveaway_id: int):
        """
        Gracefully stop a running Giveaway.

        This command will gracefully end a currently running giveaway, and immediately declare a winner.

        Parameters:
            giveaway_id - The ID of the giveaway (see /giveaways list) to stop.

        See Also:
            /giveaway kill - Forcefully terminate a giveaway
        """
        giveaway_id = giveaway_id - 1  # We present the ID as one-indexed, but python is zero-indexed.

        try:
            giveaway: GiveawayObject = self.giveaway_manager.get_giveaways()[giveaway_id]
        except ValueError:
            await ctx.send(embed=discord.Embed(
                title="Giveaway doesn't exist!",
                description=f"There is no giveaway with active ID `{giveaway_id}`! Please run `/giveaways list` to see "
                            f"giveaway IDs.",
                color=Colors.ERROR
            ))
            return

        # We hand off to the GiveawayManager for the rest of this command.
        await self.giveaway_manager.finish_giveaway(giveaway)

    @ga.command(name="kill", brief="Kill a giveaway, without defining a winner.")
    @commands.has_permissions(administrator=True)
    async def kill(self, ctx: commands.Context, giveaway_id: int):
        """
        Forcefully kill a giveaway.

        This command will stop a giveaway immediately, without declaring a winner or otherwise running any
        cleanup (such as deleting the giveaway registration message).

        NOTE THAT THIS COMMAND MAY CAUSE *VERY* UNEXPECTED BEHAVIOR WITH CERTAIN GIVEAWAYS. Use with caution!

        Parameters:
            giveaway_id - The ID of the giveaway (see /giveaways list) to stop.

        See Also:
            /giveaway stop - Gracefully stop a running Giveaway.
        """

        giveaway_id = giveaway_id - 1  # We present the ID as one-indexed, but python is zero-indexed.

        try:
            giveaway: GiveawayObject = self.giveaway_manager.get_giveaways()[giveaway_id]
        except ValueError:
            await ctx.send(embed=discord.Embed(
                title="Giveaway doesn't exist!",
                description=f"There is no giveaway with active ID `{giveaway_id}`! Please run `/giveaways list` to see "
                            f"giveaway IDs.",
                color=Colors.ERROR
            ))
            return

        self.giveaway_manager.kill_giveaway(giveaway)

        await ctx.send(embed=discord.Embed(
            title="Giveaway forcefully killed!",
            description=f"A Giveaway with ID `{giveaway_id}` (named `{giveaway.name}`) has been forcefully stopped.\n\n"
                        f"**NOTE THAT THERE MAY BE SOME UNCLEAN DATA, OR THE GIVEAWAY MAY STILL RUN IF STOPPED TOO "
                        f"LATE.**",
            color=Colors.WARNING
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Giveaway(bot))
