import logging
import os
import time

import redis

LOG = logging.getLogger("HuskyBot." + __name__)

MAX_WAIT_TIME = 30


def initialize_redis():
    conn = redis.Redis(
        host=os.environ['REDIS_HOST'],
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        password=os.getenv('REDIS_PASSWORD')
    )

    LOG.debug(f"Waiting {MAX_WAIT_TIME}s for Redis to come online...", )
    for _ in range(MAX_WAIT_TIME):
        if conn.ping():
            break
        time.sleep(1)
    else:
        LOG.critical(f"Redis didn't come up in {MAX_WAIT_TIME} seconds!")
        raise ConnectionError("Redis hit timeout!")

    LOG.debug("Redis is online.")
    return conn
