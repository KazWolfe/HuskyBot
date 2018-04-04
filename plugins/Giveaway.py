import datetime
import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfConverters
from WolfBot.WolfData import GiveawayObject
from WolfBot.WolfStatics import *
from WolfBot.managers.GiveawayManager import GiveawayManager

LOG = logging.getLogger("DiyBot.Plugin." + __name__)

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

            pretty_list += "\n{}. {} (in {}, ending {}, {} winners)".format(i + 1, g.name, channel.mention, end_time,
                                                                            g.winner_count)

        if len(giveaways) == 0:
            await ctx.send(embed=discord.Embed(
                title="No giveaways running!",
                description="There are currently no giveaways running on this guild.",
                color=Colors.WARNING
            ))
            return

        await ctx.send(embed=discord.Embed(
            title="{} giveaways running!".format(len(giveaways)),
            description="The following giveaways are currently running: \n{}".format(pretty_list),
            color=Colors.INFO
        ))

    @ga.command(name="start", brief="Start a new Giveaway on the guild")
    async def start(self, ctx: commands.Context, name: str, timedelta: WolfConverters.DateDiffConverter, winners: int):
        """
        Start a new Giveaway on the guild.

        This command allows a moderator to start a giveaway in the current channel. This command takes three arguments:

        name: The giveaway name. This may be any text string, but it will need to be wrapped in "quotes" if it will
              contain spaces.
        timedelta: The time this giveaway should run. This argument is in format ##d##h##m##s, and will always be in
                   the future.
        winners: The number of winners this giveaway will have. This number must be greater than 0.

        The Giveaway will stop around the posted time (or, within up to 60 seconds of the posted time).
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

        If necessary, this command will stop a giveaway denoted by giveaway_id. The ID may be determined by checking
        `/giveaways list`.

        This command will stop the giveaway normally, and will declare a winner. If you do not want to declare a winner,
        use `/giveaways kill`.
        """
        giveaway_id = giveaway_id - 1  # We present the ID as one-indexed, but python is zero-indexed.

        try:
            giveaway = self.giveaway_manager.get_giveaways()[giveaway_id]  # type: GiveawayObject
        except ValueError:
            await ctx.send(embed=discord.Embed(
                title="Giveaway doesn't exist!",
                description="There is no giveaway with active ID `{}`! Please run `/giveaways list` to see giveaway "
                            "IDs.".format(giveaway_id),
                color=Colors.ERROR
            ))
            return

        # We hand off to the GiveawayManager for the rest of this command.
        await self.giveaway_manager.finish_giveaway(giveaway)

    @ga.command(name="kill", brief="Kill a giveaway, without defining a winner.")
    @commands.has_permissions(administrator=True)
    async def kill(self, ctx: commands.Context, giveaway_id: int):
        """
        Non-gracefully kill a giveaway.

        If a giveaway needs to be stopped *immediately* without defining a winner, this command be used. It takes a
        single argument, giveaway_id. This may be obtained from /giveaways list.

        NOTE THAT THIS COMMAND MAY CAUSE *VERY* UNEXPECTED BEHAVIOR WITH CERTAIN GIVEAWAYS. Use with caution!
        """

        giveaway_id = giveaway_id - 1  # We present the ID as one-indexed, but python is zero-indexed.

        try:
            giveaway = self.giveaway_manager.get_giveaways()[giveaway_id]  # type: GiveawayObject
        except ValueError:
            await ctx.send(embed=discord.Embed(
                title="Giveaway doesn't exist!",
                description="There is no giveaway with active ID `{}`! Please run `/giveaways list` to see giveaway "
                            "IDs.".format(giveaway_id),
                color=Colors.ERROR
            ))
            return

        self.giveaway_manager.kill_giveaway(giveaway)

        await ctx.send(embed=discord.Embed(
            title="Giveaway forcefully killed!",
            description="A Giveaway with ID `{}` (named `{}`) has been forcefully stopped.\n\n"
                        "**NOTE THAT THERE MAY BE SOME UNCLEAN DATA, OR THE GIVEAWAY MAY STILL RUN IF STOPPED "
                        "TOO LATE.**".format(giveaway_id, giveaway.name),
            color=Colors.WARNING
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Giveaway(bot))
