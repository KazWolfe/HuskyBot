import logging
import os
import socket

from HuskyBot import HuskyBot
from libhusky.util import UtilClasses

LOG = logging.getLogger("HuskyBot." + __name__)

SHARDS_IN_INSTANCE = int(os.getenv('HUSKYBOT_INSTANCE_SHARDS', 4))
SHARD_LOCK_NAME = "huskybot-shard-lock"
SHARD_KEY = "huskybot.shards"


class ShardManager(metaclass=UtilClasses.Singleton):
    def __init__(self, bot: HuskyBot):
        self.bot = bot
        self.redis = bot.redis

    @staticmethod
    def _get_shard_ids_for_instance(index: int) -> list:
        return list(range(SHARDS_IN_INSTANCE * index, SHARDS_IN_INSTANCE * (index + 1)))

    @staticmethod
    def _get_instance_number_by_shard(shard_number) -> int:
        return shard_number // SHARDS_IN_INSTANCE

    def get_shards(self) -> dict:
        with self.redis.lock(SHARD_LOCK_NAME):
            return self.redis.hgetall(SHARD_KEY)

    def register(self, inform_others=True) -> (list, int):
        """
        Register the next available shard grouping to the current instance of the bot.

        @returns Returns a tuple of list (shards assigned to this instance) and int (total shards across all instances)
        """
        instance_hostname = socket.gethostname()

        with self.redis.lock(SHARD_LOCK_NAME):
            current_instances: list = self.redis.lrange(SHARD_KEY, 0, -1)
            shard_count = SHARDS_IN_INSTANCE * len(current_instances)

            if instance_hostname not in current_instances:
                # off-by-one magic here. with a length of 1, instance 0 will have [0 - 3].
                # we can cheat and say the next shard (by ID) will be the current length.
                my_instance_id = len(current_instances)
                my_shard_range = self._get_shard_ids_for_instance(my_instance_id)

                self.redis.rpush(SHARD_KEY, socket.gethostname())
                shard_count += SHARDS_IN_INSTANCE
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
