"""Utility functions."""

import asyncio
import random
import signal
from dataclasses import dataclass
from typing import (
    Callable,
    Dict,
    Generic,
    List,
    NoReturn,
    Tuple,
    TypeVar,
    Union,
    Optional,
)
from typing_extensions import Literal


@dataclass(unsafe_hash=True, order=True)
class Coord:
    """Represents a (col, row) coordinate pair where (0, 0) is the top left corner"""

    col: int
    row: int


# Represents a color in (Red, Green, Blue) form,
# where each value is in the range [0, 255]
Color = Tuple[int, int, int]

# This is available from `typing_extensions`, but copied here to avoid installing
# a library for just a dev dependency.
def assert_never(_arg: NoReturn) -> NoReturn:
    """Assert to the type checker that a line of code is unreachable.

    Raises:
        AssertionError: when called
    """
    raise AssertionError("Expected code to be unreachable")


# Represents the type of a generic collection element
E = TypeVar("E")

# Represents the type of a key in a generic key-value mapping
K = TypeVar("K")

# Represents the type of a value in a generic key-value mapping
V = TypeVar("V")

# Represents any type
T = TypeVar("T")
T2 = TypeVar("T2")


def partition_dict(source: Dict[K, V], pred: Callable[[K], bool]) -> Tuple[Dict[K, V], Dict[K, V]]:
    """Splits `source` into two dicts based on whether the keys pass `pred`.

    Args:
        source (Dict[K, V]): The dict to split
        pred (Callable[[K], bool]): The predicate function to test keys

    Returns:
        Tuple[Dict[K, V], Dict[K, V]]: The pair (matching dict, non-matching dict)
    """
    matching: Dict[K, V] = {}
    nonmatching: Dict[K, V] = {}
    for key, value in source.items():
        if pred(key):
            matching[key] = value
        else:
            nonmatching[key] = value
    return matching, nonmatching


def get_random_color(forbidden_colors: List[Color]) -> Color:
    """Generates a random Color that is not in the list `forbidden_colors`."""
    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    if color in forbidden_colors:
        return get_random_color(forbidden_colors)
    return color


def squared_euclidean_distance(coord1: Coord, coord2: Coord) -> int:
    """Computes the squared Euclidean distance between two coordinates."""
    return (coord1.row - coord2.row) ** 2 + (coord1.col - coord2.col) ** 2


class StreamQueue(Generic[E]):
    """Wraps an asyncio Queue with a non-blocking interface to get every available element."""

    wrapped: asyncio.Queue

    def __init__(self, wrapped: asyncio.Queue):
        self.wrapped = wrapped

    async def put(self, item: E) -> None:
        """Puts `item` on the back of the queue.

        Note:
            This is a blocking method.
        """
        await self.wrapped.put(item)

    def get(self) -> List[E]:
        """Gets all items currently available from the queue."""
        result = []
        try:
            while True:
                result.append(self.wrapped.get_nowait())
        except asyncio.queues.QueueEmpty:
            pass
        return result


@dataclass(init=False)
class Nothing:
    """Represents an *absent* form of a Maybe."""

    is_present: Literal[False]

    def __init__(self):
        self.is_present = False


@dataclass(init=False)
class Just(Generic[T]):
    """Represents a *present* form of a Maybe."""

    is_present: Literal[True]
    value: T

    def __init__(self, value: T):
        self.is_present = True
        self.value = value


Maybe = Union[Just[T], Nothing]


class CompletableFuture(Generic[T]):
    """Represents a future object which can be supplied *once*."""

    wrapped: "asyncio.Future[T]"

    def __init__(self):
        self.wrapped = asyncio.Future()

    @property
    def is_present(self) -> bool:
        """Returns True if the future has been completed."""
        return self.wrapped.done()

    def complete(self, value: T) -> None:
        """Completes this future, and wakes up all coroutines waiting for it."""
        self.wrapped.set_result(value)

    def get_now(self) -> T:
        """Gets the stored value immediately. The future must have already completed."""
        return self.wrapped.result()

    def get_or_default(self, default: T2) -> Union[T, T2]:
        """Gets the stored value immediately if available, otherwise returns `default`."""
        if not self.is_present:
            return default
        return self.get_now()

    async def get(self) -> T:
        """Waits for another coroutine to supply a result, then returns it."""
        return await self.wrapped


async def read_all_available(stream: asyncio.StreamReader, buf: bytes = None) -> Optional[bytes]:
    """Reads all available bytes from the stream.
    If `buf` is provided, appends the read bytes to it. `buf` should implement `+=`.
    """
    if buf is not None:
        buf += await stream.read(2**16)
    else:
        return await stream.read(2**16)


class PlayerTimeoutException(Exception):
    """Represents a timeout for a player's turn."""

    pass


# Adapted from https://stackoverflow.com/a/22348885/6781533
class Timeout:
    def __init__(
        self,
        seconds=1,
        error_message="Function timed out",
        exception_type: type = PlayerTimeoutException,
    ):
        self.seconds = seconds
        self.error_message = error_message
        self.exception_type = exception_type

    def handle_timeout(self, *args):
        raise self.exception_type(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)
