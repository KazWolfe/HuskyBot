from discord.ext import commands

def has_guild_permissions(**perms):
    """
    Check if a user (as determined by ctx.author) has guild-level permissions to run this command.
    :param perms: A list of perms (e.x. manage_messages=True) to check
    :return: Returns TRUE if the command can be run, FALSE otherwise.
    """

    def predicate(ctx: commands.Context):
        permissions = ctx.author.guild_permissions

        missing = [perm for perm, value in perms.items() if getattr(permissions, perm, None) != value]

        if not missing:
            return True

        raise commands.MissingPermissions(missing)

    return commands.check(predicate)


def is_superuser():
    """
    Check if the user is a bot developer.
    :return: Returns TRUE if the command can be run, FALSE otherwise.
    """

    def predicate(ctx: commands.Context):
        failure_reasons = []

        # Devs must have admin, or must be in a DM context
        if (ctx.guild is not None) and (not ctx.author.guild_permissions.administrator):
            failure_reasons.append("Administrator")

        if ctx.author.id not in ctx.bot.superusers:
            failure_reasons.append("Superuser")

        if len(failure_reasons) == 0:
            return True
        else:
            raise commands.MissingPermissions(failure_reasons)

    return commands.check(predicate)
