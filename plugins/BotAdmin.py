import logging
import os

import discord
from discord.ext import commands

from HuskyBot import HuskyBot
from libhusky import HuskyChecks, HuskyConverters, HuskyUtils
from libhusky.HuskyStatics import *

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class BotAdmin:
    """
    The BotAdmin plugin is a mandatory plugin that's required for the bot to operate normally.

    It provides core administrative functions to bot administrators to change configurations and other important values.
    """

    def __init__(self, bot: HuskyBot):
        self.bot = bot
        self._config = bot.config
        self._session_store = bot.session_store

        # Prevent unloading
        self.block_unload = True

        LOG.info("Loaded plugin!")

    @commands.group(pass_context=True, brief="Manage the bot plugin subsystem", aliases=["plugins"])
    @commands.has_permissions(administrator=True)
    async def plugin(self, ctx: discord.ext.commands.Context):
        """
        This command, when called without any subcommands, will list all plugins that the bot is aware of, and their
        current state.

        To alter a plugin's state, use one of the subcommands listed below.
        """

        if ctx.invoked_subcommand is not None:
            return

        unloaded_plugins = []
        loaded_plugins = list(self.bot.extensions.keys())

        plugin_dir = os.listdir('plugins/')

        if os.path.isdir('plugins/custom'):
            plugin_dir = list(set(plugin_dir + os.listdir('plugins/custom')))

        for plugin in plugin_dir:  # type: str
            if not plugin.endswith('.py'):
                continue

            plugin_name = plugin.split('.')[0]

            if plugin_name in loaded_plugins:
                continue

            unloaded_plugins.append(plugin_name)

        # Get everything into alphabetical order.
        unloaded_plugins.sort()
        loaded_plugins.sort()

        embed = discord.Embed(
            title=Emojis.PLUG + f" {self.bot.user.name} Plugins",
            description=f"Currently, there are {len(loaded_plugins)} plugins loaded in this instance of "
                        f"{self.bot.user.name}. See `/help plugin` to get instructions on how to load and unload "
                        f"plugins.",
            color=Colors.INFO
        )

        if len(loaded_plugins) > 0:
            embed.add_field(
                name="Loaded Plugins",
                value=f"```diff\n+ {', '.join(loaded_plugins)}```",
                inline=False
            )

        if len(unloaded_plugins) > 0:
            embed.add_field(
                name="Unloaded Plugins",
                value=f"```diff\n- {', '.join(unloaded_plugins)}```",
                inline=False
            )

        await ctx.send(embed=embed)

    @plugin.command(name="load", brief="Temporarily load a plugin into the bot.")
    async def load(self, ctx: discord.ext.commands.Context, plugin_name: HuskyConverters.CIPluginConverter):
        """
        This command will attempt to load the named plugin into the bot's runtime. It will not mark this command as
        enabled, nor will it allow the plugin to relaunch on start.

        Parameters
        ----------
            ctx          :: Discord context <!nodoc>
            plugin_name  :: A name of a plugin to load into the bot.

        See Also
        --------
            /help admin unload   :: Temporarily unload a plugin from the bot.
            /help admin reload   :: Unload and reload a plugin from the bot.
            /help admin enable   :: Permanently enable a plugin (load + run on start)
            /help admin disable  :: Permanently disable a plugin (unload + disallow startup execution)
        """

        if plugin_name in ctx.bot.cogs.keys():
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description=f"The plugin `{plugin_name}` could not be loaded, as it is already loaded.",
                color=Colors.WARNING
            ))
            LOG.warning("Attempted to unload already-unloaded plugin %s", plugin_name)
            return

        try:
            self.bot.load_extension(plugin_name)
        except (AttributeError, ImportError) as e:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description=f"The plugin `{plugin_name}` has failed to load. The following "
                            f"error is available:\n ```{type(e).__name__}: {e}```",
                color=Colors.DANGER
            ))
            LOG.error("Could not load plugin %s. Error: %s", plugin_name, e)
            return

        LOG.info("Loaded plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description=f"The plugin `{plugin_name}` has been loaded.",
            color=Colors.INFO
        ))

    @plugin.command(name="unload", brief="Temporarily unload a plugin from the bot.")
    async def unload(self, ctx: discord.ext.commands.Context, plugin_name: HuskyConverters.CIPluginConverter):
        """
        This command will attempt to unload non-critical plugin from the bot. It will not disable a plugin, and will
        only last until the bot is restarted.

        Parameters
        ----------
            ctx          :: Discord context <!nodoc>
            plugin_name  :: A name of a plugin to unload from the bot.

        See Also
        --------
            /help admin unload   :: Temporarily unload a plugin from the bot.
            /help admin reload   :: Unload and reload a plugin from the bot.
            /help admin enable   :: Permanently enable a plugin (load + run on start)
            /help admin disable  :: Permanently disable a plugin (unload + disallow startup execution)
        """

        if plugin_name == "Debug" and self.bot.developer_mode:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The `Debug` plugin may not be unloaded while Developer Mode is enabled."
                            "\nPlease disable Developer Mode first.",
                color=Colors.DANGER
            ))
            LOG.warning("A request was made to unload Debug while in DevMode. Blocked.")
            return

        if plugin_name not in ctx.bot.cogs.keys():
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description=f"The plugin `{plugin_name}` could not be unloaded, as it is not loaded. "
                            f"Plugin names are case-sensitive.",
                color=Colors.WARNING
            ))
            LOG.warning("Attempted to unload already-unloaded plugin %s", plugin_name)
            return

        plugin_instance = ctx.bot.cogs[plugin_name]

        if hasattr(plugin_instance, 'block_unload') and plugin_instance.block_unload:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description=f"The plugin `{plugin_name}` could not be unloaded. See the log for more details.",
                color=Colors.DANGER
            ))
            LOG.warning("A request was made to unload %s, but it requested it not be unloaded.", plugin_name)
            return

        """Unloads an extension."""
        self.bot.unload_extension(plugin_name)
        LOG.info("Unloaded plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description=f"The plugin `{plugin_name}` has been unloaded.",
            color=Colors.INFO
        ))

    @plugin.command(name="reload", brief="Unload and reload a plugin.")
    async def reload(self, ctx: discord.ext.commands.Context, plugin_name: HuskyConverters.CIPluginConverter):
        """
        This will not enable or disable a command, but it will cause the plugin to re-initialize and reload. This may
        wipe out configurations/timings for certain plugins, depending on how they save information.

        This command will also cause that plugin's code to be reloaded, allowing dynamic re-execution of code. Note that
        it will *not* reload imports of the plugin, so a full restart may be required to swap in other code.

        The reload command *will* work with critical modules.

        Parameters
        ----------
            ctx          :: Discord context <!nodoc>
            plugin_name  :: A name of a plugin to reload.

        See Also
        --------
            /help admin load     :: Temporarily load a plugin from the bot.
            /help admin unload   :: Temporarily unload a plugin from the bot.
            /help admin enable   :: Permanently enable a plugin (load + run on start)
            /help admin disable  :: Permanently disable a plugin (unload + disallow startup execution)
        """

        self.bot.unload_extension(plugin_name)
        LOG.info("Unloaded plugin %s for reload.", plugin_name)
        try:
            self.bot.load_extension(plugin_name)
        except (AttributeError, ImportError) as e:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description=f"The plugin `{plugin_name}` has failed to reload. The following "
                            f"error is available:\n ```{type(e).__name__}: {e}```",
                color=Colors.DANGER
            ))
            LOG.error("Could not reload plugin %s. Error: %s", plugin_name, e)
            return
        LOG.info("Reloaded plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description=f"The plugin `{plugin_name}` has been reloaded.",
            color=Colors.INFO
        ))

    @plugin.command(name="enable", brief="Enable a plugin to run now and at bot load.")
    async def enable(self, ctx: discord.ext.commands.Context, plugin_name: HuskyConverters.CIPluginConverter):
        """
        This command will attempt to load a plugin into the bot, and then mark it for automatic load on bot start. This
        should be used when a plugin is desired to permanently run alongside the bot.

        Parameters
        ----------
            ctx          :: Discord context <!nodoc>
            plugin_name  :: A name of a plugin to enable

        See Also
        --------
            /help admin load     :: Temporarily load a plugin from the bot.
            /help admin unload   :: Temporarily unload a plugin from the bot.
            /help admin reload   :: Unload and reload a plugin from the bot.
            /help admin disable  :: Permanently disable a plugin (unload + disallow startup execution)
        """
        config = self._config.get('plugins', [])

        if plugin_name in config:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description=f"The plugin `{plugin_name}` is already enabled. If it is not loaded, use "
                            f"`/admin load {plugin_name}`.",
                color=Colors.WARNING
            ))
            return

        try:
            self.bot.load_extension(plugin_name)
        except (AttributeError, ImportError) as e:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description=f"The plugin `{plugin_name}` has failed to enable. The following error is "
                            f"available:\n ```{type(e).__name__}: {e}```",
                color=Colors.DANGER
            ))
            LOG.error("Could not enable plugin %s. Error: %s", plugin_name, e)
            return
        LOG.info("Loaded plugin %s for enable", plugin_name)

        config.append(plugin_name)
        self._config.set('plugins', config)
        LOG.info("Enabled plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description=f"The plugin `{plugin_name}` has been enabled and will run automatically.",
            color=Colors.SUCCESS
        ))

    @plugin.command(name="disable", brief="Disable a plugin from running at bot load. Also stops the plugin.")
    async def disable(self, ctx: discord.ext.commands.Context, plugin_name: HuskyConverters.CIPluginConverter):
        """
        This command will unload a currently active plugin, and additionally mark it as "disabled", preventing it from
        automatically executing at bot startup. The plugin may still be manually loaded using /admin load.

        Parameters
        ----------
            ctx          :: Discord context <!nodoc>
            plugin_name  :: A name of a plugin to disable.

        See Also
        --------
            /help admin load     :: Temporarily load a plugin from the bot.
            /help admin unload   :: Temporarily unload a plugin from the bot.
            /help admin reload   :: Unload and reload a plugin from the bot.
            /help admin enable   :: Permanently enable a plugin (load + run on start)
        """
        if plugin_name == "Debug" and self.bot.developer_mode:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The `Debug` plugin may not be disabled while Developer Mode is enabled."
                            "\nPlease disable Developer Mode first.",
                color=Colors.DANGER
            ))
            LOG.warning("A request was made to disable Debug while in DevMode. Blocked.")
            return

        plugin_instance = ctx.bot.cogs[plugin_name]

        if hasattr(plugin_instance, 'block_unload') and plugin_instance.block_unload:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description=f"The plugin `{plugin_name}` could not be disabled. See the log for more details.",
                color=Colors.DANGER
            ))
            LOG.warning("A request was made to disable %s, but it requested it not be unloaded.", plugin_name)
            return

        config = self._config.get('plugins', [])

        if plugin_name not in config:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description=f"The plugin `{plugin_name}` is already disabled.",
                color=Colors.WARNING
            ))
            return

        self.bot.unload_extension(plugin_name)
        LOG.info("Unloaded plugin %s for disable", plugin_name)

        config.remove(plugin_name)
        self._config.set('plugins', config)
        LOG.info("Disabled plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description=f"The plugin `{plugin_name}` has been disabled and will no longer run automatically.",
            color=Colors.WARNING
        ))

    @commands.group(pass_context=True, brief="Alter and handle bot configurations")
    @commands.has_permissions(administrator=True)
    async def config(self, ctx: discord.ext.commands.Context):
        """
        Manage and edit certain aspects of the bot configuration.
        """

        pass

    @config.command(name="reload", brief="Reload the bot's configuration files from disk.")
    async def reload_config(self, ctx: discord.ext.commands.Context):
        """
        Dump the bot's existing in-memory configuration and reload the config from the disk.

        ANY UNSAVED CHANGES TO THE CONFIGURATION WILL BE DISCARDED! (Note: this is a rare incidence - the bot generally
        saves its config on any change)
        """

        self._config.load()
        LOG.info("Bot configuration reloaded.")
        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description="The bot configuration has been reloaded.",
            color=Colors.INFO
        ))

    @config.command(name="presence", brief="Set the bot's presence mode.")
    async def presence(self, ctx: discord.ext.commands.Context, presence_type: str, name: str, status: str):
        """
        The bot has a user-definable presence used to provide status messages or other information. This may be
        configured on-the-fly using this command.

        This command takes three arguments: the Presence Type, the Name, and a Status.

        Presence Type must be a string containing either PLAYING, LISTENING, or WATCHING. No other arguments are
        permitted at this time.

        The Name may be any (short) string that will be displayed after the presence type.

        Status must be a strong containing either ONLINE, IDLE, or DND. No other arguments are permitted.

        Parameters
        ----------
            ctx            :: Discord context <!nodoc>
            presence_type  :: PLAYING, LISTENING, or WATCHING.
            name           :: The activity name being performed.
            status         :: ONLINE, IDLE, or DND
        """
        presence_map = {"playing": 0, "listening": 2, "watching": 3}

        if status.lower() == "invisible" or status.lower() == "offline":
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The bot status can not be set to invisible or offline.",
                color=Colors.DANGER
            ))
            return

        try:
            presence_type = presence_map[presence_type.lower()]
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The presence type must be **`PLAYING`**, **`LISTENING`**, or **`WATCHING`**.",
                color=Colors.DANGER
            ))
            return

        try:
            new_status = discord.Status[status.lower()]
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="Valid values for status are: **`ONLINE`**, **`IDLE`**, **`DND`**.",
                color=Colors.DANGER
            ))
            return

        self._config.set('presence', {"game": name, "type": presence_type, "status": status.lower()})
        await ctx.bot.change_presence(activity=discord.Activity(name=name, type=presence_type), status=new_status)
        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description="The bot's presence was updated.",
            color=Colors.SUCCESS
        ))

    @config.command(name="reloadPresence", brief="Reload a Presence from the config file")
    async def reload_presence(self, ctx: discord.ext.commands.Context):
        """
        Debug commands have no help. If you need help running a debug command, just don't.
        """
        bot_presence = self._config.get('presence', {"game": f"{self.bot.user.name}", "type": 2, "status": "dnd"})

        await ctx.bot.change_presence(activity=discord.Activity(name=bot_presence['game'], type=bot_presence['type']),
                                      status=discord.Status[bot_presence['status']])

        await ctx.send("OK.")

    @config.command(name="ignoreCommand", brief="Add a command to the ignore list.", enabled=False)
    async def ignore_command(self, ctx: commands.Context, command: str):
        """
        This command will allow administrators to add commands that are silently ignored by the bot. This command takes
        only a single string as an argument. Do not include a slash when specifying a command name to ignore.

        See Also
        --------
            /config unignoreCommand - Remove a command from the ignore list
        """
        command = command.lower()

        ignored_commands = self._config.get('ignoredCommands', [])

        if command in ignored_commands:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description=f"The command `/{command}` is already being ignored.",
                color=Colors.WARNING
            ))
            return

        ignored_commands.append(command)
        self._config.set('ignoredCommands', ignored_commands)

        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description=f"The command `/{command}` has been added to the ignore list.",
            color=Colors.SUCCESS
        ))

    @config.command(name="unignoreCommand", brief="Remove a command from the ignore list.", enabled=False)
    async def unignore_command(self, ctx: commands.Context, command: str):
        """
        If a command was previously ignored by /admin ignoreCommand, this command will allow the command to be watched
        again.

        See /help admin ignoreCommand for information about the arguments for this command.

        See Also
        --------
            /help admin ignoreCommand  :: Add a command to the ignore list
        """
        command = command.lower()

        ignored_commands = self._config.get('ignoredCommands', [])

        if command not in ignored_commands:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description=f"The command `/{command}` is already being accepted.",
                color=Colors.WARNING
            ))
            return

        ignored_commands.remove(command)
        self._config.set('ignoredCommands', ignored_commands)

        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description=f"The command `/{command}` has been removed from the ignore list.",
            color=Colors.SUCCESS
        ))

    @config.command(name="bindChannel", brief="Configure a channel binding for the bot.")
    async def set_channel(self, ctx: commands.Context, name: str, channel: discord.TextChannel):
        """
        This command allows administrators to set a new channel binding for the bot. Multiple "critical" channels are
        stored in the bot configuration, including log and alert channels. This command allows them to be changed at
        runtime.

        To get a list of valid binding names, specify a junk binding (like ?) for the name parameter.

        The NAME parameter must be a valid channel binding, and the CHANNEL parameter must be a valid channel name/ID.

        Parameters
        ----------
            ctx      :: Discord context <!nodoc>
            name     :: The channel binding name to define
            channel  :: The channel to set binding to
        """
        name = name.upper()
        config = self._config.get('specialChannels', {})

        if name not in ChannelKeys.__members__:
            channel_names = []

            for ch in ChannelKeys:
                channel_names.append(ch.name)

            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="Valid channel names are: {}".format(''.join(f"\n- `{c}`" for c in channel_names)),
                color=Colors.PRIMARY
            ))
            return

        config[ChannelKeys[name].value] = channel.id

        self._config.set('specialChannels', config)

        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description=f"Channel value `{name}` has been set to {channel.mention}",
            color=Colors.SUCCESS
        ))

    @config.command(name="bindRole", brief="Configure a role binding for the bot.")
    async def set_role(self, ctx: commands.Context, name: str, role: discord.Role):
        """
        In order to track certain critical states, the bot requires an internal list of roles that must be maintained.
        This command allows these roles to be altered at runtime.

        To get a list of valid binding names, specify a junk binding (like ?) for the name parameter.

        The NAME parameter must be a valid role binding, and the ROLE parameter must be a valid role name/ID.

        Parameters
        ----------
            ctx      :: Discord context <!nodoc>
            name     :: The role binding name to define
            role     :: The role to bind to
        """
        name = name.upper()
        config = self._config.get('specialRoles', {})

        if name not in SpecialRoleKeys.__members__:
            special_roles = []

            for r in SpecialRoleKeys:
                special_roles.append(r.name)

            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="Valid role names are: \n- `" + "`\n- `".join(special_roles) + "`",
                color=Colors.PRIMARY
            ))
            return

        config[SpecialRoleKeys[name].value] = role.id

        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description=f"Role value `{name}` has been set to {role.mention}",
            color=Colors.SUCCESS
        ))

        self._config.set('specialRoles', config)

    @config.command(name="ignoreUser", brief="Block a user from interacting with the bot over messages.")
    async def block_user(self, ctx: commands.Context, user: HuskyConverters.OfflineUserConverter):
        """
        If a user is blocked through this method, the bot will ignore any and all messages from this user. This means
        that the target user will be unable to run commands (regardless of permissions). This will not affect censors
        and the like, but it will affect auto responses and command execution.

        Parameters
        ----------
            ctx   :: Discord context <!nodoc>
            user  :: The user to block from using the bot

        See Also
        --------
            /help config unblockUser  :: Unblock a user blocked by this command.
        """

        # hack for pycharm to stop complaining (duck-typing)
        user: discord.User = user

        config = self._config.get('userBlacklist', [])

        if user.id in config:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description=f"The user `{user}` is already ignored by the bot.",
                color=Colors.WARNING
            ))
            return

        if user.id in self.bot.superusers:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description=f"The user `{user}` is a superuser, and may not be ignored.",
                color=Colors.WARNING
            ))
            return

        config.append(user.id)

        self._config.set('userBlacklist', config)

        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description=f"The user `{user}` has been blacklisted by the bot.",
            color=Colors.SUCCESS
        ))

    @config.command(name="unignoreUser", brief="Unblock a blocked user from bot interactions.")
    async def unblock_user(self, ctx: commands.Context, user: HuskyConverters.OfflineUserConverter):
        """
        See /help config blockUser for more information about this command.

        Parameters
        ----------
            ctx   :: Discord context <!nodoc>
            user  :: The user to unblock from using the bot
        """

        # hack for pycharm to stop complaining (duck typing)
        user: discord.User = user

        config = self._config.get('userBlacklist', [])

        if user.id not in config:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description=f"The user `{user}` is not on the block list.",
                color=Colors.WARNING
            ))
            return

        config.remove(user.id)

        self._config.set('userBlacklist', config)

        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description=f"The user `{user}` has been removed from the blacklist.",
            color=Colors.SUCCESS
        ))

    @commands.group(name="system", pass_context=True, brief="Manage the bot itself", aliases=["admin"])
    @commands.has_permissions(administrator=True)
    async def system(self, ctx: discord.ext.commands.Context):
        """
        This command group contains primarily commands that will either get privileged system information (like logs) or
        take heavy actions on the bot itself.
        """

        pass

    @system.command(name="log", aliases=["logs"], brief="See the bot's current log.")
    async def log(self, ctx: discord.ext.commands.Context, lines: int = 10):
        """
        Extract a segment of the bot's current log file.

        This command takes an optional parameter (lines) which can be used to seek back in the bot's log file by a
        certain number of lines.

        This command has a limited output of 2000 characters, so the log may be trimmed. This allows for administrators
        to creatively abuse the lines function to get basic pagination.

        WARNING: The log command may reveal some sensitive information about bot execution!

        Parameters
        ----------
            ctx    :: Discord context <!nodoc>
            lines  :: The number of lines to pull from the log file.
        """

        log_file = self._session_store.get('logPath')

        if log_file is None:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="A log file was expected, but was not found or configured. This suggests a *serious* "
                            "problem with the bot.",
                color=Colors.DANGER
            ))
            return

        logs = HuskyUtils.tail(log_file, lines)

        log_title = f"**Log Entries from {log_file}**"
        log_data = HuskyUtils.trim_string(logs.replace('```', '`\u200b`\u200b`'), 2000 - (len(log_title) + 15), True)

        await ctx.send(log_title + "\n" + f"```{log_data}```")

    @system.command(name="restart", brief="Restart the bot.")
    async def restart(self, ctx: discord.ext.commands.Context):
        """
        Trigger a manual restart of the bot.

        This command triggers an immediate restart of the bot. This will attempt to gracefully kill the bot and then
        shut down. The bot will inform the channel upon restart.
        """
        await ctx.bot.change_presence(activity=discord.Activity(name="Restarting...", type=0),
                                      status=discord.Status.idle)
        LOG.info("Bot is going down for admin requested restart!")
        self._config.set("restartNotificationChannel", ctx.channel.id)
        self._config.set("restartReason", "admin")
        await ctx.trigger_typing()
        await ctx.bot.logout()

    @system.command(name="lockdown", brief="Toggle the bot's LOCKDOWN mode.")
    @HuskyChecks.is_superuser()
    async def lockdown(self, ctx: commands.Context, state: bool = None):
        """
        Control bot lockdown state.

        When the bot is in lockdown mode, no users outside of developers are permitted to execute any commands, nor
        will certain modules (like AutoResponder, if enabled) react to users.

        This command takes an optional argument, state. It may either be `true` or `false` to set a state manually, or
        no state to toggle.

        Parameters
        ----------
            ctx    :: Discord context <!nodoc>
            state  :: TRUE, FALSE, or blank to toggle
        """

        lockdown_state = self._session_store.get('lockdown', False)

        if state is None:
            lockdown_state = not lockdown_state
        else:
            lockdown_state = state

        if lockdown_state is False:
            st = "disabled"
        else:
            st = "enabled"

        self._session_store.set('lockdown', lockdown_state)

        await ctx.send(f"**Bot Lockdown State:** `{st}`")


def setup(bot: HuskyBot):
    bot.add_cog(BotAdmin(bot))
