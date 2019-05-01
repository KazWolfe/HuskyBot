import inspect
from abc import abstractmethod, ABCMeta

import discord
from discord.ext import commands
from discord.ext.commands import MissingPermissions


class AntiSpamModule(commands.Group, metaclass=ABCMeta):
    """
    Base module for AntiSpam Modules.
    """

    def register_commands(self, plugin):
        for c in self.commands:
            c.cog = plugin

    @abstractmethod
    def cleanup(self):
        raise NotImplementedError

    @abstractmethod
    async def on_message(self, message: discord.Message):
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

    def classhelp(self):
        return inspect.cleandoc(self.__doc__)
