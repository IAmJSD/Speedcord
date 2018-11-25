import abc


class Command(abc.ABC):
    """The ABC class for commands."""
    def __init__(self, func, checks, help_message, usage):
        self.__call__ = func
        self.checks = checks
        self._command = True
        self.help_message = help_message
        self.usage = usage

    @property
    def name(self):
        return self.__name__

    @abc.abstractmethod
    async def __call__(self, *args, **kwargs):
        pass


class User(abc.ABC):
    """The ABC class for users."""
    __slots__ = ["id", "username", "discriminator", "avatar_hash", "bot"]

    def __init__(self, data):
        self.id = data['id']
        self.username = data['username']
        self.discriminator = data['discriminator']
        self.avatar_hash = data.get("avatar")
        self.bot = data['bot']


class BaseCache(dict, abc.ABC):
    """The base object cache."""
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self._initialised = False
        self._after_init_set_queue = {}
        self._after_init_del_queue = []
        self._db = None
        self.loop.create_task(self.extra_initialisation())

    @abc.abstractmethod
    async def extra_initialisation(self):
        self._initialised = True

        for key in self._after_init_set_queue:
            self.loop.create_task(self.after_set_item(key, self._after_init_set_queue[key]))
        del self._after_init_set_queue

        for item in self._after_init_del_queue:
            self.loop.create_task(self.after_del_item(item))
        del self._after_init_del_queue

    @abc.abstractmethod
    async def after_set_item(self, key, value):
        pass

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if self._initialised:
            self.loop.create_task(self.after_set_item(key, value))
        else:
            self._after_init_set_queue[key] = value

    @abc.abstractmethod
    async def after_del_item(self, key):
        pass

    def __delitem__(self, key):
        super().__delitem__(key)
        if self._initialised:
            self.loop.create_task(self.after_del_item(key))
        else:
            self._after_init_del_queue.append(key)
