import datetime
import logging
import re

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfConverters
from WolfBot import WolfUtils
from WolfBot.WolfStatics import *
from WolfBot.managers.MuteManager import MuteManager

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class ModTools:
    """
    ModTools is a plugin that provides a set of core moderator tools to guilds running WolfBot.

    It includes such features as kick, ban, mute, warn, cleanup, and the like.

    Commands here are generally restricted to actual moderators (as determined by guild permissions). For detailed help
    about various aspects of this plugin, please see the individual help commands.
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()
        self._mute_manager = MuteManager(self.bot)
        LOG.info("Loaded plugin!")

    def __unload(self):
        # super.__unload()
        self._mute_manager.cleanup()

    # Prevent users from becoming bot role if they're not actually bots.
    async def on_member_update(self, before, after):
        if before.roles == after.roles:
            return

        special_roles = self._config.get("specialRoles", {})

        if special_roles.get('bots') is None:
            return

        bot_role = discord.utils.get(after.roles, id=int(special_roles.get('bots')))

        if (bot_role is not None) and (bot_role not in before.roles) and (not before.bot):
            await after.remove_roles(bot_role, reason="User is not an authorized bot.")
            LOG.info("User " + after.display_name + " was granted bot role, but was not a bot. Removing.")

    async def on_member_join(self, member: discord.Member):
        await self._mute_manager.restore_user_mute(member)

    @commands.command(name="pardon", aliases=["unban"], brief="Pardon a banned member from their ban")
    @commands.has_permissions(ban_members=True)
    async def pardon(self, ctx: discord.ext.commands.Context, user: WolfConverters.OfflineUserConverter):
        """
        Pardon a user currently banned from the guild.

        This command will reverse a ban of any user currently in the ban list.

        Unbanning a user generally takes a User ID, but in some rare cases (e.g. the user was recently banned), the ban
        can be lifted by using a user name or other unique mention (see /help ban for a more in-depth explanation).

        Note that a reason is not needed for an unban - just the user ID.
        """
        try:
            await ctx.guild.unban(user, reason="Unbanned by " + str(ctx.author))
        except discord.NotFound:
            await ctx.send(embed=discord.Embed(
                title="Mod Toolkit",
                description="User `" + str(user) + "` is not banned on this guild, so they can not be unbanned.",
                color=Colors.WARNING
            ))
            return

        await ctx.send(embed=discord.Embed(
            title="Mod Toolkit",
            description="User `" + str(user) + "` was successfully pardoned.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="ban", brief="Ban an active user of the Discord")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: WolfConverters.OfflineMemberConverter, *, reason: str):
        """
        Ban a user from the guild.

        The ban command will target and remove a user immediately from the guild, regardless of their guild state.

        Users with ban privileges may not ban users at or above themselves in the role hierarchy. Offline users are not
        restricted by this, as they have no roles assigned to them.

        To ban an online user, any identifiable key may be used. For example, a user ID, a username, a Name#Discrim, a
        username, or (in rare cases) a nickname. If the username has spaces in it, the username must be surrounded with
        "quotes" to be properly parsed.

        To ban an offline user, either a user ID (or a direct ping in form <@user_id>) will be necessary.

        A reason is always mandatory, and is just an arbitrary string.

        In the audit log, the bot will be credited with the ban, but a note will be added including the username of the
        responsible moderator.
        """

        # hack for pycharm (duck typing)
        user = user  # type: discord.Member

        if user == ctx.author:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description="You do not have permission to ban yourself from this guild. Please ask a staff member "
                            "with a higher rank than you for assistance.\n\nYou may also right-click the guild icon "
                            "and select **Leave Guild**. Note that leaving this guild will forfeit your staff "
                            "privileges.",
                color=Colors.DANGER
            ))
            return

        in_guild = True
        if not isinstance(user, discord.Member):
            in_guild = False
        elif user.top_role.position >= ctx.message.author.top_role.position:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description="User `{}` could not be banned, as they are not below you in the role "
                            "hierarchy.".format(user),
                color=Colors.DANGER
            ))
            return

        ban_entry = discord.utils.get(await ctx.guild.bans(), user=user)

        if ban_entry is not None:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description="User `{}` was already banned from the guild.".format(user),
                color=Colors.DANGER
            ))
            return

        await ctx.guild.ban(user, reason="[{}By {}] {}".format("HACKBAN | " if not in_guild else "",
                                                               ctx.author, reason), delete_message_days=1)

        await ctx.send(embed=discord.Embed(
            title="User banned.",
            description="User `{}` was successfully banned from the guild.".format(user),
            color=Colors.SUCCESS
        ))

    @commands.command(name="warn", brief="Issue an official warning to a user.", enabled=False)
    @commands.has_permissions(ban_members=True)
    async def warn(self, ctx: discord.ext.commands.Context, target: discord.Member, *, reason: str):
        pass

    @commands.command(name="mute", brief="Temporarily mute a user from the current channel")
    @commands.has_permissions(manage_messages=True)
    async def mute(self, ctx: discord.ext.commands.Context, target: discord.Member,
                   time: WolfConverters.DateDiffConverter, *, reason: str):
        """
        Mute a user from the current channel.

        This command will allow a moderator to temporarily (or permanently) remove a user's rights to speak and add
        new reactions in the current channel. Mutes will automatically expire within up to 15 seconds of the target time
        returned with the command.

        `target` must be any identifiable user string (mention, user ID, username, etc).

        `time` is a timedelta in the form of #d#h#m#s. To make a mute permanent, set this value to 0, perm, or -.

        `reason` is a mandatory explanation field logging why the mute was given.

        Example commands:
        /mute SomeSpammer 90s Image spam  - Mute user SomeSpammer for 90 seconds
        /mute h4xxy perm General rudeness - Mute user h4xxy permanently
        /mute Dog 0 woof                  - Mute user Dog permanently.
        """
        # ToDo: Implement database, and better logging.

        if target.top_role.position >= ctx.message.author.top_role.position:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description="User `{}` could not be muted, as they are not below you in the role "
                            "hierarchy.".format(target),
                color=Colors.DANGER
            ))
            return

        if time is None:
            mute_until = None
            pretty_string = ""
        else:
            mute_until = datetime.datetime.utcnow() + time
            pretty_string = "\nTheir mute will expire at {} UTC".format(mute_until.strftime(DATETIME_FORMAT))
            mute_until = int(mute_until.timestamp())

        # Try to find a mute from this user
        existing_mute = await self._mute_manager.find_user_mute_record(target, ctx.channel)

        if existing_mute is not None:
            await self._mute_manager.update_mute_record(existing_mute, reason, mute_until)

            await ctx.send(embed=discord.Embed(
                title=Emojis.MUTE + " {}'s mute for #{} was updated!".format(target, ctx.channel),
                description="User has been muted from the channel.{}".format(pretty_string),
                color=Colors.WARNING
            ))
            return

        await self._mute_manager.mute_user(ctx, target, ctx.channel, reason, mute_until, ctx.author)

        await ctx.send(embed=discord.Embed(
            title=Emojis.MUTE + " {} muted from {}!".format(target, "#" + str(ctx.channel)),
            description="User has been muted from this channel.{}".format(pretty_string),
            color=Colors.WARNING
        ))

    @commands.command(name="globalmute", aliases=["gmute"],
                      brief="Temporarily mute a user from the guild")
    @commands.has_permissions(ban_members=True)
    async def globalmute(self, ctx: discord.ext.commands.Context, target: discord.Member,
                         time: WolfConverters.DateDiffConverter, *, reason: str):
        """
        Mute a user from talking anywhere in the guild.

        If a full mute is desired across the entire guild, /globalmute should be used instead. The arguments are the
        same as for /mute, but this will instead grant a "Muted" role as defined in the bot configuration.

        See /help mute for further details on how this command works.
        """
        if target.top_role.position >= ctx.message.author.top_role.position:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description="User `{}` could not be muted, as they are not below you in the role "
                            "hierarchy.".format(target),
                color=Colors.DANGER
            ))
            return

        if time is None:
            mute_until = None
            pretty_string = ""
        else:
            mute_until = datetime.datetime.utcnow() + time
            pretty_string = "\nTheir mute will expire at {} UTC".format(mute_until.strftime(DATETIME_FORMAT))
            mute_until = int(mute_until.timestamp())

        # Try to find a mute from this user
        existing_mute = await self._mute_manager.find_user_mute_record(target, None)

        if existing_mute is not None:
            await self._mute_manager.update_mute_record(existing_mute, reason, mute_until)

            await ctx.send(embed=discord.Embed(
                title=Emojis.MUTE + " {}'s guild mute was updated!".format(target),
                description="User has been muted from the guild.{}".format(pretty_string),
                color=Colors.WARNING
            ))
            return

        await self._mute_manager.mute_user(ctx, target, None, reason, mute_until, ctx.author)

        await ctx.send(embed=discord.Embed(
            title=Emojis.MUTE + " {} muted from the guild!".format(target),
            description="User has been muted from the guild.{}".format(pretty_string),
            color=Colors.WARNING
        ))

    @commands.command(name="unmute", brief="Unmute a user currently muted in the active channel")
    @commands.has_permissions(manage_messages=True)
    async def unmute(self, ctx: discord.ext.commands.Context, target: discord.Member):
        """
        Unmute a currently muted user from the channel.

        This command will allow a moderator to clear all mutes for a user in the current channel. This command will not
        affect mutes in other channels, nor will it clear a global mute.

        The only parameter of this is `target`, or the user to unmute.

        Example Commands:
        /unmute SomeSpammer    - Unmute a user named SomeSpammer
        /unmute @Dog#4171      - Unmute a user named Dog
        """
        # Try to find a mute from this user
        mute = await self._mute_manager.find_user_mute_record(target, ctx.channel)

        if mute is None:
            await ctx.send(embed=discord.Embed(
                title="{} is not muted in {}.".format(target, "#" + str(ctx.channel)),
                description="The user you have tried to mute has no existing mute records for this channel.",
                color=Colors.WARNING
            ))
            return

        await self._mute_manager.unmute_user(mute, ctx.author.mention)

        await ctx.send(embed=discord.Embed(
            title=Emojis.UNMUTE + " {} unmuted from {}!".format(target, "#" + str(ctx.channel)),
            description="User has been unmuted from this channel.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="globalunmute", aliases=["gunmute"],
                      brief="Unmute a user currently muted in the active channel")
    @commands.has_permissions(manage_messages=True)
    async def global_unmute(self, ctx: discord.ext.commands.Context, target: discord.Member):
        """
        Unmute a currently globally-muted user.

        This command will allow a moderator to clear all mutes for a user across the entire guild. This command will not
        alter per-channel mutes, but it will clear the muted role.

        DO NOT manually unmute users via role, as this creates data inconsistencies!

        See /help unmute for further information on how to use this command.
        """
        # Try to find a mute from this user
        mute = await self._mute_manager.find_user_mute_record(target, None)

        if mute is None:
            await ctx.send(embed=discord.Embed(
                title="{} is not muted in the guild.".format(target),
                description="The user you have tried to mute has no existing mute records for the guild.",
                color=Colors.WARNING
            ))
            return

        await self._mute_manager.unmute_user(mute, ctx.author.mention)
        await ctx.send(embed=discord.Embed(
            title=Emojis.UNMUTE + " {} unmuted from the guild!".format(target),
            description="User has been unmuted from the guild.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="roleping", brief="Ping all users with a certain role")
    @commands.has_permissions(manage_roles=True)
    async def roleping(self, ctx: commands.Context, target: discord.Role, *, message: str):
        """
        Mention a role without permissions to *actually* manage/mention that role.

        This command is a quick-and-simple way of mentioning a role and mass pinging users without mucking around with
        configs or risking a user attempting to abuse the open hole left by making the role mentionable.

        The only required arguments for this command are a role identifier (either name, ID, or ping) and the message.

        In order to prevent mass confusion, the bot will include the name of the user who triggered the ping. This
        will also be recorded in the audit log.
        """
        is_role_mentionable = target.mentionable

        if not is_role_mentionable:
            await target.edit(reason="Role Ping requested by " + str(ctx.message.author), mentionable=True)

        await ctx.send(target.mention + " <" + ctx.message.author.display_name + "> " + message)

        if not is_role_mentionable:
            await target.edit(reason="Role Ping requested by " + str(ctx.message.author)
                                     + " completed", mentionable=False)

    @commands.command(name="cleanup", aliases=["mcu", "bulkdelete"], brief="Clean up many messages quickly")
    @commands.has_permissions(manage_messages=True)
    async def cleanup(self, ctx: commands.Context, lookback: int, *, filter_def: str = None):
        """
        Quickly and easily delete multiple messages.

        This supports an advanced filtering system, currently supporting the following flags:

        - --[user|member|author] <user reference> : Filter by a specific user
        - --[regex] <regex>                       : Filter by a regular expression

        If multiple filters of the same type are used, *any* will match to delete the message. For example, running
        "/cleanup 100 --user 123 --user 456" will delete all messages posted by users 123 and 456 that it finds in the
        last 100 messages.

        If differing filters are used, *both* must match. That is, "/cleanup 10 --user 123 --regex cat" will delete all
        messages from user 123 that match the regex `cat`.

        These can be combined, so "/cleanup 100 --user 123 --user 456 --regex cat" will delete any mention of regex
        `cat` by users 123 or 456 in the last 100 messages.

        The "lookback" value is the number of messages to search for messages that match the defined filters. If no
        filters are defined, then *all* messages match, and lookback will be the total number of messages to delete.
        """

        # BE VERY CAREFUL TOUCHING THIS METHOD!
        def generate_cleanup_filter():
            if filter_def is None:
                return None

            content_list = filter_def.split('--')

            # Filter types
            regex_list = []
            user_list = []

            for filter_candidate in content_list:
                if filter_candidate is None or filter_candidate == '':
                    continue

                filter_candidate = filter_candidate.strip()
                filter_candidate = filter_candidate.split(" ", 1)

                if filter_candidate[0] in ["user", "author", "member"]:
                    user_id = WolfUtils.get_user_id_from_arbitrary_str(ctx.guild, filter_candidate[1])
                    user_list.append(user_id)
                elif filter_candidate[0] in ["regex"]:
                    regex_list.append(filter_candidate[1])
                else:
                    raise KeyError("Filter {} is not valid!".format(filter_candidate[0]))

            def dynamic_check(message: discord.Message):
                if len(user_list) > 0 and message.author.id not in user_list:
                    return False

                for regex in regex_list:
                    if len(regex_list) > 0 and re.search(regex, message.content) is None:
                        return False

                return True

            return dynamic_check

        await ctx.channel.purge(limit=lookback + 1, check=generate_cleanup_filter(), bulk=True)


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(ModTools(bot))
