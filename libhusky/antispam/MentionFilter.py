import datetime
import logging

import discord
from discord.ext import commands

from libhusky.HuskyStatics import *
from libhusky.antispam import AntiSpamModule

LOG = logging.getLogger("HuskyBot.Plugin.AntiSpam." + __name__.split('.')[-1])

defaults = {
    "soft": 6,  # Number of unique pings in a message before deleting the message
    "hard": 15,  # Number of unique pings in a message before banning the user
    "seconds": 30  # Number of seconds (from first ping) to track.
}


class MentionFilter(AntiSpamModule):
    def __init__(self, plugin):
        super().__init__(self.base, name="mentionFilter", brief="Control the mention filter's settings",
                         checks=[super().has_permissions(mention_everyone=True)], aliases=["mf"])

        self.bot = plugin.bot
        self._config = self.bot.config
        self._events = {}

        self.add_command(self.set_ping_limit)
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

    async def on_message(self, message):
        antispam_config = self._config.get('antiSpam', {})
        ping_config = {**defaults, **antispam_config.get('MentionFilter', {}).get('config', {})}

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_ALERTS.value, None)
        if alert_channel is not None:
            alert_channel = message.guild.get_channel(alert_channel)

        # Actively (lazily) delete expired cooldowns, if any.
        if message.author.id in self._events and self._events[message.author.id]['expiry'] < datetime.datetime.utcnow():
            del self._events[message.author.id]

        if message.author.permissions_in(message.channel).mention_everyone:
            return

        if len(message.mentions) == 0:
            return

        cooldown_record = None
        if ping_config['seconds']:
            cooldown_record = self._events.setdefault(message.author.id, {
                "expiry": datetime.datetime.utcnow() + datetime.timedelta(seconds=ping_config['seconds']),
                "offenseCount": 0
            })

            cooldown_record['offenseCount'] += len(message.mentions)

        if ping_config['soft'] is not None and len(message.mentions) >= ping_config['soft']:
            try:
                await message.delete()
            except discord.NotFound:
                LOG.warning("Message already deleted before AS could handle it (censor?).")

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

        if ping_config['hard'] is not None:
            if len(message.mentions) >= ping_config['hard']:
                await message.author.ban(
                    delete_message_days=0,
                    reason="[AUTOMATIC BAN - AntiSpam Module] Multi-pinged over guild ban limit."
                )
                del self._events[message.author.id]
                return

            if cooldown_record:
                if cooldown_record['offenseCount'] >= ping_config['hard']:
                    await message.author.ban(
                        delete_message_days=0,
                        reason=f"[AUTOMATIC BAN - AntiSpam Module] Pinged over guild ban limit in "
                        f"{ping_config['seconds']} seconds."
                    )
                    del self._events[message.author.id]
                    return

    @commands.command(name="configure", brief="Set the number of pings required before AntiSpam takes action")
    async def set_ping_limit(self, ctx: commands.Context, warn_limit: int, ban_limit: int, seconds: int):
        """
        This command takes two arguments - warn_limit and ban_limit. Both of these are integers.

        Once a user exceeds the warning limit of pings in a single message, their message will be automatically deleted
        and a warning will be issued to the user.

        If a user surpasses the ban limit of pings in a single message, the message will be deleted and the user will
        be immediately banned.

        Likewise, if a user surpasses the ban limit of pings in the specified cooldown time, the user will be banned.

        Setting a value to zero or any negative number will disable that specific limit.

        Parameters
        ----------
            ctx :: Discord context <!nodoc>
            warn_limit  :: Number of mentions before warning a user
            ban_limit   :: Number of mentions before banning a user
            seconds     :: A cooldown time

        Examples
        --------
            /as pingFilter setPingLimit 6 15 30  :: Set warn limit to 6, ban limit to 15, seconds to 30
            /as pingFilter setPingLimit 6 0 0   :: Set warn limit to 6, remove the ban limit, remove seconds.
        """
        if warn_limit < 1:
            warn_limit = None

        if ban_limit < 1:
            ban_limit = None

        if seconds < 1:
            seconds = None

        as_config = self._config.get('antiSpam', {})
        ping_config = as_config.setdefault('MentionSpamFilter', {}).setdefault('config', defaults)

        ping_config['soft'] = warn_limit
        ping_config['hard'] = ban_limit
        ping_config['seconds'] = seconds
        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description=f"Ping limits have been successfully updated. Warn in `{warn_limit}` pings, "
                        f"ban in `{ban_limit}`.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="viewConfig", brief="See currently set configuration values for this plugin.")
    async def view_config(self, ctx: commands.Context):
        as_config = self._config.get('antiSpam', {})
        filter_config = as_config.get('MentionFilter', {}).get('config', defaults)

        embed = discord.Embed(
            title="Mention Filter Configuration",
            description="The below settings are the current values for the mention filter configuration.",
            color=Colors.INFO
        )

        embed.add_field(name="Cooldown Time", value=f"{filter_config['seconds']} seconds", inline=False)
        embed.add_field(name="Warning Limit", value=f"{filter_config['soft']} mentions", inline=False)
        embed.add_field(name="Ban Limit", value=f"{filter_config['hard']} mentions", inline=False)

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
            LOG.info(f"The mention cooldown record for {user} was cleared by {ctx.author}.")
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Mention Filter",
                description=f"There is no cooldown record present for `{user}`. Either this user does not exist, they "
                            f"do not have a cooldown record, or it has already been cleared.",
                color=Colors.DANGER
            ))
            return

        await ctx.send(embed=discord.Embed(
            title=Emojis.SPARKLES + " Mention Filter | Cooldown Record Cleared!",
            description=f"The cooldown record for `{user}` has been cleared. There are now no warnings on this user's "
                        f"record.",
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
        LOG.info(f"{ctx.author} cleared {record_count} cooldown records from the mention filter.")

        await ctx.send(embed=discord.Embed(
            title=Emojis.SPARKLES + " Mention Filter | Cooldown Records Cleared!",
            description=f"All cooldown records for the mention filter have been successfully cleared. No warnings "
                        f"currently exist in the system.",
            color=Colors.SUCCESS
        ))
