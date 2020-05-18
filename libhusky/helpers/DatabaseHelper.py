import asyncio
import logging
import os

from tortoise import Tortoise
from tortoise.exceptions import DBConnectionError, ConfigurationError

LOG = logging.getLogger("HuskyBot." + __name__)

MAX_WAIT_TIME = 30  # time to wait for the database to come online


def initialize_database(loop: asyncio.AbstractEventLoop):
    try:
        asyncio.ensure_future(Tortoise.init(config=generate_config()), loop=loop)
    except KeyError as e:
        LOG.critical("No database configuration was set for HuskyBot!")
        raise e
    except (DBConnectionError, ConfigurationError) as e:
        LOG.critical(f"Could not connect to the database! The error is as follows: \n{e}")
        raise e


def generate_config() -> dict:
    return {
        'connections': {
            'default': {
                'engine': 'tortoise.backends.asyncpg',
                'credentials': {
                    'host': os.environ['POSTGRES_HOST'],
                    'port': os.getenv('POSTGRES_PORT', 5432),
                    'user': os.environ['POSTGRES_USER'],
                    'password': os.environ['POSTGRES_PASSWORD'],
                    'database': os.environ['POSTGRES_DB']
                }
            }
        },
        'apps': {'models': {'models': get_models(), 'default_connection': 'default'}}
    }


def get_models():
    # ToDo: Look through plugins to find all models.
    # Walks through plugins/ and finds anything that inherits from Model.
    return []


def block_wait_for_database(loop: asyncio.AbstractEventLoop):
    return asyncio.ensure_future(wait_for_database(), loop=loop)


async def wait_for_database():
    LOG.debug(f"Waiting {MAX_WAIT_TIME}s for database to come online...")
    o_conn = None

    for _ in range(MAX_WAIT_TIME):
        try:
            o_conn = Tortoise.get_connection('default')
        except KeyError:
            pass

        if o_conn:
            result = await o_conn.execute_query('SELECT version();')
            if result:
                LOG.debug(f"Database is online.", extra={'db_response': result[1][0]['version']})
                break

        await asyncio.sleep(1)
    else:
        LOG.critical("Database didn't come up in {MAX_WAIT_TIME} seconds!")
        raise ConnectionError("DB hit timeout!")

    return o_conn
