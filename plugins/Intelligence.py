import logging

import discord
from discord.ext import commands

from WolfBot import WolfUtils
from WolfBot import WolfConfig
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


class Intelligence:
    def __init__(self, bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()
        LOG.info("Loaded plugin!")

    @commands.command(name="serverinfo", aliases=["sinfo"], brief="Get information about the current server")
    async def server_info(self, ctx: discord.ext.commands.Context):
        guild = ctx.guild

        server_details = discord.Embed(
            title="Server Information for " + guild.name,
            color=guild.owner.color
        )

        server_details.set_thumbnail(url=guild.icon_url)
        server_details.add_field(name="Guild ID", value=guild.id, inline=True)
        server_details.add_field(name="Owner", value=guild.owner.display_name + "#" + guild.owner.discriminator,
                                 inline=True)
        server_details.add_field(name="Members", value=str(len(guild.members)) + " users", inline=True)
        server_details.add_field(name="Text Channels", value=str(len(guild.text_channels)) + " channels", inline=True)
        server_details.add_field(name="Roles", value=str(len(guild.roles)) + " roles", inline=True)
        server_details.add_field(name="Voice Channels", value=str(len(guild.voice_channels)) + " channels", inline=True)
        server_details.add_field(name="Created At", value=str(guild.created_at).split('.')[0], inline=True)
        server_details.add_field(name="Region", value=guild.region, inline=True)

        if len(guild.features) > 0:
            server_details.add_field(name="Features", value=", ".join(guild.features))

        await ctx.send(embed=server_details)

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
        member_details.add_field(name="Joined Discord", value=str(member.created_at).split('.')[0], inline=True)
        member_details.add_field(name="Joined Server", value=str(member.joined_at).split('.')[0], inline=True)
        member_details.add_field(name="Roles", value=", ".join(roles), inline=False)
        member_details.set_thumbnail(url=member.avatar_url)
        member_details.set_footer(text="Member #{} on the server"
                                  .format(str(sorted(ctx.guild.members, key=lambda m: m.joined_at).index(member) + 1)))

        await ctx.send(embed=member_details)


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Intelligence(bot))
