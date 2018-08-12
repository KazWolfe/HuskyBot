import datetime
import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot.WolfStatics import *
from WolfBot.antispam import AntiSpamModule

LOG = logging.getLogger("DakotaBot.Plugin.AntiSpam." + __name__.split('.')[-1])

defaults = {
    "soft": 6,  # Number of unique pings in a message before deleting the message
    "hard": 15  # Number of unique pings in a message before banning the user
}


class MentionFilter(AntiSpamModule):
    def __init__(self, plugin):
        super().__init__(name="mentionFilter", callback=self.base, brief="Control the mention filter's settings",
                         checks=[super().has_permissions(mention_everyone=True)])

        self.bot = plugin.bot
        self._config = WolfConfig.get_config()

        self._events = {}

        self.add_command(self.set_ping_limit)

        LOG.info("Filter initialized.")

    def cleanup(self):
        # Purge expired events/cooldowns.
        for user_id in self._events.keys():
            if self._events[user_id]['expiry'] < datetime.datetime.utcnow():
                LOG.info("Cleaning up expired cooldown for user %s", user_id)
                del self._events[user_id]

    async def on_message(self, message):
        as_config = self._config.get('antiSpam', {})
        ping_config = as_config.get('MentionSpamFilter', {}).get('config', defaults)
        PING_WARN_LIMIT = ping_config['soft']
        PING_BAN_LIMIT = ping_config['hard']

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_ALERTS.value, None)
        if alert_channel is not None:
            alert_channel = message.guild.get_channel(alert_channel)

        if message.author.permissions_in(message.channel).mention_everyone:
            return

        if PING_WARN_LIMIT is not None and len(message.mentions) >= PING_WARN_LIMIT:
            try:
                await message.delete()
            except discord.NotFound:
                LOG.warning("Message already deleted before AS could handle it (censor?).")

            # ToDo: Issue actual warning through Punishment (once made available)
            await message.channel.send(embed=discord.Embed(
                title=Emojis.NO_ENTRY + " Mass Ping Blocked",
                description="A mass-ping message was blocked in the current channel.\n"
                            "Please reduce the number of pings in your message and try again.",
                color=Colors.WARNING
            ))

            if alert_channel is not None:
                await alert_channel.send(embed=discord.Embed(
                    description=f"User {message.author} has pinged {len(message.mentions)} users in a single message "
                                f"in channel {message.channel.mention}.",
                    color=Colors.WARNING
                ).set_author(name="Mass Ping Alert", icon_url=message.author.avatar_url))

            LOG.info(f"Got message from {message.author} containing {len(message.mentions)} pings.")

        if PING_BAN_LIMIT is not None and len(message.mentions) >= PING_BAN_LIMIT:
            await message.author.ban(
                delete_message_days=0,
                reason="[AUTOMATIC BAN - AntiSpam Module] Multi-pinged over guild ban limit."
            )

    @commands.command(name="setPingLimit", brief="Set the number of pings required before AntiSpam takes action")
    async def set_ping_limit(self, ctx: commands.Context, warn_limit: int, ban_limit: int):
        """
        Set the warning and ban limits for the maximum number of pings permitted in a single message.

        This command takes two arguments - warn_limit and ban_limit. Both of these are integers.

        Once a user exceeds the warning limit of pings in a single message, their message will be automatically deleted
        and a warning will be issued to the user.

        If a user surpasses the ban limit of pings in a single message, the message will be deleted and the user will
        be immediately banned.

        Setting a value to zero or any negative number will disable that specific limit.

        Example commands:
            /as setPingLimit 6 15 - Set warn limit to 6, ban limit to 15
            /as setPingLimit 6 0  - Set warn limit to 6, remove the ban limit
        """
        if warn_limit < 1:
            warn_limit = None

        if ban_limit < 1:
            ban_limit = None

        as_config = self._config.get('antiSpam', {})
        ping_config = as_config.setdefault('MentionSpamFilter', {}).setdefault('config', defaults)

        ping_config['soft'] = warn_limit
        ping_config['hard'] = ban_limit
        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description=f"Ping limits have been successfully updated. Warn in `{warn_limit}` pings, "
                        f"ban in `{ban_limit}`.",
            color=Colors.SUCCESS
        ))
