from HuskyBot import HuskyBot
from .Debug import Debug


def setup(bot: HuskyBot):
    bot.add_cog(Debug(bot))
