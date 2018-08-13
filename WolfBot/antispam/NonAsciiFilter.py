import datetime
import logging
import re

import discord
from discord.ext import commands

from WolfBot import WolfConfig, WolfUtils
from WolfBot.WolfStatics import *
from WolfBot.antispam import AntiSpamModule

LOG = logging.getLogger("DakotaBot.Plugin.AntiSpam." + __name__.split('.')[-1])

defaults = {
    'minMessageLength': 40,  # Minimum length of messages to check
    'nonAsciiThreshold': 0.5,  # Threshold (0 to 1) before marking the message as spam
    'banLimit': 3,  # Number of spam messages before banning
    'minutes': 5  # Cooldown timer (minutes)
}


class NonAsciiFilter(AntiSpamModule):
    def __init__(self, plugin):
        super().__init__(name="nonAsciiFilter", callback=self.base, brief="Control the non-ascii filter's settings",
                         checks=[super().has_permissions(manage_guild=True)], aliases=["naf"])

        self.bot = plugin.bot
        self._config = WolfConfig.get_config()

        self._events = {}

        self.add_command(self.set_ascii_cooldown)

        LOG.info("Filter initialized.")

    def cleanup(self):
        # Purge expired events/cooldowns.
        for user_id in self._events.keys():
            if self._events[user_id]['expiry'] < datetime.datetime.utcnow():
                LOG.info("Cleaning up expired cooldown for user %s", user_id)
                del self._events[user_id]

    async def on_message(self, message: discord.Message):
        ANTISPAM_CONFIG = self._config.get('antiSpam', {})
        CHECK_CONFIG = ANTISPAM_CONFIG.get('NonAsciiFilter', {}).get('config', defaults)

        # Prepare the logger
        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is not None:
            log_channel = message.guild.get_channel(log_channel)

        # We can lazily delete cooldowns on messages, instead of checking.
        if message.author.id in self._events \
                and self._events[message.author.id]['expiry'] < datetime.datetime.utcnow():
            del self._events[message.author.id]

        # Disable if min length is 0 or less
        if CHECK_CONFIG['minMessageLength'] <= 0:
            return

        # Users with MANAGE_MESSAGES are allowed to send as many nonascii things as they want.
        if message.author.permissions_in(message.channel).manage_messages:
            return

        # Message is too short, just ignore it.
        if len(message.content) < CHECK_CONFIG['minMessageLength']:
            return

        nonascii_characters = re.sub('[ -~]', '', message.content)

        # Message doesn't have enough non-ascii characters, we can ignore it.
        if len(nonascii_characters) < (len(message.content) * CHECK_CONFIG['nonAsciiThreshold']):
            return

        # Message is now over threshold, get/create their cooldown record.
        cooldown_record = self._events.setdefault(message.author.id, {
            'expiry': datetime.datetime.utcnow() + datetime.timedelta(minutes=CHECK_CONFIG['minutes']),
            'offenseCount': 0
        })

        if cooldown_record['offenseCount'] == 0:
            await message.channel.send(embed=discord.Embed(
                title=Emojis.SHIELD + " Oops! Non-ASCII Message!",
                description=f"Hey {message.author.mention}!\n\nIt looks like you posted a message containing a lot of "
                            f"non-ascii characters. In order to cut down on spam, we are a bit strict with this. We "
                            f"won't delete your message, but please keep ASCII spam off the server.\n\nContinuing to "
                            f"spam ASCII messages may result in a ban. Thank you for keeping {message.guild.name} "
                            f"clean!"
            ), delete_after=90.0)

        cooldown_record['offenseCount'] += 1

        if log_channel is not None:
            embed = discord.Embed(
                description=f"User {message.author} has sent a message with {len(nonascii_characters)} non-ASCII "
                            f"characters (out of {len(message.content)} total).",
                color=Colors.WARNING
            )

            embed.add_field(name="Message Text", value=WolfUtils.trim_string(message.content, 1000, False),
                            inline=False)

            embed.add_field(name="Message ID", value=message.id, inline=True)
            embed.add_field(name="Channel", value=message.channel.mention, inline=True)

            embed.set_footer(text=f"Strike {cooldown_record['offenseCount']} of {CHECK_CONFIG['banLimit']}, "
                                  f"resets {cooldown_record['expiry'].strftime(DATETIME_FORMAT)}")

            embed.set_author(name=f"Non-ASCII spam from {message.author} detected!",
                             icon_url=message.author.avatar_url)

            await log_channel.send(embed=embed)

        if cooldown_record['offenseCount'] >= CHECK_CONFIG['banLimit']:
            await message.author.ban(reason=f"[AUTOMATIC BAN - AntiSpam Module] User sent {CHECK_CONFIG['banLimit']} "
                                            f"messages over the non-ASCII threshold in a {CHECK_CONFIG['minutes']} "
                                            f"minute period.",
                                     delete_message_days=1)

            # And purge their record, it's not needed anymore
            del self._events[message.author.id]

    @commands.command(name="configure", brief="Configure thresholds for NonAsciiFilter")
    async def set_ascii_cooldown(self, ctx: commands.Context, cooldown_minutes: int, ban_limit: int, min_length: int,
                                 threshold: float):
        """
        Set cooldowns/ban thresholds on non-ASCII spam.

        AntiSpam will attempt to detect and ban uses who excessively post non-ASCII characters. These are defined as
        symbols that can not be typed on a normal keyboard such as emoji and box art. Effectively, this command will
        single-handedly kill ASCII art spam on the guild.

        If a user posts a message with at least `min_length` characters which contains at least `length * threshold`
        non-ASCII characters, the bot will log a warning and warn the user on the first offense. If a user exceeds
        `ban_limit` warnings, they will be automatically banned. This feature does NOT delete messages pre-ban.

        Setting min_length to 0 or less will disable this feature.

        Parameters:
            cooldown_minutes - The number of minutes before a given cooldown expires (default: 5)
            ban_limit - The number of warnings before a user is autobanned (default: 3)
            min_length - The minimum total number of characters to process a message (default: 40)
            threshold - A value (between 0 and 1) that represents the percentage of characters that need to be
                       non-ASCII before a warning is fired. (default: 0.5)
        """

        as_config = self._config.get('antiSpam', {})
        nonascii_config = as_config.setdefault('NonAsciiFilter', {}).setdefault('config', defaults)

        if not 0 <= threshold <= 1:
            await ctx.send(embed=discord.Embed(
                title="Configuration Error",
                description="The `threshold` value must be between 0 and 1!",
                color=Colors.DANGER
            ))
            return

        nonascii_config['minutes'] = cooldown_minutes
        nonascii_config['banLimit'] = ban_limit
        nonascii_config['minMessageLength'] = min_length
        nonascii_config['nonAsciiThreshold'] = threshold

        self._config.set('antiSpam', as_config)

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Plugin",
            description=f"The non-ASCII module of AntiSpam has been set to scan messages over **{min_length} "
                        f"characters** for a non-ASCII **threshold of {threshold}**. Users will be automatically "
                        f"banned for posting **{ban_limit} messages** in a **{cooldown_minutes} minute** period.",
            color=Colors.SUCCESS
        ))
