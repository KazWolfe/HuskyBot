import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfUtils
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


class ServerLog:
    """
    The ServerLog plugin exists to provide a clean and transparent method of tracking server activity on the bot.
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()
        LOG.info("Loaded plugin!")

        # ToDo: Find a better way of storing valid loggers.
        self._validLoggers = ["userJoin", "userJoin.milestones", "userJoin.audit",
                              "userLeave",
                              "userBan",
                              "userRename",
                              "messageDelete", "messageDelete.logIntegrity",
                              "messageEdit"]

    async def on_member_join(self, member):
        # Send milestones to the moderator alerts channel
        async def milestone_notifier(notif_member):
            if "userJoin.milestones" not in self._config.get("loggers", {}).keys():
                return

            milestone_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_ALERTS.value, None)
            guild = notif_member.guild

            if milestone_channel is None:
                return

            milestone_channel = guild.get_channel(milestone_channel)

            if guild.member_count % 1000 == 0:
                await milestone_channel.send(embed=discord.Embed(
                    title=Emojis.PARTY + " Guild Member Count Milestone!",
                    description="The guild has now reached " + str(guild.member_count) + " members! Thank you "
                                + notif_member.display_name + " for joining!",
                    color=Colors.SUCCESS
                ))

        # Send all joins to the logging channel
        async def general_notifier(notif_member):
            if "userJoin" not in self._config.get("loggers", {}).keys():
                return

            channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

            if channel is None:
                return

            channel = notif_member.guild.get_channel(channel)

            embed = discord.Embed(
                title=Emojis.SUNRISE + " New Member!",
                description=str(notif_member) + " has joined the guild.",
                color=Colors.PRIMARY
            )

            embed.set_thumbnail(url=notif_member.avatar_url)
            embed.add_field(name="Joined Guild", value=notif_member.joined_at.strftime(DATETIME_FORMAT), inline=True)
            embed.add_field(name="Joined Discord", value=notif_member.created_at.strftime(DATETIME_FORMAT), inline=True)
            embed.add_field(name="User ID", value=notif_member.id, inline=True)
            embed.set_footer(text="Member #{} on the guild".format(
                str(sorted(notif_member.guild.members, key=lambda m: m.joined_at).index(member) + 1)))

            await channel.send(embed=embed)

        await milestone_notifier(member)
        await general_notifier(member)

    async def on_member_remove(self, member: discord.Member):
        if "userLeave" not in self._config.get("loggers", {}).keys():
            return

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

        if alert_channel is None:
            return

        alert_channel = member.guild.get_channel(alert_channel)

        embed = discord.Embed(
            title=Emojis.DOOR + " Member left the guild",
            description=str(member) + " has left the guild.",
            color=Colors.PRIMARY
        )

        embed.set_thumbnail(url=member.avatar_url)
        embed.add_field(name="User ID", value=member.id)
        embed.add_field(name="Leave Timestamp", value=WolfUtils.get_timestamp())

        await alert_channel.send(embed=embed)

    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        if "userBan" not in self._config.get("loggers", {}).keys():
            return

        # Get timestamp as soon as the event is fired, because waiting for bans may take a while.
        timestamp = WolfUtils.get_timestamp()

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

        if alert_channel is None:
            return

        alert_channel = self.bot.get_channel(alert_channel)

        embed = discord.Embed(
            title=Emojis.BAN + " User banned",
            description=str(user) + " was banned from the guild.",
            color=Colors.DANGER
        )

        ban_entry = discord.utils.get(await guild.bans(), user=user)

        if ban_entry is None:
            raise ValueError("A ban record for user {} was expected, but no entry was found".format(user.id))

        ban_reason = ban_entry.reason

        if ban_reason is None:
            ban_reason = "<No ban reason provided>"

        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name="User ID", value=user.id, inline=True)
        embed.add_field(name="Ban Timestamp", value=timestamp, inline=True)
        embed.add_field(name="Ban Reason", value=ban_reason, inline=False)

        await alert_channel.send(embed=embed)

    # noinspection PyUnusedLocal
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        if "userBan" not in self._config.get("loggers", {}).keys():
            return

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

        if alert_channel is None:
            return

        alert_channel = self.bot.get_channel(alert_channel)

        embed = discord.Embed(
            title=Emojis.UNBAN + "User unbanned",
            description=str(user) + " was unbanned from the guild.",
            color=Colors.PRIMARY
        )

        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name="User ID", value=user.id)
        embed.add_field(name="Unban Timestamp", value=WolfUtils.get_timestamp())

        await alert_channel.send(embed=embed)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if "userRename" not in self._config.get("loggers", {}).keys():
            return

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

        if alert_channel is None:
            return

        alert_channel = self.bot.get_channel(alert_channel)

        if before.nick == after.nick and before.name == after.name:
            return

        if before.nick != after.nick:
            update_type = 'nickname'
            old_val = before.nick
            new_val = after.nick
        elif before.name != after.name:
            update_type = 'username'
            old_val = before.name
            new_val = after.name
        else:
            return

        embed = discord.Embed(
            description="User's {} has changed! Their display name in this guild is now "
                        "`{}`.".format(update_type, after.display_name),
            color=Colors.INFO
        )

        embed.add_field(name="Old {}".format(update_type.capitalize()), value=old_val, inline=True)
        embed.add_field(name="New {}".format(update_type.capitalize()), value=new_val, inline=True)
        embed.set_author(name="{}'s {} has changed!".format(after, update_type), icon_url=after.avatar_url)

        await alert_channel.send(embed=embed)

    async def on_message_delete(self, message: discord.Message):
        if message.guild is None:
            return

        if "messageDelete" not in self._config.get("loggers", {}).keys():
            return

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

        if alert_channel is None:
            return

        alert_channel = message.guild.get_channel(alert_channel)

        # Allow event cleanups for bot users.
        if message.channel == alert_channel and message.author.bot:
            return

        embed = discord.Embed(
            color=Colors.WARNING
        )

        embed.set_author(name="Deleted Message in #" + str(message.channel), icon_url=message.author.avatar_url)
        embed.add_field(name="Author", value=message.author, inline=True)
        embed.add_field(name="Message ID", value=message.id, inline=True)
        embed.add_field(name="Send Timestamp", value=message.created_at.strftime(DATETIME_FORMAT), inline=True)
        embed.add_field(name="Delete Timestamp", value=WolfUtils.get_timestamp(), inline=True)

        if message.content is not None and message.content != "":
            embed.add_field(name="Message", value=WolfUtils.trim_string(message.content, 1000, True), inline=False)

        if message.attachments is not None and len(message.attachments) > 1:
            embed.add_field(name="Attachments", value=WolfUtils.trim_string(str(message.attachments), 1000, True),
                            inline=False)
        elif message.attachments is not None and len(message.attachments) == 1:
            embed.set_image(url=message.attachments[0].url)

        await alert_channel.send(embed=embed)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.guild is None:
            return

        if "messageEdit" not in self._config.get("loggers", {}).keys():
            return

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

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
            embed.add_field(name="Message Before", value=WolfUtils.trim_string(before.content, 1000, True),
                            inline=False)
        else:
            embed.add_field(name="Message Before", value="`<No Content>`", inline=False)

        if after.content is not None and after.content != "":
            embed.add_field(name="Message After", value=WolfUtils.trim_string(after.content, 1000, True), inline=False)
        else:
            embed.add_field(name="Message After", value="`<No Content>`", inline=False)

        await alert_channel.send(embed=embed)

    @commands.group(name="logger", aliases=["logging"], brief="Parent command to manage the ServerLog module")
    @commands.has_permissions(administrator=True)
    async def logger(self, ctx: discord.ext.commands.Context):
        """
        General parent command for logging management.

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
        Add a logger to the configuration, and enable it.

        This command takes a single logger name as an argument, and adds it to the enabled loggers list. Changes to
        loggers take effect immediately.
        """
        enabled_loggers = self._config.get('loggers', {})

        if name not in self._validLoggers:
            await ctx.send(embed=discord.Embed(
                title="Logging Manager",
                description="The logger named `" + name + "` is not recognized as a valid logger.",
                color=Colors.DANGER
            ))
            return

        if name in enabled_loggers.keys():
            await ctx.send(embed=discord.Embed(
                title="Logging Manager",
                description="The logger named `" + name + "` is already enabled.",
                color=Colors.WARNING
            ))
            return

        enabled_loggers[name] = {}

        self._config.set('loggers', enabled_loggers)

        await ctx.send(embed=discord.Embed(
            title="Logging Manager",
            description="The logger named `" + name + "` was enabled.",
            color=Colors.SUCCESS
        ))

    @logger.command(name="disable", brief="Disable a specified logger")
    async def disable_logger(self, ctx: commands.Context, name: str):
        """
        Remove a logger from the configuration, and disable it.

        This command takes a single logger name as an argument, and adds it to the enabled loggers list. Changes to
        loggers take effect immediately.
        """
        enabled_loggers = self._config.get('loggers', {})

        if name not in self._validLoggers:
            await ctx.send(embed=discord.Embed(
                title="Logging Manager",
                description="The logger named `" + name + "` is not recognized as a valid logger.",
                color=Colors.DANGER
            ))
            return

        if name not in enabled_loggers.keys():
            await ctx.send(embed=discord.Embed(
                title="Logging Manager",
                description="The logger named `" + name + "` is already disabled.",
                color=Colors.WARNING
            ))
            return

        enabled_loggers.pop(name)

        self._config.set('loggers', enabled_loggers)

        await ctx.send(embed=discord.Embed(
            title="Logging Manager",
            description="The logger named `" + name + "` was disabled.",
            color=Colors.SUCCESS
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(ServerLog(bot))
