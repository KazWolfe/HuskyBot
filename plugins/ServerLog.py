import logging

import discord
from discord.ext import commands

from HuskyBot import HuskyBot
from libhusky import HuskyUtils
from libhusky.HuskyStatics import *

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


class ServerLog:
    """
    The ServerLog plugin exists to provide a clean and transparent method of tracking server activity on the bot.
    """

    def __init__(self, bot: HuskyBot):
        self.bot = bot
        self._config = bot.config
        self._session_store = self.bot.session_store

        LOG.info("Loaded plugin!")

        # ToDo: Find a better way of storing valid loggers.
        self._validLoggers = ["userJoin", "userJoin.milestones", "userJoin.audit",
                              "userLeave",
                              "userBan",
                              "userRename",
                              "messageDelete", "messageDelete.logIntegrity",
                              "messageEdit"]

    async def on_member_join(self, member: discord.Member):
        # Send milestones to the moderator alerts channel
        async def milestone_notifier():
            if "userJoin.milestones" not in self._config.get("loggers", {}).keys():
                return

            milestone_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_ALERTS.value, None)
            guild = member.guild

            if milestone_channel is None:
                return

            milestone_channel = guild.get_channel(milestone_channel)

            if guild.member_count % 1000 == 0:
                await milestone_channel.send(embed=discord.Embed(
                    title=Emojis.PARTY + " Guild Member Count Milestone!",
                    description=f"The guild has now reached {guild.member_count} members! Thank you "
                                f"{member.mention} for joining!",
                    color=Colors.SUCCESS
                ))

        # Send all joins to the logging channel
        async def general_notifier():
            if "userJoin" not in self._config.get("loggers", {}).keys():
                return

            channel = self._config.get('specialChannels', {}).get(ChannelKeys.USER_LOG.value, None)

            if channel is None:
                return

            channel = member.guild.get_channel(channel)

            embed = discord.Embed(
                title=Emojis.SUNRISE + " New Member!",
                description=f"{member} has joined the guild.",
                color=Colors.PRIMARY
            )

            embed.set_thumbnail(url=member.avatar_url)
            embed.add_field(name="Joined Discord", value=member.created_at.strftime(DATETIME_FORMAT), inline=True)
            embed.add_field(name="Joined Guild", value=member.joined_at.strftime(DATETIME_FORMAT), inline=True)
            embed.add_field(name="User ID", value=member.id, inline=True)

            member_num = sorted(member.guild.members, key=lambda m: m.joined_at).index(member) + 1
            embed.set_footer(text=f"Member #{member_num} on the guild")

            LOG.info(f"User {member} ({member.id}) has joined {member.guild.name}.")
            await channel.send(embed=embed)

        await milestone_notifier()
        await general_notifier()

    async def on_member_remove(self, member: discord.Member):
        if "userLeave" not in self._config.get("loggers", {}).keys():
            return

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.USER_LOG.value, None)

        if alert_channel is None:
            return

        alert_channel = member.guild.get_channel(alert_channel)

        embed = discord.Embed(
            title=Emojis.DOOR + " Member left the guild",
            description=f"{member} has left the guild.",
            color=Colors.PRIMARY
        )

        embed.set_thumbnail(url=member.avatar_url)
        embed.add_field(name="User ID", value=member.id)
        embed.add_field(name="Leave Timestamp", value=HuskyUtils.get_timestamp())

        LOG.info(f"User {member} has left {member.guild.name}.")
        await alert_channel.send(embed=embed)

    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        if "userBan" not in self._config.get("loggers", {}).keys():
            return

        logger_ignores: dict = self._session_store.get('loggerIgnores', {})
        ignored_bans = logger_ignores.setdefault('ban', [])

        if user.id in ignored_bans:
            return

        # Get timestamp as soon as the event is fired, because waiting for bans may take a while.
        timestamp = HuskyUtils.get_timestamp()

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

        if alert_channel is None:
            return

        alert_channel = self.bot.get_channel(alert_channel)

        embed = discord.Embed(
            title=Emojis.BAN + " User banned",
            description=f"{user} was banned from the guild.",
            color=Colors.DANGER
        )

        ban_entry = discord.utils.get(await guild.bans(), user=user)

        if ban_entry is None:
            raise ValueError(f"A ban record for user {user.id} was expected, but no entry was found")

        ban_reason = ban_entry.reason

        if ban_reason is None:
            ban_reason = "<No ban reason provided>"

        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name="User ID", value=user.id, inline=True)
        embed.add_field(name="Ban Timestamp", value=timestamp, inline=True)
        embed.add_field(name="Ban Reason", value=ban_reason, inline=False)

        LOG.info(f"User {user} was banned from {guild.name} for '{ban_reason}'.")
        await alert_channel.send(embed=embed)

    # noinspection PyUnusedLocal
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        if "userBan" not in self._config.get("loggers", {}).keys():
            return

        logger_ignores: dict = self._session_store.get('loggerIgnores', {})
        ignored_bans = logger_ignores.setdefault('ban', [])

        if user.id in ignored_bans:
            return

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

        if alert_channel is None:
            return

        alert_channel = self.bot.get_channel(alert_channel)

        embed = discord.Embed(
            title=Emojis.UNBAN + " User unbanned",
            description=f"{user} was unbanned from the guild.",
            color=Colors.PRIMARY
        )

        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name="User ID", value=user.id)
        embed.add_field(name="Unban Timestamp", value=HuskyUtils.get_timestamp())

        LOG.info(f"User {user} was unbanned from {guild.name}.")
        await alert_channel.send(embed=embed)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if "userRename" not in self._config.get("loggers", {}).keys():
            return

        logger_ignores: dict = self._session_store.get('loggerIgnores', {})
        ignored_nicks = logger_ignores.setdefault('nickname', [])

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.USER_LOG.value, None)

        if alert_channel is None:
            return

        alert_channel = self.bot.get_channel(alert_channel)

        if before.nick == after.nick and before.name == after.name:
            return

        if before.nick != after.nick:
            update_type = 'nickname'
            old_val = before.nick
            new_val = after.nick

            if before.id in ignored_nicks:
                return

        elif before.name != after.name:
            update_type = 'username'
            old_val = before.name
            new_val = after.name
        else:
            return

        embed = discord.Embed(
            description=f"User's {update_type} has been changed. Information below.",
            color=Colors.INFO
        )

        embed.add_field(name=f"Old {update_type.capitalize()}", value=old_val, inline=True)
        embed.add_field(name=f"New {update_type.capitalize()}", value=new_val, inline=True)
        embed.add_field(name="Display Name", value=HuskyUtils.escape_markdown(after.display_name), inline=True)
        embed.add_field(name="User ID", value=after.id, inline=True)
        embed.set_author(name=f"{after}'s {update_type} has changed!", icon_url=after.avatar_url)

        await alert_channel.send(embed=embed)

    async def on_message_delete(self, message: discord.Message):
        logger_config = self._config.get("loggers", {})

        if message.guild is None:
            return

        if "messageDelete" not in logger_config.keys():
            return

        if message.channel.id in logger_config.get('__global__', {}).get("ignoredChannels", []):
            return

        server_log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, -1)
        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.MESSAGE_LOG.value, None)

        if alert_channel is None:
            return

        alert_channel = message.guild.get_channel(alert_channel)

        # Allow event cleanups for bot users.
        if (message.channel.id in [alert_channel.id, server_log_channel]) and message.author.bot:
            return

        embed = discord.Embed(
            color=Colors.WARNING
        )

        embed.set_author(name=f"Deleted Message in #{message.channel.name}", icon_url=message.author.avatar_url)
        embed.add_field(name="Author", value=message.author, inline=True)
        embed.add_field(name="Message ID", value=message.id, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Send Timestamp", value=message.created_at.strftime(DATETIME_FORMAT), inline=True)
        embed.add_field(name="Delete Timestamp", value=HuskyUtils.get_timestamp(), inline=True)

        if message.content is not None and message.content != "":
            embed.add_field(name="Message", value=HuskyUtils.trim_string(message.content, 1000, True), inline=False)

        if message.attachments is not None and len(message.attachments) > 1:
            attachments_list = str(f"- {a.url}\n" for a in message.attachments)
            embed.add_field(name="Attachments",
                            value=HuskyUtils.trim_string(attachments_list, 1000, True),
                            inline=False)
        elif message.attachments is not None and len(message.attachments) == 1:
            embed.add_field(name="Attachment URL", value=message.attachments[0].url, inline=False)
            embed.set_image(url=message.attachments[0].proxy_url)

        await alert_channel.send(embed=embed)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        logger_config = self._config.get('loggers', {})

        if after.guild is None:
            return

        if "messageEdit" not in logger_config.keys():
            return

        if after.channel.id in logger_config.get('__global__', {}).get("ignoredChannels", []):
            return

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.MESSAGE_LOG.value, None)

        if alert_channel is None:
            return

        alert_channel = after.guild.get_channel(alert_channel)

        if after.channel == alert_channel and after.author.bot:
            return

        if before.content is None or after.content is None:
            return

        if before.content == after.content:
            return

        embed = discord.Embed(
            color=Colors.PRIMARY
        )

        embed.set_author(name="Message edited", icon_url=after.author.avatar_url)
        embed.add_field(name="Author", value=after.author, inline=True)
        embed.add_field(name="Message ID", value=after.id, inline=True)
        embed.add_field(name="Channel", value=after.channel.mention, inline=True)
        embed.add_field(name="Send Timestamp", value=before.created_at.strftime(DATETIME_FORMAT), inline=True)
        embed.add_field(name="Edit Timestamp", value=after.edited_at.strftime(DATETIME_FORMAT), inline=True)

        if before.content is not None and before.content != "":
            embed.add_field(name="Message Before", value=HuskyUtils.trim_string(before.content, 1000, True),
                            inline=False)
        else:
            embed.add_field(name="Message Before", value="`<No Content>`", inline=False)

        if after.content is not None and after.content != "":
            embed.add_field(name="Message After", value=HuskyUtils.trim_string(after.content, 1000, True), inline=False)
        else:
            embed.add_field(name="Message After", value="`<No Content>`", inline=False)

        await alert_channel.send(embed=embed)

    @commands.group(name="logger", aliases=["logging"], brief="Parent command to manage the ServerLog module")
    @commands.has_permissions(administrator=True)
    async def logger(self, ctx: discord.ext.commands.Context):
        """
        This command itself does nothing, but is instead a parent command.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=discord.Embed(
                title="Logging Manager",
                description="The command you have requested is not available. Please see `/help logger`",
                color=Colors.DANGER
            ))
            return

    @logger.command(name="enable", brief="Enable a specified logger")
    async def enable_logger(self, ctx: commands.Context, name: str):
        """
        This command takes a single logger name as an argument, and adds it to the enabled loggers list. Changes to
        loggers take effect immediately.

        Parameters
        ----------
            ctx   :: Discord context <!nodoc>
            name  :: The name of a logger to enable.
        """
        enabled_loggers = self._config.get('loggers', {})

        if name not in self._validLoggers:
            await ctx.send(embed=discord.Embed(
                title="Logging Manager",
                description=f"The logger named `{name}` is not recognized as a valid logger.",
                color=Colors.DANGER
            ))
            return

        if name in enabled_loggers.keys():
            await ctx.send(embed=discord.Embed(
                title="Logging Manager",
                description=f"The logger named `{name}` is already enabled.",
                color=Colors.WARNING
            ))
            return

        enabled_loggers[name] = {}

        self._config.set('loggers', enabled_loggers)

        await ctx.send(embed=discord.Embed(
            title="Logging Manager",
            description=f"The logger named `{name}` was enabled.",
            color=Colors.SUCCESS
        ))

    @logger.command(name="disable", brief="Disable a specified logger")
    async def disable_logger(self, ctx: commands.Context, name: str):
        """
        This command takes a single logger name as an argument, and adds it to the enabled loggers list. Changes to
        loggers take effect immediately.

        Parameters
        ----------
            ctx   :: Discord context <!nodoc>
            name  :: The name of a logger to disable.
        """
        enabled_loggers = self._config.get('loggers', {})

        if name not in self._validLoggers:
            await ctx.send(embed=discord.Embed(
                title="Logging Manager",
                description=f"The logger named `{name}` is not recognized as a valid logger.",
                color=Colors.DANGER
            ))
            return

        if name not in enabled_loggers.keys():
            await ctx.send(embed=discord.Embed(
                title="Logging Manager",
                description=f"The logger named `{name}` is already disabled.",
                color=Colors.WARNING
            ))
            return

        enabled_loggers.pop(name)

        self._config.set('loggers', enabled_loggers)

        await ctx.send(embed=discord.Embed(
            title="Logging Manager",
            description=f"The logger named `{name}` was disabled.",
            color=Colors.SUCCESS
        ))

    @logger.command(name="rotate", brief="Rotate the log channel out for a new clean one")
    @commands.has_permissions(administrator=True)
    async def rotate_logs(self, ctx: commands.Context):
        """
        This command will create a new server log channel, configure it the same as the old channel, and then delete
        the old channel. By doing this, server logs can be effectively rotated and all staff-accessible records of
        messages kept in the server log will be wiped.

        The user who started the rotation will be logged in both the audit log, and at the start of the rotation.

        This command takes no arguments, and may only be run by administrators.
        """
        channels_config = self._config.get('specialChannels', {})
        old_channel = channels_config.get(ChannelKeys.MESSAGE_LOG.value, None)

        if old_channel is not None:
            old_channel: discord.TextChannel = ctx.guild.get_channel(old_channel)

        if old_channel is None:
            await ctx.send(embed=discord.Embed(
                title="Logging Manager",
                description="No logging channel has been configured, so it can't be rotated.",
                color=Colors.DANGER
            ))
            return

        topic_string = f"Staff server logs, starting at {ctx.message.created_at.strftime(DATETIME_FORMAT)}"
        reason_string = f"Log rotation requested by {ctx.author}."

        new_channel: discord.TextChannel = await ctx.guild.create_text_channel(
            name=old_channel.name,
            overwrites=dict(old_channel.overwrites),
            category=old_channel.category,
            reason=reason_string
        )

        await new_channel.edit(
            reason=reason_string,
            position=old_channel.position,
            topic=topic_string,
            nsfw=old_channel.nsfw
        )

        channels_config[ChannelKeys.MESSAGE_LOG.value] = new_channel.id
        self._config.set('specialChannels', channels_config)

        await old_channel.delete(reason=reason_string)

        log_embed = discord.Embed(
            title=Emojis.REFRESH + " Server log refresh!",
            description=f"A message log refresh was executed at {ctx.message.created_at.strftime(DATETIME_FORMAT)}, "
                        f"and was requested by {ctx.message.author}.",
            color=Colors.INFO
        )

        await new_channel.send(embed=log_embed)

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

        if alert_channel is not None:
            alert_channel = ctx.message.guild.get_channel(alert_channel)
            await alert_channel.send(embed=log_embed)

        await ctx.send(embed=discord.Embed(
            title="Log refresh success!",
            description=f"The server logs were successfully refreshed, and are now available at {new_channel.mention}. "
                        f"The bot's config has been automatically updated.",
            color=Colors.SUCCESS
        ))

    @logger.command(name="ignoreChannel", brief="Ignore certain log events for a channel")
    async def ignore_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """
        This command may be used to mark certain channels as "sensitive", and therefore not appear in server logs. This
        is often used to block information leaks from restricted channels, as well as other possible security holes.

        Parameters
        ----------
            ctx      :: Discord context <!nodoc>
            channel  :: The channel reference (ID, mention, name) to add to the exclusion list.

        Examples
        --------
            /logger ignoreChannel #secret-admins  :: Block "#secret-admins" from generating log events.

        See Also
        --------
            /logger unignoreChannel  :: Remove a channel from the exclusion list.
        """

        logger_settings: dict = self._config.get('loggers', {})
        global_settings: dict = logger_settings.setdefault("__global__", {})
        ignored_channels: list = global_settings.setdefault("ignoredChannels", [])

        if channel.id in ignored_channels:
            await ctx.send(embed=discord.Embed(
                title="Channel Already Excluded!",
                description=f"The channel {channel.mention} has already been excluded from logging events.",
                colors=Colors.WARNING
            ))

        ignored_channels.append(channel.id)
        self._config.set('loggers', logger_settings)

        await ctx.send(embed=discord.Embed(
            title="Channel Excluded!",
            description=f"The channel {channel.mention} will no longer generate log events for loggers that support "
                        f"the channel blacklist feature.",
            color=Colors.SUCCESS
        ))

    @logger.command(name="unignoreChannel", brief="Remove a logging ignore on a specified channel.")
    async def unignore_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """
        Remove a channel exclusion on logging events.

        This command may be used to remove exclusions put in place by /logger ingoreChannel.

        Parameters
        ----------
            ctx      :: Discord context <!nodoc>
            channel  :: The channel reference (ID, mention, name) to add to the exclusion list.

        Examples
        --------
            /logger unignoreChannel #secret-admins  :: Allow "#secert-admins" to generate log events again.

        See Also
        --------
            /logger ignoreChannel - Add a channel to the exclusion list.

        """

        logger_settings: dict = self._config.get('loggers', {})
        global_settings: dict = logger_settings.setdefault("__global__", {})
        ignored_channels: list = global_settings.setdefault("ignoredChannels", [])

        if channel.id not in ignored_channels:
            await ctx.send(embed=discord.Embed(
                title="Channel Not Excluded!",
                description=f"The channel {channel.mention} is currently not excluded from generating logging events.",
                colors=Colors.WARNING
            ))

        ignored_channels.remove(channel.id)
        self._config.set('loggers', logger_settings)

        await ctx.send(embed=discord.Embed(
            title="Channel Exclusion Removed!",
            description=f"The channel {channel.mention} will generate logging events again.",
            color=Colors.SUCCESS
        ))


def setup(bot: HuskyBot):
    bot.add_cog(ServerLog(bot))
