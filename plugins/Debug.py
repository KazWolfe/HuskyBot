import ast
import inspect
import json
import logging
import re

import discord
from discord.ext import commands

from aiohttp import web

from WolfBot import WolfChecks
from WolfBot import WolfConfig
from WolfBot import WolfHTTP
from WolfBot.WolfStatics import Colors

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Debug:
    """
    Help documentation is not available for this plugin.
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()
        self._session_store = WolfConfig.get_session_store()
        LOG.info("Loaded plugin!")

    @commands.group(name="debug", hidden=True)
    @commands.has_permissions(administrator=True)
    async def debug(self, ctx: discord.ext.commands.Context):
        """
        Help documentation is not available for this plugin.
        """

        pass

    @debug.command(name="dumpConfig", brief="Dump the bot's active configuration.")
    async def dump_config(self, ctx: discord.ext.commands.Context):
        """
        Help documentation is not available for this plugin.
        """

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
    async def force_react(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel, message: int,
                          reaction: str):
        """
        Help documentation is not available for this plugin.
        """

        target_message = await channel.get_message(message)

        await target_message.add_reaction(reaction)

    @debug.command(name="echo", brief="Repeat the message back to the current channel.")
    async def echo(self, ctx: discord.ext.commands.Context, *, message: str):
        """
        Help documentation is not available for this plugin.
        """

        await ctx.send(message)

    @debug.command(name="richEcho", brief="Echo text in a rich embed")
    async def rich_echo(self, ctx: commands.Context, *, message: str):
        """
        Help documentation is not available for this plugin.
        """

        obj = json.loads(message)

        embed = discord.Embed.from_data(obj)

        await ctx.send(embed=embed)

    @debug.command(name="forceExcept", brief="Force an exception (useful for testing purposes)")
    async def force_except(self, ctx: discord.ext.commands.Context):
        """
        Help documentation is not available for this plugin.
        """

        raise Exception("Random exception that was requested!")

    @debug.command(name="ping", brief="Get the latency (in ms) to the Discord servers")
    async def ping(self, ctx: commands.Context):
        """
        Help documentation is not available for this plugin.
        """

        ping_in_ms = round(self.bot.latency * 1000, 2)

        if 0 < ping_in_ms < 50:
            color = 0x368C23
        elif 50 <= ping_in_ms < 100:
            color = 0x9BBF30
        elif 100 <= ping_in_ms < 150:
            color = 0xD7DE38
        elif 150 <= ping_in_ms < 200:
            color = 0xF4D43C
        elif 200 <= ping_in_ms < 250:
            color = 0xD8732E
        elif ping_in_ms >= 250:
            color = 0xBB2B2E
        else:
            # what the fuck negative ping should not be possible
            color = 0x4854AF

        await ctx.send(embed=discord.Embed(
            title="DakotaBot Debugger",
            description="The latency to Discord's servers is currently **{} ms**.".format(ping_in_ms),
            color=color
        ))

    @debug.command(name="repost", brief="Copy a specified message to the current channel")
    async def repost(self, ctx: commands.Context, channel: discord.TextChannel, message_id: int):
        """
        Help documentation is not available for this plugin.
        """

        message = await channel.get_message(message_id)

        await ctx.channel.send(
            content=message.content,
            embed=message.embeds[0] if len(message.embeds) > 0 else None,
            files=message.attachments
        )

    @commands.command(name="eval", brief="Execute an eval() statement on the guild", hidden=True)
    @WolfChecks.is_developer()
    async def evalcmd(self, ctx: discord.ext.commands.Context, *, expr: str):
        """
        Help documentation is not available for this plugin.
        """

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

    @commands.command(name="feval", brief="Execute an eval as a function/method", hidden=True)
    @WolfChecks.is_developer()
    async def func_eval(self, ctx: discord.ext.commands.Context, *, expr: str):
        """
        Help documentation is not available for this plugin.
        """

        # Block *everyone* except Kaz from running feval
        if ctx.author.id != 142494680158961664:
            ctx.send(embed=discord.Embed(
                title="Access denied!",
                description="Due to the danger of this command, access to it has been blocked for this account.",
                color=Colors.DANGER
            ))
            return

        fn_name = "_eval_expr"

        # remove code formatting if present
        expr = re.sub(r'^```(python)*\n*', '', expr, flags=re.MULTILINE)
        expr = re.sub(r'```$', '', expr, flags=re.MULTILINE)

        # add indentation
        split_expr = expr.splitlines()
        cmd = "\n".join("    {}".format(i) for i in split_expr)

        # wrap in async def body
        body = ("async def {}():\n".format(fn_name)
                + cmd)

        # format code for printing

        formatted_code = ""
        formatted_code += split_expr[0]
        if len(split_expr) > 1:
            for line in split_expr[1:]:
                formatted_code += "\n... {}".format(line)

        parsed = ast.parse(body)
        body = parsed.body[0].body

        # insert return stmt if the last expression is a expression statement
        if isinstance(body[-1], ast.Expr):
            body[-1] = ast.Return(body[-1].value)

        ast.fix_missing_locations(body[-1])

        env = {
            'bot': ctx.bot,
            'discord': discord,
            'commands': commands,
            'ctx': ctx,
            'import': __import__
        }
        exec(compile(parsed, filename="<ast>", mode="exec"), env)

        result = await eval("{}()".format(fn_name), env)

        await ctx.send(embed=discord.Embed(
            title="Evaluation Result",
            description="```python\n>>> {}\n\n{}```".format(formatted_code, result),
            color=Colors.SECONDARY
        ))

    @WolfHTTP.register("/debug/hello", ["GET"])
    async def say_hello(self, request):
        return web.Response(text="Hello world from {}!".format(self.bot.user))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Debug(bot))
