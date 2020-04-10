import datetime
import logging
import platform
import re
import socket

import discord
from discord.ext import commands

from HuskyBot import HuskyBot
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
        LOG.info("The builtin help command has been unloaded and has been replaced with this plugin's version.")

        LOG.info("Loaded plugin!")

    @commands.command(name="help", brief="Get help with this bot's commands", aliases=["?"])
    async def help_command(self, ctx: commands.Context, *command: str):
        """
        This command takes a string (command) as an argument to look up. If a command does not exist, the bot will throw
        an error.
        """
        content = ctx.message.content
        permitted = False

        # Evil parse magic is evil, I hate this code.
        if len(command) == 0:
            command = ''
            permitted = True
        elif len(command) > 0:
            command_obj = self.bot.get_command(' '.join(command))
            content = content.split(None, 1)[1]
            command = re.sub(r'[_*`~]', '', content, flags=re.M)
            command = command.split()

            if command_obj is not None:
                try:
                    permitted = await command_obj.can_run(ctx)

                    # Parent check
                    parent = command_obj.parent
                    while (parent is not None) and permitted:
                        permitted = await parent.can_run(ctx)
                        parent = parent.parent

                except commands.CommandError:
                    permitted = False
            else:
                permitted = ' '.join(command) in self.bot.cogs

        if not permitted:
            await ctx.send(embed=discord.Embed(
                title=Emojis.BOOK + f" {self.bot.user.name} Help Utility",
                description=f"I have looked everywhere, but I could not find any help documentation for your query!\n\n"
                            f"Please make sure that you don't have any typographical errors, and that you are not "
                            f"trying to pass in arguments here.",
                color=Colors.WARNING
            ))
            return

        # noinspection PyProtectedMember
        await self.bot.help_command.command_callback(ctx, command=' '.join(command) if command else None)

    @commands.command(name="about", aliases=["version"], brief="Get basic information about the bot.")
    async def about(self, ctx: discord.ext.commands.Context):
        """
        This command returns a quick summary of this bot and its current state.
        """

        debug_str = '| Developer Build' if self.bot.developer_mode else ''

        embed = discord.Embed(
            title=f"About {self.bot.user.name} {debug_str}",
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
        # embed.add_field(name="Bot Version", value=f"bot printer goes brrr", inline=True)
        embed.add_field(name="Library Version", value=f"discord.py {discord.__version__}", inline=True)
        embed.add_field(name="Python Version", value=f"Python {platform.python_version()}", inline=True)
        embed.add_field(name="Current Host", value=f"`{socket.gethostname()}`", inline=True)
        if ctx.guild.shard_id:
            embed.add_field(name="Current Shard", value=ctx.guild.shard_id, inline=True)

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


def setup(bot: HuskyBot):
    bot.add_cog(Base(bot))
