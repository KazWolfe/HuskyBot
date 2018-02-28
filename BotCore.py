#!/usr/bin/env python3

import os
import sys
import logging

import discord
from discord.ext import commands

from WolfBot.WolfConfig import WolfConfig
from WolfBot.WolfEmbed import Colors

BOT_CONFIG = WolfConfig("config/config.json")
bot = commands.Bot(command_prefix=BOT_CONFIG.get('prefix', '/'))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
LOG = logging.getLogger("DiyBot/Core")


@bot.event
async def on_ready():
    await bot.change_presence(game=discord.Game(name="DiyBot", type=2), status=discord.Status.dnd)
    LOG.info("DiyBot is online, running discordpy " + discord.__version__)
    
    if not BOT_CONFIG.get("developerMode", False):
        if BOT_CONFIG.get("guildId"):
           LOG.error("No Guild ID specified! Quitting.")
           exit(127)

        for guild in client.guilds:
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
        
    await ctx.send(embed=discord.Embed(
        title="Bot Error Handler",
        description="The bot has encountered a fatal error running the command given. Logs are below.",
        color = Colors.DANGER
    ).add_field(name="Error Log", value=str(error), inline=False))
    

if __name__ == '__main__':
    sys.path.insert(1, os.getcwd() + "/plugins/")

    bot.load_extension('BotAdmin')

    for extension in BOT_CONFIG.get('plugins', []):
        bot.load_extension(extension)

    bot.run(BOT_CONFIG['apiKey'])
