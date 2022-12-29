import asyncio
import json
import asynctest
from collections import OrderedDict

from Maze.Common.JSON.serializers import (
    color_to_json,
    coord_to_json,
    game_state_to_json, turn_action_to_json,
)
from Maze.Common.state import PlayerSecret, PlayerState, RestrictedGameState, ShiftOp
from Maze.Common.test_board import ascii_board
from Maze.Common.test_tile import default_gems
from Maze.Common.tile import Direction, Tile, TileShape
from Maze.Common.utils import Coord
from Maze.Players.player import Player
from Maze.Players.strategy import TurnWithMove, EuclidStrategy, TurnPass
from Maze.Remote.player import ProxyPlayer


class TestProxyReferee(asynctest.TestCase):
    def setUp(self):
        self.name = "testplayer"
        self.player = Player(self.name, EuclidStrategy())
        self.host = "localhost"
        self.port = 12345
        self.reader = asynctest.mock.Mock(asyncio.StreamReader)
        self.writer = asynctest.mock.Mock(asyncio.StreamWriter)
        self.proxy_player = ProxyPlayer("Zoe", self.reader, self.writer)
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

    def test_setup_with_state(self):
        json_method_call = json.dumps(
            [
                "setup",
                [game_state_to_json(self.restricted_state), coord_to_json(Coord(3, 3))],
            ], ensure_ascii=False
        )
        self.reader.read = lambda *args, **kwargs: self.mock_user_function(json.dumps("void", ensure_ascii=False))
        self.assertEqual(self.proxy_player.setup(self.restricted_state, Coord(3, 3)), "void")
        self.writer.write.assert_called_with(json_method_call.encode('utf-8'))

    def test_setup_without_state(self):
        json_method_call = json.dumps(
            [
                "setup",
                [False, coord_to_json(Coord(3, 3))],
            ], ensure_ascii=False
        )
        self.reader.read = lambda *args, **kwargs: self.mock_user_function(json.dumps("void", ensure_ascii=False))
        self.assertEqual(self.proxy_player.setup(None, Coord(3, 3)), "void")
        self.writer.write.assert_called_with(json_method_call.encode('utf-8'))

    def test_lose(self):
        json_method_call = json.dumps(
            [
                "win",
                [False],
            ], ensure_ascii=False
        )
        self.reader.read = lambda *args, **kwargs: self.mock_user_function(json.dumps("void", ensure_ascii=False))
        self.assertEqual(self.proxy_player.win(False), "void")
        self.writer.write.assert_called_with(json_method_call.encode('utf-8'))

    def test_win(self):
        json_method_call = json.dumps(
            [
                "win",
                [True],
            ], ensure_ascii=False
        )
        self.reader.read = lambda *args, **kwargs: self.mock_user_function(json.dumps("void", ensure_ascii=False))
        self.assertEqual(self.proxy_player.win(True), "void")
        self.writer.write.assert_called_with(json_method_call.encode('utf-8'))

    def test_take_turn(self):
        player_move = TurnWithMove(0, ShiftOp(Coord(2, 0), Direction.DOWN), Coord(0, 0))
        player_move_json = json.dumps(turn_action_to_json(player_move), ensure_ascii=False)
        json_method_call = json.dumps(
            [
                "take-turn",
                [game_state_to_json(self.restricted_state)],
            ], ensure_ascii=False
        )
        self.reader.read = lambda *args, **kwargs: self.mock_user_function(player_move_json)
        self.assertEqual(self.proxy_player.take_turn(self.restricted_state), player_move)
        self.writer.write.assert_called_with(json_method_call.encode('utf-8'))

    def test_take_turn_invalid_move(self):
        player_move = TurnWithMove(90, ShiftOp(Coord(0, 1), Direction.RIGHT), Coord(-1, 50))
        player_move_json = json.dumps(turn_action_to_json(player_move), ensure_ascii=False)
        json_method_call = json.dumps(
            [
                "take-turn",
                [game_state_to_json(self.restricted_state)],
            ], ensure_ascii=False
        )
        self.reader.read = lambda *args, **kwargs: self.mock_user_function(player_move_json)
        self.assertEqual(self.proxy_player.take_turn(self.restricted_state), player_move)
        self.writer.write.assert_called_with(json_method_call.encode('utf-8'))

    def test_take_turn_pass(self):
        player_move = TurnPass()
        player_move_json = json.dumps(turn_action_to_json(player_move), ensure_ascii=False)
        json_method_call = json.dumps(
            [
                "take-turn",
                [game_state_to_json(self.restricted_state)],
            ], ensure_ascii=False
        )
        self.reader.read = lambda *args, **kwargs: self.mock_user_function(player_move_json)
        self.assertEqual(self.proxy_player.take_turn(self.restricted_state), player_move)
        self.writer.write.assert_called_with(json_method_call.encode('utf-8'))

    async def mock_user_function(self, return_val):
        if self.num_read_calls == 0:
            self.num_read_calls += 1
            return return_val.encode("utf-8")
        return ""
