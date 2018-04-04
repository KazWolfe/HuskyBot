import logging
import re

import discord
from discord.ext import commands

from WolfBot import WolfChecks
from WolfBot import WolfConfig
from WolfBot import WolfUtils
from WolfBot.WolfStatics import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Censor:
    """
    The Censor plugin allows moderators to lighten their workload and allow the bot to take care of automatic message
    deletion according to regular expressions.

    Message filtering is done relatively early in the event chain, so messages tend to be deleted fairly quickly.

    There are two types of censors: Channel Censors, and Global Censors. Channel censors are restricted to a single
    channel, and are configured on a per-channel basis. Global censors apply to all channels in any given guild.

    Censors can take either plain text (that is, a single word) or regular expressions.
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()

        LOG.info("Loaded plugin!")

    async def filter_message(self, message: discord.Message, context: str = "new_message"):
        if not isinstance(message.channel, discord.TextChannel):
            return

        if not WolfUtils.should_process_message(message):
            return

        censor_config = self._config.get("censors", {})

        censor_list = censor_config.get("global", []) + censor_config.get(str(message.channel.id), []) \
                      + censor_config.get("user-" + str(message.author.id), [])

        if message.author.permissions_in(message.channel).manage_messages:
            return

        if any((re.search(censor_term, message.content, re.IGNORECASE) is not None) for censor_term in censor_list):
            await message.delete()
            LOG.info("Deleted censored message (context %s, from %s in %s): %s", context, message.author,
                     message.channel, message.content)

    async def on_message(self, message):
        await self.filter_message(message)

    # noinspection PyUnusedLocal
    async def on_message_edit(self, before, after):
        await self.filter_message(after, "edit")

    @commands.group(name="censor", brief="Manage the Censor list for the guild")
    @commands.has_permissions(manage_messages=True)
    async def censor(self, ctx: commands.Context):
        """
        The parent command for the Censor module.

        This command doesn't do anything - it's merely the entrypoint to everything else censor-related.
        """
        pass

    @censor.command(name="list", brief="List all Censors for a channel")
    async def list_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        List the censor terms in a given channel.

        This command takes one optional argument - a channel identifier (ID, #mention, or name). If this is not
        specified, the current channel is used.

        Censors in this list apply only to the specified channel. to edit the list, see /help censor
        """

        censor_config = self._config.get("censors", {})

        if channel is None:
            channel = ctx.channel

        censor_list = censor_config.setdefault(str(channel.id), [])

        await ctx.send(embed=discord.Embed(
            title="Censors for " + channel.name,
            description="The following words are censored in the requested channel:\n\n" + ", ".join(censor_list),
            color=Colors.PRIMARY
        ))

    @censor.command(name="globallist", brief="List all Censors in the global list", aliases=["glist"])
    async def list_global(self, ctx: commands.Context):
        """
        List the censor terms in the global list.

        Censors in the global list apply to the entire guild. To edit the censor list, see /help censor.
        """

        censor_config = self._config.get("censors", {})
        censor_list = censor_config.setdefault("global", [])

        await ctx.send(embed=discord.Embed(
            title="Global Censors for " + ctx.guild.name,
            description="The following words are censored in this guild:\n\n" + ", ".join(censor_list),
            color=Colors.PRIMARY
        ))

    @censor.command(name="add", brief="Add a Censor to a channel")
    @WolfChecks.has_guild_permissions(manage_messages=True)
    async def add_channel(self, ctx: commands.Context, channel: discord.TextChannel, *, censor: str):
        """
        Add a censor to the channel list.

        This command takes two arguments - a mandatory channel identifier (ID, #mention, name) and the censor text. The
        censor text may be a single word or a Python regular expression.
        """

        censor_config = self._config.get("censors", {})
        censor_list = censor_config.setdefault(str(channel.id), [])

        if censor in censor_list:
            await ctx.send(embed=discord.Embed(
                title="Censors for " + channel.name,
                description="The word `" + censor + "` was already in the censor list.",
                color=Colors.PRIMARY
            ))
            return

        censor_list.append(censor)

        self._config.set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title="Censors for " + channel.name,
            description="The word `" + censor + "` was added to the censor list for the specified channel",
            color=Colors.PRIMARY
        ))

    @censor.command(name="globaladd", brief="Add a Censor to the global list", aliases=["gadd"])
    @WolfChecks.has_guild_permissions(manage_messages=True)
    async def add_global(self, ctx: commands.Context, *, censor: str):
        """
        Add a censor to the global list

        This command takes a single mandatory argument - the censor text. This may be a single word or a Python regular
        expression.
        """

        censor_config = self._config.get("censors", {})
        censor_list = censor_config.setdefault('global', [])

        if censor in censor_list:
            await ctx.send(embed=discord.Embed(
                title="Global Censors for " + ctx.guild.name,
                description="The word `" + censor + "` was already in the censor list.",
                color=Colors.DANGER
            ))
            return

        censor_list.append(censor)

        self._config.set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title="Global Censors for " + ctx.guild.name,
            description="The word `" + censor + "` was added to the global censor list.",
            color=Colors.PRIMARY
        ))

    @censor.command(name="remove", brief="Remove a censor from a channel")
    @WolfChecks.has_guild_permissions(manage_messages=True)
    async def remove_channel(self, ctx: commands.Context, channel: discord.TextChannel, *, censor: str):
        """
        Remove a censor from a channel list.

        This command takes two arguments - a mandatory channel identifier (ID, #mention, name) and the censor text. The
        censor text must be *exactly* as it is stored in the guild configuration for the deletion to be successful.
        """

        censor_config = self._config.get("censors", {})
        censor_list = censor_config.setdefault(str(channel.id), [])

        if censor not in censor_list:
            await ctx.send(embed=discord.Embed(
                title="Censors for " + channel.name,
                description="The word `" + censor + "` was not in the censor list, so not removed.",
                color=Colors.DANGER
            ))
            return

        censor_list.remove(censor)

        self._config.set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title="Censors for " + channel.name,
            description="The word `" + censor + "` was removed from the censor list for the specified channel",
            color=Colors.PRIMARY
        ))

    @censor.command(name="globalremove", brief="Remove a censor from the global list", aliases=["gremove"])
    async def remove_global(self, ctx: commands.Context, *, censor: str):
        """
        Remove a censor from a the global list.

        This command takes only one argument - the censor text. This must be *exactly* as it is stored in the guild
        configuration for the deletion to be successful.
        """

        censor_config = self._config.get("censors", {})
        censor_list = censor_config.setdefault('global', [])

        if censor not in censor_list:
            await ctx.send(embed=discord.Embed(
                title="Global Censors for " + ctx.guild.name,
                description="The word `" + censor + "` was not in the global censor list, so not removed.",
                color=Colors.DANGER
            ))
            return

        censor_list.remove(censor)

        self._config.set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title="Censors for " + ctx.guild.name,
            description="The word `" + censor + "` was removed from the global censor list",
            color=Colors.PRIMARY
        ))

    @censor.command(name="useradd", brief="Add a censor for a specific user", aliases=["uadd"])
    async def add_user(self, ctx: commands.Context, user: discord.Member, *, censor: str):
        """
        Add a censor for a specific user.

        This command allows moderators to define censors for a specific user. This applies to all channels and all
        messages from this user. Users may not create or edit censors for users not below them in the role hierarchy.

        This command takes two arguments: a user identifier (either a username, @mention, user id, etc.) and a regex
        censor to parse on.

        See also:
            /censor userremove - Remove a censor entry from a specific user
            /censor userlist   - List all censor entries for a specific user
        """

        if user.top_role.position >= ctx.message.author.top_role.position:
            await ctx.send(embed=discord.Embed(
                title="Censor Toolkit",
                description="You may not edit censors for `{}`, as they are not below you in the role "
                            "hierarchy.".format(user),
                color=Colors.DANGER
            ))
            return

        censor_config = self._config.get("censors", {})
        censor_list = censor_config.setdefault("user-" + str(user.id), [])

        if censor in censor_list:
            await ctx.send(embed=discord.Embed(
                title="Censors for {}".format(user),
                description="The word `" + censor + "` was already in the censor list.",
                color=Colors.PRIMARY
            ))
            return

        censor_list.append(censor)

        self._config.set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title="Censors for " + str(user),
            description="The word `" + censor + "` was added to the censor list for the specified user",
            color=Colors.PRIMARY
        ))

    @censor.command(name="userremove", brief="Remove a censor for a specific user", aliases=["uremove"])
    async def remove_user(self, ctx: commands.Context, user: discord.Member, *, censor: str):
        """
        Remove a censor from the specific user.

        This command allows moderators to define censors for a specific user. This applies to all channels and all
        messages from this user. Users may not create or edit censors for users not below them in the role hierarchy.

        This command takes two arguments: a user identifier (either a username, @mention, user id, etc.) and a regex
        censor to parse on. If the regex censor does not exist, this command will throw an error.

        See also:
            /censor useradd  - Add a new censor entry for a specific user
            /censor userlist - List all censor entries for a specific user
        """

        if user.top_role.position >= ctx.message.author.top_role.position:
            await ctx.send(embed=discord.Embed(
                title="Censor Toolkit",
                description="You may not edit censors for `{}`, as they are not below you in the role "
                            "hierarchy.".format(user),
                color=Colors.DANGER
            ))
            return

        censor_config = self._config.get("censors", {})
        censor_list = censor_config.setdefault("user-" + str(user.id), [])

        if censor not in censor_list:
            await ctx.send(embed=discord.Embed(
                title="Censors for {}".format(user),
                description="The word `" + censor + "` was not in the censor list, so not removed.",
                color=Colors.DANGER
            ))
            return

        censor_list.remove(censor)

        self._config.set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title="Censors for {}".format(user),
            description="The word `" + censor + "` was removed from the censor list for the specified channel",
            color=Colors.PRIMARY
        ))

    @censor.command(name="userlist", brief="List the censors for a specific user", aliases=["ulist"])
    async def list_user(self, ctx: commands.Context, user: discord.Member):
        """
        List all censors for a specific user.

        This command will find and return all censors for a specific user, as defined in the server configuration.

        It takes a single argument, namely a user identifier (user ID, mention, nickname, etc.).

        See also:
            /censor useradd  - Add a new censor entry for a specific user
            /censor userremove - Remove a censor entry from a specific user
        """

        censor_config = self._config.get("censors", {})

        censor_list = censor_config.get("user-" + str(user.id), [])

        await ctx.send(embed=discord.Embed(
            title="Censors for {}".format(user),
            description="The following words are censored in the requested channel:\n\n" + ", ".join(censor_list),
            color=Colors.PRIMARY
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Censor(bot))
