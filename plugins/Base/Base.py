import datetime
import logging
import platform
import re
import socket

import discord
from aiohttp import web
from discord.ext import commands

from HuskyBot import HuskyBot
from libhusky import HuskyHTTP
from libhusky.HuskyStatics import *
from libhusky.util import DateUtil

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Base(commands.Cog):
    """
    The Base plugin provides the very core of the bot. It is a permanent plugin and will always be executed with the
    bot.
    """

    def __init__(self, bot: HuskyBot):
        self.bot = bot

        # Prevent unloading
        self.block_unload = True

        # Unload the conflicting /help that comes built in to DiscordPy. We hate it.
        bot.remove_command("help")
        LOG.debug("The builtin help command has been unloaded and has been replaced with this plugin's version.")

        LOG.info("Loaded plugin!")

    @commands.command(name="help", brief="Get help with this bot's commands", aliases=["?"])
    async def help_command(self, ctx: commands.Context, *command: str):
        # WRAPPER METHOD for internal help
        """
        This command takes a string (command) as an argument to look up. If a command does not exist, the bot will throw
        an error.
        """
        content = ctx.message.content
        permitted = False

        # Parser magic to determine the command to target
        if len(command) == 0:
            # in case of no command (listing request), permission is granted.
            command = ''
            permitted = True
        elif len(command) > 0:
            # otherwise, we're looking at a [list, of, commands], process that.
            command_obj = self.bot.get_command(' '.join(command))
            content = content.split(None, 1)[1]
            command = re.sub(r'[_*`~]', '', content, flags=re.M)  # strip markdown out, not needed here
            command = command.split()
            # if you're wondering if we even care about the command passed in above, we don't.

            if command_obj is not None:
                try:
                    permitted = await command_obj.can_run(ctx)

                    # Recursively check parents to make sure all permissions in the tree are satisfied
                    parent = command_obj.parent
                    while (parent is not None) and permitted:
                        parent_permitted = await parent.can_run(ctx)
                        permitted = permitted and parent_permitted
                        parent = parent.parent

                except commands.CommandError:
                    permitted = False
            else:
                permitted = ' '.join(command) in self.bot.cogs

        # Blanket case for a command not found/permission denied
        if not permitted:
            await ctx.send(embed=discord.Embed(
                title=Emojis.BOOK + f" {self.bot.user.name} Help Utility",
                description=f"I have looked everywhere, but I could not find any help documentation for your query!\n\n"
                            f"Please make sure that you don't have any typographical errors and that you aren't "
                            f"including command arguments.",
                color=Colors.WARNING
            ))
            return

        # call the internal help command (HuskyHelpFormatter) with everything else.
        await self.bot.help_command.command_callback(ctx, command=' '.join(command) if command else None)

    @commands.command(name="about", aliases=["version"], brief="Get basic information about the bot.")
    async def about(self, ctx: discord.ext.commands.Context):
        """
        This command returns a quick summary of this bot and its current state.
        """

        debug_str = ' | Developer Build' if self.bot.developer_mode else ''

        embed = discord.Embed(
            title=f"About {self.bot.user.name}{debug_str}",
            description="This bot (known in code as **HuskyBot**) is a Discord moderation and management utility bot "
                        "initially for [DIY Tech](https://discord.gg/diytech). It's built on the popular "
                        "[discord.py rewrite](https://github.com/Rapptz/discord.py) and leverages containers to run at "
                        "scale. It features tight integration into Discord itself, meaning server configurations port "
                        "directly over into the bot's own configuration for ease of use and administration.",
            color=Colors.INFO
        )

        embed.add_field(name="Authors", value="[KazWolfe](https://github.com/KazWolfe), "
                                              "[Clover](https://github.com/cclover550)", inline=False)
        # todo: better version management. this way sucks.
        embed.add_field(name="Bot Version", value=f"bot printer goes brrr", inline=True)
        embed.add_field(name="Library Version", value=f"discord.py {discord.__version__}", inline=True)
        embed.add_field(name="Python Version", value=f"Python {platform.python_version()}", inline=True)
        embed.add_field(name="Current Host", value=f"`{socket.gethostname()}`", inline=True)
        if ctx.guild.shard_id:
            embed.add_field(
                name="Current Shard",
                value=f"{ctx.guild.shard_id} ({ctx.bot.shard_count} shards)",
                inline=True
            )

        init_time = self.bot.session_store.get('initTime')
        if init_time:
            uptime = datetime.datetime.now() - init_time
            embed.add_field(
                name="Uptime",
                value=DateUtil.get_delta_timestr(uptime),
                inline=True
            )

        embed.set_thumbnail(url=ctx.bot.user.avatar_url)
        embed.set_footer(text=f"(c) {datetime.datetime.now().year}, KazWolfe | Andwooooooo!",
                         icon_url="https://avatars3.githubusercontent.com/u/5192145")

        await ctx.send(embed=embed)

    @HuskyHTTP.register("/healthcheck", ["GET"])
    async def say_hello(self, request: web.BaseRequest):
        return web.json_response({"status": "ok"})
