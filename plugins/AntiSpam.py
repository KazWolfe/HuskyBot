import logging
import re

import discord
from discord.ext import commands

from WolfBot import WolfUtils
from WolfBot import WolfConfig
from WolfBot.WolfEmbed import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class AntiSpam:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()
        LOG.info("Loaded plugin!")
        
    async def on_message(self, message):
        await self.multi_ping_check(message)
    
    async def multi_ping_check(self, message):
        PING_WARN_LIMIT = self._config.get('antiSpam', {}).get('pingSoftLimit', 6)
        PING_BAN_LIMIT = self._config.get('antiSpam', {}).get('pingHardLimit', 15)
    
        if message.author.permissions_in(message.channel).mention_everyone:
            return
            
        if PING_WARN_LIMIT is not None and len(message.mentions) >= PING_WARN_LIMIT:
            await message.delete()
            # ToDo: Issue actual warning through Punishment (once made available)
            await message.channel.send(embed=discord.Embed(
                    name="Mass Ping blocked",
                    description = "A mass-ping message was blocked in the current channel.\n"
                                + "Please reduce the number of pings in your message and try again.",
                    color=Colors.WARNING
            ))
        
        if PING_BAN_LIMIT is not None and len(message.mentions) >= PING_BAN_LIMIT:
            await message.author.ban(delete_message_days=1, reason="Multipinged over server ban limit.")
            # ToDo: Integrate with ServerLog to send custom ban message to staff logs.
            
    @commands.group(name="antispam", brief="Manage the Antispam configuration for the bot")
    @commands.has_permissions(manage_messages=True)
    async def asp(self, ctx: commands.Context):
        pass 
        
    @asp.command(name="setWarnLimit", brief="Set the number of pings required before delete/warn")
    @commands.has_permissions(mention_everyone=True)
    async def setWarnLimit(self, ctx: commands.Context, new_limit: int):
        if new_limit < 1:
            new_limit = None
            
        as_config = self._config.get('antiSpam', {})
        as_config['pingSoftLimit'] = new_limit
        self._config.set('antiSpam', as_config)
        
        await message.channel.send(embed=discord.Embed(
                name="AntiSpam Module",
                description = "The warning limit for pings has been set to " + str(new_limit) + ".",
                color=Colors.SUCCESS
        ))
        
    @asp.command(name="setBanLimit", brief="Set the number of pings required before user ban")
    @commands.has_permissions(mention_everyone=True)
    async def setWarnLimit(self, ctx: commands.Context, new_limit: int):
        if new_limit < 1:
            new_limit = None
            
        as_config = self._config.get('antiSpam', {})
        as_config['pingHardLimit'] = new_limit
        self._config.set('antiSpam', as_config)
        
        await message.channel.send(embed=discord.Embed(
                name="AntiSpam Module",
                description = "The ban limit for pings has been set to " + str(new_limit) + ".",
                color=Colors.SUCCESS
        ))
            

def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(AntiSpam(bot))
