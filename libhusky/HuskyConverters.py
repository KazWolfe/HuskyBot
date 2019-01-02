import datetime
import logging
import os
import random
import re
import uuid

import discord
from discord.ext import commands
from discord.ext.commands import EmojiConverter

from libhusky import HuskyUtils, HuskyConfig, HuskyStatics

LOG = logging.getLogger("HuskyBot.Utils." + __name__)


class OfflineUserConverter(commands.UserConverter):
    """
    Attempt to find a user (either on or off any guild).

    This is a heavy method, and should not be used outside of commands. If a user is not found, it will fail with
    BadArgument.
    """

    async def convert(self, ctx: commands.Context, argument: str) -> discord.User:
        result = None

        try:
            result = await super().convert(ctx, argument)
        except commands.BadArgument:
            match = super()._get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)

            if match is not None:
                try:
                    result = await ctx.bot.get_user_info(int(match.group(1)))
                except discord.NotFound:
                    result = None

        if result is None:
            LOG.error("Couldn't find offline user matching ID %s. They may have been banned system-wide or"
                      "their ID was typed wrong.", argument)
            raise commands.BadArgument(f'User "{argument}" could not be found. Do they exist?')

        return result


class OfflineMemberConverter(commands.MemberConverter):
    """
    Attempt to find a Member (in the present guild) *or* an offline user (if not in the present guild).

    Be careful, as this method may return User if unexpected (instead of Member).
    """

    async def convert(self, ctx: commands.Context, argument: str) -> discord.User:
        result = None

        try:
            result = await super().convert(ctx, argument)
        except commands.BadArgument:
            match = super()._get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)

            if match is not None:
                try:
                    result = await ctx.bot.get_user_info(int(match.group(1)))
                except discord.NotFound:
                    result = None

        if result is None:
            LOG.error("Couldn't find offline user matching ID %s. They may have been banned system-wide or"
                      "their ID was typed wrong.", argument)
            raise commands.BadArgument(f'User "{argument}" could not be found. Do they exist?')

        return result


class DateDiffConverter(datetime.timedelta, commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        if argument in ["0", "perm", "permanent", "inf", "infinite", "-"]:
            return None

        try:
            return HuskyUtils.get_timedelta_from_string(argument)
        except ValueError as e:
            raise commands.BadArgument(str(e))


class InviteLinkConverter(str, commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        return HuskyUtils.get_fragment_from_invite(argument)


class ChannelContextConverter(dict, commands.Converter):
    async def convert(self, ctx: commands.Context, context: str):
        logging_channel = HuskyConfig.get_config() \
            .get('specialChannels', {}).get(HuskyStatics.ChannelKeys.STAFF_LOG.value, None)

        channels = []
        name = context

        if context.lower() == "all":
            for channel in ctx.guild.text_channels:
                if channel.id == logging_channel:
                    continue

                channels.append(channel)

        elif context.lower() == "public":
            if not ctx.guild.default_role.permissions.read_messages:
                raise commands.BadArgument("No public channels exist in this guild.")

            for channel in ctx.guild.text_channels:
                if channel.overwrites_for(ctx.guild.default_role).read_messages is False:
                    continue

                channels.append(channel)
        else:
            cl = context.split(',')
            converter = commands.TextChannelConverter()

            for ch_key in cl:
                channels.append(await converter.convert(ctx, ch_key.strip()))

            if len(channels) == 1:
                name = channels[0].name
            else:
                name = str(list(c.name for c in channels))

        return {"name": name, "channels": channels}


# noinspection PyMethodMayBeStatic
class NicknameConverter(str, commands.Converter):
    async def convert(self, ctx, argument):
        providers = {
            "pony": self.pony,
            "animal": self.animal,
            "deleted": self.deleted
        }

        # If this doesn't look like a provider, just pass it through.
        if not (argument.startswith("%") and argument.endswith("%")):
            return argument

        provider_name = argument[1:-1].lower()  # remove the %s

        try:
            return providers[provider_name]()
        except KeyError:
            raise commands.BadArgument(f"\"{argument}\" is not a valid Nickname Provider.")

    # NICKNAME PROVIDERS BELOW THIS LINE #
    def pony(self):
        styles = [
            "{character} {suffix}",
            "{prefix} {character}"
        ]
        characters = ["Rainbow Dash", "Princess Celestia", "Applejack", "Twilight Sparkle", "Fluttershy", "Rarity",
                      "Pinkie Pie", "Spike", "Princess Luna", "Channcelor Neighsay", "Nightmare Moon"]
        suffixes = ["Is Cute", "Is Pretty", "Is Nice", "Is Awesome", "Is Perfect", "Is Fun", "Is Great", "Rocks",
                    "Rules", "Wins"]
        prefixes = ["Sleepy", "Funny", "Pretty", "I Love", "In Love With"]

        pd_nick: str = random.choice(styles).format(**{
            "character": random.choice(characters),
            "suffix": random.choice(suffixes),
            "prefix": random.choice(prefixes)
        })

        nick_mode = random.randint(1, 3)
        if nick_mode >= 2:
            pd_nick = pd_nick.replace(" ", "")
        if nick_mode >= 3:
            pd_nick += str(random.randint(1, 9999))

        return pd_nick

    def animal(self):
        adjective = ["angry", "beautiful", "big", "black", "blue", "brown", "crazy", "golden", "green", "happy",
                     "heavy", "lazy", "orange", "organic", "purple", "red", "sad", "silver", "small", "ticklish",
                     "tiny", "white", "yellow", "bionic", "xenial", "trusty", "cosmic", "artful", "zesty", "wily",
                     "utopic", "vivid", "saucy", "raring", "precise", "natty", "maverick", "lucid", "karmic", "jaunty",
                     "intrepid", "hardy", "gusty", "feisty", "edgy", "dapper", "breezy", "warty"]
        species = ["bear", "bird", "butterfly", "cat", "dog", "duck", "elephant", "fish", "frog", "goose", "gorilla",
                   "koala", "ladybug", "leopard", "lion", "meercat", "mouse", "ostrich", "panda", "peacock", "rabbit",
                   "snake", "swan", "tiger", "wolf", "zebra", "horse", "crab", "peguin", "dove", "aardvark", "zapus",
                   "werewolf", "salamander", "ocelot", "narwhal", "lynx", "jackalope", "heron", "gibbon", "fawn",
                   "drake", "badger," "hedgehog," "cuttlefish", "beaver"]

        number = random.randint(1, 9999)

        return f"{random.choice(adjective).capitalize()}{random.choice(species).capitalize()}{number}"

    def deleted(self):
        return "Deleted User {}".format(str(uuid.uuid4())[:8])


class PartialEmojiConverter(commands.PartialEmojiConverter):
    async def convert(self, ctx, argument):
        try:
            return await super().convert(ctx, argument)
        except commands.BadArgument:
            # Emojis suck. If this fails to convert something, the user can deal with it. Because *meh*.
            return argument


class SuperEmojiConverter(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await EmojiConverter.convert(EmojiConverter(), ctx, argument)
        except commands.BadArgument:
            try:
                return await PartialEmojiConverter.convert(PartialEmojiConverter(), ctx, argument)
            except commands.BadArgument:
                return argument


class CIPluginConverter(str, commands.Converter):
    """
    Get a plugin name and ignore case sensitivity.
    """

    async def convert(self, ctx, argument):
        all_plugins = {}

        plugin_dir = os.listdir('plugins/')

        if os.path.isdir('plugins/custom'):
            plugin_dir = list(set(plugin_dir + os.listdir('plugins/custom')))

        # Regrettably, we can't cache this as plugindir is dynamic.
        for plugin in plugin_dir:  # type: str
            if not plugin.endswith('.py'):
                continue

            plugin_name = plugin.split('.')[0]

            all_plugins[plugin_name.lower()] = plugin_name

        try:
            return all_plugins[argument.lower()]
        except KeyError:
            raise commands.BadArgument(f"A plugin named {argument} could not be found. Check that the plugin exists. "
                                       f"If a plugin was renamed, please restart the bot to reload the plugin.")
