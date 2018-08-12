import discord
from discord.ext import commands
from discord.ext.commands import MissingPermissions


class AntiSpamModule(commands.Group):
    def cleanup(self):
        raise NotImplementedError

    async def on_message(self, message: discord.Message):
        raise NotImplementedError

    async def base(self, ctx: commands.Context):
        pass

    @staticmethod
    def has_permissions(**perms):
        def predicate(ctx):
            ch = ctx.channel
            permissions = ch.permissions_for(ctx.author)

            missing = [perm for perm, value in perms.items() if getattr(permissions, perm, None) != value]

            if not missing:
                return True

            raise MissingPermissions(missing)

        return predicate
