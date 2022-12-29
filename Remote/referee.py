"""Implements the proxy referee for the players of Maze.com"""
import asyncio
import json
from typing import Any, TextIO, cast

import ijson.common
from typing_extensions import Literal

from Maze.Common.JSON.definitions import ChoiceJson, CoordinateJson, MNameJson, StateJson
from Maze.Common.JSON.deserializers import get_coord, get_state
from Maze.Common.JSON.reader import get_json_objects
from Maze.Common.JSON.serializers import turn_action_to_json
from Maze.Common.utils import read_all_available
from Maze.Players.player import AbstractPlayer

RECV_SIZE = 4096


class ServerReadError(Exception):
    """Raised when the server returns invalid JSON."""

    def __init__(self, msg: str):
        super().__init__(msg)


class RemoteReferee:
    """Represents a proxy for the referee in a Labyrinth game."""

    player: AbstractPlayer
    server_reader: asyncio.StreamReader
    server_writer: asyncio.StreamWriter

    def __init__(
        self,
        player: AbstractPlayer,
        server_reader: asyncio.StreamReader,
        server_writer: asyncio.StreamWriter,
    ):
        """Initializes a new RemoteReferee. Does not start listening for messages."""
        self.player = player
        self.server_reader = server_reader
        self.server_writer = server_writer

    def _parse_and_respond(self, msg: bytes) -> str:
        """Parses a `msg` from the server and returns the response as a JSON string.

        Raises:
            ServerReadError: If the server returns poorly-formed JSON OR an invalid request (according to the spec).
        """
        request_object = self._get_one_object(msg)
        if not self._is_valid_request(request_object):
            raise ServerReadError("Invalid request received from server")
        method_name = request_object[0]
        args = request_object[1]
        return self._dispatch_method(method_name, *args)

    def _dispatch_method(self, method_name: MNameJson, *args: Any) -> Any:
        """Dispatches a method call to the player."""
        if method_name == "setup":
            result = self._setup(*args)
        elif method_name == "take-turn":
            result = self._take_turn(*args)
        elif method_name == "win":
            result = self._win(*args)
        else:
            raise ServerReadError(f"Invalid method name received from server: {method_name}")
        return json.dumps(result, ensure_ascii=False)

    def _get_one_object(self, msg: bytes):
        """Gets a single object from the given `msg`. If there are more than one, the rest are ignored."""
        try:
            obj = next(get_json_objects(cast(TextIO, msg)))
            return obj
        except ValueError:
            raise ServerReadError(f"Invalid JSON received from server (`msg` type: {type(msg)})")
        except ijson.common.IncompleteJSONError:
            raise ServerReadError(f"Incomplete JSON received from server: {msg}")

    def _is_valid_request(self, obj: list) -> bool:
        """Returns whether the given message `obj`ect is a valid request.
        A valid request is a JSON array of the form [MName, [args...]].

        """
        if not isinstance(obj, list):
            return False
        if len(obj) != 2:
            return False
        if not isinstance(obj[0], str):
            return False
        if not isinstance(obj[1], list):
            return False
        return True

    async def listen_and_handle_messages(self) -> None:
        """Listens for messages from the referee and responds using the player."""
        while True:
            msg = await read_all_available(self.server_reader)
            if not msg:
                break
            resp = self._parse_and_respond(msg)
            self.server_writer.write(resp.encode("utf-8"))

    def _setup(self, state: StateJson, coord: CoordinateJson) -> Literal["void"]:
        """Parses the given state and coord and calls the player's setup method."""
        coord_obj = get_coord(coord)  # JSON parsing: CoordJson -> Coord
        state_obj = None if not state else get_state(state)  # JSON parsing: StateJson -> GameState
        self.player.setup(state_obj, coord_obj)
        return "void"

    def _take_turn(self, state: StateJson) -> ChoiceJson:
        """Parses the given state and calls the player's take_turn method."""
        state_obj = get_state(state)  # JSON parsing: StateJson -> GameState
        move = self.player.take_turn(state_obj)
        return turn_action_to_json(move)

    def _win(self, w) -> Literal["void"]:
        """Calls win on the player and return the string "void" """
        self.player.win(w)
        return "void"
