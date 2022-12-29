"""(deprecated) A synchronous server implementation for Maze.com."""
import json
import socket
import sys
import random
from typing import List, Set, Tuple, cast

sys.path.append("..")
from Maze.Common.board import Board
from Maze.Common.gem import Gem
from Maze.Common.JSON.definitions import NameRegex
from Maze.Common.tile import Tile, TileShape
from Maze.Common.utils import Coord, Timeout
from Maze.Referee.referee import Referee
from Maze.Remote.player import ProxyPlayer
from Maze.Remote.player import AbstractPlayer

QUEUED_SERVER_CONNECTIONS = 5  # Number of queued connections to accept
MAX_SIGNUP_WAITING_PERIODS = 2  # Number of waiting periods to wait for players to sign up
CLIENT_NAME_WAIT = 2  # in seconds
PLAYER_SIGNUP_WAIT = 20  # in seconds
MIN_PLAYERS = 2  # minimum number of players to start a game
MAX_PLAYERS = 6  # maximum number of players to start a game
RECV_SIZE = 4096  # size of the buffer to receive data from the client


class PlayerWaitTimeoutError(Exception):
    """Server timed out waiting for player signups."""


class PlayerNameTimeoutError(Exception):
    """Player timed out without providing their name."""


class Server:
    """Represents a server for one Labyrinth game."""

    host: str = "0.0.0.0"
    port: int
    server_socket: socket.socket
    remote_player_proxies: List[AbstractPlayer]
    taken_player_names: Set[str]

    def __init__(self, port: int):
        self.port = port
        self.remote_player_proxies: List[AbstractPlayer] = []
        self.taken_player_names: Set[str] = set()

    def _handle_client(self, client: socket.socket):
        """Handles a single client connection to this server."""
        try:
            with Timeout(CLIENT_NAME_WAIT, exception_type=PlayerNameTimeoutError):
                player_name = client.recv(RECV_SIZE).decode("utf-8")
                unique_player_name = self._verify_player_name(player_name)
                self.taken_player_names.add(unique_player_name)
                self.remote_player_proxies.append(ProxyPlayer(unique_player_name, client))
        except PlayerNameTimeoutError:
            client.close()
            return
        except ValueError:
            client.close()
            return

    def _verify_player_name(self, player_name: str) -> str:
        """Checks that a player's name is valid and unique. If the name is not unique, a number is appended.

        Args:
            player_name: The player's name.

        Raises:
            ValueError: If `player_name` is invalid. (See `NameRegex` for details.)

        Returns:
            str: The unique name of the player.
        """
        # TODO (quick fix): raise custom error so it is clear we intend to catch it
        if NameRegex.match(player_name) is None or not (1 <= len(player_name) <= 20):
            raise ValueError("Invalid player name")
        if player_name in self.taken_player_names:
            return player_name + str(len(self.taken_player_names) + 1)
        return player_name

    def _wait_for_player_signups(self) -> None:
        """Waits for MAX_PLAYER players to connect to the server and send their name."""
        # TODO (sizeable overhaul): Does waiting for a player to provide their name block more players from joining?
        while len(self.remote_player_proxies) < MAX_PLAYERS:
            try:
                with Timeout(PLAYER_SIGNUP_WAIT, exception_type=PlayerWaitTimeoutError):
                    (client_socket, address) = self.server_socket.accept()
                    self._handle_client(client_socket)
            except PlayerWaitTimeoutError:
                break

    def _run_game(self) -> Tuple[List[str], List[str]]:
        """Runs a game to completion with the players connected to the server.

        Returns:
            Tuple[List[str], List[str]]: The first list contains the names of the
                winners in alphabetical order; the second list contains the names of the ejected players.
        """
        # TODO (minor change): this should be handled automatically in the referee using propose_board
        board, spare_tile = self._generate_random_board_and_spare()
        outcome = Referee(board, spare_tile).start_game(self.remote_player_proxies)
        results_by_name = sorted([pl.name() for pl in outcome.winners]), sorted([pl.name() for pl in outcome.ejected])
        return results_by_name

    def start(self) -> None:
        """Starts this server, handles signups, and runs a game to completion if possible."""
        # TODO (quick fix): return result instead of printing it?
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(QUEUED_SERVER_CONNECTIONS)
        try:
            num_waiting_periods = 0
            while num_waiting_periods < MAX_SIGNUP_WAITING_PERIODS:
                self._wait_for_player_signups()
                if self._start_game_conditions_met():
                    break
                num_waiting_periods += 1
            if len(self.remote_player_proxies) == 1:  # change to <= 1
                print([[], []])
            elif len(self.remote_player_proxies) >= MIN_PLAYERS:
                print(json.dumps(self._run_game(), ensure_ascii=False))
        # TODO (TBD depending on why this is here): remove blanked exception catch, if something can cause this, catch
        # TODO (cont) it specifically, otherwise players should not be able to raise exceptions in the server
        except Exception:
            print("Unexpected error:", sys.exc_info()[0])
        finally:
            self.shutdown()

    def shutdown(self):
        """Closes this server's listening socket and shuts down all proxy player connections."""
        # TODO (minor change): store players in server as tuple of AbstractPlayer and socket to avoid cast
        for remote_player in self.remote_player_proxies:
            remote_player = cast(ProxyPlayer, remote_player)
            remote_player.tcp_conn.close()
        self.server_socket.close()

    def _start_game_conditions_met(self) -> bool:
        """Checks whether the game has reached MIN_PLAYERS successful signups."""
        return len(self.remote_player_proxies) >= MIN_PLAYERS


if __name__ == "__main__":
    port = int(sys.argv[1])
    server = Server(port)
    server.start()
