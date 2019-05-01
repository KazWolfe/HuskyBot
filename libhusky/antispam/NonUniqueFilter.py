import datetime
import logging
from difflib import SequenceMatcher

import discord
from discord.ext import commands

from libhusky import HuskyUtils
from libhusky.HuskyStatics import *
from libhusky.antispam.__init__ import AntiSpamModule

LOG = logging.getLogger("HuskyBot.Plugin.AntiSpam." + __name__.split('.')[-1])

defaults = {
    "threshold": 0.75,  # Diff threshold before considering a message "similar"
    "cacheSize": 3,  # The number of "mostly unique" messages to keep in cache.
    "minutes": 5,  # Cooldown time (in minutes)
    "warnLimit": 5,  # number of matching non-uniques before issuing a warning
    "banLimit": 15  # number of matching non-uniques before issuing a ban
}


class NonUniqueFilter(AntiSpamModule):
    def __init__(cls, plugin):
        super().__init__(cls.base, name="nonUniqueFilter", brief="Control the non-unique filter's settings",
                         checks=[super().has_permissions(manage_guild=True)], aliases=["nuf"])

        cls.bot = plugin.bot
        cls._config = cls.bot.config

        cls._events = {}

        cls.add_command(cls.nonuniqe_cooldown)
        cls.add_command(cls.test_strings)
        cls.add_command(cls.clear_cooldown)
        cls.add_command(cls.clear_all_cooldowns)
        cls.register_commands(plugin)

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

    async def on_message(self, message: discord.message):
        as_config = self._config.get('antiSpam', {})
        nonunique_config = as_config.get('NonUniqueFilter', {}).get('config', defaults)

        # Prepare the logger
        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is not None:
            log_channel = message.guild.get_channel(log_channel)

        # Actively/lazily find and delete expired cooldowns instead of waiting for event
        if message.author.id in self._events and self._events[message.author.id]['expiry'] < datetime.datetime.utcnow():
            del self._events[message.author.id]

        # Users with MANAGE_MESSAGES are allowed to send as much spam as they want
        if message.author.permissions_in(message.channel).manage_messages:
            return

        # Setting threshold to 0 disables this check.
        if nonunique_config['threshold'] == 0:
            return

        # get cooldown object for this user
        cooldown_record: dict = self._events.setdefault(message.author.id, {
            'expiry': datetime.datetime.utcnow() + datetime.timedelta(minutes=nonunique_config['minutes']),
            "messageCache": {}
        })
        message_cache = cooldown_record['messageCache']  # type: dict

        for s_message in message_cache.keys():
            diff = SequenceMatcher(None, s_message.lower(), message.content.lower()).ratio()

            if diff >= nonunique_config['threshold']:
                LOG.info(f"Message from {message.author} is too similar to past message, strike added. "
                         f"Similarity = {diff:.3f}")
                message_cache[s_message] += 1
                break
        else:
            while len(message_cache) >= nonunique_config['cacheSize']:
                # Delete the first item in the cache, until the cache is under min size.
                del message_cache[list(message_cache.keys())[0]]

            message_cache[message.content.lower()] = 0

        total_infractions = sum(message_cache.values())

        if total_infractions == nonunique_config['warnLimit'] and cooldown_record.get('wasntWarned', True):
            await message.channel.send(embed=discord.Embed(
                title=Emojis.STOP + " Calm your jets!",
                description=f"Hey there {message.author.mention}!\n\nIt looks like you're sending a bunch of "
                            f"similar messages very quickly. Please calm down on the spam there! If you have a "
                            f"question, someone will answer it shortly. Otherwise, unnecessary spam is unnecessary.\n\n"
                            f"Patience is a virtue!",
                color=Colors.WARNING
            ), delete_after=90.0)

            log_embed = discord.Embed(
                description=f"User {message.author} has posted a high number of non-unique messages in a short "
                            f"timespan. Please investigate.",
                color=Colors.WARNING
            )

            log_embed.add_field(name="Timestamp", value=HuskyUtils.get_timestamp(), inline=True)
            log_embed.add_field(name="Most Recent Channel", value=message.channel.mention, inline=True)

            log_embed.set_author(name="Possible non-unique spam!", icon_url=message.author.avatar_url)

            log_embed.set_footer(text=f"Strike {total_infractions} of {nonunique_config['banLimit']}, "
                                      f"resets {cooldown_record['expiry'].strftime(DATETIME_FORMAT)}")

            await log_channel.send(embed=log_embed)

            cooldown_record['wasntWarned'] = False

        elif total_infractions == nonunique_config['banLimit']:
            await message.author.ban(reason=f"[AUTOMATIC BAN - AntiSpam Module] User sent "
                                            f"{nonunique_config['banLimit']} nonunique messages in a "
                                            f"{nonunique_config['minutes']} minute period.",
                                     delete_message_days=1)

            del self._events[message.author.id]

    @commands.command(name="configure", brief="Configure thresholds for NonUniqueFilter")
    async def nonuniqe_cooldown(self, ctx: commands.Context, threshold: int, cache_size: int, cooldown_minutes: int,
                                warn_limit: int, ban_limit: int):
        """
        When a message is received by the bot, the system checks it for uniqueness against a cache of previous
        messages from that user. If a message is found to already be in that cache, a "strike" is added. Once a user
        accrues a set number of strikes in the configured time period, the user will either be warned publicly, or
        banned from the guild.

        Parameters
        ----------
            ctx               :: Discord context <!nodoc>
            threshold         :: A number between zero and one that determines how "similar" a message needs to be
                                 before being considered a duplicate. Set to 0 to disable this check.
                                 Default: 0.75
            cache_size        :: The number of back messages to keep in cache for any given user. This value must be
                                 above one to prevent issues. The cache can not exceed 20 messages.
                                 Default: 3
            cooldown_minutes  :: The number of minutes to keep a cooldown period active. Like most other antispam
                                 commands, this counts from the first message sent. Default: 5
            warn_limit        :: The number of non-unique messages to tolerate before issuing a warning to a user.
                                 Default: 5
            ban_limit         :: The number of non-unique messages to tolerate before banning a user.
                                 Default: 15
        """

        as_config = self._config.get('antiSpam', {})
        nonunique_config = as_config.setdefault('NonUniqueFilter', {}).setdefault('config', defaults)

        if not 0 <= threshold <= 1:
            await ctx.send(embed=discord.Embed(
                title="Configuration Error",
                description="The `threshold` value must be between 0 and 1!",
                color=Colors.DANGER
            ))
            return

        if not 1 <= threshold <= 20:
            await ctx.send(embed=discord.Embed(
                title="Configuration Error",
                description="The `cache_size` value must be between 1 and 20!",
                color=Colors.DANGER
            ))
            return

        nonunique_config['minutes'] = cooldown_minutes
        nonunique_config['threshold'] = threshold
        nonunique_config['cacheSize'] = cache_size
        nonunique_config['warnLimit'] = warn_limit
        nonunique_config['banLimit'] = ban_limit

        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Non-Unique Configuration Updated!",
            description="The configuration has been successfully saved. Changes have been applied.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="test", brief="Get the difference between two messages")
    async def test_strings(self, ctx: commands.Context, text_a: str, text_b: str):
        """
        This command will compare two strings and determine their similarity ratio (used to determine if a message is
        above the threshold or not). Additionally, it will also time the calculation for profiling purposes.

        Note that if the strings you are comparing have spaces, *both must be surrounded by quotes*.

        Parameters
        ----------
            ctx     :: Discord context <!nodoc>
            text_a  :: The first text string to compare to.
            text_b  :: The text string to compare to text_a.

        Example
        -------
            /as nuf test hello henlo  :: Compare strings "hello" and "henlo"
        """
        as_config = self._config.get('antiSpam', {})
        nonunique_config = as_config.get('NonUniqueFilter', {}).get('config', defaults)

        calc_start = datetime.datetime.utcnow()
        diff = SequenceMatcher(None, text_a.lower(), text_b.lower()).ratio()
        calc_end = datetime.datetime.utcnow()

        calc_time = calc_end - calc_start

        is_spam = (diff > nonunique_config['threshold'])

        await ctx.send(embed=discord.Embed(
            title="Non-Unique Tester",
            description=f"The difference between the two provided strings is **`{diff:.3f}`**.\n\n"
                        f"This message **WOULD {'' if is_spam else 'NOT'}** trigger a warning.\n\n"
                        f"Calculation Time: `{calc_time.total_seconds() * 1000} ms`.",
            color=Colors.WARNING if is_spam else Colors.INFO
        ))

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
            LOG.info(f"The non-unique cooldown record for {user} was cleared by {ctx.author}.")
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Non-Unique Filter",
                description=f"There is no cooldown record present for `{user}`. Either this user does not exist, they "
                            f"do not have a cooldown record, or it has already been cleared.",
                color=Colors.DANGER
            ))
            return

        await ctx.send(embed=discord.Embed(
            title=Emojis.SPARKLES + " Non-Unique Filter | Cooldown Record Cleared!",
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
        LOG.info(f"{ctx.author} cleared {record_count} cooldown records from the non-unique filter.")

        await ctx.send(embed=discord.Embed(
            title=Emojis.SPARKLES + " Non-Unique Filter | Cooldown Records Cleared!",
            description=f"All cooldown records for the non-unique filter have been successfully cleared. No warnings "
                        f"currently exist in the system.",
            color=Colors.SUCCESS
        ))
