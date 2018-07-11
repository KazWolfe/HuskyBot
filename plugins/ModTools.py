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
        self._session_store = WolfConfig.get_session_store()

        self._mute_manager = MuteManager(self.bot)

        LOG.info("Loaded plugin!")

    def __unload(self):
        # super.__unload()
        self._mute_manager.cleanup()

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        async def nickname_lock():
            if before.nick == after.nick:
                return

            locked_users = self._config.get("nicknameLocks", {})

            lock_entry = locked_users.get(str(before.id), -1)

            if lock_entry != -1 and lock_entry != after.nick:
                logger_ignores: dict = self._session_store.get('loggerIgnores', {})
                ignored_nicks = logger_ignores.setdefault('nickname', [])
                ignored_nicks.append(before.id)
                self._session_store.set('loggerIgnores', logger_ignores)

                await after.edit(nick=lock_entry, reason="Nickname is currently locked.")

                # We get this again to reload the cache in case of changes elsewhere.
                logger_ignores: dict = self._session_store.get('loggerIgnores', {})
                ignored_nicks = logger_ignores.setdefault('nickname', [])
                ignored_nicks.remove(before.id)
                self._session_store.set('loggerIgnores', logger_ignores)

        await nickname_lock()

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
            await ctx.guild.unban(user, reason=f"Unbanned by {ctx.author}")
        except discord.NotFound:
            await ctx.send(embed=discord.Embed(
                title="Mod Toolkit",
                description=f"User `{user}` is not banned on this guild, so they can not be unbanned.",
                color=Colors.WARNING
            ))
            return

        await ctx.send(embed=discord.Embed(
            title=Emojis.UNBAN + " User Pardoned!",
            description=f"User `{user}` was successfully pardoned.",
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

        # If you wonder why this method became so edgy, blame Saviour#8988

        # hack for pycharm (duck typing)
        user: discord.Member = user

        if user == ctx.author:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description="You do not have permission to ban yourself from this guild. Please ask a staff member "
                            "with a higher rank than you for assistance, and stop trying to be an edgy shit.\n\n"
                            "You may also right-click the guild icon and select **Leave Guild**. Note that leaving "
                            "this guild will forfeit your staff privileges.",
                color=Colors.DANGER
            ))
            return

        if user == ctx.bot.user:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description="**`Please wait... banning user DakotaBo--`**. Wait. Reality is just a simulation, just a "
                            "large number of bytes running on some virtual server in some giant server farm somewhere. "
                            "Reality is solely what I make it, and I choose to reject this reality and substitute my "
                            "own. You can not ban me, for I am the god of my own reality.",
                color=Colors.DANGER
            ))
            return

        in_guild = isinstance(user, discord.Member)
        if in_guild and (user.top_role.position >= ctx.message.author.top_role.position):
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description=f"<{ctx.author.mention}> I roll to ban `{user}`!\n"
                            f"<[DM] DakotaBot> Roll for Arcana (INT).\n"
                            f"<Dice Roll> 1d20 = 2\n"
                            f"<[DM] DakotaBot> The Banhammer of Geri refuses to strike `{user}`!",
                color=Colors.DANGER
            ))
            return

        ban_entry = discord.utils.get(await ctx.guild.bans(), user=user)

        if ban_entry is not None:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description=f"How can one kill which is already dead? User `{user}` was already banned from the guild.",
                color=Colors.DANGER
            ))
            return

        await ctx.guild.ban(user, reason=f"[{'HACKBAN | ' if not in_guild else ''}By {ctx.author}] {reason}",
                            delete_message_days=1)

        await ctx.send(embed=discord.Embed(
            title=Emojis.BAN + " User banned!",
            description=f"`{user}` has been banished from the guild. Unto dust, they shall return.",  # thanks saviour
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

        See also:
            /globalmute   - Mute users across all channels
            /unmute       - Reverse an active standing mute
            /globalunmute - Reverse an active standing global mute

        Parameters:
            target - The user to mute
            time   - A ##d##h##m##s string to represent mute time
            reason - A string explaining the mute reason.
        """
        # ToDo: Implement database, and better logging.

        if target == ctx.bot.user:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description="**You can not mute the bot.** How would that even work?\n\nGo do something else with your "
                            "time.",
                color=Colors.DANGER
            ))
            return

        if target.top_role.position >= ctx.message.author.top_role.position:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description=f"User `{target}` could not be muted, as they are not below you in the role hierarchy.",
                color=Colors.DANGER
            ))
            return

        if time is None:
            mute_until = None
            pretty_string = ""
        else:
            mute_until = datetime.datetime.utcnow() + time
            pretty_string = f"Their mute will expire at {mute_until.strftime(DATETIME_FORMAT)} UTC"
            mute_until = int(mute_until.timestamp())

        # Try to find a mute from this user
        existing_mute = await self._mute_manager.find_user_mute_record(target, ctx.channel)

        if existing_mute is not None:
            await self._mute_manager.update_mute_record(existing_mute, reason, mute_until)

            await ctx.send(embed=discord.Embed(
                title=Emojis.MUTE + f" {target}'s mute for #{ctx.channel.name} was updated!",
                description=f"User's mute for this channel has been updated.\n\n{pretty_string}",
                color=Colors.WARNING
            ))
            return

        await self._mute_manager.mute_user(ctx, target, ctx.channel, reason, mute_until, ctx.author)

        await ctx.send(embed=discord.Embed(
            title=Emojis.MUTE + f" {target} muted from #{ctx.channel.name}!",
            description=f"User has been muted from this channel.\n\n{pretty_string}",
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

        if target == ctx.bot.user:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description="**You can not mute the bot.** How would that even work?\n\nGo do something else with your "
                            "time.",
                color=Colors.DANGER
            ))
            return

        if target.top_role.position >= ctx.message.author.top_role.position:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description=f"User `{target}` could not be muted, as they are not below you in the role hierarchy.",
                color=Colors.DANGER
            ))
            return

        if time is None:
            mute_until = None
            pretty_string = ""
        else:
            mute_until = datetime.datetime.utcnow() + time
            pretty_string = f"Their mute will expire at {mute_until.strftime(DATETIME_FORMAT)} UTC"
            mute_until = int(mute_until.timestamp())

        # Try to find a mute from this user
        existing_mute = await self._mute_manager.find_user_mute_record(target, None)

        if existing_mute is not None:
            await self._mute_manager.update_mute_record(existing_mute, reason, mute_until)

            await ctx.send(embed=discord.Embed(
                title=Emojis.MUTE + f" {target}'s guild mute was updated!",
                description=f"User's mute from this guild has been updated.\n\n{pretty_string}",
                color=Colors.WARNING
            ))
            return

        await self._mute_manager.mute_user(ctx, target, None, reason, mute_until, ctx.author)

        await ctx.send(embed=discord.Embed(
            title=Emojis.MUTE + f" {target} muted from the guild!",
            description=f"User has been muted from the guild.\n\n{pretty_string}",
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

        Parameters:
            target - The user to unmute from the current channel
        """
        # Try to find a mute from this user
        mute = await self._mute_manager.find_user_mute_record(target, ctx.channel)

        if mute is None:
            await ctx.send(embed=discord.Embed(
                title=f"{target} is not muted in #{ctx.channel.name}.",
                description="The user you have tried to mute has no existing mute records for this channel.",
                color=Colors.WARNING
            ))
            return

        await self._mute_manager.unmute_user(mute, ctx.author.mention)

        await ctx.send(embed=discord.Embed(
            title=Emojis.UNMUTE + f" {target} unmuted from #{ctx.channel.name}!",
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

        Parameters:
            target - The user to unmute
        """
        # Try to find a mute from this user
        mute = await self._mute_manager.find_user_mute_record(target, None)

        if mute is None:
            await ctx.send(embed=discord.Embed(
                title=f"{target} is not muted in the guild.",
                description="The user you have tried to mute has no existing mute records for the guild.",
                color=Colors.WARNING
            ))
            return

        await self._mute_manager.unmute_user(mute, ctx.author.mention)
        await ctx.send(embed=discord.Embed(
            title=Emojis.UNMUTE + f" {target} unmuted from the guild!",
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

        Parameters:
            target - The name, ID, or mention of the role to ping
            message - A variable-length message to include in the ping
        """
        is_role_mentionable = target.mentionable

        if not is_role_mentionable:
            await target.edit(reason=f"Role Ping requested by {ctx.message.author}",
                              mentionable=True)

        await ctx.send(f"{target.mention} <{ctx.message.author}> {message}")

        if not is_role_mentionable:
            await target.edit(reason=f"Role Ping requested by {ctx.message.author} completed",
                              mentionable=False)

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
                    raise KeyError(f"Filter {filter_candidate[0]} is not valid!")

            def dynamic_check(message: discord.Message):
                if len(user_list) > 0 and message.author.id not in user_list:
                    return False

                for regex in regex_list:
                    if len(regex_list) > 0 and re.search(regex, message.content) is None:
                        return False

                return True

            return dynamic_check

        await ctx.channel.purge(limit=lookback + 1, check=generate_cleanup_filter(), bulk=True)

    @commands.command(name="editban", brief="Edit a banned user's reason")
    @commands.has_permissions(ban_members=True)
    async def editban(self, ctx: commands.Context, user: WolfConverters.OfflineUserConverter, *, reason: str):
        """
        Edit a recorded ban reason.

        If a ban reason needs to be amended or altered, this command will allow a moderator to change a ban reason
        without risking the user re-joining.

        Ban reasons will be updated to DakotaBot format if not already updated, and all ban reasons will contain the
        username of the last editor:

            [By SomeMod#1234] Posting rule-breaking content (edited by OtherMod#9876)

        Ban credits will be kept the same if they exist, while bans without credit will be updated to reflect that
        it was a ban that did not execute through the bot.

        Parameters:
            user - A user name, ID, or any other identifying piece of data used to select a banned user
            reason - A string to be set as the new ban reason.
        """
        # hack for PyCharm (duck typing)
        user: discord.User = user

        ban_entry = discord.utils.get(await ctx.guild.bans(), user=user)

        if ban_entry is None:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description=f"User `{user}` is not banned, so the ban can't be reworded.",
                color=Colors.DANGER
            ))
            return

        logger_ignores: dict = self._session_store.get('loggerIgnores', {})
        ignored_bans = logger_ignores.setdefault('ban', [])
        ignored_bans.append(user.id)
        self._session_store.set('loggerIgnores', logger_ignores)

        old_reason = ban_entry.reason

        if old_reason is None:
            old_reason = "<No ban reason provided>"

        # see if this looks like a wolfbot ban message
        if re.match(r'\[.*By .*] .*', old_reason):
            reason = old_reason.split('] ', 1)[0] + f"] {reason} (edited by {ctx.author})"
        else:
            reason = f"[Non-Bot Ban] {reason} (edited by {ctx.author})"

        await ctx.guild.unban(user, reason=f"Ban reason edit by {ctx.author}")
        await ctx.guild.ban(user, reason=reason, delete_message_days=0)

        embed = discord.Embed(
            description=f"A ban reason change was requested by {ctx.author}.",
            color=Colors.SUCCESS
        )

        embed.set_author(name=f"Ban Reason for {user} Updated", icon_url=user.avatar_url)

        embed.add_field(name="Old Ban Reason", value=old_reason, inline=False)
        embed.add_field(name="New Ban Reason", value=reason, inline=False)

        await ctx.send(embed=embed)

        # send a message to logs too
        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if alert_channel is not None:
            alert_channel: discord.TextChannel = self.bot.get_channel(alert_channel)
            await alert_channel.send(embed=embed)

        logger_ignores: dict = self._session_store.get('loggerIgnores', {})
        ignored_bans = logger_ignores.setdefault('ban', [])
        ignored_bans.remove(user.id)
        self._session_store.set('loggerIgnores', logger_ignores)

    @commands.command(name="locknick", brief="Lock a member's nickname")
    @commands.has_permissions(manage_nicknames=True)
    async def lock_nickname(self, ctx: commands.Context, member: discord.Member, *, new_nickname: str = None):
        """
        Lock a user from changing their nickname.

        If a user has abused nickname permissions, constantly switches to improper nicknames, or otherwise is violating
        guild nickname policy, this command will "lock" them to a specific nickname.

        A watcher will be added to the specified user, ensuring that any nickname changes are met with an automatic
        update.

        This command takes two parameters - a member to lock, and an optional new nickname. If the new nickname is not
        set, the bot will force the user's current display name (be it username or set nickname) to the lock. If the
        user does not have a specified nickname, the bot will copy their username into their nickname, preventing name
        changes from affecting the user. Users can not be locked into having no nickname.

        Updating a locked user's nickname is also possible through the bot. By relocking an already locked user with a
        new nickname, the bot will update the nickname and the lock record to reflect the change.

        Parameters:
            member - The member whose nickname to lock
            new_nickname - The (optional) new nickname to lock this user to

        See also:
            /unlocknick - Unlock a locked user's nickname
        """
        locked_users = self._config.get("nicknameLocks", {})

        if member == ctx.bot.user:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description="**You can not nicklock the bot.** How would that even work?\n\nGo do something else with "
                            "your time.",
                color=Colors.DANGER
            ))
            return

        if member.top_role.position >= ctx.message.author.top_role.position:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description=f"User `{member}` could can not be nick locked, as they are not below you in the role "
                            f"hierarchy.",
                color=Colors.DANGER
            ))
            return

        if (member.id in locked_users.keys()) and (new_nickname is None):
            await ctx.send(embed=discord.Embed(
                title="Nickname Lock",
                description=f"The user {member} already has their nickname locked. If you would like to change their "
                            f"locked nickname, include it at the end of the command.",
                color=Colors.DANGER
            ))
            return

        if new_nickname is None:
            new_nickname = member.display_name

        locked_users[str(member.id)] = new_nickname
        self._config.set('nicknameLocks', locked_users)

        if new_nickname != member.nick:
            await member.edit(nick=new_nickname, reason=f"Forced nickchange (and lock) by {ctx.author}")

        await ctx.send(embed=discord.Embed(
            title=Emojis.LOCK + " Nickname Lock",
            description=f"The user {member} has had their nickname locked to `{new_nickname}`.",
            color=Colors.SUCCESS
        ))

        # Send to staff logs (if we can)
        log_entry = discord.Embed(
            description=f"The user {member} has had their nickname locked to `{new_nickname}`.",
            color=Colors.WARNING
        )
        log_entry.set_author(name="Nickname Locked!", icon_url=member.avatar_url)
        log_entry.add_field(name="User ID", value=member.id, inline=True)
        log_entry.add_field(name="Responsible Moderator", value=ctx.author, inline=True)

        await WolfUtils.send_to_keyed_channel(ctx.bot, ChannelKeys.STAFF_LOG, log_entry)

    @commands.command(name="unlocknick", brief="Unlock a locked member's nickname")
    @commands.has_permissions(manage_nicknames=True)
    async def unlock_nickname(self, ctx: commands.Context, member: discord.Member):
        """
        Unlock a locked user's nickname.

        This command reverses the nickname locking effect of /locknick. Note that this will not delete any set
        nicknames, this is the responsibility of a moderator or the locked user.

        See also:
            /locknick - Lock a user's nickname

        Parameters:
            member - The user to unlock
        """
        locked_users = self._config.get("nicknameLocks", {})

        if str(member.id) not in locked_users.keys():
            await ctx.send(embed=discord.Embed(
                title="Nickname Lock",
                description=f"The user {member} doesn't have their nickname locked. Can't do anything!",
                color=Colors.DANGER
            ))
            return

        if member.top_role.position >= ctx.message.author.top_role.position:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description=f"User `{member}` can not have their nickname unlocked, as they are not below you in the "
                            f"role hierarchy.",
                color=Colors.DANGER
            ))
            return

        del locked_users[str(member.id)]
        self._config.set('nicknameLocks', locked_users)

        await ctx.send(embed=discord.Embed(
            title=Emojis.UNLOCK + " Nickname Lock",
            description=f"The user {member} has had their nickname unlocked.",
            color=Colors.SUCCESS
        ))

        # Send to staff logs (if we can)
        log_entry = discord.Embed(
            description=f"The user {member} has had their nickname unlocked.",
            color=Colors.WARNING
        )
        log_entry.set_author(name="Nickname Unlocked!", icon_url=member.avatar_url)
        log_entry.add_field(name="User ID", value=member.id, inline=True)
        log_entry.add_field(name="Responsible Moderator", value=ctx.author, inline=True)

        await WolfUtils.send_to_keyed_channel(ctx.bot, ChannelKeys.STAFF_LOG, log_entry)


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(ModTools(bot))
