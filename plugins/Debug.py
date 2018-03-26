import json
import logging

import discord
from discord.ext import commands

import WolfBot.WolfUtils as WolfUtils
from WolfBot import WolfConfig
from WolfBot.WolfStatics import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Debug:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()
        self._session_store = WolfConfig.getSessionStore()
        LOG.info("Loaded plugin!")

    @commands.group(name="debug", hidden=True)
    @commands.has_permissions(administrator=True)
    async def debug(self, ctx: discord.ext.commands.Context):
        pass

    @debug.command(name="dumpConfig", brief="Dump the bot's active configuration.")
    async def dumpConfig(self, ctx: discord.ext.commands.Context):
        config = str(self._config.dump())
        config = config.replace(self._config.get('apiKey', '<WTF HOW DID 8741234723890423>'), '[EXPUNGED]')

        embed = discord.Embed(
            title="Bot Manager",
            description="The current bot config is available below.",
            color=Colors.INFO
        )

        embed.add_field(name="WolfConfig.getConfig()", value="```javascript\n" + config + "```", inline=False)
        embed.add_field(name="LOCAL_STORAGE",
                        value="```javascript\n" + str(self._session_store.dump()) + "```",
                        inline=False)

        await ctx.send(embed=embed)

    # noinspection PyUnusedLocal
    @debug.command(name="react", brief="Force the bot to react to a specific message.")
    async def forceReact(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel, message: int,
                         reaction: str):
        target_message = await channel.get_message(message)

        await target_message.add_reaction(reaction)

    @debug.command(name="echo", brief="Repeat the message back to the current channel.")
    @commands.has_permissions(manage_messages=True)
    async def echo(self, ctx: discord.ext.commands.Context, *, message: str):
        await ctx.send(message)

    @commands.command(name="secho", brief="Repeat the message back to the current channel, deleting the original.",
                      hidden=True)
    @commands.has_permissions(administrator=True)
    async def secho(self, ctx: discord.ext.commands.Context, *, message: str):
        await ctx.message.delete()
        await ctx.send(message)

    # noinspection PyUnusedLocal
    @commands.command(name="sendmsg", brief="Send a message to another channel.", hidden=True)
    @commands.has_permissions(administrator=True)
    async def sendmsg(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel, *, message: str):
        await channel.send(message)




def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Debug(bot))
