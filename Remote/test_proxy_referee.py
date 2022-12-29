import asyncio
import json
import asynctest
from collections import OrderedDict
from Maze.Common.JSON.serializers import (
    coord_to_json,
    game_state_to_json,
    color_to_json,
)
from Maze.Common.state import PlayerSecret, PlayerState, RestrictedGameState
from Maze.Common.test_board import ascii_board
from Maze.Common.test_tile import default_gems
from Maze.Common.tile import Tile, TileShape
from Maze.Common.utils import Coord
from Maze.Players.player import Player
from Maze.Players.strategy import EuclidStrategy
from Maze.Remote.referee import RemoteReferee


class TestProxyReferee(asynctest.TestCase):
    def setUp(self):
        self.name = "testplayer"
        self.player = Player(self.name, EuclidStrategy())
        self.host = "localhost"
        self.port = 12345
        self.reader = asynctest.mock.Mock(asyncio.StreamReader)
        self.writer = asynctest.mock.Mock(asyncio.StreamWriter)
        self.proxy_referee = RemoteReferee(self.player, self.reader, self.writer)
        self.num_read_calls = 0

        self.five_by_five_board = ascii_board(
            # 1234
            "┌┬┬┬┐",  # 0
            "├┼┼┼┤",
            "├┼┼┼┤",  # 2
            "├┼┼┼┤",
            "└┴┴┴┘",  # 4
        )
        self.color1 = (160, 0, 255)
        self.color2 = (0, 255, 255)
        self.player_states = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 1), Coord(1, 1), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(3, 1), Coord(3, 1), self.color2, "Xena"),
                ),
            ]
        )
        self.player_secrets = {
            color_to_json(self.color1): PlayerSecret(Coord(1, 3), False),
        }
        self.spare_tile = Tile(TileShape.LINE, 0, default_gems)
        self.restricted_state = RestrictedGameState(
            self.player_states,
            self.player_secrets,
            self.spare_tile,
            self.five_by_five_board,
        )

    async def test_dispatch_messages_for_full_game_in_order(self):
        # Initial setup
        setup_return_value = json.dumps(
            [
                "setup",
                [game_state_to_json(self.restricted_state), coord_to_json(Coord(1, 3))],
            ]
        )
        self.reader.read = lambda *args, **kwargs: self.mock_user_function(setup_return_value)
        await self.proxy_referee.listen_and_handle_messages()
        self.writer.write.assert_called_with(b'"void"')

        # takeTurn
        take_turn_return_value = json.dumps(["take-turn", [game_state_to_json(self.restricted_state)]])
        self.num_read_calls = 0
        self.reader.read = lambda *args, **kwargs: self.mock_user_function(take_turn_return_value)
        await self.proxy_referee.listen_and_handle_messages()
        self.writer.write.assert_called_with(b'[0, "LEFT", 0, {"row#": 3, "column#": 1}]')

        # Setup with goal reminder

        setup_2_return_value = json.dumps(["setup", [False, coord_to_json(Coord(1, 1))]])
        self.num_read_calls = 0
        self.reader.read = lambda *args, **kwargs: self.mock_user_function(setup_2_return_value)
        await self.proxy_referee.listen_and_handle_messages()
        self.writer.write.assert_called_with(b'"void"')

        # Win
        win_json = json.dumps(["win", [True]])
        self.num_read_calls = 0
        self.reader.read = lambda *args, **kwargs: self.mock_user_function(win_json)
        await self.proxy_referee.listen_and_handle_messages()
        self.writer.write.assert_called_with(b'"void"')

    async def mock_user_function(self, return_val):
        if self.num_read_calls == 0:
            self.num_read_calls += 1
            return return_val.encode("utf-8")
        return ""
