import logging
import traceback

import discord
from discord.ext import commands

from libhusky.HuskyStatics import Colors
from libhusky.util import StringUtil, UtilClasses

LOG = logging.getLogger("HuskyBot.ErrorHandler")


# noinspection PyMethodMayBeStatic
class CommandErrorHandler(metaclass=UtilClasses.Singleton):
    def __init__(self):
        self.__errors = {
            commands.MissingPermissions: self.on_missing_permissions,
            commands.DisabledCommand: self.on_disabled_command,
            commands.CommandNotFound: self.on_command_not_found,
            commands.CheckFailure: self.on_check_failure,
            commands.MissingRequiredArgument: self.on_missing_argument,
            commands.BadArgument: self.on_bad_argument,
            commands.BotMissingPermissions: self.on_missing_permissions,
            commands.CommandOnCooldown: self.on_cooldown
        }

    async def handle_command_error(self, ctx, error):
        etx = {
            "prefix": ctx.bot.command_prefix,
            "cmd_name": StringUtil.trim_string(ctx.message.content.split(' ')[0][1:], 32, True, '...'),
            "err": StringUtil.trim_string(str(error).replace('```', '`\u200b`\u200b`'), 128)
        }
        etx['cmd'] = etx['prefix'] + etx['cmd_name']

        handler = self.__errors.get(error.__class__, self.on_generic_error)

        await handler(ctx, error, etx)

    async def on_generic_error(self, ctx: commands.Context, error: commands.MissingPermissions, etx: dict):
        await ctx.send(embed=discord.Embed(
            title="Bot Error Handler",
            description="The bot has encountered a fatal error running the command given. Logs are below.",
            color=Colors.DANGER
        ).add_field(name="Error Log", value="```" + etx['err'] + "```", inline=False))
        LOG.error("Error running command %s. See below for trace.\n%s",
                  ctx.message.content,
                  ''.join(traceback.format_exception(type(error), error, error.__traceback__)))

        # ToDo: Clean this up a bit more so these commands don't have hardcoded exemptions.
        if etx['cmd'].lower() in ["eval", "feval", "requestify"]:
            LOG.info(f"Suppressed critical error reporting for command {etx['cmd']}")
            return

        # Send it over to the main error logger as well.
        raise error

    async def on_missing_permissions(self, ctx: commands.Context, error: commands.MissingPermissions, etx: dict):
        if ctx.bot.developer_mode:
            await ctx.send(embed=discord.Embed(
                title="Command Handler",
                description=f"**You are not authorized to run `{etx['cmd']}`:**\n"
                            f"```{etx['err']}```\n\n"
                            f"Please ask a staff member for assistance.",
                color=Colors.DANGER
            ))

            LOG.error("Encountered permission error when attempting to run command %s: %s",
                      etx['cmd'], str(error))

    async def on_disabled_command(self, ctx: commands.Context, error: commands.DisabledCommand, etx: dict):
        if ctx.bot.developer_mode:
            embed = discord.Embed(
                title="Command Handler",
                description=f"**The command `{etx['cmd']}` is disabled.** See "
                            f"`{etx['prefix']}help` for valid commands.",
                color=Colors.DANGER
            )

            await ctx.send(embed=embed)

        LOG.error("Command %s is disabled.", etx['cmd'])

    async def on_command_not_found(self, ctx: commands.Context, error: commands.CommandNotFound, etx: dict):
        if ctx.bot.developer_mode:
            await ctx.send(embed=discord.Embed(
                title="Command Handler",
                description=f"**The command `{etx['cmd']}` does not exist.** See "
                            f"`{etx['prefix']}help` for valid commands.",
                color=Colors.DANGER
            ))

    async def on_check_failure(self, ctx: commands.Context, error: commands.CheckFailure, etx: dict):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description=f"**The command `{etx['cmd']}` failed an execution check.** Additional "
                        f"information may be provided below.",
            color=Colors.DANGER
        ).add_field(name="Error Log", value="```" + etx['err'] + "```", inline=False))

        LOG.error("Encountered check failure when attempting to run command %s: %s",
                  etx['cmd'], str(error))

    async def on_private_message(self, ctx: commands.Context, error: commands.CommandNotFound, etx: dict):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description=f"**The command `{etx['cmd']}` may not be run in a DM.** See `{{etx['prefix']}}help` for valid "
                        f"commands.",
            color=Colors.DANGER
        ))

        LOG.error("Command %s may not be run in a direct message!", etx['cmd'])

    async def on_missing_argument(self, ctx: commands.Context, error: commands.MissingRequiredArgument, etx: dict):
        embed = discord.Embed(
            title="Command Handler",
            description=f"**The command `{etx['cmd']}` could not run, because it is missing arguments.**\n"
                        f"See `{etx['prefix']}help {etx['cmd_name']}` for the arguments required.",
            color=Colors.DANGER
        )

        embed.add_field(name="Missing Parameter", value="`" + etx['err'].split(" ")[0] + "`", inline=True)

        await ctx.send(embed=embed)
        LOG.error("Command %s was called with the wrong parameters.", etx['cmd'])

    async def on_bad_argument(self, ctx: commands.Context, error: commands.BadArgument, etx: dict):
        embed = discord.Embed(
            title="Command Handler",
            description=f"**The command `{etx['cmd']}` could not understand the arguments given.**\n"
                        f"See `{etx['prefix']}help {etx['cmd_name']}` and the error below to fix this issue.",
            color=Colors.DANGER
        )

        embed.add_field(name="Error Log", value="```" + etx['err'] + "```", inline=False)

        await ctx.send(embed=embed)
        LOG.error("Command %s was unable to parse arguments: %s", etx['cmd'], str(error))
        # LOG.error(''.join(traceback.format_exception(type(error), error, error.__traceback__)))

    async def on_bot_missing_perms(self, ctx: commands.Context, error: commands.BotMissingPermissions, etx: dict):
        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description=f"**The command `{etx['cmd']}` could not execute successfully, as the bot does not "
                        f"have a required permission.**\nPlease make sure that the bot has the following "
                        f"permissions: " +
                        "`{}`".format(', '.join(error.missing_perms)),
            color=Colors.DANGER
        ))

        LOG.error("Bot is missing permissions %s to execute command %s", error.missing_perms, etx['cmd'])

    async def on_cooldown(self, ctx: commands.Context, error: commands.CommandOnCooldown, etx: dict):
        seconds = round(error.retry_after)
        tx = "{} {}".format(seconds, "second" if seconds == 1 else "seconds")

        await ctx.send(embed=discord.Embed(
            title="Command Handler",
            description=f"**The command `{etx['cmd']}` has been run too much recently!**\n"
                        f"Please wait **{tx}** until trying again.",
            color=Colors.DANGER
        ))

        LOG.error("Command %s was on cooldown, and is unable to be run for %s seconds. Cooldown: %s",
                  etx['cmd'], round(error.retry_after, 0), error.cooldown)
