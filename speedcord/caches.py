from .abc_classes import BaseCache
import aiosqlite
from os.path import expanduser

db = None
# To be defined later.


def set_cache_db(loop):
    """Sets the cache DB."""
    global db
    db = aiosqlite.connect(expanduser("~") + "/.speedcord.db", loop=loop)


class UserCache(BaseCache):
    """Defines the user cache."""
    async def extra_initialisation(self):
        self._db = db

        await super().extra_initialisation()
