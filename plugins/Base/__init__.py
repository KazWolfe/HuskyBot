from HuskyBot import HuskyBot
from .Base import Base


def setup(bot: HuskyBot):
    bot.add_cog(Base(bot))
