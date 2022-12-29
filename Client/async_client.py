"""An `async` client for the Maze game. Handles a single player."""
import json
import sys

sys.path.append("..")
import asyncio
import socket
from functools import wraps
from typing import Callable, Tuple, cast

from Maze.Players.player import AbstractPlayer, Player
from Maze.Players.strategy import EuclidStrategy
from Maze.Remote.referee import RemoteReferee


def connected(func: Callable) -> Callable:
    """Decorator to check if the client is connected."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        if not self.is_connected:
            raise ConnectionError("Not connected to server")
        else:
            return func(*args, **kwargs)

    return wrapper


class AsyncClient:
    """Represents a Client that runs asynchronously which will provide its player's name as it signs up to play
    then execute any instructions given to it over the network using its RemoteReferee"""
    _host: str
    _port: int
    _server_connection: Tuple[asyncio.StreamReader, asyncio.StreamWriter] = cast(
        Tuple[asyncio.StreamReader, asyncio.StreamWriter], None
    )
    _remote_referee: RemoteReferee

    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port

    @property
    def is_connected(self) -> bool:
        """Returns True if the client is connected to the server."""
        return self._server_connection is not None

    @property
    def server_reader(self) -> asyncio.StreamReader:
        return self._server_connection[0]

    @property
    def server_writer(self) -> asyncio.StreamWriter:
        return self._server_connection[1]


    async def connect(self) -> None:
        """Attempts to connect to the server and sets _server_connection if successful.

        Raises:
            ConnectionError: If the client is unable to connect to the server.
        """
        while self._server_connection is None:
            try:
                self._server_connection = await asyncio.open_connection(self._host, self._port)
            except (ConnectionRefusedError, OSError):
                # Server isn't up, wait a bit and try again.
                await asyncio.sleep(1)
                self._server_connection = None
            except socket.gaierror:
                raise ConnectionError("Invalid host name")
        if self._server_connection is None:
            raise ConnectionError("Could not connect to server")

    @connected
    async def start_remote_referee(self, player: AbstractPlayer):
        """Starts the remote referee for this client using the provided player to make decisions."""
        self._remote_referee = RemoteReferee(player, self.server_reader, self.server_writer)
        await self._remote_referee.listen_and_handle_messages()

    @connected
    async def send_name(self, name: str) -> None:
        """Sends the player's name to the server."""
        self.server_writer.write(json.dumps(name).encode("utf-8"))
        await self.server_writer.drain()


if __name__ == "__main__":
    client = AsyncClient("localhost", int(sys.argv[1]))
    name = sys.argv[2]
    player = Player(name, EuclidStrategy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.connect())
    loop.run_until_complete(client.send_name(name))
    loop.run_until_complete(client.start_remote_referee(player))
    loop.close()
