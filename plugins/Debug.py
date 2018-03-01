import logging

import discord
from discord.ext import commands

import WolfBot.WolfUtils as WolfUtils
from BotCore import BOT_CONFIG
from BotCore import LOCAL_STORAGE
from WolfBot.WolfEmbed import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Debug:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot

    async def on_ready(self):
        LOG.info("Enabled plugin!")

    @commands.group(name="debug", hidden=True)
    @commands.has_permissions(administrator=True)
    async def debug(self, ctx: discord.ext.commands.Context):
        pass

    @debug.command(name="dumpConfig", brief="Dump the bot's active configuration.")
    async def dumpConfig(self, ctx: discord.ext.commands.Context):
        config = str(BOT_CONFIG.dump())
        config = config.replace(BOT_CONFIG.get('apiKey', '<WTF HOW DID 8741234723890423>'), '[EXPUNGED]')

        await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The current bot config is available below.",
                color=Colors.INFO
            )
            .add_field(name="BOT_CONFIG", value="```javascript\n" + config + "```", inline=False)
            .add_field(name="LOCAL_STORAGE", value="```javascript\n" + str(LOCAL_STORAGE.dump()) + "```",
                       inline=False)
        )

    @debug.command(name="react", brief="Force the bot to react to a specific message.")
    async def forceReact(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel, message: int
                         , reaction: str):
        target_message = await channel.get_message(message)

        await target_message.add_reaction(reaction)

    @debug.command(name="echo", brief="Repeat the message back to the current channel.")
    @commands.has_permissions(manage_messages=True)
    async def echo(self, ctx: discord.ext.commands.Context, *, message: str):
        await ctx.send(message)

    @commands.command(name="secho", brief="Repeat the message back to the current channel, deleting the original.")
    @commands.has_permissions(administrator=True)
    async def secho(self, ctx: discord.ext.commands.Context, *, message: str):
        await ctx.message.delete()
        await ctx.send(message)

    @commands.command(name="sendmsg", brief="Send a message to another channel.")
    @commands.has_permissions(administrator=True)
    async def sendmsg(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel, *, message: str):
        await channel.send(message)

    @commands.command(name="serverinfo", aliases=["sinfo"])
    async def serverInfo(self, ctx: discord.ext.commands.Context):
        guild = ctx.guild

        server_details = discord.Embed(
            title="Server Information for " + guild.name,
            color=Colors.SECONDARY
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

    @commands.command(name="roleinfo", aliases=["rinfo"])
    async def roleInfo(self, ctx: discord.ext.commands.Context, role: discord.Role):
        role_details = discord.Embed(
            title="Role Information for " + role.name,
            color=role.color
        )

        role_details.add_field(name="Role ID", value=role.id, inline=True)
        role_details.add_field(name="Color", value=str(hex(role.color.value)).replace("0x", "#"), inline=True)
        role_details.add_field(name="Hoisted", value=role.hoist, inline=True)
        role_details.add_field(name="Position", value=role.position, inline=True)
        role_details.add_field(name="Managed Role", value=role.managed, inline=True)
        role_details.add_field(name="Mentionable", value=role.mentionable, inline=True)
        role_details.add_field(name="Member Count", value=str(len(role.members)), inline=True)

        await ctx.send(embed=role_details)

    @commands.command(name="userinfo", aliases=["uinfo", "memberinfo", "minfo"])
    async def userInfo(self, ctx: discord.ext.commands.Context, member: discord.Member = None):
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

        await ctx.send(embed=member_details)


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Debug(bot))
