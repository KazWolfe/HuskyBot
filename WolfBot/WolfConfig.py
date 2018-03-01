import json


class WolfConfig:
    def __init__(self, path: str = None):
        self._config = {}
        self._path = path

        if self._path is not None:
            self.load()

    def __len__(self):
        len(self._config)

    def __getitem__(self, item):
        return self._config[item]

    def __setitem__(self, key: str, value):
        self.set(key, value)

    def isPersistent(self):
        return self._path is not None

    def get(self, key: str, default=None):
        try:
            return self._config[key]
        except KeyError:
            return default

    def exists(self, key: str) -> bool:
        return not self.get(key) is None

    def set(self, key, value):
        self._config[key] = value
        self.save()

    def delete(self, key: str) -> None:
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
