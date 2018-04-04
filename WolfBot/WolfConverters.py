import datetime
import re

import discord
from discord.ext import commands

from WolfBot import WolfUtils


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
                result = await ctx.bot.get_user_info(int(match.group(1)))

        if result is None:
            raise commands.BadArgument('User "{}" not found'.format(argument))

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
                result = await ctx.bot.get_user_info(int(match.group(1)))

        if result is None:
            raise commands.BadArgument('User "{}" not found'.format(argument))

        return result


class DateDiffConverter(datetime.timedelta, commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        if argument in ["0", "perm", "permanent", "inf", "infinite", "-"]:
            return None

        try:
            return WolfUtils.get_timedelta_from_string(argument)
        except ValueError as e:
            raise commands.BadArgument(str(e))
