from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from HuskyBot import HuskyBot

import logging
import os
import socket

from libhusky.util import UtilClasses

LOG = logging.getLogger("HuskyBot." + __name__)

SHARDS_PER_INSTANCE = int(os.getenv('HUSKYBOT_INSTANCE_SHARDS', 4))
SHARD_LOCK_NAME = "huskybot-shard-lock"
SHARD_KEY = "huskybot.shards"


class ShardManager(metaclass=UtilClasses.Singleton):
    def __init__(self, bot: HuskyBot):
        self.bot = bot
        self.redis = bot.redis

    @staticmethod
    def _get_shard_ids_for_instance(index: int) -> list:
        return list(range(SHARDS_PER_INSTANCE * index, SHARDS_PER_INSTANCE * (index + 1)))

    @staticmethod
    def _get_instance_number_by_shard(shard_number) -> int:
        return shard_number // SHARDS_PER_INSTANCE

    def _get_hosting_shard_for_guild(self, guild_id: int) -> int:
        shard_count = self.redis.llen(SHARD_KEY)
        return (guild_id >> 22) % shard_count

    def _get_hosting_instance_number_for_guild(self, guild_id):
        shard_id = self._get_hosting_shard_for_guild(guild_id)
        return self._get_instance_number_by_shard(shard_id)

    def register(self, inform_others=True) -> (list, int):
        """
        Register the next available shard grouping to the current instance of the bot.

        @returns Returns a tuple of list (shards assigned to this instance) and int (total shards across all instances)
        """
        instance_hostname = socket.gethostname()

        with self.redis.lock(SHARD_LOCK_NAME):
            current_instances: list = self.redis.lrange(SHARD_KEY, 0, -1)
            shard_count = SHARDS_PER_INSTANCE * len(current_instances)

            if instance_hostname not in current_instances:
                # off-by-one magic here. we can cheat and say the next instance ID
                # is the length of all current instances.
                my_instance_id = len(current_instances)
                my_shard_range = self._get_shard_ids_for_instance(my_instance_id)

                self.redis.rpush(SHARD_KEY, socket.gethostname())
                shard_count += SHARDS_PER_INSTANCE
            else:
                my_instance_id = current_instances.index(instance_hostname)
                my_shard_range = self._get_shard_ids_for_instance(my_instance_id)

        LOG.debug(f"Register instance #{my_instance_id} -> {my_shard_range} (of {shard_count} shards)")

        if inform_others:
            # todo: inform all other shards to change counts/reidentify
            pass

        return my_shard_range, shard_count

    def remove_host(self, host: str = None):
        if not host:
            host = socket.gethostname()

        with self.redis.lock(SHARD_LOCK_NAME):
            self.redis.lrem(SHARD_KEY, 0, host)

        # todo: inform all other shards to change counts/reidentify
