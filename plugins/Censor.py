import logging
import re

import discord
from discord.ext import commands

from WolfBot import WolfUtils
from WolfBot import WolfConfig
from WolfBot.WolfEmbed import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Censor:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        LOG.info("Loaded plugin!")

    async def filter_message(self, message: discord.Message, context: str = "new_message"):
        if not isinstance(message.channel, discord.TextChannel):
            return

        if not WolfUtils.should_process_message(message):
            return

        censor_config = WolfConfig.getConfig().get("censors", {})

        censor_list = censor_config.setdefault("global", []) + censor_config.setdefault(str(message.channel.id), [])
        
        if (message.author.permissions_in(message.channel).manage_messages):
            return

        if any((re.search(censor_term, message.content) is not None) for censor_term in censor_list):
            await message.delete()
            LOG.info("Deleted censored message (context %s) from %s: %s", message.author, context, message.content)

    async def on_message(self, message):
        await self.filter_message(message)

    # noinspection PyUnusedLocal
    async def on_message_edit(self, before, after):
        await self.filter_message(after, "edit")

    @commands.group(name="censor", brief="Manage the Censor list for the server")
    @commands.has_permissions(manage_messages=True)
    async def censor(self, ctx: commands.Context):
        pass

    @censor.command(name="list", brief="List all Censors for a channel")
    async def listChannel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        censor_config = WolfConfig.getConfig().get("censors", {})

        if channel is None:
            channel = ctx.channel

        censor_list = censor_config.setdefault(str(channel.id), [])

        await ctx.send(embed=discord.Embed(
            title="Censors for " + channel.name,
            description="The following words are censored in the requested channel:\n\n" + ", ".join(censor_list),
            color=Colors.PRIMARY
        ))

    @censor.command(name="globallist", brief="List all Censors in the global list", aliases=["glist"])
    async def listGlobal(self, ctx: commands.Context):
        censor_config = WolfConfig.getConfig().get("censors", {})
        censor_list = censor_config.setdefault("global", [])

        await ctx.send(embed=discord.Embed(
            title="Global Censors for " + ctx.guild.name,
            description="The following words are censored in this server:\n\n" + ", ".join(censor_list),
            color=Colors.PRIMARY
        ))

    @censor.command(name="add", brief="Add a Censor to a channel")
    async def addChannel(self, ctx: commands.Context, channel: discord.TextChannel, *, censor: str):
        censor_config = WolfConfig.getConfig().get("censors", {})
        censor_list = censor_config.setdefault(str(channel.id), [])

        if censor in censor_list:
            await ctx.send(embed=discord.Embed(
                title="Censors for " + channel.name,
                description="The word `" + censor + "` was already in the censor list.",
                color=Colors.PRIMARY
            ))
            return

        censor_list.append(censor)

        WolfConfig.getConfig().set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title="Censors for " + channel.name,
            description="The word `" + censor + "` was added to the censor list for the specified channel",
            color=Colors.PRIMARY
        ))

    @censor.command(name="globaladd", brief="Add a Censor to the global list", aliases=["gadd"])
    async def addGlobal(self, ctx: commands.Context, *, censor: str):
        censor_config = WolfConfig.getConfig().get("censors", {})
        censor_list = censor_config.setdefault('global', [])

        if censor in censor_list:
            await ctx.send(embed=discord.Embed(
                title="Global Censors for " + ctx.guild.name,
                description="The word `" + censor + "` was already in the censor list.",
                color=Colors.DANGER
            ))
            return

        censor_list.append(censor)

        WolfConfig.getConfig().set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title="Global Censors for " + ctx.guild.name,
            description="The word `" + censor + "` was added to the global censor list.",
            color=Colors.PRIMARY
        ))

    @censor.command(name="remove", brief="Remove a censor from a channel")
    async def removeChannel(self, ctx: commands.Context, channel: discord.TextChannel, *, censor: str):
        censor_config = WolfConfig.getConfig().get("censors", {})
        censor_list = censor_config.setdefault(str(channel.id), [])

        if censor not in censor_list:
            await ctx.send(embed=discord.Embed(
                title="Censors for " + channel.name,
                description="The word `" + censor + "` was not in the censor list, so not removed.",
                color=Colors.DANGER
            ))
            return

        censor_list.remove(censor)

        WolfConfig.getConfig().set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title="Censors for " + channel.name,
            description="The word `" + censor + "` was added to the censor list for the specified channel",
            color=Colors.PRIMARY
        ))

    @censor.command(name="globalremove", brief="Remove a censor from the global list", aliases=["gremove"])
    async def removeGlobal(self, ctx: commands.Context, censor: str):
        censor_config = WolfConfig.getConfig().get("censors", {})
        censor_list = censor_config.setdefault('global', [])

        if censor not in censor_list:
            await ctx.send(embed=discord.Embed(
                title="Global Censors for " + ctx.guild.name,
                description="The word `" + censor + "` was not in the global censor list, so not removed.",
                color=Colors.DANGER
            ))
            return

        censor_list.remove(censor)

        WolfConfig.getConfig().set("censors", censor_config)

        await ctx.send(embed=discord.Embed(
            title="Censors for " + ctx.guild.name,
            description="The word `" + censor + "` was removed to the censor list for the specified channel",
            color=Colors.PRIMARY
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Censor(bot))
