from HuskyBot import HuskyBot
from .Intelligence import Intelligence


def setup(bot: HuskyBot):
    bot.add_cog(Intelligence(bot))
