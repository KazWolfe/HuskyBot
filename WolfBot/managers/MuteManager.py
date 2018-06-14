import asyncio
import datetime
import logging

import discord
from discord.ext import commands

from WolfBot import WolfConfig, WolfData, WolfUtils
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DakotaBot.Managers.MuteManager")


class MuteManager:
    def __init__(self, bot: commands.Bot):
        self._bot = bot
        self._bot_config = WolfConfig.get_config()
        self._mute_config = WolfConfig.get_config('mutes', create_if_nonexistent=True)
        self.__cache__ = []

        self.read_mutes_from_file()

        self.__task__ = self._bot.loop.create_task(self.check_mutes())

        LOG.info("Manager load complete.")

    def read_mutes_from_file(self):
        disk_mutes = self._mute_config.get("mutes", [])

        for raw_mute in disk_mutes:
            mute = WolfData.Mute(raw_mute)

            self.__cache__.append(mute)

        self._mute_config.set("mutes", self.__cache__)

    async def check_mutes(self):
        while not self._bot.is_closed():
            for mute in self.__cache__:
                if mute.is_expired():
                    LOG.info("Found a scheduled unmute - [{}, {}]. Triggering...".format(mute.user_id,
                                                                                         mute.channel))
                    await self.unmute_user(mute, "System - Scheduled")

                # Because mutes are sorted by expiry, we can just exit the loop if we encounter a mute that's not yet
                # over.
                else:
                    break

            await asyncio.sleep(0.5)

    async def mute_user_by_object(self, mute: WolfData.Mute, staff_member: str = "System"):
        guild = self._bot.get_guild(mute.guild)

        member = guild.get_member(mute.user_id)
        channel = None

        expiry_string = ""
        if mute.expiry is not None:
            expiry_string = " (muted until {})".format(
                datetime.datetime.fromtimestamp(mute.expiry).strftime(DATETIME_FORMAT))

        if mute.channel is None:
            mute_role = discord.utils.get(guild.roles, id=self._bot_config.get("specialRoles", {}).get("muted"))
            mute_context = "the guild"

            if mute_role is None:
                raise ValueError("A muted role is not set!")

            await member.add_roles(mute_role, reason="Muted by {} for reason {}{}"
                                   .format(staff_member, mute.reason, expiry_string))
        else:
            channel = guild.get_channel(mute.channel)
            mute_context = channel.mention

            await channel.set_permissions(member, reason="Muted by {} for reason {}{}"
                                          .format(staff_member, mute.reason, expiry_string), send_messages=False,
                                          add_reactions=False)

        if mute not in self.__cache__:
            pos = WolfUtils.get_sort_index(self.__cache__, mute, 'expiry')
            self.__cache__.insert(pos, mute)
            self.__cache__.sort(key=lambda m: m.expiry if m.expiry else 10 * 100)
            self._mute_config.set("mutes", self.__cache__)

            # Inform the guild logs
            alert_channel = self._bot_config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

            if alert_channel is not None:
                alert_channel = member.guild.get_channel(alert_channel)

                embed = discord.Embed(
                    description="User ID `{}` was muted from {}.".format(member.id, mute_context),
                    color=Colors.WARNING
                )

                embed.set_author(name="{} was muted from {}!".format(member,
                                                                     "the guild" if mute.channel is None else
                                                                     "#" + str(channel)),
                                 icon_url=member.avatar_url)
                embed.add_field(name="Responsible User", value=str(staff_member), inline=True)
                embed.add_field(name="Timestamp", value=WolfUtils.get_timestamp(), inline=True)
                embed.add_field(name="Expires At", value=datetime.datetime.fromtimestamp(mute.expiry)
                                .strftime(DATETIME_FORMAT) if mute.expiry is not None else "Never", inline=True)
                embed.add_field(name="Reason", value=mute.reason, inline=False)

                await alert_channel.send(embed=embed)

    async def mute_user(self, ctx: commands.Context, member: discord.Member, channel,
                        reason: str, expiry: int, staff_member: discord.Member):

        if channel is None:
            channel_id = None
            current_perms = None
        else:
            channel_id = channel.id
            current_perms = channel.overwrites_for(member)

        mute_obj = WolfData.Mute()
        mute_obj.guild = ctx.guild.id
        mute_obj.user_id = member.id
        mute_obj.reason = reason
        mute_obj.channel = channel_id
        mute_obj.expiry = expiry
        mute_obj.set_cached_override(current_perms)

        await self.mute_user_by_object(mute_obj, str(staff_member))

    async def unmute_user(self, mute: WolfData.Mute, staff_member: str):
        if staff_member is not None:
            unmute_reason = "user {}".format(staff_member)
        else:
            unmute_reason = "expiry"

        guild = self._bot.get_guild(mute.guild)
        member = guild.get_member(mute.user_id)

        # Member is no longer on the guild, so their perms are cleared. Delete their records once their mute
        # is up.
        if member is None:
            LOG.info("Left user ID {} has had their mute expire. Removing it.".format(mute.user_id))
            self.__cache__.remove(mute)
            self._mute_config.set("mutes", self.__cache__)

            return

        if mute.channel is not None:
            channel = self._bot.get_channel(mute.channel)
            unmute_context = channel.mention

            await channel.set_permissions(member, overwrite=mute.get_cached_override(),
                                          reason="User's channel mute has been lifted by {}".format(unmute_reason))
        else:
            unmute_context = "the guild"
            channel = None

            mute_role = discord.utils.get(guild.roles, id=self._bot_config.get("specialRoles", {})
                                          .get(SpecialRoleKeys.MUTED.value))

            if mute_role is None:
                raise ValueError("A muted role is not set!")

            await member.remove_roles(mute_role,
                                      reason="User's guild mute has been lifted by {}".format(unmute_reason))

        # Remove from the disk
        self.__cache__.remove(mute)
        self._mute_config.set("mutes", self.__cache__)

        # Inform the guild logs
        alert_channel = self._bot_config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)

        if alert_channel is not None:
            alert_channel = member.guild.get_channel(alert_channel)

            embed = discord.Embed(
                description="User ID `{}` was unmuted from {}.".format(mute.user_id, unmute_context),
                color=Colors.INFO
            )

            embed.set_author(
                name="{} was unmuted from {}!".format(member,
                                                      "the guild" if mute.channel is None else "#" + str(channel)),
                icon_url=member.avatar_url),
            embed.add_field(name="Responsible User", value=str(staff_member), inline=True)

            await alert_channel.send(embed=embed)

    async def restore_user_mute(self, member: discord.Member):
        for mute in self.__cache__:
            if (mute.user_id == member.id) and not mute.is_expired():
                LOG.info("Restoring mute state for left user {} in channel".format(member, mute.channel))
                await self.mute_user_by_object(mute, "System - ReJoin")

    async def find_user_mute_record(self, member: discord.Member, channel):
        result = None

        channel_id = None
        if channel is not None:
            channel_id = channel.id

        for mute in self.__cache__:
            if member.id == mute.user_id and channel_id == mute.channel:
                result = mute

        if result is None:
            return None

        return result

    async def update_mute_record(self, mute: WolfData.Mute, reason: str = None, expiry: int = None):

        if mute not in self.__cache__:
            raise KeyError("This record doesn't exist in the cache!")

        self.__cache__.remove(mute)

        old_reason = mute.reason
        old_expiry = mute.expiry

        if reason is not None:
            mute.reason = reason

        if expiry is not None:
            mute.expiry = expiry

        # Update cache and disk
        pos = WolfUtils.get_sort_index(self.__cache__, mute, 'expiry')
        self.__cache__.insert(pos, mute)
        self.__cache__.sort(key=lambda m: m.expiry if m.expiry else 10 * 100)
        self._mute_config.set("mutes", self.__cache__)

        alert_channel = self._bot_config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if alert_channel is not None:
            alert_channel = self._bot.get_channel(alert_channel)

            member = self._bot.get_guild(mute.guild).get_member(mute.user_id)

            mute_context = "the guild" if mute.channel is None else str(self._bot.get_channel(mute.channel))

            embed = discord.Embed(
                description="User ID `{}`'s mute from {} was updated.".format(mute.user_id, mute_context),
                color=Colors.WARNING
            )

            embed.set_author(name="{}'s mute updated!".format(member),
                             icon_url=member.avatar_url)

            if old_reason != reason:
                embed.add_field(name="Old Reason", value=old_reason, inline=False)
                embed.add_field(name="New Reason", value=mute.reason, inline=False)

            if old_expiry != expiry:
                embed.add_field(name="Old Expiry", value=old_expiry, inline=True)
                embed.add_field(name="New Expiry", value=datetime.datetime.fromtimestamp(mute.expiry)
                                .strftime(DATETIME_FORMAT) if mute.expiry is not None else "Never", inline=True)

            embed.add_field(name="Timestamp", value=WolfUtils.get_timestamp(), inline=True)

            await alert_channel.send(embed=embed)

    def cleanup(self):
        if self.__task__ is not None:
            self.__task__.cancel()
