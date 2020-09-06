import logging
import re
from typing import Union

import discord
from discord.ext import commands

LOG = logging.getLogger("HuskyBot." + __name__)


async def _convert(superclass, ctx: commands.Context, argument: str):
    result = None

    try:
        result = await superclass.convert(ctx, argument)
    except commands.BadArgument:
        # noinspection PyProtectedMember
        match = superclass._get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)

        if match is not None:
            try:
                result = await ctx.bot.fetch_user(int(match.group(1)))
            except discord.NotFound:
                result = None

    if result is None:
        LOG.error("Couldn't find offline user matching ID %s. They may have been banned system-wide or "
                  "their ID was typed wrong.", argument)
        raise commands.BadArgument(f'User "{argument}" could not be found. Do they exist?')

    return result


class OfflineUserConverter(commands.UserConverter):
    """
    Attempt to find a user (either on or off any guild).

    This is a heavy method, and should not be used outside of commands. If a user is not found, it will fail with
    BadArgument.
    """

    async def convert(self, ctx: commands.Context, argument: str) -> discord.User:
        return await _convert(super(), ctx, argument)


class OfflineMemberConverter(commands.MemberConverter):
    """
    Attempt to find a Member (in the present guild) *or* an offline user (if not in the present guild).

    Be careful, as this method may return User if unexpected (instead of Member).
    """

    async def convert(self, ctx: commands.Context, argument: str) -> Union[discord.User, discord.Member]:
        return await _convert(super(), ctx, argument)
