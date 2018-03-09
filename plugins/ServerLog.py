import logging

import discord
from discord.ext import commands

from WolfBot import WolfUtils
from WolfBot import WolfConfig
from WolfBot.WolfEmbed import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


class ServerLog:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()

    async def on_member_ban(self, guild, user):
        pass
        
    async def on_member_join(self, member):
        async def milestone_notifier(member):
            milestone_channel = self._config.get('specialChannels', {}).get('modChannel', None)
            guild = member.guild
            
            if milestone_channel is None:
                return
                
            milestone_channel = guild.get_channel(milestone_channel)
                
            if guild.member_count % 250 == 0:
                await milestone_channel.send(embed=discord.Embed(
                        title="Server Member Count Milestone!",
                        description="The server has now reached " + str(guild.member_count) + " members! Thank you " + member.display_name + " for joining!",
                        color=Colors.SUCCESS
                ))
        
        async def general_notifier(member):
            pass
        
        await milestone_notifier(member)
        await general_notifier(member)
        
    @commands.group(name="logger", alises=["logging"], brief="Control the Logging module")
    @commands.has_permissions(administrator=True)
    async def logger(self, ctx: discord.ext.commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=discord.Embed(
                title="Logging Manager",
                description="The command you have requested is not available. Please see `/help logger`",
                color=Colors.DANGER
            ))
            return 
            
    @logger.command(name="setModChannel", brief="Set the important moderator alerts channel")
    async def setModChannel(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel):
        channel_config = self._config.get('specialChannels', {})
        
        channel_config['modChannel'] = channel.id
        
        self._config.set('specialChannels', channel_config)
        
        await ctx.send(embed=discord.Embed(
                title="Logging Manager",
                description="The Moderator Alerts channel has been set to #" + str(channel) + ".",
                color=Colors.SUCCESS
            ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(ServerLog(bot))
    LOG.info("Loaded plugin!")
