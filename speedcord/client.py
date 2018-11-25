from .loop_utils import get_best_loop
from .abc_classes import Command, User
from .general_utils import DictSwitch
from .exceptions import UnknownFirstMessage, UnknownDiscordError, Ratelimited, InvalidToken, InvalidShard,\
    ShardingRequired
from .caches import set_cache_db
import inspect
import logging
import sys
import websockets
import ujson
import zlib
import asyncio
import time
import aiohttp
# Imports everything that is needed.

inflator = zlib.decompressobj()
# Defines the ZLib inflator.


class Client:
    """Defines the main client."""
    def __init__(self, prefix_handler=None, loop=None, logger=None):
        """Initialises the client."""
        self.prefix_handler = prefix_handler
        if loop:
            self.loop = loop
        else:
            self.loop = get_best_loop()
        self._ws = None
        self._no_command_handler = None
        self.handled_exceptions = {}
        self.events = {}
        self._commands_on = False
        self._last_seq = None
        self._heartbeat_back = True
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger("speedcord")
        set_cache_db(loop)
        self.commands = DictSwitch(self, "_commands_on")

    def exception(self, exception_type):
        """This is used to specify a exception handler."""
        def deco(func):
            self.handled_exceptions[exception_type] = func
            return func

        return deco

    def event(self, event_type):
        """This is used to specify a event."""
        def deco(func):
            if event_type.lower() in self.events:
                self.events[event_type.lower()].append(func)
            else:
                self.events[event_type.lower()] = [func]
            return func

        return deco

    def command(self, help_message=None, checks=None, usage=""):
        """This is used to specify a command."""
        def deco(func):
            global help_message, checks
            if not help_message:
                help_message = inspect.getdoc(func)
            checks = checks if checks else []
            cmd = Command(func, checks, help_message, usage)
            cmd.__name__ = func.__name__.lower()
            self.commands[cmd.__name__] = cmd
            return cmd

        return deco

    def no_command_handler(self, func):
        """Defines the no command handler."""
        self._no_command_handler = func
        return func

    async def _handle_initial_connection(self, identify_info, retry):
        """Handles the initial connection to Discord."""
        hello_hopefully = ujson.loads(inflator.decompress(await self._ws.recv()).decode("utf-8"))

        if hello_hopefully['op'] != 10:
            self.logger.error("Invalid first message sent by Discord. Trying again. Retry {}/10.".format(retry))
            raise UnknownFirstMessage()

        self._heartbeat_interval = hello_hopefully['d']['heartbeat_interval']
        timestamp_now = time.time()

        try:
            await self._ws.send(ujson.dumps(identify_info))
            response = ujson.loads(inflator.decompress(await self._ws.recv()).decode("utf-8"))
        except websockets.ConnectionClosed as e:
            if e.code == 4000:
                raise UnknownDiscordError
            elif e.code == 4008:
                raise Ratelimited("We were ratelimited while logging in!")
            elif e.code == 4004:
                raise InvalidToken()
            elif e.code == 4009:
                raise TimeoutError
            elif e.code == 4010:
                raise InvalidShard()
            elif e.code == 4011:
                raise ShardingRequired()
            raise

        return response, timestamp_now

    async def _handle_heartbeat(self, time_delta):
        """Handles the client heartbeat."""
        while True:
            await asyncio.sleep((self._heartbeat_interval / 1000) - time_delta)
            await self._ws.send('{"op": 1, "d": %s}' % (self._last_seq if self._last_seq else "null"))
            # TODO: Handle event 11 failure (no heartbeat response).
            self._heartbeat_back = False

    async def _handle_ready_info(self, ready_info):
        """Handles information from the ready response."""
        self.user = User(ready_info['d']['user'])
        # TODO: Add more ready-related stuff here (e.g handle cache).

    def dispatch(self, event, *args, **kwargs):
        """Dispatches the event."""
        # TODO: Finish dispatching.
        print(args[0])

    async def _handle_websocket(self):
        """Handles the WebSocket."""
        while True:
            data = ujson.loads(inflator.decompress(await self._ws.recv()).decode("utf-8"))
            op = data['op']

            if op == 0:
                self._last_seq = data['s']
                self.dispatch("raw_event", data)
            elif op == 11:
                self._heartbeat_back = True

    @staticmethod
    async def _optimal_shard_info_wss_url(token):
        """Gets the WebSocket URL/optimal shard information."""
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                "https://discordapp.com/api/gateway/bot",
                headers={
                    "Authorization": "Bot {}".format(token)
                }
            )
            resp.raise_for_status()
            return await resp.json()

    def run(self, token, shard_id=None, shard_count=None, game=None, status=None):
        """Launches the bot."""
        identify_info = {
            "op": 2,
            "d": {
                "properties": {
                    "$os": sys.platform,
                    "$browser": "Speedcord",
                    "$device": "Speedcord"
                },
                "presence": {
                    "status": str(status) if status else "online",
                    "afk": False,
                    "since": None
                },
                "compress": True,
                "large_threshold": 250,
                "token": token
            }
        }

        self.logger.info("Getting information on the WebSocket URL/optimal shard information.")

        try:
            json = self.loop.run_until_complete(self._optimal_shard_info_wss_url(token))
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                raise InvalidToken()
            raise

        if shard_id:
            if not shard_count:
                shard_count = shard_id + 1
            identify_info['d']['shard'] = [shard_id, shard_count]

        if not shard_count:
            shard_count = 1

        if shard_count > json['shards']:
            self.logger.warning(
                "Your shard count ({}) is under the {} shards that Discord suggested for your bot.".format(
                    shard_count, json['shards']
                )
            )

        if game:
            if type(game) == str:
                identify_info['d']['presence']['game'] = {
                    "name": game,
                    "type": 0
                }
            else:
                identify_info['d']['presence']['game'] = game.to_dict()

        self.logger.info("Connecting to Discord.")

        while True:
            retry = 0
            try:
                self._ws = self.loop.run_until_complete(
                    websockets.connect(json['url'] + "?v=6&encoding=json&compress=zlib-stream")
                )
                ready_info, timestamp_now = self.loop.run_until_complete(
                    self._handle_initial_connection(identify_info, retry)
                )
                break
            except UnknownFirstMessage:
                if retry == 10:
                    raise
                retry += 1
            except UnknownDiscordError:
                self.logger.error("Discord had a unknown WebSocket error. Trying again.")
            except TimeoutError:
                self.logger.error("We timed out! Trying again.")
            self.loop.run_until_complete(self._ws.close())

        self.logger.info("Successfully authenticated to Discord.")

        self.loop.run_until_complete(self._handle_ready_info(ready_info))

        self.loop.create_task(self._handle_heartbeat(time.time() - timestamp_now))
        self.loop.create_task(self._handle_websocket())

        # TODO: Add error handling here.

        self.loop.run_forever()
