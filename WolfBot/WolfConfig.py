import json
from threading import Lock


class WolfConfig:
    def __init__(self, path: str = None):
        self._config = {}
        self._path = path
        self._lock = Lock()

        if self._path is not None:
            self.load()

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

    def isPersistent(self):
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

    def load(self) -> None:
        if self._path is None:
            return

        try:
            with open(self._path, 'r') as f:
                self._config = json.loads(f.read())
        except IOError:
            print("Could not load config from specified path " + self._path)
            exit(1)

    def save(self):
        if self._path is None:
            return

        with open('config/config.json', 'w') as f:
            f.write(json.dumps(self._config, sort_keys=True))


__BOT_CONFIG = WolfConfig("config/config.json")
__SESSION_STORAGE = WolfConfig()


def getConfig():
    return __BOT_CONFIG


def getSessionStore():
    return __SESSION_STORAGE
