import asyncio
import importlib
import logging

import discord
from discord.ext import commands

from HuskyBot import HuskyBot
from libhusky import HuskyUtils
from libhusky import antispam
from libhusky.HuskyStatics import *

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class AntiSpam(commands.Cog):
    """
    The AntiSpam plugin is responsible for maintaining and running advanced logic-based moderation tasks on behalf of
    the moderator team.

    It, alongside Censor, ModTools, and the UBL help form the moderative backbone and power of the bot platform.
    """

    def __init__(self, bot: HuskyBot):
        self.bot = bot
        self._config = bot.config
        self._cleanup_time = 60 * 60 * 4  # four hours (in seconds)

        # AS Modules
        self.__modules__ = {}

        # Tasks
        self.__cleanup_task__ = self.bot.loop.create_task(self.run_scheduled_cleanups())

        # Initialize the modules
        for (module_name, module_config) in self._config.get('antiSpam', {}).items():
            # ignore system configs
            if module_name.startswith("__"):
                continue

            if module_config.get('enabled', True):
                self.load_module(module_name)

        LOG.info("Loaded plugin!")

    def cog_unload(self):
        self.__cleanup_task__.cancel()

        for mod_name in list(self.__modules__.keys()):
            self.unload_module(mod_name)

    def load_module(self, module_name):
        importlib.invalidate_caches()

        module = importlib.import_module(f".{module_name}", package=f"libhusky.antispam")
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

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # config loading
        as_config: dict = self._config.get("antiSpam", {})
        global_config: dict = as_config.get("__global__", {})
        exemption_config: list = global_config.get("exemptedRoles", [])

        if not HuskyUtils.should_process_message(message):
            return

        if exemption_config and HuskyUtils.member_has_any_role(message.author, exemption_config):
            return

        for module in self.__modules__.values():
            asyncio.ensure_future(module.on_message(message))

    @commands.group(name="antispam", aliases=['as'], brief="Manage the Antispam configuration for the bot")
    @commands.has_permissions(manage_messages=True)
    async def asp(self, ctx: commands.Context):
        """
        This command does nothing on its own, but it does grant the ability for administrators to change spam filter
        settings on the fly.
        """
        pass

    @asp.command(name="enable", brief="Enable an AntiSpam module")
    @commands.has_permissions(administrator=True)
    async def enable_module(self, ctx: commands.Context, name: str):
        """
        AntiSpam Modules are similar to plugins, except they only will target the AntiSpam plugin. They generally exist
        to isolate anti-spam processes from each other, and give them (powerful) control over their own data management.

        When an AntiSpam Module is enabled, it will load immediately as well as on every bot execution. Configuration
        changes made to a module will persist after it is disabled.

        Commands to control a module will only be visible if that module is loaded.

        Available Modules:
        ------------------
            AttachmentFilter  :: Restrict the number of attachments/files a user can post in a certain time
            InviteFilter      :: Block unauthorized Discord invites to other guilds
            LinkFilter        :: Block messages that contain excessive links, or link-spamming users.
            MentionFilter     :: Block users from "mention-spamming" over set thresholds.
            NonAsciiFilter    :: Block messages composed of non-ASCII characters, like Zalgo
            NonUniqueFilter   :: Monitor and take action against users who post the same messages over and over again.

        Parameters
        ----------
            ctx   :: Discord context <!nodoc>
            name  :: The module name (case sensitive) to enable.

        See Also
        --------
            /as disable - Disable a loaded module.
        """
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
            description=f"The anti-spam module `{name}` has been enabled. It will run every time the bot starts.",
            color=Colors.SUCCESS
        ))

    @asp.command(name="disable", brief="Disable an AntiSpam module")
    @commands.has_permissions(administrator=True)
    async def disable_module(self, ctx: commands.Context, name: str):
        """
        AntiSpam modules are dynamic, meaning they can be started and stopped at will, depending on guild configuration
        and active state. To facilitate easy removal of unnecessary modules, this command can be used.

        A disabled module will preserve its configuration, *but not its state*.

        See `/help as enable` for a list of available modules.

        Parameters
        ----------
            ctx   :: Discord context <!nodoc>
            name  :: The name of the module to disable

        See Also
        --------
            /as enable  :: Enable an AntiSpam Module.
        """
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
            title="AntiSpam Module Disabled",
            description=f"The anti-spam module `{name}` has been disabled. It will not run with the bot.",
            color=Colors.SUCCESS
        ))

    @asp.command(name="clear", brief="Clear cooldowns across all filters for a user.")
    async def clear_cooldowns(self, ctx: commands.Context, user: discord.Member):
        """
        This command allows moderators to immediately reset user filter states across all actively loaded filters,
        without affecting other records. When this command is finished, the user targeted will have *no* warnings on
        their AntiSpam record.

        Parameters
        ----------
            ctx   :: Discord context <!nodoc>
            user  :: A user object (ID, mention, etc) to target for clearing.

        See Also
        --------
            /as <filter_name> clear     :: Clear cooldowns on a single filter for a single user.
            /as <filter_name> clearAll  :: Clear all cooldowns for all users for a single filter.
            /as clearAll                :: Clear all cooldowns globally for all users (reset).
        """
        for f in self.__modules__.values():  # type: antispam.AntiSpamModule
            try:
                f.clear_for_user(user)
            except KeyError as _:
                # If we get a KeyError, that means the user has no record. Move on with our lives.
                pass

        await ctx.send(embed=discord.Embed(
            title=Emojis.SPARKLES + " AntiSpam | Cooldowns Cleared",
            description=f"All cooldowns for {user} across all antispam filters have been successfully cleared. "
                        f"{user} no longer has any antispam-related warnings on their profile.",
            color=Colors.SUCCESS
        ))

    @asp.command(name="clearAll", brief="Clear cooldowns across all filters for all users.")
    @commands.has_permissions(administrator=True)
    async def clear_all_cooldowns(self, ctx: commands.Context):
        """
        This command effectively resets the AntiSpam cooldown system entirely, and is equivalent to reloading the entire
        AntiSpam module.

        See Also
        --------
            /as clear                   :: Clear cooldowns on all filters for a single user.
            /as <filter_name> clear     :: Clear cooldowns on a single filter for a single user.
            /as <filter_name> clearAll  :: Clear all cooldowns for all users for a single filter.
        """

        for f in self.__modules__.values():  # type: antispam.AntiSpamModule
            f.clear_all()

        await ctx.send(embed=discord.Embed(
            title=Emojis.SPARKLES + " AntiSpam | Cooldowns Cleared",
            description=f"All cooldowns for all users across all antispam filters have been successfully cleared.",
            color=Colors.SUCCESS
        ))

    @asp.group(name="exemptions", brief="Manage exemptions to the AntiSpam plugin")
    @commands.has_permissions(manage_guild=True)
    async def exemptions(self, ctx: commands.Context):
        """
        This command allows certain roles to be exempted from anti-spam triggering.

        This is useful for moderators and other roles where granting MANAGE_MESSAGES is not beneficial. Note that this
        command will override any modules that do not have MANAGE_MESSAGES exemptions.

        In the future, this will become a per-module check, with this serving as the "global" override.
        """

        pass

    @exemptions.command(name="add", brief="Add a role to the exemptions list.")
    async def add_exemption(self, ctx: commands.Context, *, role: discord.Role):
        as_config: dict = self._config.get("antiSpam", {})
        global_config: dict = as_config.setdefault("__global__", {})
        exemption_config: list = global_config.setdefault("exemptedRoles", [])

        if role.id in exemption_config:
            await ctx.send(embed=discord.Embed(
                title="Role Already Exempt",
                color=Colors.WARNING,
                description=f"The role {role.mention} is already exempt from AntiSpam, and may not be re-added."
            ))
            return

        exemption_config.append(role.id)
        self._config.set("antiSpam", as_config)

        await ctx.send(embed=discord.Embed(
            title="Role Exempted!",
            color=Colors.SUCCESS,
            description=f"The role {role.mention} is now exempt from AntiSpam checks."
        ))

    @exemptions.command(name="remove", brief="Remove a role from the exemptions list")
    async def remove_exemption(self, ctx: commands.Context, *, role: discord.Role):
        as_config: dict = self._config.get("antiSpam", {})
        global_config: dict = as_config.get("__global__", {})
        exemption_config: list = global_config.get("exemptedRoles", [])

        if role.id not in exemption_config:
            await ctx.send(embed=discord.Embed(
                title="Role Wasn't Exempted",
                color=Colors.WARNING,
                description=f"The role {role.mention} isn't exempt from AntiSpam, and may not be removed."
            ))
            return

        exemption_config.remove(role.id)
        self._config.set("antispam", as_config)

        await ctx.send(embed=discord.Embed(
            title="Role Unexempted!",
            color=Colors.SUCCESS,
            description=f"The role {role.mention} is now subject to AntiSpam checks again."
        ))

    @exemptions.command(name="list", brief="List all exempted roles in the AntiSpam config.")
    async def list_exemptions(self, ctx: commands.Context):
        as_config: dict = self._config.get("antiSpam", {})
        global_config: dict = as_config.get("__global__", {})
        exemption_config: list = global_config.get("exemptedRoles", [])

        if not exemption_config:
            await ctx.send(embed=discord.Embed(
                title="AntiSpam Exemptions",
                color=Colors.WARNING,
                description=f"There are no configured AntiSpam exemptions."
            ))
            return

        rls = []

        for role_id in exemption_config:
            rls.append(f"- <@&{role_id}>")

        await ctx.send(embed=discord.Embed(
            title="AntiSpam Exemptions",
            color=Colors.INFO,
            description="The following roles are exempt from AntiSpam checks:\n\n" + "\n".join(rls)
        ))


def setup(bot: HuskyBot):
    bot.add_cog(AntiSpam(bot))
