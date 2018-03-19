import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot.WolfEmbed import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class ModTools:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        LOG.info("Loaded plugin!")

    # Prevent users from becoming bot role if they're not actually bots.
    async def on_member_update(self, before, after):
        if before.roles == after.roles:
            return

        special_roles = WolfConfig.getConfig().get("specialRoles", {})

        if special_roles.get('bots') is None:
            return

        bot_role = discord.utils.get(after.roles, id=int(special_roles.get('bots')))

        if (bot_role is not None) and (bot_role not in before.roles) and (not before.bot):
            await after.remove_roles(bot_role, reason="User is not an authorized bot.")
            LOG.info("User " + after.display_name + " was granted bot role, but was not a bot. Removing.")

    @commands.command(name="autoban", aliases=["hackban"], brief="Ban any user by UID", enabled=False)
    @commands.has_permissions(ban_members=True)
    async def hackban(self, ctx: discord.ext.commands.Context, user: int, *, reason: str):
        await ctx.guild.ban(user, reason="[" + str(ctx.author) + "] " + reason, delete_message_days=1)
        
        await ctx.send(embed=discord.Embed(
            title="Mod Toolkit",
            description="User `" + str(user) + "` was successfully banned.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="unautoban", aliases=["unhackban", "pardonautoban", "pardonhackban"], brief="Pardon a banned member not on the server", enabled=False)
    @commands.has_permissions(ban_members=True)
    async def unhackban(self, ctx: discord.ext.commands.Context, user: int):
        await ctx.guild.unban(user, reason="Unbanned by " + str(ctx.author))
        
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
                description="User `" + str(user) + "` could not be banned, as they are not below you in the role hierarchy.",
                color=Colors.DANGER
            ))
            return
    
        await ctx.guild.ban(user, reason="[" + str(ctx.author) + "] " + reason, delete_message_days=1)
        
        await ctx.send(embed=discord.Embed(
            title="Ka-Ban!",
            description="User `" + str(user) + "` was successfully banned.",
            color=Colors.SUCCESS
        ))
        
    @commands.command(name="unban", alaises=["pardon"], brief="Pardon a currently banned member of the server")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: discord.ext.commands.Context, user: discord.User):
        await ctx.guild.unban(user, reason="Unbanned by " + str(ctx.author))
        
        await ctx.send(embed=discord.Embed(
            title="Mod Toolkit",
            description="User `" + str(user) + "` was successfully pardoned.",
            color=Colors.SUCCESS
        ))

    @commands.command(name="warn", brief="Issue an official warning to a user.", enabled=False)
    @commands.has_permissions(ban_members=True)
    async def warn(self, ctx: discord.ext.commands.Context, target: discord.Member, *, reason: str):
        pass

    @commands.command(name="mute", brief="Temporarily mute a user from the current channel", enabled=False)
    @commands.has_permissions(manage_messages=True)
    async def mute(self, ctx: discord.ext.commands.Context, target: discord.Member, time: str = None, *, reason: str):
        pass

    @commands.command(name="globalmute", aliases=["gmute"],
                      brief="Temporarily mute a user from the server", enabled=False)
    @commands.has_permissions(ban_members=True)
    async def globalmute(self, ctx: discord.ext.commands.Context, target: discord.Member, time: str = None, *,
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


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(ModTools(bot))
