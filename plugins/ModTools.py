import asyncio
import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfUtils
from WolfBot.WolfStatics import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic,PyUnresolvedReferences
class ModTools:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()
        self._mutes = WolfConfig.WolfConfig('config/mutes.json', create_if_nonexistent=True)
        LOG.info("Loaded plugin!")

    # Prevent users from becoming bot role if they're not actually bots.
    async def on_member_update(self, before, after):
        if before.roles == after.roles:
            return

        special_roles = self._config.get("specialRoles", {})

        if special_roles.get('bots') is None:
            return

        bot_role = discord.utils.get(after.roles, id=int(special_roles.get('bots')))

        if (bot_role is not None) and (bot_role not in before.roles) and (not before.bot):
            await after.remove_roles(bot_role, reason="User is not an authorized bot.")
            LOG.info("User " + after.display_name + " was granted bot role, but was not a bot. Removing.")

    async def load_mute_tasks(self):
        mutes = self._mutes.get('mutes', [])

    @commands.command(name="autoban", aliases=["hackban"], brief="Ban a user (by ID) currently not in the guild")
    @commands.has_permissions(ban_members=True)
    async def hackban(self, ctx: discord.ext.commands.Context, user_id: int, *, reason: str):
        try:
            user = await self.bot.get_user_info(user_id)
        except discord.NotFound:
            await ctx.send(embed=discord.Embed(
                title="Mod Toolkit",
                description="User ID `" + str(user_id) + "` could not be hackbanned. Do they even exist?",
                color=Colors.DANGER
            ))
            return

        # If the user to be banned is the user calling the ban, let them have it.
        if user == ctx.author:
            await ctx.send(embed=discord.Embed(
                title="Hello darkness my old friend...",
                url="https://www.youtube.com/watch?v=4zLfCnGVeL4",
                description="Permissions willing, you will be banned in 30 seconds. Thank you for using the WolfBot "
                            "suicide booth. On behalf of the DIY Tech Discord, we wish you the best of luck in your "
                            "next life, provided such a thing even exists.",
                color=0x000000
            ))
            await asyncio.sleep(30)
            await ctx.guild.ban(user, reason="User requested self-ban through /hackban")
            return

        # Make sure we don't ban an existing member of the Discord.
        if ctx.guild.get_member(user.id) is not None:
            await ctx.send(embed=discord.Embed(
                title="Mod Toolkit",
                description="User `" + str(user) + "` may not be hackbanned, as they are an active member of the "
                                                   "guild. Use the `/ban` command instead.",
                color=Colors.DANGER
            ))
            return

        # Finally, ban the (in-cache) user, and inform the context of the ban.
        await ctx.guild.ban(user, reason="[By " + str(ctx.author) + " - HACKBAN] " + reason, delete_message_days=1)

        await ctx.send(embed=discord.Embed(
            title="Mod Toolkit",
            description="User `" + str(user) + "` was successfully banned.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="unautoban", aliases=["pardon", "unban", "unhackban", "pardonautoban", "pardonhackban"],
                      brief="Pardon a banned member not on the guild")
    @commands.has_permissions(ban_members=True)
    async def unhackban(self, ctx: discord.ext.commands.Context, user_id: int):
        try:
            user = await self.bot.get_user_info(user_id)
        except discord.NotFound:
            await ctx.send(embed=discord.Embed(
                title="Mod Toolkit",
                description="User ID `" + str(user_id) + "` could not be hackbanned. Do they even exist?",
                color=Colors.DANGER
            ))
            return

        try:
            await ctx.guild.unban(user, reason="Unbanned by " + str(ctx.author))
        except discord.NotFound:
            await ctx.send(embed=discord.Embed(
                title="Mod Toolkit",
                description="User `" + str(user) + "` is not banned on this guild, so they can not be unbanned.",
                color=Colors.WARNING
            ))
            return

        await ctx.send(embed=discord.Embed(
            title="Mod Toolkit",
            description="User `" + str(user) + "` was successfully pardoned.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="ban", brief="Ban an active user of the Discord")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: discord.Member, *, reason: str):
        if ctx.message.author == user:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description="No matter how much you hate yourself, you can not use this command to "
                            + "ban yourself. Try `/hackban` instead?",
                color=Colors.DANGER
            ))
            return

        if user.top_role.position >= ctx.message.author.top_role.position:
            await ctx.send(embed=discord.Embed(
                title="Moderator Toolkit",
                description="User `" + str(
                    user) + "` could not be banned, as they are not below you in the role hierarchy.",
                color=Colors.DANGER
            ))
            return

        await ctx.guild.ban(user, reason="[By " + str(ctx.author) + "] " + reason, delete_message_days=1)

        await ctx.send(embed=discord.Embed(
            title="Ka-Ban!",
            description="User `" + str(user) + "` was successfully banned.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="warn", brief="Issue an official warning to a user.", enabled=False)
    @commands.has_permissions(ban_members=True)
    async def warn(self, ctx: discord.ext.commands.Context, target: discord.Member, *, reason: str):
        pass

    @commands.command(name="mute", brief="Temporarily mute a user from the current channel", enabled=False)
    @commands.has_permissions(manage_messages=True)
    async def mute(self, ctx: discord.ext.commands.Context, target: discord.Member, *, reason: str):
        # ToDo: Implement database, and better logging.
        pass

    @commands.command(name="globalmute", aliases=["gmute"],
                      brief="Temporarily mute a user from the guild", enabled=False)
    @commands.has_permissions(ban_members=True)
    async def globalmute(self, ctx: discord.ext.commands.Context, target: discord.Member, *,
                         reason: str):
        pass

    @commands.command(name="roleping", brief="Ping all users with a certain role")
    @commands.has_permissions(manage_roles=True)
    async def roleping(self, ctx: commands.Context, target: discord.Role, *, message: str):
        is_role_mentionable = target.mentionable

        if not is_role_mentionable:
            await target.edit(reason="Role Ping requested by " + str(ctx.message.author), mentionable=True)

        await ctx.send(target.mention + " <" + ctx.message.author.display_name + "> " + message)

        if not is_role_mentionable:
            await target.edit(reason="Role Ping requested by " + str(ctx.message.author)
                                     + " completed", mentionable=False)

    @commands.command(name="cleanup", aliases=["mcu", "bulkdelete"], brief="Clean up many messages quickly")
    @commands.has_permissions(manage_messages=True)
    async def cleanup(self, ctx: commands.Context, lookback: int, *, filter: str = None):
        """
        Quickly and easily delete multiple messages.

        This supports an advanced filtering system, currently supporting the following flags:

        - --[user|member|author] <user reference> : Filter by a specific user
        - --[regex] <regex>                       : Filter by a regular expression

        If multiple filters of the same type are used, *any* will match to delete the message. For example, running
        "/cleanup 100 --user 123 --user 456" will delete all messages posted by users 123 and 456 that it finds in the
        last 100 messages.

        If differing filters are used, *both* must match. That is, "/cleanup 10 --user 123 --regex cat" will delete all
        messages from user 123 that match the regex `cat`.

        These can be combined, so "/cleanup 100 --user 123 --user 456 --regex cat" will delete any mention of regex
        `cat` by users 123 or 456 in the last 100 messages.

        The "lookback" value is the number of messages to search for messages that match the defined filters. If no
        filters are defined, then *all* messages match, and lookback will be the total number of messages to delete.
        """

        # BE VERY CAREFUL TOUCHING THIS METHOD!
        def generate_cleanup_filter(ctx: commands.Context, filter_def: str):
            if filter_def is None:
                return None

            content_list = filter_def.split('--')

            # Filter types
            regex_list = []
            user_list = []

            for filter_candidate in content_list:
                if filter_candidate is None or filter_candidate == '':
                    continue

                filter_candidate = filter_candidate.strip()
                filter_candidate = filter_candidate.split(" ", 1)

                if filter_candidate[0] in ["user", "author", "member"]:
                    user_id = WolfUtils.get_user_id_from_arbitrary_str(ctx.guild, filter_candidate[1])
                    user_list.append(user_id)
                elif filter_candidate[0] in ["regex"]:
                    regex_list.append(filter_candidate[1])
                else:
                    raise KeyError("Filter {} is not valid!".format(filter_candidate[0]))

            def dynamic_check(message: discord.Message):
                if len(user_list) > 0 and message.author.id not in user_list:
                    return False

                for regex in regex_list:
                    if len(regex_list) > 0 and re.search(regex, message.content) is None:
                        return False

                return True

            return dynamic_check

        await ctx.channel.purge(limit=lookback + 1, check=generate_cleanup_filter(ctx, filter), bulk=True)


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(ModTools(bot))
