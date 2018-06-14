import json
from threading import Lock


def override_dumper(obj):
    if hasattr(obj, "toJSON"):
        return obj.to_json()
    else:
        return obj.__dict__


class WolfConfig:
    def __init__(self, path: str = None, create_if_nonexistent: bool = False):
        self._config = {}
        self._path = path
        self._lock = Lock()

        if self._path is not None:
            self.load(create_if_nonexistent)

    def __len__(self):
        with self._lock:
            return len(self._config)

    def __getitem__(self, item):
        with self._lock:
            return self._config[item]

    def __setitem__(self, key: str, value):
        with self._lock:
            self.set(key, value)

    def dump(self):
        with self._lock:
            return self._config

    def is_persistent(self):
        with self._lock:
            return self._path is not None

    def get(self, key: str, default=None):
        with self._lock:
            try:
                return self._config[key]
            except KeyError:
                return default

    def exists(self, key: str) -> bool:
        with self._lock:
            return not self.get(key) is None

    def set(self, key, value):
        with self._lock:
            self._config[key] = value
            self.save()

    def delete(self, key: str) -> None:
        with self._lock:
            self._config.pop(key)
            self.save()

    def load(self, create_if_nonexistent: bool = False) -> None:
        if self._path is None:
            return

        try:
            with open(self._path, 'r') as f:
                self._config = json.loads(f.read())
        except IOError:
            if not create_if_nonexistent:
                raise

            self.save()

    def save(self):
        if self._path is None:
            return

        with open(self._path, 'w') as f:
            f.write(json.dumps(self._config, sort_keys=True, default=override_dumper))


__cache__ = {}


def get_config(name: str = 'config', create_if_nonexistent: bool = False):
    """
    Get the bot's current persistent configuration (thread-safe).

    Due to Python's annoyance, we can't grab the same object from everything, so instead we will just load the config
    here, and expose it through get_config() to clients. DO NOT access the config manually, as it may be out of date, or
    otherwise rewrite configs without expectation.

    :param name: Define the name of the persistent configuration to get.
    :param create_if_nonexistent: Create this config file if it doesn't exist.
    :return: Returns the bot's shared persistent configuration.
    """

    if name != 'config':
        key = 'config_{}'.format(name)
    else:
        key = 'config'

    if name not in __cache__:
        # The requested store does not exist in cache.
        __cache__[key] = WolfConfig('config/{}.json'.format(name), create_if_nonexistent=create_if_nonexistent)

    return __cache__[key]


def get_session_store(name: str = None):
    """
    Get the bot's Session Store (thread-safe).

    The Session Store is a ephemeral key-value store used for information that does *not* need to persist past a bot
    restart. Because of this, nothing should be stored in the Session Store that requires persistence - this is a temp
    space.

    Session Stores are completely ephemeral, so either the shared session store can be used or one may be created by
    passing a name value.

    :param name: The name of the Session Store to retrieve
    :return: Returns a Session Store with a specified name.
    """

    if name is None:
        key = 'session_store'
    else:
        key = 'session_store_{}'.format(name)

    if key not in __cache__:
        # The requested store does not exist in cache.
        __cache__[key] = WolfConfig()

    return __cache__[key]
