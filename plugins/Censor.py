import logging
import re

import discord
from discord.ext import commands

from WolfBot import WolfChecks
from WolfBot import WolfConfig
from WolfBot import WolfUtils
from WolfBot.WolfStatics import Colors

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Censor:
    """
    The Censor plugin allows moderators to lighten their workload and allow the bot to take care of automatic message
    deletion according to regular expressions.

    Message filtering is done relatively early in the event chain, so messages tend to be deleted fairly quickly.

    There are three types of censors:

    - Global Censors: As the name implies, a global censor applies to every channel in the configured guild. These
      messages are deleted by the bot no matter where they are.
    - Channel Censors: These censors only take effect in the defined channel. This allows for lower-level censor
      management and prevents the bot from being as strict.
    - User Censors: These censors apply only to a specific user, but they apply globally. Unlike the other two censors,
      staff members are not permitted to bypass them.

    Censors can take either plain text (that is, a single word) or regular expressions. All censors are evaluated as
    regular expressions.
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()

        LOG.info("Loaded plugin!")

    async def filter_message(self, message: discord.Message, context: str = "new_message"):
        if not WolfUtils.should_process_message(message):
            return

        censor_config = self._config.get("censors", {})

        global_censors = censor_config.get("global", [])
        channel_censors = censor_config.get(str(message.channel.id), [])
        user_censors = censor_config.get(f"user-{message.author.id}", [])

        censor_list = global_censors + channel_censors + user_censors

        if not isinstance(message.author, discord.Member):
            LOG.warning("Attempted to censor a message (ID %s) from user %s (ID %s), but they do not exist.",
                        message.id, str(message.author), message.author.id)
        elif message.author.permissions_in(message.channel).manage_messages:
            if len(user_censors) > 0:
                censor_list = user_censors
            else:
                return

        if any((re.search(censor_term, message.content, re.IGNORECASE) is not None) for censor_term in censor_list):
            try:
                await message.delete()
                LOG.info("Deleted censored message (context %s, from %s in %s): %s", context, message.author,
                         message.channel, message.content)
            except discord.NotFound:
                LOG.warning("I tried to delete a censored message (ID %s, ctx %s, from %s in %s), but I couldn't find "
                            "it. Was it already deleted?", message.id, context, message.author, message.channel)

    async def on_message(self, message):
        await self.filter_message(message)

    # noinspection PyUnusedLocal
    async def on_message_edit(self, before, after):
        await self.filter_message(after, "edit")

    @commands.group(name="censor", brief="Manage the Censor list for the guild")
    @commands.has_permissions(manage_messages=True)
    async def censor(self, ctx: commands.Context):
        """
        The parent command for the Censor plugin.

        This command doesn't do anything - it's merely the entrypoint to everything else censor-related.

        If you would like to see documentation on the Censor plugin, see `/help Censor`.
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
            title=f"Censors for {channel.name}",
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
            title=f"Global Censors for {ctx.guild.name}",
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
                title=f"Censors for {channel.name}",
                description=f"The word `{censor}` was already in the censor list.",
                color=Colors.PRIMARY
            ))
            return

        censor_list.append(censor)

        self._config.set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title=f"Censors for {channel.name}",
            description=f"The word `{censor}` was added to the censor list for the specified channel",
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
                title=f"Global Censors for {ctx.guild.name}",
                description=f"The word `{censor}` was already in the censor list.",
                color=Colors.DANGER
            ))
            return

        censor_list.append(censor)

        self._config.set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title=f"Global Censors for {ctx.guild.name}",
            description=f"The word `{censor}` was added to the global censor list.",
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
                title=f"Censors for {channel.name}",
                description=f"The word `{censor}` was not in the censor list, so not removed.",
                color=Colors.DANGER
            ))
            return

        censor_list.remove(censor)

        self._config.set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title=f"Censors for {channel.name}",
            description=f"The word `{censor}` was removed from the censor list for the specified channel",
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
                title=f"Global Censors for {ctx.guild.name}",
                description=f"The word `{censor}` was not in the global censor list, so not removed.",
                color=Colors.DANGER
            ))
            return

        censor_list.remove(censor)

        self._config.set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title=f"Censors for {ctx.guild.name}",
            description=f"The word `{censor}` was removed from the global censor list",
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
                description=f"You may not edit censors for `{user}`, as they are not below you in the role hierarchy.",
                color=Colors.DANGER
            ))
            return

        censor_config = self._config.get("censors", {})
        censor_list = censor_config.setdefault(f"user-{user.id}", [])

        if censor in censor_list:
            await ctx.send(embed=discord.Embed(
                title=f"Censors for {user}",
                description=f"The word `{censor}` was already in the censor list.",
                color=Colors.PRIMARY
            ))
            return

        censor_list.append(censor)

        self._config.set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title=f"Censors for {user}",
            description=f"The word `{censor}` was added to the censor list for the specified user",
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
                description=f"You may not edit censors for `{user}`, as they are not below you in the role hierarchy.",
                color=Colors.DANGER
            ))
            return

        censor_config = self._config.get("censors", {})
        censor_list = censor_config.setdefault(f"user-{user.id}", [])

        if censor not in censor_list:
            await ctx.send(embed=discord.Embed(
                title=f"Censors for {user}",
                description=f"The word `{censor}` was not in the censor list, so not removed.",
                color=Colors.DANGER
            ))
            return

        censor_list.remove(censor)

        self._config.set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title=f"Censors for {user}",
            description=f"The word `{censor}` was removed from the censor list for the specified channel",
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

        censor_list = censor_config.get(f"user-{user.id}", [])

        await ctx.send(embed=discord.Embed(
            title=f"Censors for {user}",
            description="The following words are censored in the requested channel:\n\n" + ", ".join(censor_list),
            color=Colors.PRIMARY
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Censor(bot))
