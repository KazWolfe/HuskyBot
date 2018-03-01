#!/usr/bin/env python3

import os
import sys
import logging
import datetime

import discord
from discord.ext import commands

from WolfBot.WolfConfig import WolfConfig
from WolfBot.WolfEmbed import Colors

BOT_CONFIG = WolfConfig("config/config.json")
LOCAL_STORAGE = WolfConfig()

bot = commands.Bot(command_prefix=BOT_CONFIG.get('prefix', '/'))

LOCAL_STORAGE.set('logPath', 'logs/log-' + str(datetime.datetime.now()).split('.')[0] + ".log")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S", handlers=[logging.FileHandler(LOCAL_STORAGE.get('logPath')),logging.StreamHandler(sys.stdout)])
LOG = logging.getLogger("DiyBot.Core")


@bot.event
async def on_ready():
    botPresence = BOT_CONFIG.get('presence', {"game": "DiyBot", "type": 2, "status": "dnd"})

    await bot.change_presence(game=discord.Game(name=botPresence['game'], type=botPresence['type']), status=discord.Status[botPresence['status']])
    LOG.info("DiyBot is online, running discordpy " + discord.__version__)
    
    if not BOT_CONFIG.get("developerMode", False):
        if BOT_CONFIG.get("guildId") is None:
           LOG.error("No Guild ID specified! Quitting.")
           exit(127)

        for guild in bot.guilds:
            if guild.id != BOT_CONFIG.get("guildId"):
                guild.leave()
               

#@bot.event
#async def on_message(message):
#    if not BOT_CONFIG.get("developerMode", False):
#        if isinstance(message.channel, discord.textChannel) and message.guild.id != BOT_CONFIG.get("guildId"):
#            guild.leave()
           

@bot.event
async def on_guild_join(guild):
    if not BOT_CONFIG.get("developerMode", False):
        if message.guild.id != BOT_CONFIG.get("guildId"):
           guild.leave()
              

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        return # fail silently on permission error
        
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(embed=discord.Embed(
            title="Bot Error Handler",
            description="**The command `" + ctx.message.content.split(' ')[0] + "` does not exist.** See `/help` for valid commands.",
            color = Colors.DANGER
        ))
        return
        
    await ctx.send(embed=discord.Embed(
        title="Bot Error Handler",
        description="The bot has encountered a fatal error running the command given. Logs are below.",
        color = Colors.DANGER
    ).add_field(name="Error Log", value="```" + str(error) + "```", inline=False))
    
    
@bot.event
async def on_message(message):
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)

if __name__ == '__main__':
    sys.path.insert(1, os.getcwd() + "/plugins/")

    bot.load_extension('BotAdmin')

    for extension in BOT_CONFIG.get('plugins', []):
        bot.load_extension(extension)

    bot.run(BOT_CONFIG['apiKey'])
