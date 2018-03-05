import logging

import discord
from discord.ext import commands

from BotCore import BOT_CONFIG
from WolfBot import WolfUtils
from WolfBot.WolfEmbed import Colors

LOG = logging.getLogger("DiyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class AutoResponder:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot

    async def on_ready(self):
        LOG.info("Enabled plugin!")
        
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

        responses = BOT_CONFIG.get("responses", {})

        for response in responses.keys():
            if not (message.content.lower().startswith(response.lower())):
                continue

            if not ((responses[response].get('allowedChannels') is None)
                    or (message.channel.id in responses[response].get('allowedChannels'))):
                continue

            if WolfUtils.memberHasAnyRole(message.author, responses[response].get('requiredRoles')) \
                    or bool(message.author.permissions_in(message.channel).manage_messages):
                if responses[response].get('isEmbed', False):
                    await message.channel.send(content=None,
                                               embed=discord.Embed.from_data(responses[response]['response']))
                else:
                    await message.channel.send(content=responses[response]['response'])

    @commands.group(name="responses", brief="Manage the AutoResponder plugin")
    async def responses(self, ctx: discord.ext.commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=discord.Embed(
                title="Response Manager",
                description="The command you have requested is not available.",
                color=Colors.DANGER
            ))
            return

    @responses.command(name="add", aliases=["create"], brief="Add a new automatic response")
    @commands.has_permissions(manage_messages=True)
    async def addResponse(self, ctx: discord.ext.commands.Context, trigger: str, response: str):
        responses = BOT_CONFIG.get("responses", {})

        new = {}

        if trigger in responses.keys():
            await ctx.send(embed=discord.Embed(
                title="Response Manager",
                description="The response you have tried to create already exists. Delete it first.",
                color=Colors.DANGER
            ))
            return

        new['isEmbed'] = False
        new['response'] = response
        new['requiredRoles'] = []
        new['allowedChannels'] = [ctx.channel.id]

        responses[trigger.lower()] = new
        BOT_CONFIG.set('responses', responses)
        await ctx.send(embed=discord.Embed(
            title="Response Manager",
            description="Your response has been created. It may be used by users with MANAGE_MESSAGES in the "
                        + "current channel. To change this, use `/responses editResponse`",
            color=Colors.SUCCESS
        ))

    @responses.command(name="edit", brief="Alter an existing automatic response")
    @commands.has_permissions(manage_messages=True)
    async def editResponse(self, ctx: discord.ext.commands.Context, trigger: str, param: str, action: str,
                           value: str = None):
        responses = BOT_CONFIG.get("responses", {})

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
                response['response'] = value
            else:
                await ctx.send(embed=discord.Embed(
                    title="Response Manager",
                    description="Valid actions for `response` are: **`set`**.",
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

        BOT_CONFIG.set('responses', responses)

        # Done, let's inform the user
        confirmation = discord.Embed(
            title="Response Manager",
            description="The response for `" + trigger + "` has been updated.",
            color=Colors.DANGER
        )

        for k in response.keys():
            confirmation.add_field(name=k, value=response[k], inline=True)

        await ctx.send(embed=confirmation)

    @responses.command(name="delete", aliases=["remove"], brief="Delete an existing automatic response")
    @commands.has_permissions(manage_messages=True)
    async def deleteResponse(self, ctx: discord.ext.commands.Context, trigger: str):
        responses = BOT_CONFIG.get("responses", {})

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
        BOT_CONFIG.set('responses', responses)

        await ctx.send(embed=discord.Embed(
            title="Response Manager",
            description="The response named `" + trigger + "` has been deleted.",
            color=Colors.SUCCESS
        ))

    @responses.command(name="list", brief="List all registered automatic responses")
    @commands.has_permissions(manage_messages=True)
    async def listResponses(self, ctx: discord.ext.commands.Context):
        responses = BOT_CONFIG.get("responses", {})

        await ctx.send(embed=discord.Embed(
            title="Response Manager",
            description="The following responses are available:\n```- " + "\n- ".join(responses.keys() + "```"),
            color=Colors.SUCCESS
        ))

    @responses.command(name="deleteAll", hidden=True)
    @commands.has_permissions(administrator=True)
    async def purge(self, ctx: discord.ext.commands.Context):
        BOT_CONFIG.set('responses', {})

        await ctx.send(embed=discord.Embed(
            title="Response Manager",
            description="All responses purged.",
            color=Colors.SUCCESS
        ))

        
def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(AutoResponder(bot))
