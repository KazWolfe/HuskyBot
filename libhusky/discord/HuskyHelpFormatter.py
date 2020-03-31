"""
Originally from Rapptz's DiscordPy, under MIT license.

Modified by KazWolfe for HuskyBot, and likely botched beyond belief.
"""

import itertools
import re

import discord
from discord.ext.commands import DefaultHelpCommand, Paginator


class HuskyHelpFormatter(DefaultHelpCommand):
    """
    A modified help formatter that does some things differently.
    """

    def __init__(self, **options):
        self.asciidoc_prefix = "```asciidoc"
        self.paginator = Paginator(prefix=self.asciidoc_prefix)
        self.commands_heading = "Commands\n--------"

        super().__init__(paginator=self.paginator, commands_heading=self.commands_heading, **options)

    def preprocess_message_newlines(self, doc) -> str:
        regex = r"(?<![\r\n])(\r?\n|\r)(?![\r\n]|\-+|\s+)"

        return re.sub(regex, ' ', doc)

    def get_command_signature(self, command):
        parent = command.full_parent_name
        alias = command.name if not parent else parent + ' ' + command.name
        signature = command.signature + " " if command.signature else ""

        return '%s%s %s:: **%s**' % (self.clean_prefix, alias, signature, command.brief)

    def add_indented_commands(self, commands, *, heading, max_size=None):
        if not commands:
            return

        self.paginator.add_line(heading)
        max_size = max_size or self.get_max_size(commands)

        # noinspection PyProtectedMember
        get_width = discord.utils._string_width

        for command in commands:
            name = command.name
            width = max_size - (get_width(name) - len(name))
            entry = '{0}{1:<{width}} :: {2}'.format(self.indent * ' ', name, command.short_doc, width=width)
            self.paginator.add_line(self.shorten_text(entry))

    async def prepare_help_command(self, ctx, command):
        # The more upstream changes break my help formatter, the more I think I'm insane for making
        # the help formatter so terrible.
        #
        # Oh well.
        self.context = ctx
        await super().prepare_help_command(ctx, command)

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot

        if bot.description:
            # <description> portion
            self.paginator.add_line(bot.description, empty=True)

        no_category = '\u200b{0.no_category}:'.format(self)

        def get_category(command):
            cog = command.cog
            name = cog.qualified_name if cog is not None else no_category
            return name + "\n" + "-" * len(name)

        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        max_size = self.get_max_size(filtered)
        to_iterate = itertools.groupby(filtered, key=get_category)

        # Now we can add the commands to the page.
        for category, commands in to_iterate:
            commands = sorted(commands, key=lambda c: c.name) if self.sort_commands else list(commands)
            self.add_indented_commands(commands, heading=category, max_size=max_size)

        note = self.get_ending_note()
        if note:
            self.paginator.add_line()
            self.paginator.add_line(note)

        await self.send_pages()

    def add_command_formatting(self, command):
        """A utility function to format the non-indented block of commands and groups.

        Parameters
        ------------
        command: :class:`Command`
            The command to format.
        """

        # ToDo: Codesmell, this overrides `help` for the command. Not the best, but relatively safe.

        if command.help:
            pretty_helpdoc = self.preprocess_message_newlines(command.help)
            lines = []

            for line in pretty_helpdoc.splitlines():
                if "<!nodoc>" in line:
                    continue

                lines.append(line)

            command.help = "\n".join(lines)

        super().add_command_formatting(command)

    async def send_cog_help(self, cog):
        # ToDo: Codesmell, this overrides `__cog_cleaned_doc` for the cog. Not the best, but relatively safe.

        if cog.description:
            cog.__cog_cleaned_doc__ = self.preprocess_message_newlines(cog.description)

        await super().send_cog_help(cog)
