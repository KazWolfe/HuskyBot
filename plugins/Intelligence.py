import datetime
import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfConverters
from WolfBot import WolfUtils
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


class Intelligence:
    def __init__(self, bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()
        LOG.info("Loaded plugin!")

    @commands.command(name="guildinfo", aliases=["sinfo", "ginfo"], brief="Get information about the current guild")
    async def guild_info(self, ctx: discord.ext.commands.Context):
        guild = ctx.guild

        guild_details = discord.Embed(
            title="Guild Information for " + guild.name,
            color=guild.owner.color
        )

        guild_details.set_thumbnail(url=guild.icon_url)
        guild_details.add_field(name="Guild ID", value=guild.id, inline=True)
        guild_details.add_field(name="Owner", value=guild.owner.display_name + "#" + guild.owner.discriminator,
                                 inline=True)
        guild_details.add_field(name="Members", value=str(len(guild.members)) + " users", inline=True)
        guild_details.add_field(name="Text Channels", value=str(len(guild.text_channels)) + " channels", inline=True)
        guild_details.add_field(name="Roles", value=str(len(guild.roles)) + " roles", inline=True)
        guild_details.add_field(name="Voice Channels", value=str(len(guild.voice_channels)) + " channels", inline=True)
        guild_details.add_field(name="Created At", value=guild.created_at.strftime(DATETIME_FORMAT), inline=True)
        guild_details.add_field(name="Region", value=guild.region, inline=True)

        if len(guild.features) > 0:
            guild_details.add_field(name="Features", value=", ".join(guild.features))

        await ctx.send(embed=guild_details)

    @commands.command(name="roleinfo", aliases=["rinfo"], brief="Get information about a specified role.")
    async def role_info(self, ctx: discord.ext.commands.Context, *, role: discord.Role):
        role_details = discord.Embed(
            title="Role Information for " + role.name,
            color=role.color
        )

        role_details.add_field(name="Role ID", value=role.id, inline=True)

        if role.color.value == 0:
            role_details.add_field(name="Color", value="None", inline=True)
        else:
            role_details.add_field(name="Color", value=str(hex(role.color.value)).replace("0x", "#"), inline=True)

        role_details.add_field(name="Hoisted", value=role.hoist, inline=True)
        role_details.add_field(name="Position", value=role.position, inline=True)
        role_details.add_field(name="Managed Role", value=role.managed, inline=True)
        role_details.add_field(name="Mentionable", value=role.mentionable, inline=True)
        role_details.add_field(name="Member Count", value=str(len(role.members)), inline=True)

        await ctx.send(embed=role_details)

    @commands.command(name="userinfo", aliases=["uinfo", "memberinfo", "minfo"],
                      brief="Get information about self or specified user")
    async def user_info(self, ctx: discord.ext.commands.Context, *, member: discord.Member = None):
        member = member or ctx.author
        member_details = discord.Embed(
            title="User Information for " + member.name + "#" + member.discriminator,
            color=member.color,
            description="Currently in **" + str(member.status) + "** mode " + WolfUtils.getFancyGameData(member)
        )

        roles = []
        for r in member.roles:
            if r.name == "@everyone":
                continue

            roles.append(r.name)

        if len(roles) == 0:
            roles.append("None")

        member_details.add_field(name="User ID", value=member.id, inline=True)
        member_details.add_field(name="Display Name", value=member.display_name, inline=True)
        member_details.add_field(name="Joined Discord", value=member.created_at.strftime(DATETIME_FORMAT), inline=True)
        member_details.add_field(name="Joined Guild", value=member.joined_at.strftime(DATETIME_FORMAT), inline=True)
        member_details.add_field(name="Roles", value=", ".join(roles), inline=False)
        member_details.set_thumbnail(url=member.avatar_url)
        member_details.set_footer(text="Member #{} on the guild"
                                  .format(str(sorted(ctx.guild.members, key=lambda m: m.joined_at).index(member) + 1)))

        await ctx.send(embed=member_details)

    @commands.command(name="avatar", brief="Get a link/high-resolution version of a user's avatar")
    async def avatar(self, ctx: commands.Context, user: discord.User = None):
        user = user or ctx.author

        embed = discord.Embed(
            title="Avatar for {}".format(user),
            color=Colors.INFO
        )

        embed.add_field(name="Avatar ID", value="`{}`".format(user.avatar), inline=False)
        embed.add_field(name="Avatar URL", value="[Open In Browser >]({})".format(user.avatar_url), inline=False)
        embed.set_image(url=user.avatar_url)

        await ctx.send(embed=embed)

    @commands.command(name="msgcount", brief="Get a count of messages in a given context")
    @commands.has_permissions(manage_messages=True)
    async def message_count(self, ctx: commands.Context, context: str, timedelta: WolfConverters.DateDiffConverter):
        """
        Get a count of messages in any given context.

        A context/area is defined as a single channel, the keyword "all", or the keyword "public". If a channel name is
        specified, only that channel will be searched. "all" will attempt to search every channel that exists in the
        guild. "public" will search every channel in the guild that can be seen by the @everyone user.

        Timedelta is a time string formatted in 00d00h00m00s format. This may only be used to search back.

        CAVEATS: It is important to know that this is a *slow* command, because it needs to iterate over every message
        in the search channels in order to successfully operate. Because of this, the "Typing" indicator will display.
        Also note that this command may not return accurate results due to the nature of the search system. It should be
        used for approximation only.

        Example commands:

        /msgcount public 7d   - Get a count of all public messages in the last 7 days
        /msgcount all 2d      - Get a count of all messages in the last two days.
        /msgcount #general 5h - Get a count of all messages in #general within the last 5 hours.
        """

        message_count = 0
        search_channels = []

        now = datetime.datetime.utcnow()
        search_start = now - timedelta

        async with ctx.typing():
            if context.lower() == "all":
                for channel in ctx.guild.text_channels:
                    search_channels.append(channel)

            elif context.lower() == "public":
                if not ctx.guild.default_role:
                    await ctx.send(embed=discord.Embed(
                        title="Intelligence Toolkit Error",
                        description="There do not appear to be any public channels in this server.",
                        color=Colors.DANGER
                    ))
                    return

                for channel in ctx.guild.text_channels:
                    if not channel.overwrites_for(ctx.guild.default_role).read_messages:
                        continue

                    search_channels.append(channel)
            else:
                converter = commands.TextChannelConverter()
                search_channels.append(await converter.convert(ctx, context))

            for channel in search_channels:
                hist = channel.history(limit=None, after=search_start)

                async for m in hist:
                    message_count += 1

            await ctx.send(embed=discord.Embed(
                title="Message Count Report",
                description="Since **`{} UTC`**, the channel context **`{}`** has seen about **`{}`** messages."
                    .format(search_start.strftime(DATETIME_FORMAT), context, message_count),
                color=Colors.INFO
            ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Intelligence(bot))
