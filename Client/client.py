"""(Deprecated) A synchronous client for the Maze game."""

import sys
import socket
from functools import wraps
from typing import cast, Callable

sys.path.append("..")
from Maze.Players.player import AbstractPlayer, Player
from Maze.Players.strategy import EuclidStrategy
from Maze.Remote.referee import RemoteReferee

MAX_CONNECTION_ATTEMPTS = 5


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


class Client:
    """Represents a player client connected to the server for Labyrinth."""

    _host: str
    _port: int
    _server_connection: socket.socket = cast(socket.socket, None)
    _remote_referee: RemoteReferee

    @property
    def is_connected(self) -> bool:
        """Returns True if the client is connected to the server."""
        return self._server_connection is not None

    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self._connect()

    def _connect(self) -> None:
        """Connects to the server and sets _server_connection."""
        # TODO: I guess to satisfy requirement about waiting for server we just remove check on MAX_CONNECTION_ATTEMPTS
        # TODO and leave player hanging
        connection_attempts = 0
        while connection_attempts < MAX_CONNECTION_ATTEMPTS and self._server_connection is None:
            try:
                self._server_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._server_connection.connect((self._host, self._port))
            except ConnectionRefusedError:
                connection_attempts += 1
                self._server_connection = None
            except socket.gaierror:
                raise ConnectionError("Invalid host name")
        if self._server_connection is None:
            raise ConnectionError("Could not connect to server")

    @connected
    def send_name(self, name: str) -> None:
        """Sends the player's name to the server."""
        self._server_connection.send(name.encode("utf-8"))

    @connected
    def start_remote_referee(self, player: AbstractPlayer) -> None:
        """Starts the proxy referee for the player."""
        self._remote_referee = RemoteReferee(player, self._server_connection)


if __name__ == "__main__":
    name = sys.argv[2]
    player = Player(name, EuclidStrategy())
    client = Client("localhost", int(sys.argv[1]))
    client.send_name(name)
    client.start_remote_referee(player)
