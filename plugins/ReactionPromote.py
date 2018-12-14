import logging

import discord
from discord.ext import commands

from libhusky import HuskyConverters
from libhusky.HuskyStatics import *

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class ReactionPromote:
    """
    Give users a role based on their reaction to a message in a channel. If the user removes their reaction to the
    message, the bot should also remove the role from that user.
    """

    def __init__(self, bot):
        self.bot = bot
        self._config = bot.config
        self.roleRemovalBlacklist = []
        LOG.info("Loaded plugin!")

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        promotion_config = self._config.get('promotions', {})

        channel = self.bot.get_channel(payload.channel_id)

        if not isinstance(channel, discord.TextChannel):
            return

        message = await channel.get_message(payload.message_id)
        guild = message.guild
        user = guild.get_member(payload.user_id)

        try:
            role_id = promotion_config[str(payload.channel_id)][str(payload.message_id)][str(payload.emoji)]
            group_to_add = guild.get_role(role_id)
            await user.add_roles(group_to_add)
            LOG.info(f"Added user {user.display_name} to role {str(group_to_add)}")
        except KeyError:
            if promotion_config.get(str(payload.channel_id)) is None:
                # LOG.warning("Not configured for this channel. Ignoring.")
                return

            if promotion_config.get(str(payload.channel_id)).get(str(payload.message_id)) is None \
                    and not promotion_config.get(str(payload.channel_id)).get('strictReacts'):
                LOG.warning("Not configured for this message. Ignoring.")
                return

            LOG.warning(f"Got bad emoji {str(payload.emoji)}")
            self.roleRemovalBlacklist.append(str(payload.user_id) + str(payload.message_id))
            await message.remove_reaction(payload.emoji, user)

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        promotion_config = self._config.get('promotions', {})

        if (str(payload.user_id) + str(payload.message_id)) in self.roleRemovalBlacklist:
            # LOG.warning("Removal throttled.")
            self.roleRemovalBlacklist.remove(str(payload.user_id) + str(payload.message_id))
            return

        channel = self.bot.get_channel(payload.channel_id)

        if not isinstance(channel, discord.TextChannel):
            return

        message = await channel.get_message(payload.message_id)
        guild = message.guild
        user = guild.get_member(payload.user_id)

        try:
            role_id = promotion_config[str(payload.channel_id)][str(payload.message_id)][str(payload.emoji)]
            group_to_remove = guild.get_role(role_id)
            await user.remove_roles(group_to_remove)
            LOG.info(f"Removed user {user.display_name} from role {str(group_to_remove)}")
        except KeyError:
            if promotion_config.get(str(payload.channel_id)) is None:
                # LOG.warning("Not configured for this channel. Ignoring.")
                return

            if promotion_config.get(str(payload.channel_id)).get(str(payload.message_id)) is None:
                LOG.warning("Not configured for this message. Ignoring.")
                return

            LOG.warning(f"Got bad emoji {str(payload.emoji)}")

    @commands.group(pass_context=True, brief="Control the promotions plugin")
    @commands.has_permissions(administrator=True)
    async def rpromote(self, ctx: discord.ext.commands.Context):
        """
        Run /help rpromote <subcommand> for more information.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=discord.Embed(
                title="Reaction Promotes",
                description="The command you have requested is not available.",
                color=Colors.DANGER
            ))
            return

    @rpromote.command(name="add", brief="Add a new promotion to the configs")
    async def add_promotion(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel, message_id: int,
                            emoji: HuskyConverters.PartialEmojiConverter, *, role: discord.Role):
        """
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

        Parameters
        ----------
            ctx         :: Discord context <!nodoc>
            channel     :: The channel that this promotion will live in
            message_id  :: The message ID that will handle this promotion
            emoji       :: A string representation of the emoji to add
            role        :: The role that this promotion will grant
        """
        promotion_config = self._config.get('promotions', {})

        try:
            message: discord.Message = await channel.get_message(message_id)
        except discord.NotFound:
            await ctx.send(embed=discord.Embed(
                title=Emojis.WARNING + " Error Adding ReactionPromote",
                description="The message you specified could not be found. Please double-check all message IDs.",
                color=Colors.ERROR
            ))
            return

        try:
            await message.add_reaction(emoji)
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(
                title=Emojis.WARNING + " Error Adding ReactionPromote",
                description="The bot does not have permission to add a reaction to the specified message. Please "
                            "check channel permissions.",
                color=Colors.ERROR
            ))
            return
        except (discord.NotFound, discord.InvalidArgument):
            # It may seem  strange to react before we save the emote to config. This is why. Emoji handling is *hard* so
            # we can just let Discord handle it instead (and reject any invalid emojis) for us.
            await ctx.send(embed=discord.Embed(
                title=Emojis.WARNING + " Error Adding ReactionPromote",
                description="The emoji specified is invalid or could otherwise not be processed. Please double-check "
                            "that you are using a valid emoji.",
                color=Colors.ERROR
            ))
            return

        message_config = promotion_config.setdefault(str(channel.id), {}).setdefault(str(message_id), {})

        message_config[str(emoji)] = role.id
        self._config.set('promotions', promotion_config)

        await ctx.send(embed=discord.Embed(
            title="Reaction Promotes",
            description=f"Users reacting to the specified message with {emoji} will now receive "
                        f"the role {role.mention}.",
            color=Colors.SUCCESS
        ))

    @rpromote.command(name="remove", brief="Remove a promotion to the configs")
    async def remove_promotion(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel, message_id: int,
                               emoji: str):

        promotion_config = self._config.get('promotions', {})

        try:
            del promotion_config[str(channel.id)][str(message_id)][emoji]
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Reaction Promotes",
                description="Could not delete the specified promotion, because it does not exist.",
                color=Colors.DANGER
            ))
            return
        self._config.set('promotions', promotion_config)

        # Clean up the entry as well.
        try:
            message: discord.Message = await channel.get_message(message_id)
            reaction: discord.Reaction = discord.utils.get(message.reactions, emoji=emoji)
            async for user in reaction.users():
                self.roleRemovalBlacklist.append(str(user.id) + str(message_id))
                await message.remove_reaction(emoji, user)

        except discord.NotFound as _:
            pass

        await ctx.send(embed=discord.Embed(
            title="Reaction Promotes",
            description=f"The specified promotion has been successfully deleted.",
            color=Colors.SUCCESS
        ))


def setup(bot):
    bot.add_cog(ReactionPromote(bot))
