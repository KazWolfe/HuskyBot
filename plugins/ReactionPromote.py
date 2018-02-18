import discord

from BotCore import BOT_CONFIG
import logging

LOG = logging.getLogger("DiyBot/Plugin/" + __name__)


class ReactionPromote:
    def __init__(self, bot):
        self.bot = bot
        self.roleRemovalBlacklist = []

    async def on_ready(self):
        LOG.info("Enabled plugin!")

    async def on_raw_reaction_add(self, emoji, message_id, channel_id, user_id):
        promotion_config = BOT_CONFIG.get('promotions', {})

        channel = self.bot.get_channel(channel_id)

        if not isinstance(channel, discord.TextChannel):
            return

        message = await channel.get_message(message_id)
        guild = message.guild
        user = guild.get_member(user_id)

        try:
            group_to_add = discord.utils.get(guild.roles,
                                             id=promotion_config[str(channel_id)][str(message_id)][emoji.name])
            await user.add_roles(group_to_add)
            LOG.info("Added user " + user.display_name + " to role " + str(group_to_add))
        except KeyError:
            if promotion_config.get(str(channel_id)) is None:
                LOG.warn("Not configured for this channel. Ignoring.")
                return

            if promotion_config.get(str(channel_id)).get(str(message_id)) is None \
                    and not promotion_config.get(str(channel_id)).get('strictReacts'):
                LOG.warn("Not configured for this message. Ignoring.")
                return

            LOG.warn("Got bad emoji " + emoji.name + " (" + str(hex(ord(emoji.name))) + ")")
            self.roleRemovalBlacklist.append(str(user_id) + str(message_id))
            await message.remove_reaction(emoji, user)

    async def on_raw_reaction_remove(self, emoji, message_id, channel_id, user_id):
        promotion_config = BOT_CONFIG.get('promotions', {})

        if (str(user_id) + str(message_id)) in self.roleRemovalBlacklist:
            LOG.warn("Removal throttled.")
            self.roleRemovalBlacklist.remove(str(user_id) + str(message_id))
            return

        channel = self.bot.get_channel(channel_id)

        if not isinstance(channel, discord.TextChannel):
            return

        message = await channel.get_message(message_id)
        guild = message.guild
        user = guild.get_member(user_id)

        try:
            group_to_remove = discord.utils.get(guild.roles,
                                                id=promotion_config[str(channel_id)][str(message_id)][emoji.name])
            await user.remove_roles(group_to_remove)
            LOG.info("Removed user " + user.display_name + " from role " + str(group_to_remove))
        except KeyError:
            if promotion_config.get(str(channel_id)) is None:
                LOG.warn("Not configured for this channel. Ignoring.")
                return

            if promotion_config.get(str(channel_id)).get(str(message_id)) is None:
                LOG.warn("Not configured for this message. Ignoring.")
                return

            LOG.warn("Got bad emoji " + emoji.name + " (" + str(hex(ord(emoji.name))) + ")")


def setup(bot):
    bot.add_cog(ReactionPromote(bot))
