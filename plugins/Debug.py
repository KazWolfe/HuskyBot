import ast
import datetime
import inspect
import io
import json
import logging
import math
import os
import pprint
import subprocess
import time
import zipfile

import aiohttp
import discord
from aiohttp import web
from discord.ext import commands

from HuskyBot import HuskyBot
from libhusky import HuskyChecks, HuskyConfig
from libhusky import HuskyHTTP
from libhusky import HuskyUtils
from libhusky.HuskyStatics import *

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Debug(commands.Cog):
    """
    Help documentation is not available for this plugin.
    """

    def __init__(self, bot: HuskyBot):
        self.bot = bot
        self._config = bot.config
        self._session_store = bot.session_store
        LOG.info("Loaded plugin!")

    def cog_unload(self):
        HuskyHTTP.get_router().unload_plugin(self)

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

        ts = math.floor(time.time() * 1000)
        with io.BytesIO() as buf:
            with zipfile.ZipFile(buf, mode='w') as zipf:
                # Special handling for the environment, as it's a bit... unique.
                env_snapshot = '\n'.join(f"{k}={v}" for k, v in dict(os.environ).items())
                env_snapshot = env_snapshot.replace(self.bot.http.token, '[EXPUNGED]')  # Redact the token
                env_snapshot = env_snapshot.replace(
                    os.environ.get('POSTGRES_PASSWORD', f"<nosetdbpass_{ts}>"), '[EXPUNGED]')  # redact db pass
                zipf.writestr(f'environment.txt', env_snapshot)

                for key, config in HuskyConfig.__cache__.items():  # type: HuskyConfig.WolfConfig
                    if config.is_persistent():
                        cs = json.dumps(config.dump(), sort_keys=True, indent=2)
                        fn = f"{key}.json"
                    else:
                        cs = pprint.pformat(config.dump(), indent=2, width=120)
                        fn = f"{key}.txt"

                    cs = cs.replace(self.bot.http.token, '[EXPUNGED]')

                    zipf.writestr(fn, cs)

            buf.seek(0)
            await ctx.send("The configuration files and caches currently associated with this instance of HuskyBot "
                           "have been zipped and uploaded alongside this message.\n\n"
                           "**CAUTION:** While the Discord bot token has been removed from all files, other API keys "
                           "may still be present inside of this config dump! Additionally, depending on your system "
                           "configuration, some environment variables (e.g. database credentials) may be leaked.",
                           file=discord.File(buf, f"{self.bot.user.name}-dump-{ts}.zip"))

    # noinspection PyUnusedLocal
    @debug.command(name="react", brief="Force the bot to react to a specific message.")
    async def force_react(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel, message: int,
                          reaction: str):
        """
        Help documentation is not available for this plugin.
        """

        target_message = await channel.fetch_message(message)

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

        embed = discord.Embed.from_dict(obj)

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
            title=f"{Emojis.TIMER} {self.bot.user.name} Debugger - Latency Report",
            description=f"This test determines how long is takes the current instance of {self.bot.user.name} "
            f"to reach Discord. High results may indicate network or processing issues with Discord "
            f"or {self.bot.user.name}.",
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

        message = await channel.fetch_message(message_id)

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

    @debug.command(name="uptime", brief="Get bot application uptime")
    async def get_bot_uptime(self, ctx: commands.Context):
        init_time = self._session_store.get('initTime')
        if init_time:
            uptime = datetime.datetime.now() - init_time
            await ctx.send(f"**Uptime:** {HuskyUtils.get_delta_timestr(uptime)}")
        else:
            await ctx.send("Bot initialization time is unavailable.")

    @commands.command(name="eval", brief="Execute an eval() statement on the bot")
    @HuskyChecks.is_superuser()
    async def evalcmd(self, ctx: discord.ext.commands.Context, *, expr: str):
        """
        Help documentation is not available for this plugin.
        """
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
    @HuskyChecks.is_superuser()
    async def func_exec(self, ctx: discord.ext.commands.Context, *, expr: str):
        """
        Help documentation is not available for this plugin.
        """

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
    @HuskyChecks.is_superuser()
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
            title=f"Command {command.split(' ')[0]} returned code {output['status']}",
            color=output['color']
        ))
        await ctx.send(pretty_desc)

    @commands.command(name='requestify', brief="Make a HTTP request through the bot")
    @HuskyChecks.is_superuser()
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
                    description="```{}```".format(HuskyUtils.trim_string(await response.text(), 2000)),
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

    @commands.command(name="superusers", brief="Get a list of all bot superusers.")
    async def get_superusers(self, ctx: commands.Context):
        su_list = self.bot.superusers[:]  # copy list so we can tamper with it
        app_info: discord.AppInfo = self._session_store.get("appInfo", await self.bot.application_info())
        owner_id = self.bot.owner_id or app_info.owner.id

        embed = discord.Embed(
            title=Emojis.CROWN + " Bot Superusers",
            description="The below users have full permission on the bot to perform superuser (dangerous) actions.",
            color=Colors.DANGER
        )

        if app_info.team:
            team_members = []
            for tm in app_info.team.members:
                if not tm.bot and tm.membership_state == discord.TeamMembershipState.accepted:
                    team_members.append(tm.id)

                    # remove from declared superusers
                    try:
                        su_list.remove(tm.id)
                    except ValueError:
                        pass

            try:
                team_members.remove(app_info.team.owner_id)
            except ValueError:
                pass

            embed.add_field(name="Owning Team", value=app_info.team.name, inline=True)
            embed.add_field(name="Owning Team ID", value=app_info.team.id, inline=True)
            embed.add_field(name="Team Owner", value=app_info.team.owner.mention, inline=False)

            if team_members:
                embed.add_field(name="Team Members", value="\n".join(f"<@{i}>" for i in team_members), inline=False)

            embed.set_thumbnail(url=app_info.team.icon_url)
        else:
            embed.add_field(name="Bot Owner", value=app_info.owner.mention, inline=False)

        try:
            su_list.remove(owner_id)
        except ValueError:
            pass

        if su_list:
            embed.add_field(name="Configured Superusers", value="\n".join(f"<@{i}>" for i in su_list), inline=False)

        await ctx.send(embed=embed)

    @HuskyHTTP.register("/debug/hello", ["GET", "POST"])
    async def say_hello(self, request: web.BaseRequest):
        target = "world"
        if request.method == "POST":
            data = await request.json()
            target = data.get("name", "world")
        return web.Response(text=f"Hello {target} from {self.bot.user}!")


def setup(bot: HuskyBot):
    bot.add_cog(Debug(bot))
