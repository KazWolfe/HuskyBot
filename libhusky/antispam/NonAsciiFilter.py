#   This Source Code Form is "Incompatible With Secondary Licenses", as
#   defined by the Mozilla Public License, v. 2.0.

import datetime
import logging
import re

import discord
from discord.ext import commands

from libhusky import HuskyUtils
from libhusky.HuskyStatics import *
from libhusky.antispam import AntiSpamModule

LOG = logging.getLogger("HuskyBot.Plugin.AntiSpam." + __name__.split('.')[-1])

defaults = {
    'minMessageLength': 40,  # Minimum length of messages to check
    'nonAsciiThreshold': 0.5,  # Threshold (0 to 1) before marking the message as spam
    'nonAsciiDelete': 0.75,  # Threshold (0 to 1) before marking the message as spam *and* deleting it.
    'banLimit': 3,  # Number of spam messages before banning
    'minutes': 5  # Cooldown timer (minutes)
}


class NonAsciiFilter(AntiSpamModule):
    def __init__(self, plugin):
        super().__init__(self.base, name="nonAsciiFilter", brief="Control the non-ascii filter's settings",
                         checks=[super().has_permissions(manage_guild=True)], aliases=["naf"])

        self.bot = plugin.bot
        self._config = self.bot.config

        self._events = {}

        self.add_command(self.set_ascii_cooldown)
        self.add_command(self.test_strings)
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

    @staticmethod
    def calculate_nonascii_value(text: str):
        text = text.replace(' ', '')
        nonascii_characters = re.sub('[!-~]', '', text)

        return len(nonascii_characters) / float(len(text))

    async def process_message(self, message: discord.Message, context, meta: dict = None):
        antispam_config = self._config.get('antiSpam', {})
        check_config = {**defaults, **antispam_config.get('NonAsciiFilter', {}).get('config', {})}

        # Prepare the logger
        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is not None:
            log_channel = message.guild.get_channel(log_channel)

        # We can lazily delete cooldowns on messages, instead of checking.
        if message.author.id in self._events and self._events[message.author.id]['expiry'] < datetime.datetime.utcnow():
            del self._events[message.author.id]

        # Disable if min length is 0 or less
        if check_config['minMessageLength'] <= 0:
            return

        # Users with MANAGE_MESSAGES are allowed to send as many nonascii things as they want.
        if message.author.permissions_in(message.channel).manage_messages:
            return

        # Message is too short, just ignore it.
        if len(message.content) < check_config['minMessageLength']:
            return

        nonascii_percentage = self.calculate_nonascii_value(message.content)

        # Message doesn't have enough non-ascii characters, we can ignore it.
        if nonascii_percentage < min(check_config['nonAsciiThreshold'], check_config['nonAsciiDelete']):
            return

        if nonascii_percentage > check_config['nonAsciiDelete']:
            LOG.info(f"Deleted message containing non-ascii percentage over threshold of "
                     f"{check_config['nonAsciiDelete']}: {nonascii_percentage}")
            await message.delete()

        # Message is now over threshold, get/create their cooldown record.
        cooldown_record = self._events.setdefault(message.author.id, {
            'expiry': datetime.datetime.utcnow() + datetime.timedelta(minutes=check_config['minutes']),
            'offenseCount': 0
        })

        if cooldown_record['offenseCount'] == 0:
            await message.channel.send(embed=discord.Embed(
                title=Emojis.SHIELD + " Oops! Non-ASCII Message!",
                description=f"Hey {message.author.mention}!\n\nIt looks like you posted a message containing a lot of "
                            f"non-ascii characters. In order to cut down on spam, we are a bit strict with this.\n\n"
                            f"Continuing to spam ASCII messages may result in a ban. Thank you for keeping "
                            f"{message.guild.name} clean!"
            ), delete_after=90.0)
            LOG.info(f"Warned user {message.author} for non-ascii spam publicly. A cooldown record has been created.")

        cooldown_record['offenseCount'] += 1
        LOG.info(f"Offense record for {message.author} incremented. User has "
                 f"{cooldown_record['offenseCount']} / {check_config['banLimit']} warnings.")

        if log_channel is not None:
            embed = discord.Embed(
                description=f"User {message.author} has sent a message with {100 * nonascii_percentage:.1f}% non-ASCII "
                            f"characters (out of {len(message.content)} total).",
                color=Colors.WARNING
            )

            embed.add_field(name="Message Text", value=HuskyUtils.trim_string(message.content, 1000, False),
                            inline=False)

            embed.add_field(name="Message ID", value=message.id, inline=True)
            embed.add_field(name="Channel", value=message.channel.mention, inline=True)

            embed.set_footer(text=f"Strike {cooldown_record['offenseCount']} of {check_config['banLimit']}, "
                                  f"resets {cooldown_record['expiry'].strftime(DATETIME_FORMAT)}")

            embed.set_author(name=f"Non-ASCII spam from {message.author} detected!",
                             icon_url=message.author.avatar_url)

            await log_channel.send(embed=embed)

        if cooldown_record['offenseCount'] >= check_config['banLimit']:
            await message.author.ban(reason=f"[AUTOMATIC BAN - AntiSpam Module] User sent {check_config['banLimit']} "
                                            f"messages over the non-ASCII threshold in a {check_config['minutes']} "
                                            f"minute period.",
                                     delete_message_days=1)

            # And purge their record, it's not needed anymore
            del self._events[message.author.id]

    @commands.command(name="configure", brief="Configure thresholds for NonAsciiFilter")
    async def set_ascii_cooldown(self, ctx: commands.Context, cooldown_minutes: int, ban_limit: int, min_length: int,
                                 warn_threshold: float, delete_threshold: float):
        """
        AntiSpam will attempt to detect and ban uses who excessively post non-ASCII characters. These are defined as
        symbols that can not be typed on a normal keyboard such as emoji and box art. Effectively, this command will
        single-handedly kill ASCII art spam on the guild.

        If a user posts a message with at least `min_length` characters which contains at least `length * threshold`
        non-ASCII characters, the bot will log a warning and warn the user on the first offense. If a user exceeds
        `ban_limit` warnings, they will be automatically banned. This feature does NOT delete messages pre-ban.

        Setting min_length to 0 or less will disable this feature.

        Parameters
        ----------
            ctx               :: Discord context <!nodoc>
            cooldown_minutes  :: The number of minutes before a given cooldown expires (default: 5)
            ban_limit         :: The number of warnings before a user is autobanned (default: 3)
            min_length        :: The minimum total number of characters to process a message (default: 40)
            warn_threshold    :: A value (between 0 and 1) that represents the percentage of characters that need to be
                                 non-ASCII before a warning is fired. (default: 0.5)
            delete_threshold  :: A value (between 0 and 1) that represents the percentage of characters that need to be
                                 non-ASCII before the message is deleted as well as warned (default: 0.75)
        """

        as_config = self._config.get('antiSpam', {})
        nonascii_config = as_config.setdefault('NonAsciiFilter', {}).setdefault('config', defaults)

        if not 0 <= warn_threshold <= 1:
            await ctx.send(embed=discord.Embed(
                title="Configuration Error",
                description="The `warn_threshold` value must be between 0 and 1!",
                color=Colors.DANGER
            ))
            return

        if not 0 <= delete_threshold <= 1:
            await ctx.send(embed=discord.Embed(
                title="Configuration Error",
                description="The `delete_threshold` value must be between 0 and 1!",
                color=Colors.DANGER
            ))
            return

        nonascii_config['minutes'] = cooldown_minutes
        nonascii_config['banLimit'] = ban_limit
        nonascii_config['minMessageLength'] = min_length
        nonascii_config['nonAsciiThreshold'] = warn_threshold
        nonascii_config['nonAsciiDelete'] = delete_threshold

        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description=f"The non-ASCII module of AntiSpam has been set to scan messages over **{min_length} "
                        f"characters** for a non-ASCII **threshold of {warn_threshold}**. Users will be automatically "
                        f"banned for posting **{ban_limit} messages** in a **{cooldown_minutes} minute** period.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="viewConfig", brief="See currently set configuration values for this plugin.")
    async def view_config(self, ctx: commands.Context):
        as_config = self._config.get('antiSpam', {})
        filter_config = as_config.get('NonAsciiFilter', {}).get('config', defaults)

        embed = discord.Embed(
            title="Non-Ascii Filter Configuration",
            description="The below settings are the current values for the non-ascii filter configuration.",
            color=Colors.INFO
        )

        embed.add_field(name="Cooldown Timer", value=f"{filter_config['minutes']} minutes", inline=False)
        embed.add_field(name="Min Processing Length", value=f"{filter_config['minMessageLength']} characters",
                        inline=False)
        embed.add_field(name="Non-Ascii Warn %", value=f"{filter_config['nonAsciiThreshold']}% nac", inline=False)
        embed.add_field(name="Non-Ascii Delete %", value=f"{filter_config['nonAsciiDelete']}% nac", inline=False)
        embed.add_field(name="Deletes to Ban", value=f"{filter_config['banLimit']} deletes", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="test", brief="Get the non-ascii percentage of a string")
    async def test_strings(self, ctx: commands.Context, *, text: str):
        """
        Test a string for non-ascii percentage.

        This command allows a moderator to directly call the NAF to determine the fate and status of any given message.
        This command will list the percentage of non-ascii characters detected in the string, as well as return what the
        system will do with the message in question.

        Parameters
        ----------
            ctx   :: Discord context <!nodoc>
            text  :: The text to process.

        Examples
        --------
            /as naf test hello  :: Get NAF percentage of "hello"
        """
        as_config = self._config.get('antiSpam', {})
        nonascii_config = {**defaults, **as_config.get('NonAsciiFilter', {}).get('config', {})}

        calc_start = datetime.datetime.utcnow()
        percentage = self.calculate_nonascii_value(text)
        calc_end = datetime.datetime.utcnow()

        calc_time = calc_end - calc_start

        is_spam = (percentage >= nonascii_config['nonAsciiThreshold'])
        is_deleted = (percentage >= nonascii_config['nonAsciiDelete'])

        await ctx.send(embed=discord.Embed(
            title="Non-Ascii Tester",
            description=f"The passed message is **`{100 * percentage:.1f}%` non-ascii**.\n\n"
                        f"Message result: `{'DELETED' if is_deleted else 'FLAGGED' if is_spam else 'IGNORED'}`\n\n"
                        f"Calculation Time: `{round(calc_time.total_seconds() * 1000, 3)} ms`.",
            color=Colors.DANGER if is_deleted else (Colors.WARNING if is_spam else Colors.INFO)
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
            LOG.info(f"The non-ascii cooldown record for {user} was cleared by {ctx.author}.")
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Non-Ascii Filter",
                description=f"There is no cooldown record present for `{user}`. Either this user does not exist, they "
                            f"do not have a cooldown record, or it has already been cleared.",
                color=Colors.DANGER
            ))
            return

        await ctx.send(embed=discord.Embed(
            title=Emojis.SPARKLES + " Non-Ascii Filter | Cooldown Record Cleared!",
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
        LOG.info(f"{ctx.author} cleared {record_count} cooldown records from the non-ascii filter.")

        await ctx.send(embed=discord.Embed(
            title=Emojis.SPARKLES + " Non-Ascii Filter | Cooldown Records Cleared!",
            description=f"All cooldown records for the non-ascii filter have been successfully cleared. No warnings "
                        f"currently exist in the system.",
            color=Colors.SUCCESS
        ))
