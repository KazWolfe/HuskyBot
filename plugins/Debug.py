import inspect
import json
import logging

import discord
from discord.ext import commands

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
    async def echo(self, ctx: discord.ext.commands.Context, *, message: str):
        await ctx.send(message)

    @debug.command(name="richEcho", brief="Echo text in a rich embed")
    async def rich_echo(self, ctx: commands.Context, *, message: str):
        obj = json.loads(message)

        embed = discord.Embed.from_data(obj)

        await ctx.send(embed=embed)

    @debug.command(name="forceExcept", brief="Force an exception (useful for testing purposes)")
    async def forceExcept(self, ctx: discord.ext.commands.Context):
        raise Exception("Random exception that was requested!")

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

    @commands.command(name="eval", brief="Execute an eval() statement on the server", hidden=True)
    @commands.has_permissions(administrator=True)
    async def evalcmd(self, ctx: discord.ext.commands.Context, *, expr: str):
        # Block *everyone* except Kaz from running eval
        if ctx.author.id != 142494680158961664:
            ctx.send(embed=discord.Embed(
                title="Access denied!",
                description="Due to the danger of this command, access to it has been blocked for this account.",
                color=Colors.DANGER
            ))
            return

        code = expr.strip('` ')

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'message': ctx.message,
            'guild': ctx.message.guild,
            'channel': ctx.message.channel,
            'author': ctx.message.author
        }

        env.update(globals())

        result = eval(code, env)
        if inspect.isawaitable(result):
            result = await result

        await ctx.send(embed=discord.Embed(
            title="Evaluation Result",
            description="```python\n>>> {}\n\n{}```".format(code, result),
            color=Colors.SECONDARY
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Debug(bot))
