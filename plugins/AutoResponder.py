import json
import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot import WolfUtils
from WolfBot.WolfStatics import Colors

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class AutoResponder:
    """
    The AutoResponder plugin allows staff members to generate simple non-interactive commands quickly, easily, and
    without code changes.

    The AutoResponder plugin watches all messages sent across all channels, and checks if a sent message begins with a
    string of defined characters. If so, it will load the appropriate response and then reply in the same context.

    Responses can be restricted to use by only certain roles, or only in certain channels. Multiple roles may be
    permitted to use an auto response. If *any* role matches, the bot will respond. Likewise, the bot may also be
    configured to only reply to certain channels. If both roles and channels are defined, both checks must be satisfied.
    """
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()
        self._session_store = WolfConfig.get_session_store()
        LOG.info("Loaded plugin!")

    #   responses: {
    #       "someString": {
    #           "requiredRoles": [],             // Any on the list, *or* MANAGE_MESSAGES
    #           "allowedChannels": [],           // If none, global.
    #           "isEmbed": False                 // Determine whether to treat as embed or whatever
    #           "response": "my response"
    #       }
    #   }

    async def on_message(self, message: discord.Message):
        if not WolfUtils.should_process_message(message):
            return

        if message.author.id in self._config.get('userBlacklist', []):
            return

        if self._session_store.get('lockdown', False):
            return

        responses = self._config.get("responses", {})

        for response in responses.keys():
            if not (message.content.lower().startswith(response.lower())):
                continue

            if not ((responses[response].get('allowedChannels') is None)
                    or (message.channel.id in responses[response].get('allowedChannels'))):
                continue

            if WolfUtils.member_has_any_role(message.author, responses[response].get('requiredRoles')) \
                    or bool(message.author.permissions_in(message.channel).manage_messages):
                if responses[response].get('isEmbed', False):
                    await message.channel.send(content=None,
                                               embed=discord.Embed.from_data(responses[response]['response']))
                else:
                    await message.channel.send(content=responses[response]['response'])

    @commands.group(name="responses", aliases=["response"], brief="Manage the AutoResponder plugin")
    @commands.has_permissions(manage_messages=True)
    async def responses(self, ctx: discord.ext.commands.Context):
        """
        This is the parent command for the AutoResponder plugin.

        It by default does nothing, but simply exists as a container for the other commands. See the below command list
        for valid commands to pass to the plugin.
        """

        pass

    @responses.command(name="add", aliases=["create"], brief="Add a new automatic response")
    @commands.has_permissions(manage_messages=True)
    async def add_response(self, ctx: discord.ext.commands.Context, trigger: str, response: str):
        """
        Add a new response to the configuration.

        By default, this will create a new response (with trigger `trigger`) that spits back `response` as plaintext.
        This will only be usable in the current channel by users with the MANAGE_MESSAGES permission (that is, can pin
        or delete messages). These settings allow the creation/use of a "stage" to ensure the response works as
        intended.

        If you would like to alter the configuration of a created response, please use the /responses edit command.
        """

        responses = self._config.get("responses", {})

        new = {}

        if trigger in responses.keys():
            await ctx.send(embed=discord.Embed(
                title="Response Manager",
                description="The response you have tried to create already exists. Delete it first.",
                color=Colors.DANGER
            ))
            return

        if trigger.startswith(self.bot.command_prefix):
            await ctx.send(embed=discord.Embed(
                title="Response Manager",
                description="Responses may not start with the command prefix (`{}`)!".format(self.bot.command_prefix),
                color=Colors.DANGER
            ))
            return

        new['isEmbed'] = False
        new['response'] = response
        new['requiredRoles'] = []  # empty set = MANAGE_MESSAGES only
        new['allowedChannels'] = [ctx.channel.id]

        responses[trigger.lower()] = new
        self._config.set('responses', responses)
        await ctx.send(embed=discord.Embed(
            title="Response Manager",
            description="Your response has been created. It may be used by users with `MANAGE_MESSAGES` in the "
                        + "current channel. To change this, use `/responses edit`",
            color=Colors.SUCCESS
        ))

    @responses.command(name="edit", brief="Alter an existing automatic response")
    @commands.has_permissions(manage_messages=True)
    async def edit_response(self, ctx: discord.ext.commands.Context, trigger: str, param: str, action: str, *,
                            value: str = None):
        """
        Advanced editor for responses.

        This command is a utility command, meaning it has some rather interesting subcommands. The format of the command
        is described above. "Actions" are a subset of "Params". The mapping is available below:

        | PARAMETER       | ACTION         | DESCRIPTION                                                  |
        |-----------------|----------------|--------------------------------------------------------------|
        | response        | set            | Set a new plain-text response for the specified trigger.     |
         --               | json           | Set a new JSON embed for the specified trigger.              |
                          |                |                                                              |
        | requiredRoles   | set            | Set a new comma-separated list of required roles.            |
         --               | add            | Add a new required role to use the specified trigger.        |
         --               | remove         | Remove a required role from the trigger permission set.      |
         --               | clear          | Clear the list of required roles for this trigger.           |
                          |                |                                                              |
        | allowedChannels | set            | Set a new comma-separated list of channels for this trigger. |
         --               | add            | Add a new channel allowed to use this trigger.               |
         --               | remove         | Remove a channel from the allowed list for this trigger.     |
         --               | clear          | Clear the allowed channels list for this trigger             |

        To set a response as usable everywhere by everyone, simply run these commands:
            /responses edit !myTrigger allowedChannels clear
            /responses edit !myTrigger requiredRoles clear
        """

        responses = self._config.get("responses", {})

        try:
            response = responses[trigger.lower()]
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Response Manager",
                description="The trigger `" + trigger + "` does not exist. Please create it first.",
                color=Colors.DANGER
            ))
            return

        if param == 'response':
            if response.get('isEmbed', False):
                await ctx.send(embed=discord.Embed(
                    title="Response Manager",
                    description="Unable to edit embedded responses after creation!",
                    color=Colors.DANGER
                ))
                return

            if action.lower() == 'set':
                response['isEmbed'] = False
                response['response'] = value
            elif action.lower() == 'json':
                json_obj = json.loads(value)

                response['response'] = json_obj
                response['isEmbed'] = True

            else:
                await ctx.send(embed=discord.Embed(
                    title="Response Manager",
                    description="Valid actions for `response` are: **`set`**, **`json`**.",
                    color=Colors.DANGER
                ))
                return
        elif param == 'requiredRoles' or param == 'allowedChannels':
            if action.lower() == 'set':
                if not value.replace(',', '').isdigit():
                    await ctx.send(embed=discord.Embed(
                        title="Response Manager",
                        description="Setting parameter `" + param + "` requires a comma-separated list of numbers.",
                        color=Colors.DANGER
                    ))
                    return

                new_values = []
                for v in value.split(','):
                    new_values.append(int(v))

                response[param] = new_values

            elif action.lower() == 'add' or action.lower() == 'remove':
                try:
                    val = int(value)
                except ValueError:
                    await ctx.send(embed=discord.Embed(
                        title="Response Manager",
                        description="Modifying parameter `" + param + "` requires a single number.",
                        color=Colors.DANGER
                    ))
                    return

                if response[param] is None:
                    response[param] = []

                if action.lower() == "add":
                    response[param].append(val)
                else:
                    response[param].remove(val)

            elif action.lower() == 'clear':
                response[param] = None

            else:
                await ctx.send(embed=discord.Embed(
                    title="Response Manager",
                    description="Valid actions for `response` are: **`set`**, **`add`**, **`remove`**, **`clear`**.",
                    color=Colors.DANGER
                ))
                return
        else:
            await ctx.send(embed=discord.Embed(
                title="Response Manager",
                description="You may only edit **`requiredRoles`**, **`allowedChannels`**, or **`response`**.",
                color=Colors.DANGER
            ))
            return

        self._config.set('responses', responses)

        # Done, let's inform the user
        confirmation = discord.Embed(
            title="Response Manager",
            description="The response for `" + trigger + "` has been updated.",
            color=Colors.SUCCESS
        )

        for k in response.keys():
            confirmation.add_field(name=k, value=response[k], inline=True)

        await ctx.send(embed=confirmation)

    @responses.command(name="delete", aliases=["remove"], brief="Delete an existing automatic response")
    @commands.has_permissions(manage_messages=True)
    async def delete_response(self, ctx: discord.ext.commands.Context, trigger: str):
        """
        Delete a response from the database.

        Given a trigger (of type string), remove it and its configuration from the guild.
        """

        responses = self._config.get("responses", {})

        try:
            responses[trigger.lower()]
        except KeyError:
            await ctx.send(embed=discord.Embed(
                title="Response Manager",
                description="The trigger `" + trigger + "` does not exist, so can't delete.",
                color=Colors.DANGER
            ))
            return

        responses.pop(trigger.lower())
        self._config.set('responses', responses)

        await ctx.send(embed=discord.Embed(
            title="Response Manager",
            description="The response named `" + trigger + "` has been deleted.",
            color=Colors.SUCCESS
        ))

    @responses.command(name="list", brief="List all registered automatic responses")
    @commands.has_permissions(manage_messages=True)
    async def list_responses(self, ctx: discord.ext.commands.Context):
        """
        List all available responses.

        This command will list all responses allowed on the guild as a whole. It takes no arguments.
        """

        responses = self._config.get("responses", {})

        await ctx.send(embed=discord.Embed(
            title="Response Manager",
            description="The following responses are available:\n```- " + "\n- ".join(responses.keys()) + "```",
            color=Colors.SUCCESS
        ))

    @responses.command(name="deleteAll", hidden=True)
    @commands.has_permissions(administrator=True)
    async def purge(self, ctx: discord.ext.commands.Context):
        """
        Debug commands have no help. If you need help running a debug command, just don't.
        """

        self._config.set('responses', {})

        await ctx.send(embed=discord.Embed(
            title="Response Manager",
            description="All responses purged.",
            color=Colors.SUCCESS
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(AutoResponder(bot))
