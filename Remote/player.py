"""Proxy player implementation for Maze.com."""
import asyncio

"""
Asyncio is a horrible library.
This is used to monkeypatch asyncio to allow tasks to be created while the event loop is already running. 
This is important for reading from a asyncio.StreamReader in a non-async function.

Additionally, this classes methods cannot be converted to `async` methods because that would break the interface.
If we were to convert the methods in `AbstractPlayer` to async methods, we would have to convert the methods in `Player`
to async methods, which is a WHOLE LOT of work that, frankly, I don't want to do.
https://stackoverflow.com/questions/46827007/runtimeerror-this-event-loop-is-already-running-in-python
"""
import nest_asyncio

nest_asyncio.apply()

import json
from typing import Any, Iterator, Optional, TextIO, cast

from Maze.Common.board import Board
from Maze.Common.JSON.deserializers import get_turn_action_from_json
from Maze.Common.JSON.reader import get_json_objects
from Maze.Common.JSON.serializers import coord_to_json, game_state_to_json, mname_to_json
from Maze.Common.state import GameState
from Maze.Common.utils import Coord, read_all_available
from Maze.Players.player import AbstractPlayer
from Maze.Players.strategy import TurnAction


class ProxyPlayer(AbstractPlayer):
    """Represents a proxy for a remote player in a Labyrinth game."""

    _name: str
    client_reader: asyncio.StreamReader
    client_writer: asyncio.StreamWriter

    def __init__(
        self,
        name: str,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
    ):
        """Create a proxy player with a name and read/write stream"""
        self._name = name
        self.client_reader = client_reader
        self.client_writer = client_writer

    def name(self) -> str:
        """Return the name of this proxy player"""
        return self._name

    def propose_board0(self, rows: int, columns: int) -> Board:
        """Proposes an initial board of the given size (not implemented for a proxy player)."""
        raise NotImplementedError()

    def setup(self, state0: Optional[GameState], goal: Coord) -> str:
        """Updates this player with an initial state (or None), and a goal position.

        Raises:
            ValueError: If the remote player returns anything other than the string 'void'
            ijson.IncompleteJsonError: If the remote player returns invalid JSON
        """
        game_state_json = False if state0 is None else game_state_to_json(state0)
        func_json = json.dumps(
            [mname_to_json("setup"), [game_state_json, coord_to_json(goal)]],
            ensure_ascii=False,
        )
        resp_objects = self._send_and_receive_json(func_json)

        resp = next(resp_objects)
        # the second half of this if block is validating that the player sends just the string "void" and nothing else
        if resp != "void" or next(resp_objects, None) is not None:
            raise ValueError("Expected void return from setup (got {})".format(resp))
        return "void"

    def take_turn(self, s: GameState) -> TurnAction:
        """Selects an action for this turn using the player's strategy.

        Raises:
            ValueError: If the remote player returns anything other than a Choice.
            ijson.IncompleteJsonError: If the remote player returns invalid JSON
        """
        func_json = json.dumps(
            [mname_to_json("take_turn"), [game_state_to_json(s)]],
            ensure_ascii=False,
        )
        resp_objects = list(self._send_and_receive_json(func_json))
        if resp_objects and len(resp_objects) == 1:
            return get_turn_action_from_json(resp_objects[0], s.board)
        raise ValueError("Expected Choice return from take_turn")

    def win(self, w: bool) -> str:
        """Updates this player to indicate that they won the game.

        Raises:
           ValueError: If the remote player returns anything other than the string 'void'
           ijson.IncompleteJsonError: If the remote player returns invalid JSON
        """
        func_json = json.dumps(
            [mname_to_json("win"), [w]],
            ensure_ascii=False,
        )
        resp_objects = self._send_and_receive_json(func_json)
        resp = next(resp_objects)
        if resp != "void" or next(resp_objects, None) is not None:
            raise ValueError("Expected void return from win (got {})".format(resp))
        return "void"

    def _send_and_receive_json(self, func_json: str) -> Iterator[Any]:
        """Sends `func_json` to the remote player and returns the parsed response.

        Raises:
            ValueError: If the remote player returns no data
            ijson.IncompleteJsonError: If the remote player returns invalid JSON
        """
        # Send data
        self.client_writer.write(func_json.encode("utf-8"))

        # Read response
        # Why does reading from a StreamReader require an async function?
        # But writing does not? The world may never know.
        task = asyncio.ensure_future(read_all_available(self.client_reader))
        asyncio.get_event_loop().run_until_complete(task)
        data = cast(bytes, task.result()).decode("utf-8")
        if len(data) == 0:
            raise ValueError("No bytes received from remote player")

        # Parse the received data as JSON
        return get_json_objects(cast(TextIO, data))
