import inspect
from abc import abstractmethod

import discord
from discord.ext import commands
from discord.ext.commands import MissingPermissions, CogMeta


class AntiSpamModule(commands.Group, metaclass=CogMeta):
    """
    Base module for AntiSpam Modules.

    This entire class is a bit of dark magic to (abuse) dpy's Cog feature. It is probably poorly written.

    Due to the modular requirements of antispam, it is important that one be able to dynamically load and unload the
    antispam submodules. As a result, we abuse a dpy cog-like mechanism, while also treating the commands themselves as
    a subcommand. This is probably not the most elegant way of doing this, but it works.

    As such, the "base" cog methods are present here, just for the sake of dpy not throwing errors. It's weird dumb
    magic, and should probably be made better, but the dev is lazy.
    """

    def register_commands(self, plugin):
        for c in self.commands:
            c.cog = self

    @abstractmethod
    def cleanup(self):
        raise NotImplementedError

    @abstractmethod
    async def process_message(self, message: discord.Message, context: str, meta: dict = None):
        raise NotImplementedError

    @abstractmethod
    def clear_for_user(self, user: discord.Member):
        raise NotImplementedError

    @abstractmethod
    def clear_all(self):
        raise NotImplementedError

    async def base(self, ctx):
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

    def cog_check(self, ctx):
        return True

    async def cog_before_invoke(self, ctx):
        pass

    async def cog_after_invoke(self, ctx):
        pass

    async def cog_command_error(self, ctx, error):
        pass

    def classhelp(self):
        return inspect.cleandoc(self.__doc__)
