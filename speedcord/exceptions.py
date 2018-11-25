class UnknownFirstMessage(Exception):
    """The first message sent by Discord is of a opcode unknown to Speedcord."""
    def __init__(self):
        super().__init__("The first message sent by Discord is of a opcode unknown to Speedcord.")


class UnknownDiscordError(Exception):
    """Error 4000: We're not sure what went wrong. Try reconnecting?"""


class Ratelimited(Exception):
    """A ratelimit happened."""


class InvalidToken(Exception):
    """The token given was invalid."""
    def __init__(self):
        super().__init__("The token given was invalid.")


class InvalidShard(Exception):
    """The shard ID given was invalid."""
    def __init__(self):
        super().__init__("The shard ID given was invalid.")


class ShardingRequired(Exception):
    """You require more shards."""
    def __init__(self):
        super().__init__("You require more shards.")
