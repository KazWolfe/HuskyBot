import asyncio
import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfConverters
from WolfBot import WolfUtils
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class GuildSecurity:
    """
    GuildSecurity is a plugin designed to add more security to Discord guilds.

    It will prevent user promotions in a number of cases, as well as protect the guild from unauthorized bots
    and other potentially nefarious actions
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()
        self._guildsecurity_store = WolfConfig.get_session_store("guildSecurity")
        LOG.info("Loaded plugin!")

    async def on_member_join(self, member: discord.Member):
        async def prevent_bot_joins():
            if not member.bot:
                # ignore non-bots
                return

            permitted_bots = self._guildsecurity_store.get('permittedBotList', [])

            if member.id not in permitted_bots:
                await member.kick(reason="[AUTOMATIC KICK - Guild Security] User is not an authorized bot.")

        await prevent_bot_joins()

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        async def protect_roles():
            if before.roles == after.roles:
                return

            sec_config = self._config.get('guildSecurity', {})
            protected_roles = sec_config.get('protectedRoles', [])
            allowed_promotions = self._guildsecurity_store.get('allowedPromotions', {})
            allowed_promotions_for_user = allowed_promotions.get(after.id, [])

            new_roles = list(set(after.roles).difference(before.roles))

            for r in new_roles:
                if r.id in protected_roles and r.id not in allowed_promotions_for_user:
                    await after.remove_roles(r, reason="Unauthorized grant of protected role")
                    LOG.info("A protected role {} was granted to {} without prior authorization. "
                             "Removed.".format(r, after))

        async def lockdown_bot_role():
            if before.roles == after.roles:
                return

            special_roles = self._config.get("specialRoles", {})

            if special_roles.get('bots') is None:
                return

            bot_role = discord.utils.get(after.roles, id=int(special_roles.get('bots')))

            if (bot_role is not None) and (bot_role not in before.roles) and (not before.bot):
                await after.remove_roles(bot_role, reason="User is not an authorized bot.")
                LOG.info("User {} was granted bot role, but was not a bot. Removing.".format(after))

        asyncio.ensure_future(protect_roles())
        asyncio.ensure_future(lockdown_bot_role())

    @commands.group(name="guildsecurity", brief="Manage the Guild Security plugin", aliases=["gs", "guildsec"])
    @commands.has_permissions(manage_guild=True)
    async def guildsecurity(self, ctx: commands.Context):
        """
        This command is a virtual group to manage guild security.

        Please see below for the command list:
        """
        pass

    @guildsecurity.command(name="allowBot", brief="Allow a bot to join the guild")
    @commands.has_permissions(administrator=True)
    async def allow_bot(self, ctx: commands.Context, user: WolfConverters.OfflineUserConverter):
        # pycharm codecomplete hack
        user = user  # type: discord.User

        permitted_bots = self._guildsecurity_store.get('permittedBotList', [])  # type: list
        permitted_bots.append(user.id)
        self._guildsecurity_store.set('permittedBotList', permitted_bots)

        await ctx.send(embed=discord.Embed(
            title=Emojis.CHECK + "Bot allowed to join guild.",
            description="The bot `{}` has been given permission to join the guild. This permission will be valid until "
                        "DakotaBot restarts.",
            color=Colors.SUCCESS
        ))

    @guildsecurity.command(name="protectRole", brief="Protect a certain role from grants")
    @commands.has_permissions(administrator=True)
    async def protect_role(self, ctx: commands.Context, *, role: discord.Role):
        if role.position >= ctx.guild.get_member(self.bot.user.id).top_role.position:
            raise commands.BadArgument(message="This role can not be protected - it is above the bot's role")

        if role.managed:
            raise commands.BadArgument(message="This role can not be protected - it is managed")

        sec_config = self._config.get('guildSecurity', {})  # type: dict
        protected_roles = sec_config.setdefault('protectedRoles', [])  # type: list

        if role.id in protected_roles:
            await ctx.send(embed=discord.Embed(
                title="Role Already Protected!",
                description="The role {} is already protected by the bot.".format(role.mention),
                color=Colors.WARNING
            ))
            return

        protected_roles.append(role.id)
        self._config.set('guildSecurity', sec_config)

        await ctx.send(embed=discord.Embed(
            title=Emojis.LOCK + "Role Protected!",
            description="The role {} may now only be granted by using `/promote`.".format(role.mention),
            color=Colors.SUCCESS
        ))

    @commands.command(name="promote", brief="Grant a user a protected role", aliases=["addrole"])
    @commands.has_permissions(manage_roles=True)
    async def promote_user(self, ctx: commands.Context, member: discord.Member, *, role: discord.Role):
        if role.managed:
            raise commands.BadArgument(message="This role is a managed role and can not be altered.")

        if role.position >= ctx.author.top_role.position:
            await ctx.send(embed=discord.Embed(
                title="Permission Error",
                description="You are not permitted to promote users to {}, as that role is not below your highest "
                            "role. Please contact an administrator for assistance.".format(role.mention),
                color=Colors.ERROR
            ))
            return

        if role.position >= ctx.guild.get_member(self.bot.user.id).top_role.position:
            raise commands.BadArgument(message="This role is above the bot's role, and can not be promoted to.")

        if role in member.roles:
            await ctx.send(embed=discord.Embed(
                title="Promotion Failed!",
                description="User {} already has role {}, so it can't be assigned again!".format(member, role.mention),
                color=Colors.ERROR
            ))
            return

        confirm_dialog = await ctx.send(embed=discord.Embed(
            title="Confirm Promotion",
            description="You are going to promote user {} to role {}. Is this intended?\n\nTo confirm, react with the "
                        "{} emoji. To cancel, either wait 30 seconds or press the {} "
                        "emoji.".format(member.mention, role.mention, Emojis.CHECK, Emojis.X)
        ))  # type: discord.Message

        await confirm_dialog.add_reaction(Emojis.CHECK)
        await confirm_dialog.add_reaction(Emojis.X)

        reaction, confirming_user = None, None

        try:
            reaction, confirming_user = \
                await self.bot.wait_for('reaction_add', timeout=30.0, check=WolfUtils.confirm_dialog_check(ctx.author))
        except asyncio.TimeoutError as _:
            pass

        confirmed = (reaction is not None) and (reaction.emoji == Emojis.CHECK)
        if confirming_user is None:
            confirming_user = "TIMEOUT"

        await confirm_dialog.clear_reactions()

        if not confirmed:
            await confirm_dialog.edit(embed=discord.Embed(
                title=Emojis.X + " Promotion DENIED",
                description="The promotion of `{}` to {} was **DENIED** by "
                            "{}.".format(member, role.mention, confirming_user),
                color=Colors.DANGER
            ))
            return

        allowed_promotions = self._guildsecurity_store.get('allowedPromotions', {})
        allowed_promotions[member.id] = allowed_promotions.get(member.id, []) + [role.id]
        self._guildsecurity_store.set("allowedPromotions", allowed_promotions)

        await member.add_roles(role, reason="Promoted by {}".format(confirming_user))

        await self.bot.wait_for('member_update', timeout=10.0, check=lambda b, a: role in a.roles)

        allowed_promotions = self._guildsecurity_store.get("allowedPromotions", {})
        allowed_promotions[member.id].remove(role.id)
        self._guildsecurity_store.set("allowedPromotions", allowed_promotions)

        await confirm_dialog.edit(embed=discord.Embed(
            title=Emojis.CHECK + " Promotion APPROVED",
            description="The promotion of `{}` to {} was **APPROVED** by "
                        "{}.\n\nUser has been promoted.".format(member, role.mention, confirming_user),
            color=Colors.SUCCESS
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(GuildSecurity(bot))
