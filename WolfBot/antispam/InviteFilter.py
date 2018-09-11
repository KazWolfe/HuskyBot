import datetime
import logging
import re

import discord
from discord.ext import commands
from discord.http import Route

from WolfBot import WolfConfig
from WolfBot.WolfStatics import *
from WolfBot.antispam import AntiSpamModule

LOG = logging.getLogger("DakotaBot.Plugin.AntiSpam." + __name__.split('.')[-1])

defaults = {
    'minutes': 30,  # Cooldown timer (reset)
    'banLimit': 5  # Number of warnings before ban
}


class InviteFilter(AntiSpamModule):

    def __init__(self, plugin):
        super().__init__(name="inviteFilter", callback=self.base, brief="Control the invite filter's settings",
                         checks=[super().has_permissions(manage_guild=True)], aliases=["if"])

        self.bot = plugin.bot
        self._config = WolfConfig.get_config()

        self._events = {}
        self._invite_cache = {}

        self.add_command(self.allow_invite)
        self.add_command(self.block_invite)
        self.add_command(self.set_invite_cooldown)
        self.add_command(self.clear_cooldown)
        self.add_command(self.clear_all_cooldowns)

        LOG.info("Filter initialized.")

    def cleanup(self):
        # Purge expired events/cooldowns.
        for user_id in self._events.keys():
            if self._events[user_id]['expiry'] < datetime.datetime.utcnow():
                LOG.info("Cleaning up expired cooldown for user %s", user_id)
                del self._events[user_id]

        # Purge cached fragment after cache expiry
        for fragment in self._invite_cache.keys():
            if datetime.datetime.utcnow() > self._invite_cache[fragment]['__cache_expiry']:
                del self._invite_cache[fragment]

    def clear_for_user(self, user: discord.Member):
        if user.id not in self._events.keys():
            raise KeyError("The user requested does not have a record for this filter.")

        del self._events[user.id]

    def clear_all(self):
        self._events = {}

    async def on_message(self, message: discord.Message):
        class UserFate:
            WARN = 0
            KICK_NEW = 50
            BAN = 100

        filter_settings = self._config.get('antiSpam', {}).get('InviteFilter', {}).get('config', defaults)
        allowed_guilds = filter_settings.get('allowedInvites', [message.guild.id])

        # Prepare the logger
        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is not None:
            log_channel = message.guild.get_channel(log_channel)

        # Prevent memory abuse by deleting expired cooldown records for this member
        if message.author.id in self._events and self._events[message.author.id]['expiry'] < datetime.datetime.utcnow():
            del self._events[message.author.id]
            LOG.info(f"Cleaned up stale invite cooldowns for user {message.author}")

        # Users with MANAGE_MESSAGES are allowed to send unauthorized invites.
        if message.author.permissions_in(message.channel).manage_messages:
            return

        # Determine user's fate right now.
        new_user = (message.author.joined_at > datetime.datetime.utcnow() - datetime.timedelta(seconds=60))

        regex_matches = re.finditer(Regex.INVITE_REGEX, message.content, flags=re.IGNORECASE)

        for regex_match in regex_matches:
            fragment = regex_match.group('fragment')

            # Attempt to validate the invite, deleting invalid ones
            invite_data = None
            invite_guild = None
            try:
                # We're going to be caching guild invite data to prevent discord from getting too mad at us, especially
                # during raids.

                cache_item = self._invite_cache.get(fragment, None)

                if (cache_item is not None) and (datetime.datetime.utcnow() <= cache_item['__cache_expiry']):
                    invite_data = self._invite_cache[fragment]
                else:
                    # discord py doesn't let us do this natively, so let's do it ourselves!
                    invite_data = await self.bot.http.request(
                        Route('GET', '/invite/{invite_id}?with_counts=true', invite_id=fragment))

                    LOG.debug(f"Fragment {fragment} was not in the invite cache. Downloaded and added.")
                    invite_data['__cache_expiry'] = datetime.datetime.utcnow() + datetime.timedelta(hours=4)
                    self._invite_cache[fragment] = invite_data

                invite_guild = discord.Guild(state=self.bot, data=invite_data['guild'])

            except discord.errors.NotFound:
                LOG.warning(f"Couldn't resolve invite key {fragment}. Either it's invalid or the bot was banned.")

            # This guild is allowed to have invites on our guild, so we can ignore them.
            if (invite_guild is not None) and (invite_guild.id in allowed_guilds):
                continue

            # The guild either is invalid or not on the whitelist - delete the message.
            try:
                await message.delete()
            except discord.NotFound:
                # Message not found, let's log this
                LOG.warning(f"The message I was trying to delete does not exist! ID: {message.id}")

            # Grab the existing cooldown record, or make a new one if it doesn't exist.
            record = self._events.setdefault(message.author.id, {
                'expiry': datetime.datetime.utcnow() + datetime.timedelta(minutes=filter_settings['minutes']),
                'offenseCount': 0
            })

            # Warn the user on their first offense only.
            if (not new_user) and (record['offenseCount'] == 0):
                await message.channel.send(embed=discord.Embed(
                    title=Emojis.STOP + " Discord Invite Blocked",
                    description=f"Hey {message.author.mention}! It looks like you posted a Discord invite.\n\n"
                                f"Here on {message.guild.name}, we have a strict no-invites policy in order to prevent "
                                f"spam and advertisements. If you would like to post an invite, you may contact the "
                                f"admins to request an invite code be whitelisted.\n\n"
                                f"We apologize for the inconvenience.",
                    color=Colors.WARNING
                ), delete_after=90.0)

            # And we increment the offense counter here, and extend their expiry
            record['offenseCount'] += 1
            record['expiry'] = datetime.datetime.utcnow() + datetime.timedelta(minutes=filter_settings['minutes'])

            user_fate = UserFate.WARN

            # Kick the user if necessary (performance)
            if new_user:
                await message.author.kick(reason="New user (less than 60 seconds old) posted invite.")
                LOG.info(f"User {message.author} kicked for posting invite within 60 seconds of joining.")
                user_fate = UserFate.KICK_NEW

            # Ban the user if necessary (performance)
            if filter_settings['banLimit'] > 0 and (record['offenseCount'] >= filter_settings['banLimit']):
                await message.author.ban(
                    reason=f"[AUTOMATIC BAN - AntiSpam Plugin] User sent {filter_settings['banLimit']} "
                           f"unauthorized invites in a {filter_settings['minutes']} minute period.",
                    delete_message_days=0)
                LOG.info(f"User {message.author} was banned for exceeding set invite thresholds.")
                user_fate = UserFate.BAN

            #  Log their offense to the server log (if it exists)
            if log_channel is not None:
                # We've a valid invite, so let's log that with invite data.
                log_embed = discord.Embed(
                    description=f"An invite with key `{fragment}` by user {message.author} (ID `{message.author.id}`) "
                                f"was caught and filtered.",
                    color=Colors.INFO
                )
                log_embed.set_author(name=f"Invite from {message.author} intercepted!",
                                     icon_url=message.author.avatar_url)

                if invite_guild is not None:
                    log_embed.add_field(name="Invited Guild Name", value=invite_guild.name, inline=True)

                    ch_type = {0: "#", 2: "[VC] ", 4: "[CAT] "}
                    log_embed.add_field(name="Invited Channel Name",
                                        value=ch_type[invite_data['channel']['type']] + invite_data['channel']['name'],
                                        inline=True)
                    log_embed.add_field(name="Invited Guild ID", value=invite_guild.id, inline=True)

                    log_embed.add_field(name="Invited Guild Creation",
                                        value=invite_guild.created_at.strftime(DATETIME_FORMAT),
                                        inline=True)

                    if invite_data.get('approximate_member_count', -1) != -1:
                        log_embed.add_field(name="Invited Guild User Count",
                                            value=f"{invite_data.get('approximate_member_count', -1)} "
                                                  f"({invite_data.get('approximate_presence_count', -1)} online)",
                                            )

                    if invite_data.get('inviter') is not None:
                        inviter: dict = invite_data.get('inviter', {})
                        log_embed.add_field(
                            name="Invite Creator",
                            value=f"{inviter['username']}#{inviter['discriminator']}"
                        )

                    log_embed.set_thumbnail(url=invite_guild.icon_url)

                log_embed.set_footer(text=f"Strike {record['offenseCount']} "
                                          f"of {filter_settings['banLimit']}, "
                                          f"resets {record['expiry'].strftime(DATETIME_FORMAT)}"
                                          f"{' | User Removed' if user_fate > UserFate.WARN else ''}")

                await log_channel.send(embed=log_embed)

            # If the user got banned, we can go and clean up their mess
            if user_fate == UserFate.BAN:
                try:
                    del self._events[message.author.id]
                except KeyError:
                    LOG.warning("Attempted to delete cooldown record for user %s (ban over limit), but failed as the "
                                "record count not be found. The user was probably already banned.", message.author.id)
            else:
                LOG.info(f"User {message.author} was issued an invite warning ({record['offenseCount']} / "
                         f"{filter_settings['banLimit']}, resetting at {record['expiry'].strftime(DATETIME_FORMAT)})")

            # We don't need to process anything anymore.
            break

    @commands.command(name="allowInvite", brief="Allow an invite from a guild")
    async def allow_invite(self, ctx: commands.Context, guild: int):
        """
        Add a guild to the AntiSpam Invite Whitelist.

        By default, AntiSpam will block all guild invites not posted by authorized members (or invites that are not to
        this guild). This may be overridden on a case-by-case basis using this command. Once a guild is added to the
        whitelist, their invites will not be touched on this guild.

        This command expects a single argument - a guild ID.

        Example commands:
            /as allowInvite 11223344 - Allow invites from guild ID 11223344

        See also:
            /help as blockInvite    - Remove a guild from the invite whitelist
            /help as inviteCooldown - Edit cooldown settings for the invite limiter.
        """
        as_config = self._config.get('antiSpam', {})
        filter_config = as_config.setdefault('InviteFilter', {}).setdefault('config', defaults)
        allowed_invites = filter_config.setdefault('allowedInvites', [ctx.guild.id])

        if guild in allowed_invites:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Plugin",
                description=f"The guild with ID `{guild}` is already whitelisted!",
                color=Colors.WARNING
            ))
            return

        allowed_invites.append(guild)
        self._config.set("antiSpam", as_config)
        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description=f"The invite to guild `{guild}` has been added to the whitelist.",
            color=Colors.SUCCESS
        ))
        return

    @commands.command(name="blockInvite", brief="Block a previously-approved guild's invites")
    async def block_invite(self, ctx: commands.Context, guild: int):
        """
        Remove a guild from the AntiSpam Invite Whitelist.

        If a guild was added to the AntiSpam whitelist, this command may be used to remove the whitelist entry. See
        /help antispam allowInvite for more information on this command.

        This command expects a single argument - a guild ID.

        This command will return an error if a guild not on the whitelist is removed.

        Example Commands:
            /as blockInvite 11223344 - No longer allow invites from guild ID 11223344

        See also:
            /help as allowInvite    - Add a guild to the invite whitelist
            /help as inviteCooldown - Edit cooldown settings for the invite limiter.
        """
        as_config = self._config.get('antiSpam', {})
        filter_config = as_config.setdefault('InviteFilter', {}).setdefault('config', defaults)
        allowed_invites = filter_config.setdefault('allowedInvites', [ctx.guild.id])

        if guild == ctx.guild.id:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Plugin",
                description=f"This guild may not be removed from the whitelist!",
                color=Colors.WARNING
            ))
            return

        if guild not in allowed_invites:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Plugin",
                description=f"The guild `{guild}` is not whitelisted!",
                color=Colors.WARNING
            ))
            return

        allowed_invites.pop(guild)
        self._config.set("antiSpam", as_config)
        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description=f"The guild with ID `{guild}` has been removed from the whitelist.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="configure", brief="Configure thresholds for InviteFilter")
    async def set_invite_cooldown(self, ctx: commands.Context, cooldown_minutes: int, ban_limit: int):
        """
        Set cooldowns/ban thresholds for guild invite spam.

        The bot will automatically ban a user after posting a certain number of invites in a defined time period. This
        command allows those limits to be altered.

        The command takes two arguments: cooldown_minutes, and ban_limit.

        If a user posts `ban_limit` or more guild invites in the span of `cooldown_minutes` minutes, they will be
        automatically banned from the guild.

        See also:
            /help as blockInvite    - Remove a guild from the invite whitelist
            /help as blockInvite    - Add a guild to the invite whitelist
        """
        as_config = self._config.get('antiSpam', {})
        filter_config = as_config.setdefault('InviteFilter', {}).setdefault('config', defaults)

        filter_config['minutes'] = cooldown_minutes
        filter_config['banLimit'] = ban_limit

        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description=f"The invite module of AntiSpam has been set to allow a max of **`{ban_limit}`** unauthorized "
                        f"invites in a **`{cooldown_minutes}` minute** period.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="clear", brief="Clear a cooldown record for a specific user")
    async def clear_cooldown(self, ctx: commands.Context, user: discord.Member):
        """
        Clear a user's cooldown record for this filter.

        This command allows moderators to override the antispam expiry system, and clear a user's cooldowns/strikes/
        warnings early. Any accrued warnings for the selected user are discarded and the user starts with a clean slate.

        Parameters:
            user - A user object (ID, mention, etc) to target for clearing.

        See also:
            /as <filter_name> clearAll - Clear all cooldowns for all users for a single filter.
            /as clear - Clear cooldowns on all filters for a single user.
            /as clearAll - Clear all cooldowns globally for all users (reset).
        """

        try:
            self.clear_for_user(user)
            LOG.info(f"The invite cooldown record for {user} was cleared by {ctx.author}.")
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Invite Filter",
                description=f"There is no cooldown record present for `{user}`. Either this user does not exist, they "
                            f"do not have a cooldown record, or it has already been cleared.",
                color=Colors.DANGER
            ))
            return

        await ctx.send(embed=discord.Embed(
            title=Emojis.SPARKLES + " Invite Filter | Cooldown Record Cleared!",
            description=f"The cooldown record for `{user}` has been cleared. There are now no warnings on this user's "
                        f"record.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="clearAll", brief="Clear all cooldown records for this filter.")
    @commands.has_permissions(administrator=True)
    async def clear_all_cooldowns(self, ctx: commands.Context):
        """
        Clear cooldown records for all users for this filter.

        This command will clear all cooldowns for the current filter, effectively resetting its internal state. No users
        will have any warnings for this filter after this command is executed.

        See also:
            /as <filter_name> clear - Clear cooldowns on a single filter for a single user.
            /as clear - Clear cooldowns on all filters for a single user.
            /as clearAll - Clear all cooldowns globally for all users (reset).
        """

        record_count = len(self._events)

        self.clear_all()
        LOG.info(f"{ctx.author} cleared {record_count} cooldown records from the invite filter.")

        await ctx.send(embed=discord.Embed(
            title=Emojis.SPARKLES + " Invite Filter | Cooldown Records Cleared!",
            description=f"All cooldown records for the invite filter have been successfully cleared. No warnings "
                        f"currently exist in the system.",
            color=Colors.SUCCESS
        ))
