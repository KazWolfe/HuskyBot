import logging
import re

import aiohttp
import discord
import jwt
from aiohttp import web
from discord.ext import commands

from HuskyBot import HuskyBot, Colors
from libhusky import HuskyHTTP

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class Gatekeeper(commands.Cog):
    """
    Gatekeeper is a next-generation humanity verification and alt account detection system. Guilds that use Gatekeeper
    will send all users either through the phone-verification flow or a customized captcha flow.

    Gatekeeper also handles browser fingerprinting and behavioral traits to ensure that users coming in are legitimate.
    Users verifying themselves via Gatekeeper go through the following steps:

    1. User gets redirected to a HuskyBot server, where they click a Log In With Discord button.
    2. After logging in with their Account, Husky associates a User ID with an IP address, fingerprint, and cookie.
    3. The user is sent back to the Husky page, where they are challenged with a CAPTCHA.
    4. If they pass the captcha, a "human" role is assigned to the user, granting them access to the guild and bypassing
    verification requirements.

    """

    def __init__(self, bot: HuskyBot):
        self.bot = bot
        self._config = bot.config
        self._session_store = bot.session_store

        self._http_session = aiohttp.ClientSession(loop=bot.loop)

        LOG.info("Loaded plugin!")

    def cog_unload(self):
        self.bot.loop.create_task(self._http_session.close())

    @commands.group(name="gatekeeper", brief="Base command for Gatekeeper")
    async def gatekeeper(self, ctx: commands.Context):
        pass

    @gatekeeper.group(name="config", brief="Configure Gatekeeper")
    @commands.has_permissions(administrator=True)
    async def gk_config(self, ctx: commands.Context):
        pass

    @gk_config.command(name="setUrl", brief="Set the Gatekeeper Server URL")
    async def set_url(self, ctx: commands.Context, url: str):
        gatekeeper_config = self._config.get('gatekeeper', {})

        gatekeeper_config['serverUrl'] = url
        self._config.set('gatekeeper', gatekeeper_config)

        await ctx.send(embed=discord.Embed(
            title="Gatekeeper Configuration",
            description=f"The Gatekeeper server URL has been set to:```{url}```",
            color=Colors.SUCCESS
        ))

    @gk_config.command(name="setPubkey", brief="Set the Gatekeeper Server Public Key")
    async def set_key(self, ctx: commands.Context, pubkey: str):
        gatekeeper_config = self._config.get('gatekeeper', {})

        gatekeeper_config['pubkey'] = pubkey
        self._config.set('gatekeeper', gatekeeper_config)

        await ctx.send(embed=discord.Embed(
            title="Gatekeeper Configuration",
            description=f"The Gatekeeper server public key has been set.",
            color=Colors.SUCCESS
        ))

    @gk_config.command(name="setRole", brief="Set the Gatekeeper verified role")
    async def set_role(self, ctx: commands.Context, role: discord.Role):
        gatekeeper_config = self._config.get('gatekeeper', {})

        gatekeeper_config['role'] = role.id
        self._config.set('gatekeeper', gatekeeper_config)

        await ctx.send(embed=discord.Embed(
            title="Gatekeeper Configuration",
            description=f"The Gatekeeper verified role is now {role.mention}.",
            color=Colors.SUCCESS
        ))

    @gatekeeper.command(name="url", brief="Get the Gatekeeper URL")
    @commands.has_permissions(manage_guild=True)
    async def get_url(self, ctx: commands.Context):
        gatekeeper_config = self._config.get('gatekeeper', {})

        embed = discord.Embed(
            title="Gatekeeper",
            description=f"{ctx.guild.name} is using Gatekeeper, powered by Husky Verify. This technology allows users "
                        f"to easily verify themselves without giving their phone number to Discord, while still "
                        f"protecting the community.\n\nIf you need to verify your account, please [head over to Husky "
                        f"Verify]({gatekeeper_config['serverUrl']}?guild={ctx.guild.id}) to get started.",
            color=Colors.INFO
        )

        embed.set_thumbnail(url=ctx.guild.icon_url)

        await ctx.send(embed=embed)

    @HuskyHTTP.register("/gatekeeper/hook", ["POST"])
    async def gatekeeper_autoverify_hook(self, request: web.BaseRequest):
        gatekeeper_config = self._config.get('gatekeeper', {})

        data = await request.json()
        decoded_jwt = self.unpack_gatekeeper_jwt(data['jwt'])

        target_guild: discord.Guild = self.bot.get_guild(int(decoded_jwt['gid']))
        target_member: discord.Member = target_guild.get_member(int(decoded_jwt['uid']))

        verified_role = target_guild.get_role(gatekeeper_config['role'])

        # if len(target_member.roles) > 1:
        if verified_role in target_member.roles:
            LOG.info(f"Got a verify attempt for member {target_member}, but they're already verified.")
            return web.Response(text=f"ok")

        await target_member.add_roles(verified_role, reason="Gatekeeper Verified")

        return web.Response(text=f"ok")

    def unpack_gatekeeper_jwt(self, jwt_o):
        gatekeeper_config = self._config.get('gatekeeper', {})
        server_pubkey = gatekeeper_config.get('pubkey')
        if not server_pubkey:
            raise KeyError("MissingPublicKey")

        # hack to fix a dumb type thing
        server_pubkey = "ssh-rsa " + server_pubkey

        return jwt.decode(jwt_o, server_pubkey, algorthims=["RS256"])

    def determine_token_type(self, token):
        if re.match(r"[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}", token.upper()):
            return "ovt"

        try:
            if jwt.decode(token, verify=False):
                return "jwt"
        except jwt.exceptions.DecodeError:
            return False


def setup(bot: HuskyBot):
    bot.add_cog(Gatekeeper(bot))
