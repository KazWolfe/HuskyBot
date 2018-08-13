import datetime
import logging
from difflib import SequenceMatcher

import discord
from discord.ext import commands

from WolfBot import WolfConfig, WolfUtils
from WolfBot.WolfStatics import *
from WolfBot.antispam.__init__ import AntiSpamModule

LOG = logging.getLogger("DakotaBot.Plugin.AntiSpam." + __name__.split('.')[-1])

defaults = {
    "threshold": 0.75,  # Diff threshold before considering a message "similar"
    "cacheSize": 3,  # The number of "mostly unique" messages to keep in cache.
    "minutes": 5,  # Cooldown time (in minutes)
    "warnLimit": 5,  # number of matching non-uniques before issuing a warning
    "banLimit": 15  # number of matching non-uniques before issuing a ban
}


class NonUniqueFilter(AntiSpamModule):
    def __init__(self, plugin):
        super().__init__(name="nonUniqueFilter", callback=self.base, brief="Control the non-unique filter's settings",
                         checks=[super().has_permissions(manage_guild=True)], aliases=["nuf"])

        self.bot = plugin.bot
        self._config = WolfConfig.get_config()

        self._events = {}

        self.add_command(self.nonuniqe_cooldown)
        self.add_command(self.test_strings)

        LOG.info("Filter initialized.")

    def cleanup(self):
        # Purge expired events/cooldowns.
        for user_id in self._events.keys():
            if self._events[user_id]['expiry'] < datetime.datetime.utcnow():
                LOG.info("Cleaning up expired cooldown for user %s", user_id)
                del self._events[user_id]

    async def on_message(self, message: discord.message):
        ANTISPAM_CONFIG = self._config.get('antiSpam', {})
        CHECK_CONFIG = ANTISPAM_CONFIG.get('cooldowns', {}).get('nonUnique', defaults)

        # Prepare the logger
        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is not None:
            log_channel = message.guild.get_channel(log_channel)

        # Users with MANAGE_MESSAGES are allowed to send as much spam as they want
        if message.author.permissions_in(message.channel).manage_messages:
            return

        # Setting threshold to 0 disables this check.
        if CHECK_CONFIG['threshold'] == 0:
            return

        # get cooldown object for this user
        cooldown_record: dict = self._events.setdefault(message.author.id, {
            'expiry': datetime.datetime.utcnow() + datetime.timedelta(minutes=CHECK_CONFIG['minutes']),
            "messageCache": {}
        })
        message_cache = cooldown_record['messageCache']  # type: dict

        for s_message in message_cache.keys():
            diff = SequenceMatcher(None, s_message.lower(), message.content.lower()).ratio()

            if diff >= CHECK_CONFIG['threshold']:
                LOG.info(f"Message from {message.author} is too similar to past message, strike added. "
                         f"Similarity = {diff:.3f}")
                message_cache[s_message] += 1
                break
        else:
            while len(message_cache) >= CHECK_CONFIG['cacheSize']:
                # Delete the first item in the cache, until the cache is under min size.
                del message_cache[list(message_cache.keys())[0]]

            message_cache[message.content.lower()] = 0

        total_infractions = sum(message_cache.values())

        if total_infractions == CHECK_CONFIG['warnLimit'] and cooldown_record.get('wasntWarned', True):
            await message.channel.send(embed=discord.Embed(
                title=Emojis.STOP + " Calm your jets!",
                description=f"Hey there {message.author.mention}!\n\nIt looks like you're sending a bunch of "
                            f"similar messages very quickly. Please calm down on the spam there! Someone will be "
                            f"around to help you soon.\n\nPatience is a virtue!",
                color=Colors.WARNING
            ), delete_after=90.0)

            log_embed = discord.Embed(
                description=f"User {message.author} has posted a high number of non-unique messages in a short "
                            f"timespan. Please investigate.",
                color=Colors.WARNING
            )

            log_embed.add_field(name="Timestamp", value=WolfUtils.get_timestamp(), inline=True)
            log_embed.add_field(name="Most Recent Channel", value=message.channel.mention, inline=True)

            log_embed.set_author(name="Possible non-unique spam!", icon_url=message.author.avatar_url)

            log_embed.set_footer(text=f"Strike {total_infractions} of {CHECK_CONFIG['banLimit']}, "
                                      f"resets {cooldown_record['expiry'].strftime(DATETIME_FORMAT)}")

            await log_channel.send(embed=log_embed)

            cooldown_record['wasntWarned'] = False

        elif total_infractions == CHECK_CONFIG['banLimit']:
            await message.author.ban(reason=f"[AUTOMATIC BAN - AntiSpam Module] User sent {CHECK_CONFIG['banLimit']} "
                                            f"nonunique messages in a {CHECK_CONFIG['minutes']} minute period.",
                                     delete_message_days=1)

            del self._events[message.author.id]

    @commands.command(name="configure", brief="Configure thresholds for NonUniqueFilter")
    async def nonuniqe_cooldown(self, ctx: commands.Context, threshold: int, cache_size: int, cooldown_minutes: int,
                                warn_limit: int, ban_limit: int):
        """
        Configure cooldowns/antispam system for non-unique messages.

        When a message is received by DakotaBot, the system checks it for uniqueness against a cache of previous
        messages from that user. If a message is found to already be in that cache, a "strike" is added. Once a user
        accrues a set number of strikes in the configured time period, the user will either be warned publicly, or
        banned from the guild.

        Parameters:
            threshold - A number between zero and one that determines how "similar" a message needs to be before being
                        considered a duplicate. Set to 0 to disable this check. Default: 0.75
            cache_size - The number of back messages to keep in cache for any given user. This value must be above one
                         to prevent issues. The cache can not exceed 20 messages. Default: 3
            cooldown_minutes - The number of minutes to keep a cooldown period active. Like most other antispam
                               commands, this counts from the first message sent. Default: 5
            warn_limit - The number of non-unique messages to tolerate before issuing a warning to a user. Default: 5
            ban_limit - The number of non-unique messages to tolerate before banning a user. Default: 15
        """

        as_config = self._config.get('antiSpam', {})
        nonunique_config = as_config.setdefault('cooldowns', {}).setdefault('nonUnique', defaults)

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
        Test the difference between two strings to NonUniqueFilter.

        This command will compare two strings and determine their similarity ratio (used to determine if a message is
        above the threshold or not). Additionally, it will also time the calculation for profiling purposes.

        Note that if the strings you are comparing have spaces, *both must be surrounded by quotes*.

        Parameters:
            text_a - The first text string to compare to.
            text_b - The text string to compare to text_a.

        Example Commands:
            /as nuf test hello henlo - Compare strings "hello" and "henlo"
        """
        as_config = self._config.get('antiSpam', {})
        nonunique_config = as_config.get('cooldowns', {}).get('nonUnique', defaults)

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
