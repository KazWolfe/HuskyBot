import datetime
import logging

import aiohttp
import discord
from discord.ext import commands

from WolfBot import WolfConfig
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class HamRadio:
    CALLSIGN_LOOKUP_URL = "https://callook.info/{callsign}/json"

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self._config = WolfConfig.get_config()

        self._http_session = aiohttp.ClientSession(loop=bot.loop)

        LOG.info("Loaded plugin!")

    def __unload(self):
        self.bot.loop.create_task(self._http_session.close())

    @commands.command(name="callsign", brief="Get information about a callsign")
    async def get_callsign_data(self, ctx: commands.Context, callsign: str):

        async with self._http_session.get(self.CALLSIGN_LOOKUP_URL.format(callsign=callsign)) as r:
            if r.status != 200:
                await ctx.send(embed=discord.Embed(
                    title="Callsign Server Error",
                    description=f"The callsign lookup server responded with HTTP status code {r.status}. Please try "
                                f"your query again later.",
                    color=Colors.ERROR
                ))
                return

            callsign_data = await r.json()

        if callsign_data['status'] == "UPDATING":
            await ctx.send(embed=discord.Embed(
                title="Callsign Server Offline",
                description=f"The callsign lookup server is currently busy updating. Please try your request in ten "
                            f"minutes.",
                color=Colors.ERROR
            ))
            return
        elif callsign_data['status'] == "INVALID":
            await ctx.send(embed=discord.Embed(
                title="Invalid Callsign",
                description=f"The callsign lookup server has reported that the callsign queried is invalid. Please "
                            f"check your query to ensure its accuracy.\n\nIf the callsign is valid and issued "
                            f"recently, please wait 24 hours for the callsign server to receive callsign information "
                            f"from the FCC.",
                color=Colors.WARNING
            ))
            return
        elif callsign_data['status'] != "VALID":
            raise ValueError(f"The callsign server responded with illegal value {callsign_data['status']}")

        callsign = Callsign(callsign_data)

        notes = []

        if callsign.is_expired():
            notes.append("**This callsign is EXPIRED.**")

        notes = "\n".join(notes)
        embed = discord.Embed(
            title=f"{Emojis.RADIO} Callsign Database Lookup",
            description=f"Data for {callsign.name} (callsign `{callsign.callsign}`) was successfully retrieved from "
                        f"the server.\n"
                        f"{notes}".strip(),
            color=Colors.WARNING if callsign.is_expired() else Colors.INFO
        )

        # Line 1
        embed.add_field(name="Callsign Type", value=callsign.type.capitalize())

        if callsign.operator_class is not None:
            embed.add_field(name="Operator Class", value=callsign.operator_class.capitalize())

        # Line 2 if person, line 1 otherwise
        embed.add_field(name="FRN", value=str(callsign.frn))

        # Line 6
        embed.add_field(name="Issuance Date", value=str(callsign.granted_on))
        embed.add_field(name="Last Update Date", value=str(callsign.updated_on))
        embed.add_field(name="Expiration Date", value=str(callsign.expires_on))

        # Line 3
        if callsign.club_trustee is not None:
            embed.add_field(name="Club Trustee",
                            value=f"{callsign.club_trustee_name} (`{callsign.club_trustee}`)",
                            inline=False)

        # Line 4
        if callsign.address is not None:
            embed.add_field(name="Mailing Address",
                            value=callsign.address,
                            inline=False)

        # Line 5
        embed.add_field(name="Location",
                        value=f"[{callsign.latitude:.5f}, {callsign.longitude:5f}]({callsign.google_maps_url()})",
                        inline=True)
        embed.add_field(name="Grid Square", value=callsign.gridsquare, inline=True)

        # Line 7
        embed.add_field(name="Links", value=f"[ULS Entry >]({callsign.uls_url})\n"
                                            f"[QRZ Page >](https://www.qrz.com/db/{callsign.callsign})",
                        inline=False)

        embed.set_footer(text="Data retrieved from https://callook.info/", icon_url="https://callook.info/favicon.ico")

        await ctx.send(embed=embed)


class Callsign:
    def __init__(self, data: dict):
        self.status = data.get('status', 'INVALID')
        self.type = data.get('type', 'UNKNOWN')

        self.name = data.get('name', 'INVALID CALLSIGN')
        self.frn = data.get('otherInfo').get('frn') or None

        self.callsign = data.get('current', {}).get('callsign') or None
        self.operator_class = data.get('current', {}).get('operClass') or None

        self.club_trustee = data.get('trustee', {}).get('callsign') or None
        self.club_trustee_name = data.get('trustee', {}).get('name') or None

        addr_line1 = data.get('address', {}).get('line1') or None
        addr_line2 = data.get('address', {}).get('line2') or None
        addr_attn = data.get('address', {}).get('attn') or None
        formatted_addr = [addr_attn, addr_line1, addr_line2]
        self.address = "\n".join([x for x in formatted_addr if x is not None]) or None

        self.latitude = float(data.get('location', {}).get('latitude', 0))
        self.longitude = float(data.get('location', {}).get('longitude', 0))
        self.gridsquare = data.get('location', {}).get('gridsquare')

        self.granted_on = datetime.datetime.strptime(
            data.get('otherInfo', {}).get('grantDate', '01/01/0001'), '%m/%d/%Y'
        ).date()
        self.expires_on = datetime.datetime.strptime(
            data.get('otherInfo', {}).get('expiryDate', '01/01/0001'), '%m/%d/%Y'
        ).date()
        self.updated_on = datetime.datetime.strptime(
            data.get('otherInfo', {}).get('lastActionDate', '01/01/0001'), '%m/%d/%Y'
        ).date()

        self.uls_url = data.get('otherInfo', {}).get('ulsUrl') or None

    def is_expired(self):
        return self.expires_on < datetime.date.today()

    def is_person(self):
        return self.type == "PERSON"

    def google_maps_url(self):
        return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(HamRadio(bot))
