#!/usr/bin/env python3

import os
import sys
import logging

import discord
from discord.ext import commands

from WolfBot.WolfConfig import WolfConfig

BOT_CONFIG = WolfConfig("config/config.json")
bot = commands.Bot(command_prefix=BOT_CONFIG.get('prefix', '/'))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
LOG = logging.getLogger("DiyBot/Core")


@bot.event
async def on_ready():
    await bot.change_presence(game=discord.Game(name="DiyBot", type=2), status=discord.Status.dnd)
    LOG.info("DiyBot is online!")


if __name__ == '__main__':
    sys.path.insert(1, os.getcwd() + "/plugins/")

    bot.load_extension('BotAdmin')

    for extension in BOT_CONFIG.get('plugins', []):
        bot.load_extension(extension)

    bot.run(BOT_CONFIG['apiKey'])
