from HuskyBot import HuskyBot
from .CrashBlock import CrashBlock


def setup(bot: HuskyBot):
    bot.add_cog(CrashBlock(bot))
