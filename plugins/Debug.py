import ast
import inspect
import json
import logging
import subprocess
import time

import aiohttp
import discord
from aiohttp import web
from discord.ext import commands

from WolfBot import WolfChecks
from WolfBot import WolfConfig
from WolfBot import WolfHTTP
from WolfBot import WolfUtils
from WolfBot.WolfStatics import *

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

    def __unload(self):
        WolfHTTP.get_router().unload_plugin(self)

    @commands.group(name="debug")
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

        # Grab the latency for the websocket
        websocket_lantency_ms = round(self.bot.latency * 1000, 1)

        # Grab the message/event latency
        time_pre = time.perf_counter()
        await ctx.trigger_typing()
        time_post = time.perf_counter()
        message_latency_ms = round((time_post - time_pre) * 1000, 1)

        if 0 < websocket_lantency_ms < 50:
            color = 0x368C23
        elif 50 <= websocket_lantency_ms < 100:
            color = 0x9BBF30
        elif 100 <= websocket_lantency_ms < 150:
            color = 0xD7DE38
        elif 150 <= websocket_lantency_ms < 200:
            color = 0xF4D43C
        elif 200 <= websocket_lantency_ms < 250:
            color = 0xD8732E
        elif websocket_lantency_ms >= 250:
            color = 0xBB2B2E
        else:
            # what the fuck negative ping should not be possible
            color = 0x4854AF

        embed = discord.Embed(
            title=f"{Emojis.TIMER} DakotaBot Debugger - Latency Report",
            description=f"This test determines how long is takes the current instance of DakotaBot to reach Discord. "
                        f"High results may indicate network or processing issues with Discord or DakotaBot.",
            color=color
        )

        embed.add_field(name="Websocket Latency", value=f"{websocket_lantency_ms} ms", inline=False)
        embed.add_field(name="Message Latency", value=f"{message_latency_ms} ms", inline=False)

        await ctx.send(embed=embed)

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

    @debug.command(name="spamLog", brief="Spam the log with a *lot* of content")
    async def spam_log(self, ctx: commands.Context, spams: int = 300):

        for i in range(spams):
            LOG.info("spam " * 30)

        await ctx.send("OK")

    @commands.command(name="eval", brief="Execute an eval() statement on the bot")
    @WolfChecks.is_developer()
    async def evalcmd(self, ctx: discord.ext.commands.Context, *, expr: str):
        """
        Help documentation is not available for this plugin.
        """

        # Block *everyone* except Kaz from running eval
        if ctx.author.id != 142494680158961664:
            await ctx.send(embed=discord.Embed(
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
            description=f"```python\n>>> {code}\n\n{result}```",
            color=Colors.SECONDARY
        ))

    @commands.command(name="exec", brief="Execute an eval as a function/method", aliases=["feval"])
    @WolfChecks.is_developer()
    async def func_exec(self, ctx: discord.ext.commands.Context, *, expr: str):
        """
        Help documentation is not available for this plugin.
        """

        # Block *everyone* except Kaz from running feval
        if ctx.author.id != 142494680158961664:
            await ctx.send(embed=discord.Embed(
                title="Access denied!",
                description="Due to the danger of this command, access to it has been blocked for this account.",
                color=Colors.DANGER
            ))
            return

        fn_name = "_eval_expr"

        # remove code formatting if present
        expr = expr.strip('```')
        if expr.startswith('python'):
            expr = expr.replace("python", "", 1)

        # add indentation
        split_expr = expr.splitlines()
        cmd = "\n".join(f"    {i}" for i in split_expr)

        # wrap in async def body
        body = (f"async def {fn_name}():\n" + cmd)

        # format code for printing
        formatted_code = ""
        formatted_code += split_expr[0]
        if len(split_expr) > 1:
            for line in split_expr[1:]:
                formatted_code += f"\n... {line}"

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

        result = await eval(f"{fn_name}()", env)

        await ctx.send(embed=discord.Embed(
            title="Evaluation Result",
            description=f"```python\n>>> {formatted_code}\n\n{result}```",
            color=Colors.SECONDARY
        ))

    @commands.command(name="shell", brief="Run a command through the shell")
    @WolfChecks.is_developer()
    async def run_command(self, ctx: commands.Context, *, command: str):
        command = command.strip('`')

        try:
            output = {
                "text": subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT).decode('utf-8'),
                "status": 0,
                "color": Colors.SUCCESS
            }
        except subprocess.CalledProcessError as e:
            output = {
                "text": e.output.decode('utf-8'),
                "status": e.returncode,
                "color": Colors.ERROR,
            }

        pretty_desc = "```$ {}\n{}```".format(command.replace("```", "`\u200b``"),
                                              output['text'].replace("```", "`\u200b``"))

        await ctx.send(embed=discord.Embed(
            title=f"Command returned code {output['status']}",
            description=pretty_desc,
            color=output['color']
        ))

    @commands.command(name='requestify', brief="Make a HTTP request through DakotaBot")
    @WolfChecks.is_developer()
    async def requestify(self, ctx: commands.Context, url: str, method: str = "GET", *, data: str = None):
        method = method.upper()
        supported_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]

        if method not in supported_methods:
            await ctx.send(embed=discord.Embed(
                title="Invalid request method!",
                description="Only the following request methods are supported:\n\n"
                            "{}".format(', '.join('`{}`'.format(m) for m in supported_methods)),
                color=Colors.ERROR
            ))
            return

        try:
            async with aiohttp.client.request(method, url, data=data) as response:
                if 100 <= response.status <= 199:
                    color = Colors.INFO
                elif 200 <= response.status <= 299:
                    color = Colors.SUCCESS
                elif 300 <= response.status <= 399:
                    color = Colors.WARNING
                else:
                    color = Colors.DANGER

                await ctx.send(embed=discord.Embed(
                    title=f"HTTP Status {response.status}",
                    description="```{}```".format(WolfUtils.trim_string(await response.text(), 2000)),
                    color=color
                ))
        except aiohttp.client.ClientError as ex:
            await ctx.send(embed=discord.Embed(
                title="Could Not Make Request",
                description=f"Requestify failed to make a request due to error `{type(ex).__name__}`. "
                            f"Data has been logged.",
                color=Colors.DANGER
            ))
            LOG.warning("Requestify raised exception.", ex)

    @WolfHTTP.register("/debug/hello", ["GET", "POST"])
    async def say_hello(self, request: web.BaseRequest):
        target = "world"
        if request.method == "POST":
            data = await request.json()
            target = data.get("name", "world")
        return web.Response(text=f"Hello {target} from {self.bot.user}!")


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Debug(bot))
