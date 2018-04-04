import inspect
import json
import logging

import discord
from discord.ext import commands

from WolfBot import WolfChecks
from WolfBot import WolfConfig
from WolfBot.WolfStatics import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Debug:
    """
    This is the debug module. It's used to debug the bot. It's meant for developers only. If you're not a developer,
    don't touch this. You will break things and you will get yelled at.

    If you do not know how to use this plugin, you have no place using it. Seriously, this isn't an insult to your
    intelligence or anything. There are just *no* checks for any of these commands, no safeties. It is dangerously
    easy to completely and possibly permanently cripple the bot with these commands.
    """

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
        """
        Debug commands have no help. If you need help running a debug command, just don't.
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
    async def forceReact(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel, message: int,
                         reaction: str):
        """
        Debug commands have no help. If you need help running a debug command, just don't.
        """

        target_message = await channel.get_message(message)

        await target_message.add_reaction(reaction)

    @debug.command(name="echo", brief="Repeat the message back to the current channel.")
    async def echo(self, ctx: discord.ext.commands.Context, *, message: str):
        """
        Debug commands have no help. If you need help running a debug command, just don't.
        """

        await ctx.send(message)

    @debug.command(name="richEcho", brief="Echo text in a rich embed")
    async def rich_echo(self, ctx: commands.Context, *, message: str):
        """
        Debug commands have no help. If you need help running a debug command, just don't.
        """

        obj = json.loads(message)

        embed = discord.Embed.from_data(obj)

        await ctx.send(embed=embed)

    @debug.command(name="forceExcept", brief="Force an exception (useful for testing purposes)")
    async def forceExcept(self, ctx: discord.ext.commands.Context):
        """
        Debug commands have no help. If you need help running a debug command, just don't.
        """

        raise Exception("Random exception that was requested!")

    @debug.command(name="ping", brief="Get the latency (in ms) to the Discord servers")
    async def ping(self, ctx: commands.Context):
        ping_in_ms = round(self.bot.latency * 1000, 2)

        if 0 < ping_in_ms < 50:
            color = 0x368C23
        elif ping_in_ms < 100:
            color = 0x9BBF30
        elif ping_in_ms < 150:
            color = 0xD7DE38
        elif ping_in_ms < 200:
            color = 0xF4D43C
        elif ping_in_ms < 250:
            color = 0xD8732E
        elif ping_in_ms > 250:
            color = 0xBB2B2E
        else:
            color = 0x4854AF

        await ctx.send(embed=discord.Embed(
            title="WolfBot Debugger",
            description="The latency to Discord's servers is currently **{} ms**.".format(ping_in_ms),
            color=color
        ))

    @commands.command(name="eval", brief="Execute an eval() statement on the guild", hidden=True)
    @WolfChecks.is_developer()
    async def evalcmd(self, ctx: discord.ext.commands.Context, *, expr: str):
        """
        Debug commands have no help. If you need help running a debug command, just don't.
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


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Debug(bot))
