import asyncio
import datetime
import logging
import re

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfConverters
from WolfBot import WolfData
from WolfBot import WolfUtils
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic,PyUnresolvedReferences
class ModTools:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()
        self._mute_manager = MuteHandler(self.bot)
        LOG.info("Loaded plugin!")

    def __unload(self):
        super.__unload()
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

        The ban command will target and remove a user immediately from the guild, regardless of their server state.

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
        if user == ctx.author:
            await ctx.send(embed=discord.Embed(
                title="Hello darkness my old friend...",
                url="https://www.youtube.com/watch?v=4zLfCnGVeL4",
                description="Permissions willing, you will be banned in 30 seconds. Thank you for using the WolfBot "
                            "suicide booth. On behalf of the DIY Tech Discord, we wish you the best of luck in your "
                            "next life, provided such a thing even exists.",
                color=0x000000
            ))
            await asyncio.sleep(30)
            await ctx.guild.ban(user, reason="User requested self-ban.")
            return

        in_server = True
        if not isinstance(user, discord.Member):
            in_server = False
        elif user.top_role.position >= ctx.message.author.top_role.position:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description="User `{}` could not be banned, as they are not below you in the role hierarchy."
                    .format(user),
                color=Colors.DANGER
            ))
            return

        await ctx.guild.ban(user, reason="[{}By {}] {}".format("HACKBAN | " if not in_server else "",
                                                               ctx.author, reason), delete_message_days=1)

        await ctx.send(embed=discord.Embed(
            title="Ka-Ban!",
            description="User `{}` was successfully banned.".format(user),
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

        `time` is a timedelta in the form of #h#m#s. To make a mute permanent, set this value to 0, perm, or -.

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
                description="User `{}` could not be muted, as they are not below you in the role hierarchy."
                    .format(target),
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
                description="User `{}` could not be muted, as they are not below you in the role hierarchy."
                    .format(user),
                color=Colors.DANGER
            ))
            return

        if time.lower() in ["permanent", "perm", "0", "-"]:
            mute_until = None
            pretty_string = ""
        else:
            mute_until = datetime.datetime.utcnow() + WolfUtils.get_timedelta_from_string(time)
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


class MuteHandler:
    def __init__(self, bot: commands.Bot):
        self._bot = bot
        self._bot_config = WolfConfig.getConfig()
        self._mute_config = WolfConfig.WolfConfig('config/mutes.json')
        self.__cache__ = []

        self.load_mutes()
        self.__task__ = self._bot.loop.create_task(self.check_mutes())

        LOG.info("Loaded mute submodule!")

    def load_mutes(self):
        disk_mutes = self._mute_config.get("mutes", [])

        for raw_mute in disk_mutes:
            mute = WolfData.Mute()
            mute.load_dict(raw_mute)

            if not mute.is_expired():
                self.__cache__.append(mute)
            else:
                self.__cache__.remove(mute)

        self._mute_config.set("mutes", self.__cache__)

    async def check_mutes(self):
        while not self._bot.is_closed():
            for mute in self.__cache__:
                # Check if the mute in-cache is expired.
                if mute.is_expired():
                    LOG.info("Found a scheduled unmute - [{}, {}]. Triggering...".format(mute.user_id, mute.channel))
                    await self.unmute_user(mute, "System - Scheduled")

            # Check again every 15 seconds (or thereabouts)
            await asyncio.sleep(5 if len(self.__cache__) < 60 else 15)

    async def mute_user_by_object(self, mute: WolfData.Mute, staff_member: str = "System"):
        guild = self._bot.get_guild(mute.guild)

        member = guild.get_member(mute.user_id)
        channel = None

        expiry_string = ""
        if mute.expiry is not None:
            expiry_string = " (muted until {})".format(
                datetime.datetime.fromtimestamp(mute.expiry).strftime(DATETIME_FORMAT))

        if mute.channel is None:
            mute_role = discord.utils.get(guild.roles, id=self._bot_config.get("specialRoles", {}).get("muted"))
            mute_context = "the guild"

            if mute_role is None:
                raise ValueError("A muted role is not set!")

            await member.add_roles(mute_role, reason="Muted by {} for reason {}{}"
                                   .format(staff_member, mute.reason, expiry_string))
        else:
            channel = guild.get_channel(mute.channel)
            mute_context = channel.mention

            await channel.set_permissions(member, reason="Muted by {} for reason {}{}"
                                          .format(staff_member, mute.reason, expiry_string), send_messages=False,
                                          add_reactions=False)

        if mute not in self.__cache__:
            self.__cache__.append(mute)
            self._mute_config.set("mutes", self.__cache__)

            # Inform the server logs
            alert_channel = self._bot_config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

            if alert_channel is None:
                return

            alert_channel = member.guild.get_channel(alert_channel)

            embed = discord.Embed(
                description="User ID `{}` was muted from {}.".format(member.id, mute_context),
                color=Colors.WARNING
            )

            embed.set_author(name="{} was muted from {}!".format(member,
                                                                 "the guild" if mute.channel is None else
                                                                 "#" + str(channel)),
                             icon_url=member.avatar_url)
            embed.add_field(name="Responsible User", value=str(staff_member), inline=True)
            embed.add_field(name="Timestamp", value=WolfUtils.get_timestamp(), inline=True)
            embed.add_field(name="Expires At", value=datetime.datetime.fromtimestamp(mute.expiry)
                            .strftime(DATETIME_FORMAT) if mute.expiry is not None else "Never", inline=True)
            embed.add_field(name="Reason", value=mute.reason, inline=False)

            await alert_channel.send(embed=embed)

    async def mute_user(self, ctx: commands.Context, member: discord.Member, channel,
                        reason: str, expiry: int, staff_member: discord.Member):

        if channel is None:
            channel_id = None
            current_perms = None
        else:
            channel_id = channel.id
            current_perms = channel.overwrites_for(member)

        mute_obj = WolfData.Mute()
        mute_obj.guild = ctx.guild.id
        mute_obj.user_id = member.id
        mute_obj.reason = reason
        mute_obj.channel = channel_id
        mute_obj.expiry = expiry
        mute_obj.set_cached_override(current_perms)

        await self.mute_user_by_object(mute_obj, staff_member.mention)

    async def unmute_user(self, mute: WolfData.Mute, staff_member: str):
        if staff_member is not None:
            unmute_reason = "user {}".format(staff_member)
        else:
            unmute_reason = "expiry"

        guild = self._bot.get_guild(mute.guild)
        member = guild.get_member(mute.user_id)

        # Member is no longer on the server, so their perms are cleared. Delete their records once their mute
        # is up.
        if member is None:
            LOG.info("Left user ID {} has had their mute expire. Removing it.".format(mute.user_id))
            self.__cache__.remove(mute)
            self._mute_config.set("mutes", self.__cache__)

            return

        if mute.channel is not None:
            channel = self._bot.get_channel(mute.channel)
            unmute_context = channel.mention

            await channel.set_permissions(member, overwrite=mute.get_cached_override(),
                                          reason="User's channel mute has been lifted by {}".format(unmute_reason))
        else:
            unmute_context = "the guild"
            channel = None

            mute_role = discord.utils.get(guild.roles, id=self._bot_config.get("specialRoles", {})
                                          .get(SpecialRoleKeys.MUTED.value))

            if mute_role is None:
                raise ValueError("A muted role is not set!")

            await member.remove_roles(mute_role,
                                      reason="User's server mute has been lifted by {}".format(unmute_reason))

        # Remove from the disk
        self.__cache__.remove(mute)
        self._mute_config.set("mutes", self.__cache__)

        # Inform the server logs
        alert_channel = self._bot_config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

        if alert_channel is None:
            return

        alert_channel = member.guild.get_channel(alert_channel)

        embed = discord.Embed(
            description="User {} was unmuted from #{}.".format(mute.user_id, unmute_context),
            color=Colors.INFO
        )

        embed.set_author(
            name="{} was unmuted from {}!".format(member, "the guild" if mute.channel is None else "#" + str(channel)),
            icon_url=member.avatar_url),
        embed.add_field(name="Responsible User", value=str(staff_member), inline=True)

        await alert_channel.send(embed=embed)

    async def restore_user_mute(self, member: discord.Member):
        for mute in self.__cache__:
            if (mute.user_id == member.id) and not mute.is_expired():
                LOG.info("Restoring mute state for left user {} in channel".format(member, mute.channel))
                await self.mute_user_by_object(mute, "System - ReJoin")

    async def find_user_mute_record(self, member: discord.Member, channel):
        result = None

        channel_id = None
        if channel is not None:
            channel_id = channel.id

        for mute in self.__cache__:
            if member.id == mute.user_id and channel_id == mute.channel:
                result = mute

        if result is None:
            return None

        return result

    async def update_mute_record(self, mute: WolfData.Mute, reason: str = None, expiry: int = None):

        if mute not in self.__cache__:
            raise KeyError("This record doesn't exist in the cache!")

        self.__cache__.remove(mute)

        if reason is not None:
            mute.reason = reason

        if expiry is not None:
            mute.expiry = expiry

        # Update cache
        self.__cache__.append(mute)

        # Update the disk
        self._mute_config.set("mutes", self.__cache__)

    async def cleanup(self):
        self.__task__.cancel()


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(ModTools(bot))
