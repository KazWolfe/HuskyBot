import logging
import os

import discord
from discord.ext import commands

from WolfBot import WolfChecks
from WolfBot import WolfConfig
from WolfBot.WolfStatics import *
from WolfBot.apis import LaMetric as LaMetricApi

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class LaMetric:
    """
    Plugin for interfacing with LaMetric devices based on server events.

    This plugin is still work in progress, and will so far only send notifications on user count changes. In the future,
    this will be configurable and additional events may trigger notifications.
    """

    CONFIG_KEY = "lametric"

    '''
    {
        "devices": {
            "<device_id>": {
                "ownerId": <some user id>,
                "appId": "<some id string>",
                "authToken": "<my auth token>",
                "enabledTasks": [
                    "userCount",
                ]
            }
        }
    }
    '''

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()

        self._pending_registrations = {}
        '''
        {
            <device_id> : <user_id>
        '''

        LOG.info("Loaded plugin!")

    def update_lametric_counts(self, guild: discord.Guild):
        lametric_conf = self._config.get('lametric', {})
        devices = lametric_conf.setdefault('devices', {})

        new_count = str(guild.member_count)

        for device_id in devices.keys():
            device = devices[device_id]

            if "userCount" not in device.get("enabledTasks", []):
                continue

            LOG.info("Updating usercount for LaMetric device ID {}".format(device_id))
            LaMetricApi.push_to_lametric(device['appId'], LaMetricApi.build_data("i18290", new_count),
                                         device['authToken'])

    async def on_member_join(self, member: discord.Member):
        self.update_lametric_counts(member.guild)

    async def on_member_remove(self, member: discord.Member):
        self.update_lametric_counts(member.guild)

    @commands.group(name="lametric", brief="Base command for LaMetric interfaces")
    async def lametric(self, ctx: commands.Context):
        pass

    @lametric.command(name="register", brief="Register a new LaMetric device")
    @WolfChecks.has_guild_permissions(administrator=True)
    async def register(self, ctx: commands.Context):
        """
        Begin the registration process for a LaMetric device.

        This code will initialize a registration for a LaMetric device, and will take you through the second part
        of the registration.
        """
        device_id = os.urandom(4).hex()

        self._pending_registrations[device_id.lower()] = ctx.author.id

        await ctx.send(embed=discord.Embed(
            title="LaMetric Setup",
            description="Please DM the bot with the following command:\n\n"
                        "```/lametric authorize {} your_app_id your_auth_token```\n\n"
                        "Be sure to include the version in your AppID (`abcdef/1`).".format(device_id.lower()),
            color=Colors.INFO
        ))

    @lametric.command(name="authorize", brief="Send the bot an Auth Key", aliases=["auth"])
    async def authorize(self, ctx: commands.Context, device_id: str, app_id: str, auth_key: str):
        """
        Authorize a LaMetric device.

        When a LaMetric device is registered, authorization must be completed. This command allows users to privately
        register their device without leaking credentials. This command may *only* be run from a DM.

        The Device ID is given by the `/lametric register` command initially.

        The App ID is given to you by the LaMetric developer panel. In the POST url, look for "com.lametric.XXXX/1".
        This command will expect the "XXXXXXXXXXX/X" part.

        The Auth Key is given by the developer panel.
        """
        if not isinstance(ctx.channel, discord.DMChannel):
            raise commands.CommandInvokeError("This command may only be run from a DM!")

        if device_id.lower() not in self._pending_registrations.keys():
            raise commands.BadArgument("This Device ID is not known.")

        if ctx.author.id != self._pending_registrations[device_id]:
            raise commands.BadArgument("This Device ID is not known.")

        lametric_conf = self._config.get('lametric', {})
        devices = lametric_conf.setdefault('devices', {})

        verification_key = os.urandom(2).hex().upper()

        devices[device_id.lower()] = {
            "ownerId": ctx.author.id,
            "appId": app_id,
            "authToken": auth_key,
            "enabledTasks": [
                "userCount"
            ],
            "verified": False,
            "verificationKey": verification_key
        }

        self._config.set('lametric', lametric_conf)

        del self._pending_registrations[device_id.lower()]

        await ctx.send(embed=discord.Embed(
            title="Device Registered!",
            description="Your device ID `{}` has been registered successfully!".format(device_id.lower()),
            color=Colors.SUCCESS
        ))

    @lametric.command(name="send", brief="Send a text string to a LaMetric device.")
    @WolfChecks.has_guild_permissions(administrator=True)
    async def send(self, ctx: commands.Context, device_id: str, icon: str, text: str):
        """
        Send a message to a LaMetric device.

        The Device ID is the registered device ID, as given by /lametric list.

        The Icon is an Icon ID from the LaMetric database, and the Text is whatever you want it to be.
        """
        lametric_conf = self._config.get('lametric', {})
        devices = lametric_conf.setdefault('devices', {})

        if device_id.lower() not in devices.keys():
            raise commands.BadArgument("This Device ID is not known.")

        device = devices[device_id.lower()]

        data = {
            'frames': [
                {
                    "text": text,
                    "icon": icon
                }
            ]
        }

        r = LaMetricApi.push_to_lametric(device['appId'], data, device['authToken'])

        await ctx.send("Status code: {}".format(r.status_code))

    @lametric.command(name="list", brief="List registered LaMetric devices")
    @WolfChecks.has_guild_permissions(administrator=True)
    async def list(self, ctx: commands.Context):
        """
        List all registered LaMetric devices.

        This command takes no arguments.
        """
        lametric_conf = self._config.get('lametric', {})
        devices = lametric_conf.setdefault('devices', {})

        device_list = ""

        for i in devices.keys():
            dev = devices[i]
            device_list += "\n- ID `{}` (owned by <@{}>), events: `{}`".format(i.lower(), dev['ownerId'],
                                                                               dev['enabledTasks'])

        await ctx.send(embed=discord.Embed(
            title="Registered LaMetric Devices",
            description="The following devices are registered with the bot.\n{}".format(device_list),
            color=Colors.INFO
        ))

    @lametric.command(name="remove", brief="Remove a LaMetric device")
    @WolfChecks.has_guild_permissions(administrator=True)
    async def delete(self, ctx: commands.Context, device_id: str):
        """
        De-register a LaMetric device.

        This command will remove a LaMetric device from the bot. The Device ID (provided by /lametric list) is required.
        """
        lametric_conf = self._config.get('lametric', {})
        devices = lametric_conf.setdefault('devices', {})

        if device_id.lower() not in devices.keys():
            raise commands.BadArgument("This Device ID is not known.")

        del devices[device_id.lower()]

        self._config.set('lametric', lametric_conf)

        await ctx.send(embed=discord.Embed(
            title="LaMetric Device Removed",
            description="The LaMetric device with ID `{}` has been removed.".format(device_id.lower())
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(LaMetric(bot))
