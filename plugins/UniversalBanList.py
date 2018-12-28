import logging
import re

import discord

from HuskyBot import HuskyBot
from libhusky import HuskyUtils, HuskyStatics

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class UniversalBanList:
    """
    The (poorly named) Universal Ban List module is responsible for kicking users that meet certain (very strict)
    conditions. The bot will automatically kick any user that contains certain key phrases in a username, or sends a
    message containing key phrases.

    When a user is removed for a message violation, they will be banned from the guild and then immediately unbanned
    in order to delete all messages from that user.

    The Universal Ban List may be edited only through the configuration file for the bot, as it is not meant for
    standard enforcement. The UBL configuration syntax is as follows:

        "ubl": {
            "bannedUsernames": [
                'cat',
                'dog'
            ],
            "bannedPhrases": [
                'fish',
                'pie'
            ],
            "kickInviteUsernames": true
        }

    Banned usernames are the union of the bannedUsernames and bannedPhrases list. It will apply to both usernames as
    well as nicknames. Banned phrases are only the result of the bannedPhrases list. Both fields are regex-sensitive and
    will process regular expressions.

    The UBL will not apply (on message) to users with the MANAGE_MESSAGES permission. It will also not apply to users
    with the MANAGE_GUILD permission.
    """

    def __init__(self, bot: HuskyBot):
        self.bot = bot

        LOG.info("Loaded plugin!")

    def get_banned_usernames(self):
        ubl_config = self.bot.config.get('ubl', {})

        banned_list = ubl_config.get('bannedUsernames', []) + ubl_config.get('bannedPhrases', [])

        if ubl_config.get('kickInviteUsernames', False):
            banned_list.append(HuskyStatics.Regex.INVITE_REGEX)

        return banned_list

    async def filter_message(self, message: discord.Message, context: str = "new_message"):
        if not HuskyUtils.should_process_message(message):
            return

        if message.author.permissions_in(message.channel).manage_messages:
            return

        for ubl_term in self.bot.config.get('ubl', {}).get('bannedPhrases', []):
            if re.search(ubl_term, message.content, re.IGNORECASE) is not None:
                await message.author.ban(reason=f"User used UBL keyword `{ubl_term}`. Purging user...",
                                         delete_message_days=5)
                await message.guild.unban(message.author, reason="UBL ban reversal")
                LOG.info("Kicked UBL triggering user (context %s, keyword %s, from %s in %s): %s", context,
                         message.author, ubl_term, message.channel, message.content)

    async def on_message(self, message):
        await self.filter_message(message)

    # noinspection PyUnusedLocal
    async def on_message_edit(self, before, after):
        await self.filter_message(after, "edit")

    async def on_member_join(self, member: discord.Member):
        if member.guild_permissions.manage_guild:
            return

        for ubl_term in self.get_banned_usernames():
            if re.search(ubl_term, member.display_name, re.IGNORECASE) is not None:
                await member.kick(reason=f"[AUTOMATIC KICK - UBL Module] New user's name contains UBL keyword "
                                         f"`{ubl_term}`")
                LOG.info("Kicked UBL triggering new join of user %s (matching UBL %s)", member, ubl_term)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.guild_permissions.manage_guild:
            return

        if before.nick == after.nick and before.name == after.name:
            return

        for ubl_term in self.get_banned_usernames():
            if after.nick is not None and re.search(ubl_term, after.nick, re.IGNORECASE) is not None:
                u_type = 'nickname'
            elif after.name is not None and re.search(ubl_term, after.name, re.IGNORECASE):
                u_type = 'username'
            else:
                continue

            await after.kick(reason=f"[AUTOMATIC BAN - UBL Module] User {after} changed {u_type} to include UBL "
                                    f"keyword {ubl_term}")
            LOG.info("Kicked UBL triggering %s change of user %s (matching UBL %s)", u_type, after, ubl_term)


def setup(bot: HuskyBot):
    bot.add_cog(UniversalBanList(bot))
