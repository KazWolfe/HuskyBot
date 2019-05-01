import logging

import discord
from discord.ext import commands

from HuskyBot import HuskyBot
from libhusky.HuskyStatics import *

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


class EmojiRestriction(commands.Cog):
    """
    EmojiRestriction allows administrators to restrict which user may use a certain emoji.

    This is a builtin Discord feature, generally reserved for emojis provided by integrations such as Twitch or
    GameWisp, however the API is freely available to all guilds. This implementation allows control of these restriction
    lists on *any* guild, regardless of integration status.
    """

    def __init__(self, bot: HuskyBot):
        self.bot = bot
        self._config = bot.config

        LOG.info("Loaded plugin!")

    @commands.group(name="emojirestrict", brief="Restrict use of certain emojis.", aliases=["erestrict",
                                                                                            "restrictemoji"])
    @commands.has_permissions(manage_emojis=True)
    async def erestrict(self, ctx: commands.Context):
        pass

    @erestrict.command(name="list", brief="Get current restrictions for an emoji.", aliases=["get"])
    async def get_restrictions(self, ctx: commands.Context, emoji: discord.Emoji):
        if emoji.guild != ctx.guild:
            raise commands.BadArgument(f"Emoji :{emoji.name}: not found.")

        await ctx.send(embed=discord.Embed(
            title=f"Emoji Restrictions for {emoji.name}",
            description=f"The emoji {emoji} may only be used by the following roles:\n\n" +
                        (", ".join(role.mention for role in emoji.roles) or "Anyone"),
            color=Colors.INFO
        ))

    @erestrict.command(name="add", brief="Add roles to a restriction list for an emoji")
    async def add_restrictions(self, ctx: commands.Context, emoji: discord.Emoji, *roles: discord.Role):
        if emoji.guild != ctx.guild:
            raise commands.BadArgument(f"Emoji :{emoji.name}: not found.")

        new_restriction = list(set(emoji.roles + list(roles)))

        await emoji.edit(name=emoji.name, roles=new_restriction, reason=f"Update by {ctx.author}")

        await ctx.send(embed=discord.Embed(
            name=f"Emoji Restrictions set for {emoji.name}",
            description=f"The emoji {emoji} may now only be used by the following roles:\n\n" +
                        ", ".join(role.mention for role in new_restriction),
            color=Colors.SUCCESS
        ))

    @erestrict.command(name="set", brief="Set a restriction list for an emoji")
    async def set_restrictions(self, ctx: commands.Context, emoji: discord.Emoji, *roles: discord.Role):
        if emoji.guild != ctx.guild:
            raise commands.BadArgument(f"Emoji :{emoji.name}: not found.")

        await emoji.edit(name=emoji.name, roles=list(roles), reason=f"Update by {ctx.author}")

        await ctx.send(embed=discord.Embed(
            title=f"Emoji Restrictions set for {emoji.name}",
            description=f"The emoji {emoji} may now only be used by the following roles:\n\n" +
                        ", ".join(role.mention for role in roles),
            color=Colors.SUCCESS
        ))

    @erestrict.command(name="clear", brief="Clear an emoji's restriction list")
    async def clear_restrictions(self, ctx: commands.Context, emoji: discord.Emoji):
        if emoji.guild != ctx.guild:
            raise commands.BadArgument(f"Emoji :{emoji.name}: not found.")

        await emoji.edit(name=emoji.name, roles=None, reason=f"Update by {ctx.author}")

        await ctx.send(embed=discord.Embed(
            title=f"Emoji Restrictions set for {emoji.name}",
            description=f"The emoji {emoji} may now be used by any role.",
            color=Colors.SUCCESS
        ))

    @erestrict.command(name="remove", brief="Remove roles from an emoji's restriction list")
    async def remove_restrictions(self, ctx: commands.Context, emoji: discord.Emoji, *roles: discord.Role):
        if emoji.guild != ctx.guild:
            raise commands.BadArgument(f"Emoji :{emoji.name}: not found.")

        new_restriction = [r for r in emoji.roles if r not in list(roles)]

        await emoji.edit(name=emoji.name, roles=new_restriction, reason=f"Update by {ctx.author}")

        await ctx.send(embed=discord.Embed(
            title=f"Emoji Restrictions set for {emoji.name}",
            description=f"The emoji {emoji} may now only be used by the following roles:\n\n" +
                        (", ".join(role.mention for role in new_restriction) or "Anyone"),
            color=Colors.SUCCESS
        ))


def setup(bot: HuskyBot):
    bot.add_cog(EmojiRestriction(bot))
