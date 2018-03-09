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
        
        # ToDo: Find a better way of storing valid loggers. This is hacky as all hell.
        self._validLoggers = ["userJoin", "userJoin.milestones", "userJoin.audit"]

    async def on_member_ban(self, guild, user):
        pass
        
    async def on_member_join(self, member):
    
        # Send milestones to the moderator alerts channel
        async def milestone_notifier(member):        
            if "userJoin.milestones" not in self._config.get("loggers", {}).keys():
                return
        
            milestone_channel = self._config.get('specialChannels', {}).get('modAlerts', None)
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
        
        # Send all joins to the logging channel
        async def general_notifier(member):
            if "userJoin" not in self._config.get("loggers", {}).keys():
                return
        
            channel = self._config.get('specialChannels', {}).get('logs', None)
            
            if channel is None:
                return
                
            channel = member.guild.get_channel(channel)
                
            embed = discord.Embed(
                title="New Member!",
                description=str(member) + " has joined the server.",
                color=Colors.PRIMARY
            )
            
            embed.set_thumbnail(url=member.avatar_url)
            embed.add_field(name="Joined Server", value=str(member.joined_at).split('.')[0], inline=True)
            embed.add_field(name="Joined Discord", value=str(member.created_at).split('.')[0], inline=True)
            embed.add_field(name="User ID", value=member.id, inline=True)
            
            await channel.send(embed=embed)
            
        # Send all joins to the auditing channel
        async def audit_notifier(member):
            if "userJoin.audit" not in self._config.get("loggers", {}).keys():
                return
            
            channel = self._config.get('specialChannels', {}).get('auditing', None)
            
            if channel is None:
                return
                
            channel = member.guild.get_channel(channel)
                
            embed = discord.Embed(
                title="New Member!",
                description=str(member) + " has joined the server. Welcome!",
                color=Colors.PRIMARY
            )
            
            embed.set_thumbnail(url=member.avatar_url)
            
            await channel.send(embed=embed)
        
        await milestone_notifier(member)
        await general_notifier(member)
        
    async def on_error(event_method, *args, **kwargs):  
        channel = self._config.get('specialChannels', {}).get('logs', None)
        
        if channel is None:
            return
            
        channel = member.guild.get_channel(channel)
        
        embed = discord.Embed(
            title="Bot Exception Handler",
            description="Exception in method `" + event_method + "`:\n```" + traceback.format_exc() + "```",
            color=Colors.DANGER
        )
        
        await channel.send(embed=embed)
        
    @commands.group(name="logger", aliases=["logging"], brief="Control the Logging module")
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
        
        channel_config['modAlerts'] = channel.id
        
        self._config.set('specialChannels', channel_config)
        
        await ctx.send(embed=discord.Embed(
                title="Logging Manager",
                description="The Moderator Alerts channel has been set to " + channel.mention + ".",
                color=Colors.SUCCESS
            ))
            
    @logger.command(name="setLogChannel", brief="Set the standard log messages channel")
    async def setLogChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        channel_config = self._config.get('specialChannels', {})
        
        channel_config['logs'] = channel.id
        
        self._config.set('specialChannels', channel_config)
        
        await ctx.send(embed=discord.Embed(
                title="Logging Manager",
                description="The logging channel has been set to " + channel.mention + ".",
                color=Colors.SUCCESS
            ))
            
    @logger.command(name="setAuditChannel", brief="Set the audit log messages channel")
    async def setAuditChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        channel_config = self._config.get('specialChannels', {})
        
        channel_config['audits'] = channel.id
        
        self._config.set('specialChannels', channel_config)
        
        await ctx.send(embed=discord.Embed(
                title="Logging Manager",
                description="The auditing channel has been set to " + channel.mention + ".",
                color=Colors.SUCCESS
            ))
            
    @logger.command(name="enable", brief="Enable a specified logger")
    async def enableLogger(self, ctx: commands.Context, name: str):
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
    async def disableLogger(self, ctx: commands.Context, name: str):
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
    LOG.info("Loaded plugin!")
