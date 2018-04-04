import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


class Community:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.getConfig()
        LOG.info("Loaded plugin!")

    @commands.command(name="staff", aliases=["stafflist"], brief="Get an up-to-date list of all staff on the guild")
    async def stafflist(self, ctx: commands.Context):
        mod_role = discord.utils.get(ctx.guild.roles, id=self._config.get("specialRoles", {})
                                     .get(SpecialRoleKeys.MODS.value))
        admin_role = discord.utils.get(ctx.guild.roles, id=self._config.get("specialRoles", {})
                                       .get(SpecialRoleKeys.ADMINS.value))

        embed = discord.Embed(
            title=Emojis.SHIELD + " Staff List",
            description="The following users are currently staff members on {}.".format(ctx.guild.name),
            color=Colors.INFO
        )

        embed.add_field(name="Owner", value=ctx.guild.owner.mention, inline=False)

        admins = []
        if admin_role is not None:
            for staff in admin_role.members:
                if (staff == ctx.guild.owner) or staff.bot:
                    continue

                admins.append(staff.mention)

            if len(admins) > 0:
                embed.add_field(name=admin_role.name, value=", ".join(admins[::-1]), inline=False)

        mods = []
        if mod_role is not None:
            for staff in mod_role.members:
                # no dupes
                if (staff.mention in admins) or (staff == ctx.guild.owner) or staff.bot:
                    continue

                mods.append(staff.mention)

            if len(mods) > 0:
                embed.add_field(name=mod_role.name, value=", ".join(mods[::-1]), inline=False)

        await ctx.send(embed=embed)

    @commands.group(name="rules", brief="Get a copy of the guild rules")
    async def rules(self, ctx: commands.Context):
        if ctx.invoked_subcommand is not None:
            return

        rules_list = self._config.get("guildRules", [])

        if len(rules_list) == 0:
            await ctx.send(embed=discord.Embed(
                title="Guild Rules",
                description="No guild rules have been defined! Administrators can use `/rules add` to create new "
                            "rules",
                color=Colors.DANGER
            ))
            return

        rule_embed = discord.Embed(
            title=Emojis.BOOKMARK2 + "Guild Rules for {}".format(ctx.guild.name),
            description="The following rules have been defined by the staff members. Please make sure you understand "
                        "them before participating.",
            color=Colors.INFO
        )

        for i in range(len(rules_list)):
            rule = rules_list[i]

            rule_embed.add_field(name="{}. {}".format(i + 1, rule['title']), value=rule['description'], inline=False)

        await ctx.send(embed=rule_embed)

    @rules.command(name="add", brief="Add a new rule to the system")
    @commands.has_permissions(administrator=True)
    async def add_rule(self, ctx: commands.Context, title: str, *, description: str):
        rules_list = self._config.get("guildRules", [])

        rules_list.append({"title": title, "description": description})

        self._config.set("guildRules", rules_list)

        await ctx.send(embed=discord.Embed(
            title="Guild Rule Added!",
            description="Your rule (titled **{}**) has been successfully added to the rules list.".format(title),
            color=Colors.SUCCESS
        ))

    @rules.command(name="remove", brief="Remove a rule from the system")
    @commands.has_permissions(administrator=True)
    async def remove_rule(self, ctx: commands.Context, index: int):
        rules_list = self._config.get("guildRules", [])

        try:
            rules_list.remove(index - 1)
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Guild Rule Removal Failed",
                description="Guild Rule number {} does not exist.".format(index),
                color=Colors.SUCCESS
            ))
            return

        self._config.set("guildRules", rules_list)

        await ctx.send(embed=discord.Embed(
            title="Guild Rule Removed!",
            description="Guild Rule number {} was removed from the rules list.".format(index),
            color=Colors.SUCCESS
        ))

    @rules.command(name="edit", brief="Change the description of a rule")
    @commands.has_permissions(administrator=True)
    async def edit_rule(self, ctx: commands.Context, index: int, *, new_description: str):
        rules_list = self._config.get("guildRules", [])

        try:
            rule = rules_list[index - 1]
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Guild Rule Edit Failed",
                description="Guild Rule number {} does not exist.".format(index),
                color=Colors.SUCCESS
            ))
            return

        rule['description'] = new_description

        self._config.set("guildRules", rules_list)

        await ctx.send(embed=discord.Embed(
            title="Guild Rule Description Updated!",
            description="Your rule (index {}) has had its description updated.".format(index),
            color=Colors.SUCCESS
        ))

    @rules.command(name="rename", brief="Rename a rule")
    @commands.has_permissions(administrator=True)
    async def rename_rule(self, ctx: commands.Context, index: int, *, new_title: str):
        rules_list = self._config.get("guildRules", [])

        try:
            rule = rules_list[index - 1]
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Guild Rule Rename Failed",
                description="Guild Rule number {} does not exist.".format(index),
                color=Colors.SUCCESS
            ))
            return

        rule['title'] = new_title

        self._config.set("guildRules", rules_list)

        await ctx.send(embed=discord.Embed(
            title="Guild Rule Title Updated!",
            description="Your rule (index {}) has had its title updated.".format(index),
            color=Colors.SUCCESS
        ))

    @commands.group(name="invite", brief="Get this guild's invite link")
    async def get_invite(self, ctx: commands.Context):
        if ctx.invoked_subcommand is not None:
            return

        embed = discord.Embed(
            title="{} Invite Link".format(ctx.guild.name),
            description="Want to invite your friends? Awesome! Share this handy invite link with them to get them into "
                        "the fun.",
            color=Colors.INFO
        )

        embed.set_thumbnail(url=ctx.guild.icon_url)

        try:
            invite = await ctx.guild.vanity_invite()
            invite_url = invite.url

            invite_url.replace("http", "https")
        except discord.HTTPException:
            invite_fragment = self._config.get("inviteKey")

            if invite_fragment is None:
                await ctx.send(embed=discord.Embed(
                    title="No Invite Link defined!",
                    description="This guild doesn't appear to have a configured vanity URL or preferred invite key. "
                                "Please ask an administrator for assistance.",
                    color=Colors.DANGER
                ))
                return

            invite_url = "https://discord.gg/{}".format(invite_fragment)

        embed.add_field(name="Invite Link", value="[`{}`]({})".format(invite_url, invite_url), inline=False)

        await ctx.send(embed=embed)

    @get_invite.command(name="set", brief="Set a preferred invite URL")
    @commands.has_permissions(administrator=True)
    async def set_invite(self, ctx: commands.Context, fragment: str):
        self._config.set("inviteKey", fragment)

        await ctx.send(embed=discord.Embed(
            title="Invite Link Set!",
            description="The server invite link was set to https://discord.gg/{}.".format(fragment),
            color=Colors.SUCCESS
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(Community(bot))
