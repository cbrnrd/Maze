"""An implementation of the Maze.com server using `asyncio`"""
import sys

sys.path.append("..")
import asyncio
import json
import time
from typing import List, Optional, Tuple

from Maze.Common.JSON.definitions import NameRegex
from Maze.Common.state import GameState
from Maze.Common.utils import Coord, read_all_available
from Maze.Players.player import AbstractPlayer
from Maze.Referee.observer import Observer
from Maze.Referee.referee import AsyncReferee
from Maze.Remote.player import ProxyPlayer


class PlayerWaitTimeoutError(Exception):
    """Server timed out waiting for player signups."""


class PlayerNameTimeoutError(Exception):
    """Player timed out without providing their name."""


class AsyncServer:
    QUEUED_SERVER_CONNECTIONS = 5  # Number of queued connections to accept
    MAX_SIGNUP_WAITING_PERIODS = 2  # Number of waiting periods to wait for players to sign up
    CLIENT_NAME_WAIT = 2  # in seconds
    PLAYER_SIGNUP_WAIT = 20  # in seconds
    MIN_PLAYERS = 2  # minimum number of players to start a game
    MAX_PLAYERS = 6  # maximum number of players to start a game
    ONE_MS_SLEEP = 0.001

    host: str  # Hostname to bind on
    port: int  # Port to listen on
    remote_player_proxies: List[AbstractPlayer]  # List of players in the order they signed up (oldest first)
    player_names: List[str]  # List of player names (in order of signup)

    # List of read/write streams for each player
    # in the order they signed up
    read_write_stream_pairs = List[Tuple[asyncio.StreamReader, asyncio.StreamWriter]]

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server = None
        self.remote_player_proxies = []
        self.player_names = []
        self.read_write_stream_pairs = []

    async def start(
        self,
        state_to_start_from: GameState = None,
        observers: Optional[List[Observer]] = None,
        goal_queue: Optional[List[Coord]] = None,
    ) -> List[List[str]]:
        """Starts the server and runs the game. Returns the winning and ejected player names.

        Args:
            state_to_start_from: The state to start the game from. If None, the game will start with a random board and spare.
            observers: A list of observers to observe the game.
            goal_queue: A list of goals to use for the game.

        Returns:
            List[List[str], List[str]]: A list containing a list containing the winning player names and
                                        a list containing the ejected player names.
        """
        self.server = await asyncio.start_server(
            self._handle_client_conn, self.host, self.port
        )  # , start_serving=False)
        result = await self.wait_for_signups_and_run_game(
            state_to_start_from, observers=observers, goal_queue=goal_queue
        )
        self.server.close()
        return result

    async def wait_for_signups_and_run_game(
        self,
        state_to_start_from: GameState,
        observers: Optional[List[Observer]] = None,
        goal_queue: Optional[List[Coord]] = None,
    ) -> List[List[str]]:
        """Enters the signup phase(s) and runs the game when it's done. Returns the winning and ejected player names.

        Args:
           state_to_start_from: The state to start the game from. If None, the game will start with a random board and spare.
           observers: A list of observers to observe the game.
           goal_queue: A list of goals to use for the game.

        Returns:
           List[List[str], List[str]]: A list containing a list containing the winning player names and
                                       a list containing the ejected player names.
        """
        num_elapsed_waiting_periods = 0
        while num_elapsed_waiting_periods < self.MAX_SIGNUP_WAITING_PERIODS:
            await self._wait_for_player_signups()
            if self._start_game_conditions_met():
                break
            num_elapsed_waiting_periods += 1
        if len(self.remote_player_proxies) < self.MIN_PLAYERS:
            return [[], []]
        return await self._run_game(state_to_start_from, observers=observers, goal_queue=goal_queue)

    async def _wait_for_player_signups(self):
        """Waits for PLAYER_SIGNUP_WAIT seconds for players to sign up for the game. If the number of players reaches
        MAX_PLAYERS, the waiting period will end prematurely."""
        init_time = time.time()
        elapsed_time = 0
        while elapsed_time < self.PLAYER_SIGNUP_WAIT and len(self.remote_player_proxies) < self.MAX_PLAYERS:
            await asyncio.sleep(self.ONE_MS_SLEEP)
            elapsed_time = time.time() - init_time

    def _start_game_conditions_met(self):
        """Checks if the server has enough players to start the game."""
        return self.MIN_PLAYERS <= len(self.remote_player_proxies) <= self.MAX_PLAYERS

    async def _read_player_name(self, reader: asyncio.StreamReader):
        """Reads a player's name from the client."""
        name = await read_all_available(reader)
        return json.loads(name.decode("utf-8"))

    def _close_conn(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Closes a player connection. Does not remove the readers and writers from read_write_stream_pairs."""
        reader.feed_eof()
        writer.close()

    async def _handle_client_conn(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        """Callback for a single client connection. Reads & verifies the
        player's name and adds them to the list of players."""
        try:
            player_name = await asyncio.wait_for(self._read_player_name(client_reader), self.CLIENT_NAME_WAIT)
            if len(self.remote_player_proxies) >= self.MAX_PLAYERS:
                self._close_conn(client_reader, client_writer)
                return
            self._verify_player_name(player_name)
            self.read_write_stream_pairs.append((client_reader, client_writer))
            self.remote_player_proxies.append(ProxyPlayer(player_name, client_reader, client_writer))
        except asyncio.TimeoutError:
            # Name timeout
            self._close_conn(client_reader, client_writer)
            return
        except ValueError as e:
            # Invalid name
            self._close_conn(client_reader, client_writer)
            return

    async def _run_game(
        self,
        state_to_start_from: GameState,
        observers: Optional[List[Observer]] = None,
        goal_queue: Optional[List[Coord]] = None,
    ) -> List[List[str]]:
        """Runs the game with the current list of players. Returns the winning and ejected player names."""
        if goal_queue is None:
            goal_queue = []
        if observers is None:
            observers = []
        ref = AsyncReferee()
        if state_to_start_from is None:
            outcome = await ref.start_game(self.remote_player_proxies, observers=observers)
        else:
            # NOTE: Some test failures were caused by reversing names in the wrong place, this is the correct place
            # to reverse the names of players so the youngest players go first
            # NOTE: The order of the player proxies is irrelevant as the ordering is handled by the the state
            # and when we call associate_players we establish which player is associated with which player in the state
            self.player_names.reverse()
            state_to_start_from = state_to_start_from.associate_players(self.player_names)
            outcome = await ref.start_game_from_state(
                state_to_start_from,
                self.remote_player_proxies,
                goal_queue,
                observers=observers,
            )
        results_by_name = [
            sorted([pl.name() for pl in outcome.winners]),
            sorted([pl.name() for pl in outcome.ejected]),
        ]
        # Close all player connections
        self._close_all_connections()

        return results_by_name

    def _close_all_connections(self):
        """Closes all player connections."""
        for reader, writer in self.read_write_stream_pairs:
            reader.feed_eof()
            writer.close()

    def _verify_player_name(self, player_name: str) -> None:
        """Checks that a player's name is valid. If so, add it to the list of player names

        Args:
            player_name: The player's name.

        Raises:
            ValueError: If `player_name` is invalid. (See `NameRegex` for details.)

        """
        if NameRegex.match(player_name) is None or not (1 <= len(player_name) <= 20):
            raise ValueError("Invalid player name")
        self.player_names.append(player_name)


class AsyncServerWrapper:
    wrapped: AsyncServer
    loop: asyncio.AbstractEventLoop

    def __init__(self, host: str, port: int):
        self.wrapped = AsyncServer(host, port)
        self.loop = asyncio.get_event_loop()

    def start(self, state_to_start_from: GameState = None, observers=None):
        result = self.loop.run_until_complete(self.wrapped.start(state_to_start_from, observers=observers))
        self.loop.close()
        print(json.dumps(result))


if __name__ == "__main__":
    server = AsyncServerWrapper("0.0.0.0", 12345)
    server.start()
