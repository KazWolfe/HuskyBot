import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot.WolfStatics import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class ReactionPromote:
    """
    The original reason DIY Bot was created.

    Give users a role based on their reaction to a message in a channel. If the user removes their reaction to the
    message, the bot should also remove the role from that user.
    """

    def __init__(self, bot):
        self.bot = bot
        self._config = WolfConfig.get_config()
        self.roleRemovalBlacklist = []
        LOG.info("Loaded plugin!")

    async def on_raw_reaction_add(self, emoji, message_id, channel_id, user_id):
        promotion_config = self._config.get('promotions', {})

        channel = self.bot.get_channel(channel_id)

        if not isinstance(channel, discord.TextChannel):
            return

        message = await channel.get_message(message_id)
        guild = message.guild
        user = guild.get_member(user_id)

        emoji_slug = emoji.name
        if emoji.is_custom_emoji():
            emoji_slug = str(emoji)

        try:
            group_to_add = discord.utils.get(guild.roles,
                                             id=promotion_config[str(channel_id)][str(message_id)][emoji_slug])
            await user.add_roles(group_to_add)
            LOG.info("Added user " + user.display_name + " to role " + str(group_to_add))
        except KeyError:
            if promotion_config.get(str(channel_id)) is None:
                # LOG.warning("Not configured for this channel. Ignoring.")
                return

            if promotion_config.get(str(channel_id)).get(str(message_id)) is None \
                    and not promotion_config.get(str(channel_id)).get('strictReacts'):
                LOG.warning("Not configured for this message. Ignoring.")
                return

            LOG.warning("Got bad emoji " + emoji_slug + " (" + str(hex(ord(emoji_slug))) + ")")
            self.roleRemovalBlacklist.append(str(user_id) + str(message_id))
            await message.remove_reaction(emoji, user)

    async def on_raw_reaction_remove(self, emoji, message_id, channel_id, user_id):
        promotion_config = self._config.get('promotions', {})

        if (str(user_id) + str(message_id)) in self.roleRemovalBlacklist:
            LOG.warning("Removal throttled.")
            self.roleRemovalBlacklist.remove(str(user_id) + str(message_id))
            return

        channel = self.bot.get_channel(channel_id)

        if not isinstance(channel, discord.TextChannel):
            return

        message = await channel.get_message(message_id)
        guild = message.guild
        user = guild.get_member(user_id)

        emoji_slug = emoji.name
        if emoji.is_custom_emoji():
            emoji_slug = str(emoji)

        try:
            group_to_remove = discord.utils.get(guild.roles,
                                                id=promotion_config[str(channel_id)][str(message_id)][emoji_slug])
            await user.remove_roles(group_to_remove)
            LOG.info("Removed user " + user.display_name + " from role " + str(group_to_remove))
        except KeyError:
            if promotion_config.get(str(channel_id)) is None:
                # LOG.warning("Not configured for this channel. Ignoring.")
                return

            if promotion_config.get(str(channel_id)).get(str(message_id)) is None:
                LOG.warning("Not configured for this message. Ignoring.")
                return

            LOG.warning("Got bad emoji " + emoji_slug + " (" + str(hex(ord(emoji_slug))) + ")")

    @commands.group(pass_context=True, brief="Control the promotions plugin", hidden=True)
    @commands.has_permissions(administrator=True)
    async def rpromote(self, ctx: discord.ext.commands.Context):
        """
        Parent command for the reaction promotion module.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=discord.Embed(
                title="Reaction Promotes",
                description="The command you have requested is not available.",
                color=Colors.DANGER
            ))
            return

    @rpromote.command(name="addPromotion", brief="Add a new promotion to the configs")
    async def add_promotion(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel, message_id: int,
                            emoji: str, role: discord.Role):
        """
        Add a new Promotion to the Reaction Promotion configuration.

        This is a relatively convoluted command due to the number of things that need to happen for it.

        This command takes a large number of arguments, as it requires a lot to store and configure a promotion. There
        is a strict limit of one emoji -> one role. This mapping may not be overridden or changed, as it would severely
        increase the difficulty of maintaining and using this command.

        The Channel is a channel identifier (name, ID, #mention, etc.) that will hold the reaction in question. This may
        be any channel in the guild. Note that if the bot's strict mode is on for the channel, adding a new channel
        *will* cause all reactions in that channel to be deleted.

        The Message ID is a field that the bot should listen to reactions on. This allows administrators to force users
        to react to specific messages for specific roles.

        The Emoji is any way of expressing an emoji (raw unicode, standard discord embed, :colon_notation:, etc). This
        will become the promotion key. For best results, use a native emoji, but theoretically any will work.

        The Role is the name (or other identifiable piece - ID, @mention, etc) of a role. This role will be granted to
        a user when they click on the specified Emoji on the specified Message in the specified Channel.
        """
        promotion_config = self._config.get('promotions', {})

        print(promotion_config)
        message_config = promotion_config.setdefault(str(channel.id), {}).setdefault(str(message_id), {})

        print(promotion_config)
        message_config[emoji] = role.id
        self._config.set('promotions', promotion_config)
        print(promotion_config)

        await ctx.send(embed=discord.Embed(
            title="Reaction Promotes",
            description="The promotion " + emoji + " => `" + role.name + "` has been registered for promotions!",
            color=Colors.SUCCESS
        ))


def setup(bot):
    bot.add_cog(ReactionPromote(bot))
