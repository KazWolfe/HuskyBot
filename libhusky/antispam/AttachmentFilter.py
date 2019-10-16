#   This Source Code Form is "Incompatible With Secondary Licenses", as
#   defined by the Mozilla Public License, v. 2.0.

import datetime
import logging

import discord
from discord.ext import commands

from libhusky.HuskyStatics import *
from libhusky.antispam import AntiSpamModule

LOG = logging.getLogger("HuskyBot.Plugin.AntiSpam." + __name__.split('.')[-1])

defaults = {
    'seconds': 15,  # Cooldown timer (reset)
    'warnLimit': 3,  # Number of attachment messages before warning the user
    'banLimit': 5  # Number of attachment messages before banning the user
}


class AttachmentFilter(AntiSpamModule):
    """
    The Attachment Filter is one of the modules that makes up the AntiSpam system.

    It will block users who post excessive numbers of messages in short timespans. Users who post over the specified
    amount of attachments (without a text-only message breaking things up) will be issued a warning, and then banned.

    This antispam module is specifically geared towards raids and image dumps. Multiple images on one message will not
    trigger this filter.

    Default Parameters:
        Time to Cooldown: 15 Seconds
        Warning Limit: 3 Attachments
        Ban Limit: 5 Attachments
    """

    def __init__(self, plugin):
        super().__init__(
            self.base,
            name="attachFilter",
            brief="Control the attachment filter's settings",
            checks=[super().has_permissions(manage_guild=True)],
            help=self.classhelp(),
            aliases=["af"]
        )

        self.bot = plugin.bot
        self._config = self.bot.config

        self._events = {}

        self.add_command(self.set_attach_cooldown)
        self.add_command(self.clear_cooldown)
        self.add_command(self.clear_all_cooldowns)
        self.add_command(self.view_config)
        self.register_commands(plugin)

        LOG.info("Filter initialized.")

    def cleanup(self):
        # Purge expired events/cooldowns.
        for user_id in self._events.keys():
            if self._events[user_id]['expiry'] < datetime.datetime.utcnow():
                LOG.info("Cleaning up expired cooldown for user %s", user_id)
                del self._events[user_id]

    def clear_for_user(self, user: discord.Member):
        if user.id not in self._events.keys():
            raise KeyError("The user requested does not have a record for this filter.")

        del self._events[user.id]

    def clear_all(self):
        self._events = {}

    async def process_message(self, message: discord.Message, context):
        as_config = self._config.get('antiSpam', {})
        filter_config = as_config.get('AttachmentFilter', {}).get('config', defaults)

        # Prepare the logger
        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is not None:
            log_channel = message.guild.get_channel(log_channel)

        # Clear expired cooldown record for this user, if it exists.
        if message.author.id in self._events and self._events[message.author.id]['expiry'] < datetime.datetime.utcnow():
            del self._events[message.author.id]
            LOG.info(f"Cleaned up stale attachment cooldowns for user {message.author}")

        # Users with MANAGE_MESSAGES are allowed to bypass attachment rate limits.
        if message.author.permissions_in(message.channel).manage_messages:
            return

        if len(message.attachments) > 0:
            # User posted an attachment, and is not in the cache. Let's add them, on strike 0.
            cooldown_record = self._events.setdefault(message.author.id, {
                'expiry': datetime.datetime.utcnow() + datetime.timedelta(seconds=filter_config['seconds']),
                'offenseCount': 0
            })

            # And we increment the offense counter here.
            cooldown_record['offenseCount'] += 1

            # Give them a fair warning on attachment #3
            if filter_config['warnLimit'] != 0 and cooldown_record['offenseCount'] == filter_config['warnLimit']:
                await message.channel.send(embed=discord.Embed(
                    title=Emojis.STOP + " Whoa there, pardner!",
                    description=f"Hey there {message.author.mention}! You're sending files awfully fast. Please help "
                                f"us keep this chat clean and readable by not sending lots of files so quickly. "
                                f"Thanks!",
                    color=Colors.WARNING
                ), delete_after=90.0)

                if log_channel is not None:
                    await log_channel.send(embed=discord.Embed(
                        description=f"User {message.author} has sent {cooldown_record['offenseCount']} attachments in "
                                    f"a {filter_config['seconds']}-second period in channel "
                                    f"{message.channel.mention}.",
                        color=Colors.WARNING
                    ).set_author(name="Possible Attachment Spam", icon_url=message.author.avatar_url))
                    return

                LOG.info(f"User {message.author} has been warned for posting too many attachments in a short while.")
            elif cooldown_record['offenseCount'] >= filter_config['banLimit']:
                await message.author.ban(reason=f"[AUTOMATIC BAN - AntiSpam Module] User sent "
                                                f"{cooldown_record['offenseCount']} attachments in a "
                                                f"{filter_config['seconds']} second period.",
                                         delete_message_days=1)
                del self._events[message.author.id]
                LOG.info(f"User {message.author} has been banned for posting over {filter_config['banLimit']} "
                         f"attachments in a {filter_config['seconds']} period.")
            else:
                LOG.info(f"User {message.author} posted a message with {len(message.attachments)} attachments, "
                         f"incident logged. User on warning {cooldown_record['offenseCount']} of "
                         f"{filter_config['banLimit']}.")

        else:
            # They sent a message containing text. Clear their cooldown.
            if message.author.id in self._events:
                LOG.info(f"User {message.author} previously on file cooldown warning list has sent a file-less "
                         f"message. Deleting cooldown entry.")
                del self._events[message.author.id]

    @commands.command(name="configure", brief="Configure thresholds for AttachmentFilter")
    async def set_attach_cooldown(self, ctx: commands.Context, cooldown_seconds: int, warn_limit: int, ban_limit: int):
        """
        AntiSpam will log and ban users that go over a set amount of attachments in a second. This command allows those
        limits to be altered on the fly.

        If a user sends `warn_limit` announcements in a `cooldown_seconds` second period, they will be issued a warning
        message to cool on the spam. If they persist to `ban_limit` attachments in the same period, they will be
        automatically banned from the guild.

        A message not containing attachments will reset the cooldown period.

        Parameters
        ----------
            ctx               :: Discord context <!nodoc>
            cooldown_seconds  :: The number of seconds before an activity record expires.
            warn_limit        :: The number of attachment records before a user is warned.
            ban_limit         :: The number of attachment records before a user is banned.
        """

        as_config = self._config.get('antiSpam', {})
        attach_config = as_config.setdefault('AttachmentFilter', {}).setdefault('config', defaults)

        attach_config['seconds'] = cooldown_seconds
        attach_config['warnLimit'] = warn_limit
        attach_config['banLimit'] = ban_limit

        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description=f"The attachments module of AntiSpam has been set to allow a max of **`{ban_limit}`** "
                        f"attachments in a **`{cooldown_seconds}` second** period, warning after **`{warn_limit}`** "
                        f"attachments",
            color=Colors.SUCCESS
        ))

    @commands.command(name="viewConfig", brief="See currently set configuration values for this plugin.")
    async def view_config(self, ctx: commands.Context):
        as_config = self._config.get('antiSpam', {})
        filter_config = as_config.get('NonUniqueFilter', {}).get('config', defaults)

        embed = discord.Embed(
            title="NonUnique Filter Configuration",
            description="The below settings are the current values for the nonunique filter configuration.",
            color=Colors.INFO
        )

        embed.add_field(name="Cooldown Timer", value=f"{filter_config['seconds']} seconds", inline=False)
        embed.add_field(name="Warning Limit", value=f"{filter_config['warnLimit']} attachments", inline=False)
        embed.add_field(name="Ban Limit", value=f"{filter_config['banLimit']} attachments", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="clear", brief="Clear a cooldown record for a specific user")
    async def clear_cooldown(self, ctx: commands.Context, user: discord.Member):
        """
        This command allows moderators to override the antispam expiry system, and clear a user's cooldowns/strikes/
        warnings early. Any accrued warnings for the selected user are discarded and the user starts with a clean slate.

        Parameters
        ----------
            ctx   :: Discord context <!nodoc>
            user  :: A user object (ID, mention, etc) to target for clearing.

        See Also
        --------
            /as <filter_name> clearAll  :: Clear all cooldowns for all users for a single filter.
            /as clear                   :: Clear cooldowns on all filters for a single user.
            /as clearAll                :: Clear all cooldowns globally for all users (reset).
        """

        try:
            self.clear_for_user(user)
            LOG.info(f"The attachment cooldown record for {user} was cleared by {ctx.author}.")
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Attachment Filter",
                description=f"There is no cooldown record present for `{user}`. Either this user does not exist, they "
                            f"do not have a cooldown record, or it has already been cleared.",
                color=Colors.DANGER
            ))
            return

        await ctx.send(embed=discord.Embed(
            title=Emojis.SPARKLES + " Attachment Filter | Cooldown Record Cleared!",
            description=f"The attachment record for `{user}` has been cleared. There are now no warnings on this "
                        f"user's record.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="clearAll", brief="Clear all cooldown records for this filter.")
    @commands.has_permissions(administrator=True)
    async def clear_all_cooldowns(self, ctx: commands.Context):
        """
        This command will clear all cooldowns for the current filter, effectively resetting its internal state. No users
        will have any warnings for this filter after this command is executed.

        See Also
        --------
            /as <filter_name> clear  :: Clear cooldowns on a single filter for a single user.
            /as clear                :: Clear cooldowns on all filters for a single user.
            /as clearAll             :: Clear all cooldowns globally for all users (reset).
        """

        record_count = len(self._events)

        self.clear_all()
        LOG.info(f"{ctx.author} cleared {record_count} cooldown records from the attachment filter.")

        await ctx.send(embed=discord.Embed(
            title=Emojis.SPARKLES + " Attachment Filter | Cooldown Record Cleared!",
            description=f"All cooldown records for the attachment filter have been successfully cleared. No warnings "
                        f"currently exist in the system.",
            color=Colors.SUCCESS
        ))
