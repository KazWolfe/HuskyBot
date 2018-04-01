from discord.ext import commands


def has_server_permissions(**perms):
    """
    Check if a user (as determined by ctx.author) has server-level permissions to run this command.
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
