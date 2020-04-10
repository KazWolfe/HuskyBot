import gzip
import logging
import os
from logging import handlers


class CompressingRotatingFileHandler(logging.handlers.RotatingFileHandler):
    # Code source: https://stackoverflow.com/a/35547094/1817097
    # Modified by Kaz Wolfe

    def __init__(self, filename, **kws):
        backup_count = kws.get('backupCount', 0)
        self.backup_count = backup_count
        os.makedirs(os.path.dirname(filename), exist_ok=True)  # Make logs if we need to
        super().__init__(filename, **kws)

    @staticmethod
    def do_archive(old_log):
        with open(old_log, 'rb') as log:
            with gzip.open(old_log + '.gz', 'wb') as comp_log:
                comp_log.writelines(log)

        os.remove(old_log)

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        if self.backup_count > 0:
            for i in range(self.backup_count - 1, 0, -1):
                sfn = "%s.%d.gz" % (self.baseFilename, i)
                dfn = "%s.%d.gz" % (self.baseFilename, i + 1)
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)

        dfn = self.baseFilename + ".1"

        if os.path.exists(dfn):
            os.remove(dfn)

        if os.path.exists(self.baseFilename):
            os.rename(self.baseFilename, dfn)
            self.do_archive(dfn)

        if not self.delay:
            # noinspection PyAttributeOutsideInit
            # pycharm cant see far enough to ignore this, somehow.
            self.stream = self._open()


class Singleton(type):
    # Borrowed from https://stackoverflow.com/a/6798042/1817097
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
