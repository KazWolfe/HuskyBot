import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig, WolfUtils, WolfConverters
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


class ReactToPin:
    """
    ReactToPin allows users to pin their own posts, after a set number of reactions are added to any given post.

    This is often useful for posts with images and other similar threads, where a guild would want to use pins as a
    "featured" section.

    If a channel is "full" of pins, ReactToPin will attempt to intelligently remove the oldest pin from the system.
    It will not delete pins marked as "permanent" through the `/react2pin permapin` command.

    Pins may be removed from the permanent list by deletion or unpinning.
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        """
        Config format:

        {
           ...
           "reactToPin": {
               "channel_id": {
                   "enabled": False,
                   "emoji": "EMOJI_HASH",
                   "requiredToPin": 6
                   "permanent": [
                       111222333
                   ]
               }
           }
        }
        """
        self.bot = bot
        self._config = WolfConfig.get_config()

        LOG.info("Loaded plugin!")

    async def count_reactions(self, message: discord.Message, emoji: discord.PartialEmoji):
        count = 0

        for reaction in message.reactions:
            if str(reaction.emoji) != str(emoji):
                continue

            async for user in reaction.users():
                if user == self.bot.user or user == message.author:
                    continue

                count += 1

            break  # optimization to not loop after we find the response we need

        LOG.debug(f"Message {message.id} has {count} reactions of type {emoji} on it.")
        return count

    async def smart_unpin_oldest(self, channel: discord.TextChannel):
        persistent_pinned_messages = self._config.get('reactToPin', {}).get(str(channel.id), {}).get('permanent', [])

        pin_list = reversed(await channel.pins())

        for item in pin_list:  # type: discord.Message
            if item.id in persistent_pinned_messages:
                continue

            # we have something we can unpin, go ahead and do it, and then break
            LOG.info(f"Unpinned message ID {item.id} from channel {channel} using SmartUnpin")
            await item.unpin()
            return

        raise EOFError("No messages are eligible to be unpinned!")

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        channel = self.bot.get_channel(payload.channel_id)  # type: discord.TextChannel
        message = await channel.get_message(payload.message_id)  # type: discord.Message

        channel_config = self._config.get('reactToPin', {}).get(str(channel.id))  # type: dict

        LOG.debug("Got react event, processing.")

        if not WolfUtils.should_process_message(message):
            return

        if channel_config is None or not channel_config.get('enabled', False):
            LOG.debug(f"A pin configuration was not found for channel {channel}. Ignoring message.")
            return

        # Check if the message is pinned
        if message in await channel.pins():
            LOG.debug("Can't repin an already-pinned message.")
            return

        if str(payload.emoji) != channel_config.get('emoji'):
            LOG.debug(f"Got an invalid emoji for message {message.id} in channel {channel}, ignoring.")
            return

        # we are in a valid channel now, with a valid emote.
        current_reactions = await self.count_reactions(message, payload.emoji)

        if current_reactions < channel_config.get('requiredToPin', 6):
            LOG.debug("Got a valid emote reaction, but still below pin threshold. Ignoring (for now).")
            return

        if len(await channel.pins()) >= 3:
            LOG.debug("Too many pins in the current channel, removing oldest one using smart unpin.")
            try:
                await self.smart_unpin_oldest(channel)
            except EOFError:
                dev_id = self._config.get("specialRoles", {}).get(SpecialRoleKeys.BOT_DEVS.value)

                if dev_id is None:
                    dev_ping = "Please contact a staff member to investigate."
                else:
                    dev_ping = f"Please investigate, <@&{dev_id}>"

                await channel.send(f"I tried to pin a message, but there aren't any pins that I'm allowed to remove. "
                                   f"{dev_ping}")
                LOG.warning("Couldn't unpin any messages with smart unpin! Aborting.")

                return

        await message.pin()
        LOG.info(f"Pinned message {message.id} in {channel}, as it got enough reactions.")

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        channel = self.bot.get_channel(payload.channel_id)  # type: discord.TextChannel
        message = await channel.get_message(payload.message_id)  # type: discord.Message

        channel_config = self._config.get('reactToPin', {}).get(str(channel.id))  # type: dict

        if not WolfUtils.should_process_message(message):
            return

        if channel_config is None or not channel_config.get('enabled', False):
            LOG.debug(f"A pin configuration was not found for channel {channel}. Ignoring message.")
            return

        # Check if the message is pinned
        if message not in await channel.pins():
            LOG.debug("Can't unpin a message that isn't currently pinned.")
            return

        if str(payload.emoji) != channel_config.get('emoji'):
            LOG.debug(f"Got an invalid emoji for message {message.id} in channel {channel}, ignoring.")
            return

        if message.id in channel_config.get('permanent', []):
            LOG.info("Reactions dropped below threshold on permanently pinned message, ignoring but logging.")
            return

        # we are in a valid channel now, with a valid emote.
        current_reactions = await self.count_reactions(message, payload.emoji)

        if current_reactions >= channel_config.get('requiredToPin', 6):
            LOG.debug("Got a valid removal event for the emote, but there are too many reactions to unpin.")
            return

        await message.unpin()
        LOG.info(f"Unpinned previously pinned message {message.id} in {channel}, as it is no longer at the required "
                 f"reaction count.")

    async def on_raw_reaction_clear(self, event: discord.RawReactionClearEvent):
        channel = self.bot.get_channel(event.channel_id)  # type: discord.TextChannel
        message = await channel.get_message(event.message_id)  # type: discord.Message

        channel_config = self._config.get('reactToPin', {}).get(str(channel.id))  # type: dict

        if not WolfUtils.should_process_message(message):
            return

        if message.id in channel_config.get('permanent', []):
            LOG.info("Reactions were cleared on a permanently pinned message, ignoring.")
            return

        # Check if the message is pinned
        if message not in await channel.pins():
            LOG.debug("Can't unpin a message that isn't currently pinned.")
            return

        await message.unpin()

    async def on_raw_message_edit(self, event: discord.RawMessageUpdateEvent):
        message_id = event.message_id
        channel_id = event.data.get('channel_id', None)

        plugin_config = self._config.get('reactToPin', {})  # type: dict
        channel_config = plugin_config.get(str(channel_id), {})
        permapinned = channel_config.setdefault('permanent', [])

        # Ignore non-permanently pinned messages
        if message_id not in permapinned:
            return

        # Message is still pinned.
        if event.data.get('pinned', False):
            return

        permapinned.remove(message_id)
        LOG.info(f"Removed permanently pinned message {message_id} from channel {channel_id} as it's no longer "
                 f"pinned.")

        self._config.set('reactToPin', plugin_config)

    async def on_raw_message_delete(self, event: discord.RawMessageDeleteEvent):
        message_id = event.message_id
        channel_id = event.channel_id

        plugin_config = self._config.get('reactToPin', {})  # type: dict
        channel_config = plugin_config.get(str(channel_id), {})
        permapinned = channel_config.setdefault('permanent', [])

        # Ignore non-permanently pinned messages
        if message_id not in permapinned:
            return

        permapinned.remove(message_id)
        LOG.info(f"Removed permanently pinned message {message_id} from channel {channel_id} as it's deleted.")

        self._config.set('reactToPin', plugin_config)

    async def on_raw_bulk_message_delete(self, event: discord.RawBulkMessageDeleteEvent):
        channel_id = event.channel_id

        plugin_config = self._config.get('reactToPin', {})  # type: dict
        channel_config = plugin_config.get(str(channel_id), {})
        permapinned = channel_config.setdefault('permanent', [])

        if len(permapinned) == 0:
            return

        for message_id in event.message_ids:
            # Ignore non-permanently pinned messages
            if message_id not in permapinned:
                continue

            permapinned.remove(message_id)
            LOG.info(f"Removed permanently pinned message {message_id} from channel {channel_id} as it's deleted.")

        self._config.set('reactToPin', plugin_config)

    @commands.group(name="react2pin", brief="Automatically pin posts that get reactions.")
    @commands.has_permissions(manage_channels=True)
    async def react2pin(self, ctx: commands.Context):
        pass

    @react2pin.command(name="enable", brief="Enable ReactToPin for a channel")
    async def enable(self, ctx: commands.Context, channel: discord.TextChannel = None):
        plugin_config = self._config.get('reactToPin', {})  # type: dict

        if channel is None:
            channel = ctx.channel

        if not channel.permissions_for(ctx.author).manage_channels:
            # Prevent editing channels out of scope.
            raise commands.MissingPermissions(discord.Permissions.manage_channels)

        channel_config = plugin_config.setdefault(str(channel.id), {'enabled': False})

        if channel_config.get('enabled', False):
            await ctx.send(embed=discord.Embed(
                title=Emojis.PIN + " ReactToPin Already Enabled!",
                description=f"ReactToPin has already been enabled for {channel.mention}. No changes were made.",
                color=Colors.WARNING
            ))
            return

        channel_config['enabled'] = True
        self._config.set('reactToPin', plugin_config)

        await ctx.send(embed=discord.Embed(
            title=Emojis.PIN + " ReactToPin Enabled!",
            description=f"ReactToPin has been enabled for {channel.mention} with default settings. Use "
                        f"`/reactToPin config` in the defined channel to configure it.",
            color=Colors.SUCCESS
        ))

    @react2pin.command(name="disable", brief="Disable ReactToPin for a channel.")
    async def disable(self, ctx: commands.Context, channel: discord.TextChannel = None):
        plugin_config = self._config.get('reactToPin', {})  # type: dict

        if channel is None:
            channel = ctx.channel

        if not channel.permissions_for(ctx.author).manage_channels:
            # Prevent editing channels out of scope.
            raise commands.MissingPermissions(discord.Permissions.manage_channels)

        channel_config = plugin_config.setdefault(str(channel.id), {'enabled': False})

        if not channel_config.get('enabled', False):
            await ctx.send(embed=discord.Embed(
                title=Emojis.PIN + " ReactToPin Already Disabled!",
                description=f"ReactToPin has already been disabled for {channel.mention}. No changes were made.",
                color=Colors.WARNING
            ))
            return

        channel_config['enabled'] = False
        self._config.set('reactToPin', plugin_config)

        await ctx.send(embed=discord.Embed(
            title=Emojis.PIN + " ReactToPin Disabled!",
            description=f"ReactToPin has been disabled for {channel.mention} with default settings. Settings are "
                        "preserved.",
            color=Colors.SUCCESS
        ))

    @react2pin.command(name="configure", aliases=["config"], brief="Configure ReactToPin for the current channel")
    async def config(self, ctx: commands.Context, emoji: WolfConverters.PartialEmojiConverter, min_reacts: int):
        # pycharm duck hack
        emoji = emoji  # type: discord.PartialEmoji

        plugin_config = self._config.get('reactToPin', {})  # type: dict
        channel_config = plugin_config.get(str(ctx.channel.id))

        if channel_config is None or not channel_config.get('enabled', False):
            await ctx.send(embed=discord.Embed(
                title=Emojis.PIN + " ReactToPin Disabled!",
                description=f"ReactToPin is disabled, so changes to its configuration are not permitted.",
                color=Colors.WARNING
            ))
            return

        channel_config['emoji'] = emoji
        channel_config['requiredToPin'] = min_reacts

        self._config.set('reactToPin', plugin_config)

        await ctx.send(embed=discord.Embed(
            title=Emojis.PIN + " ReactToPin Configured!",
            description=f"ReactToPin will now automatically pin messages in this channel that have {min_reacts} "
                        f"minimum reactions with emoji {emoji}",
            color=Colors.SUCCESS
        ))

    @react2pin.command(name="permapin", brief="Permanently pin a message", aliases=["pin"])
    @commands.has_permissions(manage_messages=True)
    async def permapin(self, ctx: commands.Context, message: int):
        plugin_config = self._config.get('reactToPin', {})  # type: dict
        channel_config = plugin_config.get(str(ctx.channel.id), {})  # type: dict

        message = await ctx.channel.get_message(message)
        perm_pins = channel_config.setdefault('permanent', [])

        if message is None:
            await ctx.send("Can not find the requested message in this channel.")
            return

        if message.id in perm_pins:
            await ctx.send("Message is already permanently pinned.")
            return

        await message.pin()

        perm_pins.append(message.id)

        self._config.set('reactToPin', plugin_config)
        await ctx.send("Message pinned permanently.")


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(ReactToPin(bot))
