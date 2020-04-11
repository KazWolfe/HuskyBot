import ast
import datetime
import inspect
import json
import logging
import subprocess
import time

import aiohttp
import discord
from aiohttp import web
from discord.ext import commands

from HuskyBot import HuskyBot
from libhusky import HuskyHTTP
from libhusky.HuskyStatics import *
from libhusky.util import SuperuserUtil, DateUtil, StringUtil

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


class Debug(commands.Cog):
    """
    Internal HuskyBot debugging toolkit.

    This plugin provides a number of internal debugging commands useful for development and low-level maintenance of
    the bot. This plugin (typically) should not be loaded on production Husky servers. However, certain functionality
    may be useful in certain use cases, so it is made available.

    The Debug plugin is automatically loaded in Developer Mode.
    """

    # ToDo: Add some stuff to test the database and redis, make sure it's working.

    def __init__(self, bot: HuskyBot):
        self.bot = bot

        # This module may not load on non-development instances.
        if not bot.developer_mode:
            raise PermissionError("Plugin may not be loaded on non-development instances.")

        LOG.info("Loaded plugin!")

    def cog_unload(self):
        HuskyHTTP.get_router().unload_plugin(self)

    @commands.group(name="debug")
    @commands.has_permissions(administrator=True)
    async def debug(self, ctx: discord.ext.commands.Context):
        """
        Base helper command for most debug applications.

        This command is the general permission manager and entrypoint for most subcommands in the debug module. Unless
        otherwise noted, users must be guild administrators in order to run most of these commands.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=discord.Embed(
                title="HuskyBot Debug Toolkit",
                description="The command you have requested is not available. See `/help debug` for valid commands.",
                color=Colors.DANGER
            ))
            return

    # noinspection PyUnusedLocal
    @debug.command(name="react", brief="Force the bot to react to a specific message.")
    async def force_react(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel, message: int,
                          reaction: str):
        """
        This command will force-add a reaction to a specific message.

        The reaction must be specified as an emote or valid emote-like string.
        """

        target_message = await channel.fetch_message(message)

        await target_message.add_reaction(reaction)

    @debug.command(name="echo", brief="Repeat the message back to the current channel.")
    async def echo(self, ctx: discord.ext.commands.Context, *, message: str):
        """
        Echo a text string back to the current channel.
        """

        await ctx.send(message)

    @debug.command(name="richEcho", brief="Echo text in a rich embed")
    async def rich_echo(self, ctx: commands.Context, *, message: str):
        """
        Echo a Discord embed back to the current channel.

        Use a tool like https://leovoel.github.io/embed-visualizer/ to generate valid embed code.
        """

        obj = json.loads(message)

        embed = discord.Embed.from_dict(obj)

        await ctx.send(embed=embed)

    @debug.command(name="forceExcept", brief="Force an exception (useful for testing purposes)")
    async def force_except(self, ctx: discord.ext.commands.Context):
        """
        Raise an exception (of type Exception) to test error handling or logging.
        """

        raise Exception("Random exception that was requested!")

    @debug.command(name="ping", brief="Get the latency (in ms) to the Discord servers")
    async def ping(self, ctx: commands.Context):
        """
        Check latency to the Discord servers.

        This system will measure two separate systems:
        - The current websocket latency (measured in milliseconds), as determined by discord.py
        - The current message latency (time for the bot to send and receive confirmation of an event.

        Note that latency measurements may be affected by bot load, network congestion, Discord server issues, and
        other similar systems. This command should not be a direct measure of latency to Discord but rather a generic
        debugging tool.
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
        Copy (report) a message from one channel to the current channel.

        This command may be used to copy logs or other important events from one channel to another.
        """

        message = await channel.fetch_message(message_id)

        await ctx.channel.send(
            content=message.content,
            embed=message.embeds[0] if len(message.embeds) > 0 else None,
            files=message.attachments
        )

    @debug.command(name="spamLog", brief="Spam the log with a *lot* of content")
    async def spam_log(self, ctx: commands.Context, spams: int = 300):
        """
        Spam the bot's system log.

        This command is useful to test log rotation and other systems.
        """

        for i in range(spams):
            LOG.info("spam " * 30)

        await ctx.send("OK")

    @debug.command(name="uptime", brief="Get bot application uptime")
    async def get_bot_uptime(self, ctx: commands.Context):
        """
        Return the bot's current system uptime.
        """

        init_time = self.bot.session_store.get('initTime')
        if init_time:
            uptime = datetime.datetime.now() - init_time
            await ctx.send(f"**Uptime:** {DateUtil.get_delta_timestr(uptime)}")
        else:
            await ctx.send("Bot initialization time is unavailable.")

    @commands.command(name="eval", brief="Execute an eval() statement on the bot")
    @SuperuserUtil.superuser_check()
    async def evalcmd(self, ctx: discord.ext.commands.Context, *, expr: str):
        """
        Evaluate a simple Python command, generally for debugging.

        This command will execute evaluations on the bot's context, automatically determining if the result will need
        to be awaited. Certain globals are available for command execution.

        This command does NOT support multiline expressions nor does it support certain use cases (double-awaits). If
        this is required, use the more powerful /exec command.

        Users must be superusers in order to run this command, or admins if the bot is in recovery mode.

        Globals
        -------
            bot      :: The current HuskyBot instance.
            ctx      :: The context that triggered this command execution.
            message  :: The message that triggered this command execution (from ctx.message)
            guild    :: The guild that triggered this command execution (from message.guild)
            channel  :: The channel that triggered this command execution (from message.channel)
            author   :: The author that triggered this command execution (from message.author)
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

    @commands.command(name="exec", brief="Run an arbitrary script", aliases=["script", "feval"])
    @SuperuserUtil.superuser_check()
    async def func_exec(self, ctx: discord.ext.commands.Context, *, expr: str):
        """
        This command allows bot superusers to run arbitrary Python scripts in the context of the bot.

        Unlike /eval, this command allows for multiline entry (and therefore, scripts) to run, as well as finer control
        over awaitable objects (however, automatic awaiting is not available). Arbitrary code may be imported as well.

        By default, only the returned object is echoed back to Discord. If no explicit return method is found, the last
        line will act as an implicit return. Standard Output (e.g. print()) will not be captured.

        Globals
        -------
            bot      :: The current HuskyBot instance.
            ctx      :: The context that triggered this command execution.
            discord  :: The discord.py library (auto-imported)
            commands :: The discord.py Commands Extension (auto-imported)
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
            description="Execution results are below.",
            color=Colors.SECONDARY
        ))

        await ctx.send(f"```python\n>>> {formatted_code.strip()}\n\n{result}```")

    @commands.command(name="shell", brief="Run a command through the shell")
    @SuperuserUtil.superuser_check()
    async def run_command(self, ctx: commands.Context, *, command: str):
        """
        Run a shell command on Husky's host instance.

        This command will be restricted to the host instance in which the bot is -- that is, it can not run a command on
        the parent host if the bot is containerized.

        Commands are run in a shell (typically bash). Multiline input is not supported.
        """
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

    @commands.command(name='requestify', brief="Make a HTTP request through the bot", aliases=["curl"])
    @SuperuserUtil.superuser_check()
    async def requestify(self, ctx: commands.Context, url: str, method: str = "GET", *, data: str = None):
        """
        Make an HTTP call to an [external] server.

        This command functionally acts as cURL, and allows for HTTP calls to be made and sent to a server. This command
        may hit HuskyBot's internal API server.

        The following HTTP methods are supported: GET, POST, PUT, DELETE, PATCH

        The bot API server is available at http://127.0.0.1 at whatever port is defined (default 9339).
        """
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
                    description="```{}```".format(StringUtil.trim_string(await response.text(), 2000)),
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
        """
        Return a list of all superusers currently registered with the bot.

        This command will attempt to "parse" and re-execute the superuser logic to determine how a superuser was granted
        their power. Note that in some cases, this command may be somewhat out of date (e.g. if a Team changes).
        """
        su_list = self.bot.superusers[:]  # copy list so we can tamper with it
        app_info: discord.AppInfo = self.bot.session_store.get("appInfo", await self.bot.application_info())
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
