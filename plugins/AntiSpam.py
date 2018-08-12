import asyncio
import importlib
import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfUtils
from WolfBot import antispam
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class AntiSpam:
    """
    The AntiSpam plugin is responsible for maintaining and running advanced logic-based moderation tasks on behalf of
    the moderator team.

    It, alongside Censor, ModTools, and the UBL help form the moderative backbone and power of the bot platform.
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()
        self._cleanup_time = 60 * 60 * 4  # four hours (in seconds)

        # AS Modules
        self.__modules__ = {}

        # Tasks
        self.__cleanup_task__ = self.bot.loop.create_task(self.run_scheduled_cleanups())

        # Initialize the modules
        for (module_name, module_config) in self._config.get('antiSpam', {}).items():
            if module_config.get('enabled', True):
                self.load_module(module_name)

        LOG.info("Loaded plugin!")

    def __unload(self):
        self.__cleanup_task__.cancel()

        for mod_name in self.__modules__.keys():
            self.unload_module(mod_name)

    def load_module(self, module_name):
        module = importlib.import_module(f".{module_name}", package=f"WolfBot.antispam")
        clazz = getattr(module, module_name)

        impl = clazz(self)
        self.__modules__[module_name] = impl
        self.asp.add_command(impl)

    def unload_module(self, module_name):
        self.asp.remove_command(self.__modules__[module_name])
        del self.__modules__[module_name]

    async def run_scheduled_cleanups(self):
        """
        Iterate through all of our modules, and call their module cleanup (if any)
        """
        while not self.bot.is_closed():
            for module in self.__modules__.values():  # type: antispam.AntiSpamModule
                module.cleanup()

            await asyncio.sleep(self._cleanup_time)  # sleep for four hours

    async def on_message(self, message):
        if not WolfUtils.should_process_message(message):
            return

        for module in self.__modules__.values():
            asyncio.ensure_future(module.on_message(message))

    @commands.group(name="antispam", aliases=['as'], brief="Manage the Antispam configuration for the bot")
    @commands.has_permissions(manage_messages=True)
    async def asp(self, ctx: commands.Context):
        """
        This is the parent command for the AntiSpam module.

        It does nothing on its own, but it does grant the ability for administrators to change spam filter settings on
        the fly.
        """
        pass

    @asp.command(name="enable", brief="Enable an AntiSpam module")
    @commands.has_permissions(administrator=True)
    async def enable_module(self, ctx: commands.Context, name: str):
        as_conf = self._config.get('antiSpam', {})
        mod_config = as_conf.setdefault(name, {"enabled": False})

        if mod_config['enabled'] and name in self.__modules__:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Module Already Enabled",
                description=f"The anti-spam module `{name}` has already been enabled.",
                color=Colors.WARNING
            ))
            return

        try:
            self.load_module(name)
            mod_config['enabled'] = True
        except ModuleNotFoundError:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Module Load Error",
                description=f"The anti-spam module `{name}` does not exist. Please ensure you are typing the correct "
                            f"name, and using the correct case.",
                color=Colors.DANGER
            ))
            return
        except Exception as e:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Module Load Error",
                description=f"The anti-spam module `{name}` has failed to enable. The following error is "
                            f"available:\n ```{type(e).__name__}: {e}```",
                color=Colors.DANGER
            ))
            LOG.error("Could not enable AS Module %s. Error: %s", name, e)
            return

        self._config.set('antiSpam', as_conf)
        await ctx.send(embed=discord.Embed(
            title="AntiSpam Module Enabled",
            description=f"The anti-spam module `{name}` has been enabled. It will run every time the bot starts."
        ))

    @asp.command(name="disable", brief="Disable an AntiSpam module")
    @commands.has_permissions(administrator=True)
    async def disable_module(self, ctx: commands.Context, name: str):
        as_conf = self._config.get('antiSpam', {})
        mod_config = as_conf.setdefault(name, {"enabled": False})

        if (not mod_config['enabled']) and (name not in self.__modules__):
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Module Already Disabled",
                description=f"The anti-spam module `{name}` has already been disabled.",
                color=Colors.WARNING
            ))
            return

        self.unload_module(name)
        mod_config['enabled'] = False

        self._config.set('antiSpam', as_conf)
        await ctx.send(embed=discord.Embed(
            title="AntiSpam Module Enabled",
            description=f"The anti-spam module `{name}` has been disabled. It will not run with the bot."
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(AntiSpam(bot))
