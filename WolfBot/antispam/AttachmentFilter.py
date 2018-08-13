import datetime
import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot.WolfStatics import *
from WolfBot.antispam import AntiSpamModule

LOG = logging.getLogger("DakotaBot.Plugin.AntiSpam." + __name__.split('.')[-1])

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
        super().__init__(name="attachFilter", callback=self.base, brief="Control the attachment filter's settings",
                         checks=[super().has_permissions(manage_guild=True)], help=self.classhelp(), aliases=["af"])

        self.bot = plugin.bot
        self._config = WolfConfig.get_config()

        self._events = {}

        self.add_command(self.set_attach_cooldown)

        LOG.info("Filter initialized.")

    def cleanup(self):
        # Purge expired events/cooldowns.
        for user_id in self._events.keys():
            if self._events[user_id]['expiry'] < datetime.datetime.utcnow():
                LOG.info("Cleaning up expired cooldown for user %s", user_id)
                del self._events[user_id]

    async def on_message(self, message: discord.Message):
        as_config = self._config.get('antiSpam', {})
        filter_config = as_config.get('AttachmentFilter', {}).get('config', defaults)

        # Prepare the logger
        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is not None:
            log_channel = message.guild.get_channel(log_channel)

        # Clear expired cooldown record for this user, if it exists.
        if message.author.id in self._events \
                and self._events[message.author.id]['expiry'] < datetime.datetime.utcnow():
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
        Set cooldowns/ban thresholds on attachment spam.

        AntiSpam will log and ban users that go over a set amount of attachments in a second. This command allows those
        limits to be altered on the fly.

        If a user sends `warn_limit` announcements in a `cooldown_seconds` second period, they will be issued a warning
        message to cool on the spam. If they persist to `ban_limit` attachments in the same period, they will be
        automatically banned from the guild.

        A message not containing attachments will reset the cooldown period.
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
