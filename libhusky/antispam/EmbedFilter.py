#   This Source Code Form is "Incompatible With Secondary Licenses", as
#   defined by the Mozilla Public License, v. 2.0.

import logging

import discord
from discord.ext import commands

from libhusky.HuskyStatics import *
from libhusky.antispam import AntiSpamModule

LOG = logging.getLogger("HuskyBot.Plugin.AntiSpam." + __name__.split('.')[-1])

defaults = {
    "banOnOffense": True,  # Whether to ban users on offense
    "deleteOnOffense": False,  # Whether to delete messages on offense (reporting)
}


class EmbedFilter(AntiSpamModule):
    def __init__(self, plugin):
        super().__init__(self.base, name="embedFilter", brief="Control the embed filter's settings",
                         checks=[super().has_permissions(mention_everyone=True)], aliases=["ef"])

        self.bot = plugin.bot
        self._config = self.bot.config

        self.add_command(self.set_config)
        self.add_command(self.view_config)
        self.register_commands(plugin)

        LOG.info("Filter initialized.")

    def cleanup(self):
        # This method has no cleanup - it's an instant ban
        return

    def clear_for_user(self, user: discord.Member):
        # This method has no cleanup - it's an instant ban
        return

    def clear_all(self):
        # This method has no cleanup - it's an instant ban
        return

    async def process_message(self, message, context):
        antispam_config = self._config.get('antiSpam', {})
        filter_config = {**defaults, **antispam_config.get('EmbedFilter', {}).get('config', {})}

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_ALERTS.value, None)
        if alert_channel is not None:
            alert_channel = message.guild.get_channel(alert_channel)

        if message.author.bot or message.webhook_id:
            # ignore bots and webhooks
            return

        if len(message.clean_content) != 0:
            # ignore messages with content. risky but works
            return

        actions = []

        if len(message.embeds):
            if filter_config['banOnOffense']:
                await message.author.ban(
                    reason=f"[AUTOMATIC BAN - AntiSpam Plugin] User sent an embed without accompanying message. "
                           f"Self-bot detected/probable.",
                    delete_message_days=7 if filter_config['deleteOnOffense'] else 0)

                actions.append("User Banned")

                if filter_config['deleteOnOffense']:
                    actions.append("Messages Deleted")
            elif filter_config['deleteOnOffense']:
                await message.delete()
                actions.append("Message Deleted")

            LOG.info(f"User ID {message.author.id} sent embed without accompanying message content. "
                     f"Actions taken: {','.join(actions)}")

            log_embed = discord.Embed(
                description=f"The user {message.author.mention} was determined to be a selfbot. Please review this "
                            f"account, if necessary",
                color=Colors.WARNING
            )

            log_embed.set_author(name=f"Selfbot detected: {message.author}!", icon_url=message.author.avatar_url)
            log_embed.add_field(name="User ID", value=message.author.id, inline=True)
            log_embed.add_field(name="Detection Channel", value=message.channel.mention, inline=True)
            log_embed.add_field(name="Message ID", value=message.id, inline=False)
            log_embed.add_field(name="Action Taken", value=", ".join(actions), inline=False)

            if alert_channel:
                await alert_channel.send(embed=log_embed)

    @commands.command(name="configure", brief="Set the configuration on the EmbedFilter")
    async def set_config(self, ctx: commands.Context, ban_on_offense: bool, delete_on_offense: bool):
        """
        This command takes two arguments - ban_on_offense and delete_on_offense. Both are booleans.

        Parameters
        ----------
            ctx :: Discord context <!nodoc>
            ban_on_offense    :: Ban any user posting a message-less embed
            delete_on_offense :: Delete any offending messages by users

        Examples
        --------
            /as embedFilter configure True False  :: Set filter to autoban users posting embeds, but don't delete.
            /as embedFilter configure False False :: Set filter to "warn-only" mode
        """
        as_config = self._config.get('antiSpam', {})
        filter_config = as_config.setdefault('EmbedFilter', {}).setdefault('config', defaults)

        filter_config['banOnOffense'] = ban_on_offense
        filter_config['deleteOnOffense'] = delete_on_offense
        self._config.set('antiSpam', as_config)

        embed = discord.Embed(
            title="AntiSpam Plugin",
            description=f"Embed settings successfully updated.",
            color=Colors.SUCCESS
        )

        embed.add_field(name="Ban on Offense", value=filter_config['banOnOffense'], inline=False)
        embed.add_field(name="Delete on Offense", value=filter_config['deleteOnOffense'], inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="viewConfig", brief="See currently set configuration values for this plugin.")
    async def view_config(self, ctx: commands.Context):
        as_config = self._config.get('antiSpam', {})
        filter_config = as_config.get('EmbedFilter', {}).get('config', defaults)

        embed = discord.Embed(
            title="Embed Filter Configuration",
            description="The below settings are the current values for the mention filter configuration.",
            color=Colors.INFO
        )

        embed.add_field(name="Ban on Offense", value=filter_config['banOnOffense'], inline=False)
        embed.add_field(name="Delete on Offense", value=filter_config['deleteOnOffense'], inline=False)

        await ctx.send(embed=embed)
