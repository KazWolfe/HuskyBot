"""
Originally from Rapptz's DiscordPy, under MIT license.

Modified by KazWolfe for HuskyBot, and likely botched beyond belief.
"""

import inspect
import itertools

from discord.ext.commands import HelpFormatter, Paginator
from discord.ext.commands.core import Command


class HuskyHelpFormatter(HelpFormatter):
    """
    A modified help formatter that does some things differently.
    """

    def __init__(self):
        self.asciidoc_prefix = "```asciidoc"

        self.paginator = Paginator(prefix=self.asciidoc_prefix)

        super().__init__()

    def _add_subcommands_to_page(self, max_width, commands):
        for name, command in commands:
            if name in command.aliases:
                # skip aliases
                continue

            entry = '  {0:<{width}} :: {1}'.format(name, command.short_doc, width=max_width)
            shortened = self.shorten(entry)
            self.paginator.add_line(shortened)

    async def format(self):
        """Handles the actual behaviour involved with formatting.

        To change the behaviour, this method should be overridden.

        Returns
        --------
        list
            A paginated output of the help command.
        """

        self.paginator = Paginator(prefix=self.asciidoc_prefix)  # re-initialize the paginator here.

        # we need a padding of ~80 or so

        description = self.command.description if not self.is_cog() else inspect.getdoc(self.command)

        if description:
            # <description> portion
            self.paginator.add_line(description, empty=True)

        if isinstance(self.command, Command):
            # <signature portion>
            signature = self.get_command_signature()
            self.paginator.add_line(signature + "\n" + ('-' * len(signature)), empty=True)

            # <long doc> section
            if self.command.help:
                self.paginator.add_line(self.command.help, empty=True)

            # end it here if it's just a regular command
            if not self.has_subcommands():
                self.paginator.close_page()
                return self.paginator.pages

        max_width = self.max_name_size

        def category(tup):
            cog = tup[1].cog_name
            # we insert the zero width space there to give it approximate
            # last place sorting position.
            return cog + "\n" + ('-' * len(cog)) if cog is not None else '\u200bNo Category:\n------------'

        filtered = await self.filter_command_list()
        if self.is_bot():
            data = sorted(filtered, key=category)
            for category, commands in itertools.groupby(data, key=category):
                # there simply is no prettier way of doing this.
                commands = sorted(commands)
                if len(commands) > 0:
                    self.paginator.add_line(category)

                self._add_subcommands_to_page(max_width, commands)
        else:
            filtered = sorted(filtered)
            if filtered:
                self.paginator.add_line('Commands:')
                self._add_subcommands_to_page(max_width, filtered)

        # add the ending note
        self.paginator.add_line()
        ending_note = self.get_ending_note()
        self.paginator.add_line(ending_note)
        return self.paginator.pages
