import logging
import socket

import discord
import git
from discord.ext import commands

from BotCore import get_developers
from WolfBot import WolfChecks
from WolfBot import WolfConfig
from WolfBot import WolfConverters
from WolfBot import WolfUtils
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class BotAdmin:
    """
    The BotAdmin plugin is a mandatory plugin that's required for the bot to operate normally.

    It provides core administrative functions to bot administrators to change configurations and other important values.
    """
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()
        self._session_store = WolfConfig.get_session_store()
        self._debugmode = self._config.get("developerMode", False)
        LOG.info("Loaded plugin!")

    @commands.command(name="about", aliases=["version"], brief="Get basic information about the bot.")
    async def about(self, ctx: discord.ext.commands.Context):
        """
        Get basic information about the current running instance of this bot.

        This command returns a quick summary of this bot and its current state.
        """

        repo = git.Repo(search_parent_directories=True)
        sha = repo.head.object.hexsha

        embed = discord.Embed(
            title="DakotaBot" + (" [DEBUG MODE]" if self._debugmode else ""),
            description="This is DakotaBot, a fork of the WolfBot core Discord bot platform. It is responsible for "
                        "managing and assisting the moderators on the DIY Tech subreddit.",
            color=Colors.INFO
        )

        embed.add_field(name="Authors", value="KazWolfe, Clover", inline=False)
        embed.add_field(name="Bot Version", value="[`{}`]({}/commit/{})".format(sha[:8], GIT_URL, sha), inline=True)
        embed.add_field(name="Library Version", value=discord.__version__, inline=True)
        embed.add_field(name="Current Host", value="`{}`".format(socket.gethostname()), inline=True)
        embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/" + str(ctx.bot.user.id) + "/"
                                + str(ctx.bot.user.avatar) + ".png")
        embed.set_footer(text="(c) 2018, KazWolfe | Rooooooo!",
                         icon_url="https://avatars3.githubusercontent.com/u/5192145")

        await ctx.send(embed=embed)

    @commands.group(pass_context=True, brief="Administrative bot control commands.")
    @commands.has_permissions(administrator=True)
    async def admin(self, ctx: discord.ext.commands.Context):
        """
        Parent command for the BotAdmin module.

        This command does nothing, but it instead acts as the parent to all other commands.
        """

        pass

    @admin.command(name="reloadConfig", brief="Reload the bot's configuration files from disk.")
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

    @admin.command(name="load", brief="Temporarily load a plugin into the bot.")
    async def load(self, ctx: discord.ext.commands.Context, plugin_name: str):
        """
        Load a plugin (temporarily) into the bot.

        This command will attempt to load the named plugin into the bot's runtime. It will not mark this command as
        enabled, nor will it allow the plugin to relaunch on start.

        Plugin names are case sensitive, and almost always start with a capital letter.

        See also:
            /help admin unload   - Temporarily unload a plugin from the bot.
            /help admin reload   - Unload and reload a plugin from the bot.
            /help admin enable   - Permanently enable a plugin (load + run on start)
            /help admin disable  - Permanently disable a plugin (unload + disallow startup execution)
        """

        if plugin_name in ctx.bot.cogs.keys():
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The plugin `" + plugin_name
                            + "` could not be loaded, as it is already loaded.",
                color=Colors.WARNING
            ))
            LOG.warning("Attempted to unload already-unloaded plugin %s", plugin_name)
            return

        try:
            self.bot.load_extension(plugin_name)
        except (AttributeError, ImportError) as e:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The plugin `" + plugin_name
                            + "` has failed to load. The following "
                            + "error is available:\n ```{}: {}```".format(type(e).__name__, str(e)),
                color=Colors.DANGER
            ))
            LOG.error("Could not load plugin %s. Error: %s", plugin_name, e)
            return

        LOG.info("Loaded plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description="The plugin `" + plugin_name + "` has been loaded.",
            color=Colors.INFO
        ))

    @admin.command(name="unload", brief="Temporarily unload a plugin from the bot.")
    async def unload(self, ctx: discord.ext.commands.Context, plugin_name: str):
        """
        (Temporarily) unload a plugin from the bot.

        This command will attempt to unload non-critical plugin from the bot. It will not disable a plugin, and will
        only last until the bot is restarted.

        Plugin names are case sensitive, and almost always start with a capital letter.

        See also:
            /help admin unload   - Temporarily unload a plugin from the bot.
            /help admin reload   - Unload and reload a plugin from the bot.
            /help admin enable   - Permanently enable a plugin (load + run on start)
            /help admin disable  - Permanently disable a plugin (unload + disallow startup execution)
        """

        if plugin_name == "BotAdmin":
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The plugin `" + plugin_name
                            + "` could not be unloaded, as it is a critical module. ",
                color=Colors.DANGER
            ))
            LOG.warning("A request was made to unload BotAdmin. Blocked.")
            return

        if plugin_name == "Debug" and self._debugmode:
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
                description="The plugin `" + plugin_name
                            + "` could not be unloaded, as it is not loaded. Plugin names are case-sensitive.",
                color=Colors.WARNING
            ))
            LOG.warning("Attempted to unload already-unloaded plugin %s", plugin_name)
            return

        """Unloads an extension."""
        self.bot.unload_extension(plugin_name)
        LOG.info("Unloaded plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description="The plugin `" + plugin_name + "` has been unloaded.",
            color=Colors.INFO
        ))

    @admin.command(name="reload", brief="Unload and reload a plugin.")
    async def reload(self, ctx: discord.ext.commands.Context, plugin_name: str):
        """
        Unload and reload a plugin from the bot.

        This will not enable or disable a command, but it will cause the plugin to re-initialize and reload. This may
        wipe out configurations/timings for certain plugins, depending on how they save information.

        This command will also cause that plugin's code to be reloaded, allowing dynamic re-execution of code. Note that
        it will *not* reload imports of the plugin, so a full restart may be required to swap in other code.

        The reload command *will* work with critical modules.

        Plugin names are case sensitive, and almost always start with a capital letter.

        See also:
            /help admin load     - Temporarily load a plugin from the bot.
            /help admin unload   - Temporarily unload a plugin from the bot.
            /help admin enable   - Permanently enable a plugin (load + run on start)
            /help admin disable  - Permanently disable a plugin (unload + disallow startup execution)
        """

        self.bot.unload_extension(plugin_name)
        LOG.info("Unloaded plugin %s for reload.", plugin_name)
        try:
            self.bot.load_extension(plugin_name)
        except (AttributeError, ImportError) as e:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The plugin `" + plugin_name
                            + "` has failed to reload. The following "
                            + "error is available:\n ```{}: {}```".format(type(e).__name__, str(e)),
                color=Colors.DANGER
            ))
            LOG.error("Could not reload plugin %s. Error: %s", plugin_name, e)
            return
        LOG.info("Reloaded plugin %s", plugin_name)
        await ctx.send(embed=discord.Embed(
            title="Plugin Manager",
            description="The plugin `" + plugin_name + "` has been reloaded.",
            color=Colors.INFO
        ))

    @admin.command(name="enable", brief="Enable a plugin to run now and at bot load.")
    async def enable(self, ctx: discord.ext.commands.Context, plugin_name: str):
        """
        Load a plugin into the bot, and mark it as auto-load.

        This command will attempt to load a plugin into the bot, and then mark it for automatic load on bot start. This
        should be used when a plugin is desired to permanently run alongside the bot.

        Plugin names are case sensitive, and almost always start with a capital letter.

        See also:
            /help admin load     - Temporarily load a plugin from the bot.
            /help admin unload   - Temporarily unload a plugin from the bot.
            /help admin reload   - Unload and reload a plugin from the bot.
            /help admin disable  - Permanently disable a plugin (unload + disallow startup execution)
        """
        config = self._config.get('plugins', [])

        if plugin_name in config:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The plugin `" + plugin_name
                            + "` is already enabled. If it is not loaded, use `/admin load " + plugin_name + "`.",
                color=Colors.WARNING
            ))
            return

        try:
            self.bot.load_extension(plugin_name)
        except (AttributeError, ImportError) as e:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The plugin `" + plugin_name + "` has failed to enable. The following error is "
                            + "available:\n ```{}: {}```".format(type(e).__name__, str(e)),
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
            description="The plugin `" + plugin_name + "` has been enabled and will run automatically.",
            color=Colors.SUCCESS
        ))

    @admin.command(name="disable", brief="Disable a plugin from running at bot load. Also stops the plugin.")
    async def disable(self, ctx: discord.ext.commands.Context, plugin_name: str):
        """
        Unload a plugin from the bot, and prevent it from auto-loading

        This command will unload a currently active plugin, and additionally mark it as "disabled", preventing it from
        automatically executing at bot startup. The plugin may still be manually loaded using /admin load.

        Plugin names are case sensitive, and almost always start with a capital letter.

        See also:
            /help admin load     - Temporarily load a plugin from the bot.
            /help admin unload   - Temporarily unload a plugin from the bot.
            /help admin reload   - Unload and reload a plugin from the bot.
            /help admin enable   - Permanently enable a plugin (load + run on start)
        """
        if plugin_name == "BotAdmin":
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The plugin `" + plugin_name
                            + "` could not be disabled, as it is a critical module. ",
                color=Colors.DANGER
            ))
            LOG.warning("The BotAdmin module was requested to be disabled.")
            return

        if plugin_name == "Debug" and self._debugmode:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The `Debug` plugin may not be disabled while Developer Mode is enabled."
                            "\nPlease disable Developer Mode first.",
                color=Colors.DANGER
            ))
            LOG.warning("A request was made to disable Debug while in DevMode. Blocked.")
            return

        config = self._config.get('plugins', [])

        if plugin_name not in config:
            await ctx.send(embed=discord.Embed(
                title="Plugin Manager",
                description="The plugin `" + plugin_name + "` is already disabled.",
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
            description="The plugin `" + plugin_name + "` has been disabled and will no longer run automatically.",
            color=Colors.WARNING
        ))

    @admin.command(name="log", aliases=["logs"], brief="See the bot's current log.")
    async def log(self, ctx: discord.ext.commands.Context, lines: int = 10):
        """
        Extract a segment of the bot's current log file.

        This command takes an optional parameter (lines) which can be used to seek back in the bot's log file by a
        certain number of lines.

        This command has a limited output of 2000 characters, so the log may be trimmed. This allows for administrators
        to creatively abuse the lines function to get basic pagination.

        WARNING: The log command may reveal some sensitive information about bot execution!
        """

        log_file = self._session_store.get('logPath')

        if log_file is None:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="A log file was expected, but was not found or configured. This suggests a *serious* "
                            + "problem with the bot.",
                color=Colors.DANGER
            ))
            return

        logs = WolfUtils.tail(log_file, lines)

        await ctx.send(embed=discord.Embed(
            title="Log Entries from " + log_file,
            description="```" + WolfUtils.trim_string(logs, 2042, True) + "```",
            color=Colors.SECONDARY
        ))

    @admin.command(name="presence", brief="Set the bot's presence mode.")
    async def presence(self, ctx: discord.ext.commands.Context, presence_type: str, name: str, status: str):
        """
        Set a new Presence for the bot.

        The bot has a user-definable presence used to provide status messages or other information. This may be
        configured on-the-fly using this command.

        This command takes three arguments: the Presence Type, the Name, and a Status.

        Presence Type must be a string containing either PLAYING, LISTENING, or WATCHING. No other arguments are
        permitted at this time.

        The Name may be any (short) string that will be displayed after the presence type.

        Status must be a strong containing either ONLINE, IDLE, or DND. No other arguments are permitted.
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

    @admin.command(name="reloadpresence", brief="Reload a Presence from the config file", aliases=["rpresence"])
    async def reload_presence(self, ctx: discord.ext.commands.Context):
        """
        Debug commands have no help. If you need help running a debug command, just don't.
        """
        bot_presence = self._config.get('presence', {"game": "DakotaBot", "type": 2, "status": "dnd"})

        await ctx.bot.change_presence(activity=discord.Activity(name=bot_presence['game'], type=bot_presence['type']),
                                      status=discord.Status[bot_presence['status']])

    @admin.command(name="restart", brief="Restart the bot.")
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

    @admin.command(name="ignoreCommand", brief="Add a command to the ignore list.", enabled=False)
    async def ignore(self, ctx: commands.Context, command: str):
        """
        [DEPRECATED COMMAND] Add a new command to the ignore list.

        This command will allow administrators to add commands that are silently ignored by the bot. This command takes
        only a single string as an argument. Do not include a slash when specifying a command name to ignore.

        See also:
            /help admin unignoreCommand - Remove a command from the ignore list
        """
        command = command.lower()

        ignoredCommands = self._config.get('ignoredCommands', [])

        if ctx.bot.get_command(command) is not None:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="Real commands may not be added to the ignore list!",
                color=Colors.DANGER
            ))
            return

        if command in ignoredCommands:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The command `/" + command + "` is already being ignored.",
                color=Colors.WARNING
            ))
            return

        ignoredCommands.append(command)
        self._config.set('ignoredCommands', ignoredCommands)

        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description="The command `/" + command + "` has been added to the ignore list.",
            color=Colors.SUCCESS
        ))

    @admin.command(name="unignoreCommand", brief="Remove a command from the ignore list.", enabled=False)
    async def unignore(self, ctx: commands.Context, command: str):
        """
        [DEPRECATED COMMAND] Remove a command from the ignore list.

        If a command was previously ignored by /admin ignoreCommand, this command will allow the command to be watched
        again.

        See /help admin ignoreCommand for information about the arguments for this command.

        See also:
            /help admin ignoreCommand - Add a command to the ignore list
        """
        command = command.lower()

        ignoredCommands = self._config.get('ignoredCommands', [])

        if command not in ignoredCommands:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The command `/" + command + "` is already being accepted.",
                color=Colors.WARNING
            ))
            return

        ignoredCommands.remove(command)
        self._config.set('ignoredCommands', ignoredCommands)

        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description="The command `/" + command + "` has been removed from the ignore list.",
            color=Colors.SUCCESS
        ))

    @admin.command(name="setChannel", brief="Configure a channel binding for the bot.")
    async def set_channel(self, ctx: commands.Context, name: str, channel: discord.TextChannel):
        """
        Set a channel binding for the bot.

        This command allows administrators to set a new channel binding for the bot. Multiple "critical" channels are
        stored in the bot configuration, including log and alert channels. This command allows them to be changed at
        runtime.

        To get a list of valid binding names, specify a junk binding (like ?) for the name parameter.

        The NAME parameter must be a valid channel binding, and the CHANNEL parameter must be a valid channel name/ID.
        """
        name = name.upper()
        config = self._config.get('specialChannels', {})

        if name not in ChannelKeys.__members__:
            channelNames = []

            for ch in ChannelKeys:
                channelNames.append(ch.name)

            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="Valid channel names are: \n- `" + "`\n- `".join(channelNames) + "`",
                color=Colors.PRIMARY
            ))
            return

        config[ChannelKeys[name].value] = channel.id

        self._config.set('specialChannels', config)

        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description="Channel value `{}` has been set to {}".format(name, channel.mention),
            color=Colors.SUCCESS
        ))

    @admin.command(name="setRole", brief="Configure a role binding for the bot.")
    async def set_role(self, ctx: commands.Context, name: str, role: discord.Role):
        """
        Set a role binding for the bot.

        In order to track certain critical states, the bot requires an internal list of roles that must be maintained.
        This command allows these roles to be altered at runtime.

        To get a list of valid binding names, specify a junk binding (like ?) for the name parameter.

        The NAME parameter must be a valid role binding, and the ROLE parameter must be a valid role name/ID.
        """
        name = name.upper()
        config = self._config.get('specialRoles', {})

        if name not in SpecialRoleKeys.__members__:
            specialRoles = []

            for r in SpecialRoleKeys:
                specialRoles.append(r.name)

            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="Valid role names are: \n- `" + "`\n- `".join(specialRoles) + "`",
                color=Colors.PRIMARY
            ))
            return

        config[SpecialRoleKeys[name].value] = role.id

        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description="Role value `{}` has been set to {}".format(name, role.mention),
            color=Colors.SUCCESS
        ))

        self._config.set('specialRoles', config)

    @admin.command(name="blockUser", brief="Block a user from interacting with the bot over messages.")
    async def block_user(self, ctx: commands.Context, user: WolfConverters.OfflineUserConverter):
        """
        Block a user from interacting with the bot.

        If a user is blocked through this method, the bot will ignore any and all messages from this user. This means
        that the target user will be unable to run commands (regardless of permissions). This will not affect censors
        and the like, but it will affect auto responses and command execution.

        See also:
            /help admin unblockUser - Unblock a user blocked by this command.
        """

        # hack for pycharm to stop complaining (duck-typing)
        user = user  # type: discord.User

        config = self._config.get('userBlacklist', [])

        if user.id in config:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The user `{}` is already ignored by the bot.".format(user),
                color=Colors.WARNING
            ))
            return

        if user.id in get_developers():
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The user `{}` is a bot developer, and may not be ignored.".format(user),
                color=Colors.WARNING
            ))
            return

        config.append(user.id)

        self._config.set('userBlacklist', config)

        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description="The user `{}` has been blacklisted by the bot.".format(user),
            color=Colors.SUCCESS
        ))

    @admin.command(name="unblockUser", brief="Unblock a blocked user from bot interactions.")
    async def unblock_user(self, ctx: commands.Context, user: WolfConverters.OfflineUserConverter):
        """
        Unblock a user blocked from interacting with the bot.

        See /help admin blockUser for more information about this command.
        """

        # hack for pycharm to stop complaining (duck typing)
        user = user  # type: discord.User

        config = self._config.get('userBlacklist', [])

        if user.id not in config:
            await ctx.send(embed=discord.Embed(
                title="Bot Manager",
                description="The user `{}` is not on the block list..".format(user),
                color=Colors.WARNING
            ))
            return

        config.remove(user.id)

        self._config.set('userBlacklist', config)

        await ctx.send(embed=discord.Embed(
            title="Bot Manager",
            description="The user `{}` has been removed from the blacklist.".format(user),
            color=Colors.SUCCESS
        ))

    @admin.command(name="lockdown", brief="Toggle the bot's LOCKDOWN mode.")
    @WolfChecks.is_developer()
    async def lockdown(self, ctx: commands.Context, state: bool = None):
        """
        Control bot lockdown state.

        When the bot is in lockdown mode, no users outside of developers are permitted to execute any commands, nor
        will certain modules (like AutoResponder, if enabled) react to users.

        This command takes an optional argument, state. It may either be `true` or `false` to set a state manually, or
        no state to toggle.
        """

        lockdown_state = self._config.get('lockdown', False)

        if state is None:
            lockdown_state = not lockdown_state
        else:
            lockdown_state = state

        if lockdown_state is False:
            st = "disabled"
        else:
            st = "enabled"

        self._config.set('lockdown', lockdown_state)

        await ctx.send("**Bot Lockdown State:** `{}`".format(st))


def setup(bot: commands.Bot):
    bot.add_cog(BotAdmin(bot))
