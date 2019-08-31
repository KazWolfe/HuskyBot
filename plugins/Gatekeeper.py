import logging

from discord.ext import commands

from HuskyBot import HuskyBot

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Gatekeeper(commands.Cog):
    """
    Gatekeeper is a next-generation humanity verification and alt account detection system. Guilds that use Gatekeeper
    will send all users either through the phone-verification flow or a customized captcha flow.

    Gatekeeper also handles browser fingerprinting and behavioral traits to ensure that users coming in are legitimate.
    Users verifying themselves via Gatekeeper go through the following steps:

    1. User gets redirected to a HuskyBot server, where they click a Log In With Discord button.
    2. After logging in with their Account, Husky associates a User ID with an IP address, fingerprint, and cookie.
    3. The user is sent back to the Husky page, where they are challenged with a CAPTCHA.
    4. If they pass the captcha, a "human" role is assigned to the user, granting them access to the guild and bypassing
    verification requirements.

    """

    def __init__(self, bot: HuskyBot):
        self.bot = bot
        self._config = bot.config
        self._session_store = bot.session_store

        LOG.info("Loaded plugin!")


def setup(bot: HuskyBot):
    bot.add_cog(Gatekeeper(bot))
