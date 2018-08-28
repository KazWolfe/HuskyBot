import asyncio
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

        self._api = LaMetricApi.LaMetricApi()

        self._pending_registrations = {}
        '''
        {
            <device_id> : <user_id>
        '''

        LOG.info("Loaded plugin!")

    async def update_lametric_counts(self, guild: discord.Guild):
        lametric_conf = self._config.get('lametric', {})
        devices = lametric_conf.setdefault('devices', {})

        new_count = str(guild.member_count)

        # icon = "i18290"
        icon = "i5582"

        for device_id in devices.keys():
            device = devices[device_id]

            if "userCount" not in device.get("enabledTasks", []):
                continue

            LOG.info(f"Updating usercount for LaMetric device ID {device_id}")
            await self._api.push(device['appId'], LaMetricApi.build_data(icon, new_count), device['authToken'])

    async def on_member_join(self, member: discord.Member):
        await self.update_lametric_counts(member.guild)

    async def on_member_remove(self, member: discord.Member):
        await self.update_lametric_counts(member.guild)

    @commands.group(name="lametric", brief="Base command for LaMetric interfaces", hidden=True)
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

        await ctx.author.send("Thanks for requesting a setup for your LaMetric device! Before I can start sending "
                              "messages to your device, I'll need to get a bit of information about your device first. "
                              "If you haven't already, you'll need to make an [indicator app]("
                              "https://lametric-documentation.readthedocs.io/en/latest/guides/first-steps/"
                              "first-lametric-indicator-app.html). I will need your **Application ID** and "
                              "**Authentication Token** to register your device.")

        await ctx.author.send("Let's start with your **Application ID**. This will be a string like `XXXXXXXXX/1`, and "
                              "will be preceded by `com.lametric` as part of the URL. An example Application ID will "
                              "look like this: `22e45a6407da88c0c938a8aaf8f7406f/1`. Once you have it, send it here.")

        try:
            app_id = await self.bot.wait_for('message', check=lambda m: m.channel == ctx.author.dm_channel, timeout=30)
        except asyncio.TimeoutError:
            await ctx.author.send("Hello? I didn't get a response. When you have your **Application ID** and **Access "
                                  "Token**, run `/lametric register` again.")
            return

        await ctx.author.send("Alright, great! Next, I'll need your **Access Token**.  This will be a relatively long "
                              "Base-64 string, and will be on the developer panel. Please send it here.")

        try:
            app_auth = await self.bot.wait_for('message', check=lambda m: m.channel == ctx.author.dm_channel,
                                               timeout=30)
        except asyncio.TimeoutError:
            await ctx.author.send("Hello? I didn't get a response. When you have your **Application ID** and **Access "
                                  "Token**, run `/lametric register` again.")
            return

        verification_key = os.urandom(2).hex().upper()

        await ctx.author.send("Great! Thank you for that. I'm going to send four characters to your LaMetric device "
                              "right now. Please enter these four characters here so I can verify everything is set "
                              "up correctly.")

        await self._api.push(app_id, LaMetricApi.build_data("i59", verification_key), app_auth)

        try:
            verification_resp = await self.bot.wait_for('message', check=lambda m: m.channel == ctx.author.dm_channel,
                                                        timeout=90)
        except asyncio.TimeoutError:
            await ctx.author.send("Hello? I didn't get a response. I couldn't verify your device works. Please double "
                                  "check your App ID and Access Token, and try again.")
            return

        await ctx.send(embed=discord.Embed(
            title="LaMetric Setup",
            description=f"Please DM the bot with the following command:\n\n"
                        f"```/lametric authorize {device_id.lower()} your_app_id your_auth_token```\n\n"
                        f"Be sure to include the version in your AppID (`abcdef/1`).",
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
            description=f"Your device ID `{device_id.lower()}` has been registered successfully!",
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

        r = await self._api.push(device['appId'], data, device['authToken'])

        await ctx.send(f"Status code: {r.status}")

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
            device_list += f"\n- ID `{i.lower()}` (owned by <@{dev['ownerId']}>), events: `{dev['enabledTasks']}`"

        await ctx.send(embed=discord.Embed(
            title="Registered LaMetric Devices",
            description=f"The following devices are registered with the bot.\n{device_list}",
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
            description=f"The LaMetric device with ID `{device_id.lower()}` has been removed."
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(LaMetric(bot))
