import discord
from discord.ext import commands


async def get_superusers(app_info: discord.AppInfo) -> []:
    su_list = []

    if app_info.team:
        for team_member in app_info.team.members:
            if team_member.membership_state == discord.TeamMembershipState.accepted and not team_member.bot:
                su_list.append(team_member.id)
    else:
        su_list.append(app_info.owner.id)

    return list(set(su_list))


def superuser_check():
    """
    Check if the user is a bot developer.
    :return: Returns TRUE if the command can be run, FALSE otherwise.
    """

    def predicate(ctx: commands.Context):

        if ctx.author.id in ctx.bot.superusers:
            return True
        else:
            raise commands.MissingPermissions(["BOT_SUPERUSER"])

    return commands.check(predicate)
