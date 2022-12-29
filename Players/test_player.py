# pylint: disable=missing-function-docstring,missing-module-docstring,protected-access
import random
import unittest
from collections import OrderedDict

from Maze.Common.JSON.serializers import color_to_json
from Maze.Common.gem import Gem
from Maze.Common.state import PlayerSecret, PlayerState, RestrictedGameState, ShiftOp
from Maze.Common.test_board import ascii_board, board_to_ascii
from Maze.Common.test_tile import default_gems
from Maze.Common.tile import Direction, Tile, TileShape
from Maze.Common.utils import Coord
from Maze.Players.player import (
    IncorrectPhaseError,
    Player,
    PlayerGameplayImpl,
    PlayerScoringImpl,
    PlayerSetupImpl,
)
from Maze.Players.strategy import EuclidStrategy, TurnPass, TurnWithMove


class TestPlayer(unittest.TestCase):
    """Tests for the `Player` class"""

    def setUp(self):
        self.color = (160, 0, 255)
        self.other_color = (0, 255, 255)
        self.player = Player("Zoe", EuclidStrategy())
        self.concentric_board = ascii_board(
            # 123456
            "┌─────┐",  # 0
            "│┌───┐│",
            "││┌─┐││",  # 2
            "│││┼│││",
            "││└─┘││",  # 4
            "│└───┘│",
            "└─────┘",  # 6
        )
        self.inaccessible_board = ascii_board(
            # 123456
            "┌┐┌──┌┐",  # 0
            "└┌┌──└┘",
            "┌┌┌──││",  # 2
            "│││┼│││",
            "││───││",  # 4
            "┌┐───┌┐",
            "└┘───└┘",  # 6
        )
        self.player_states = OrderedDict(
            [
                (
                    color_to_json(self.color),
                    PlayerState(Coord(1, 1), Coord(1, 1), self.color, "Zoe"),
                ),
                (
                    color_to_json(self.other_color),
                    PlayerState(Coord(5, 1), Coord(5, 1), self.other_color, "Xena"),
                ),
            ]
        )
        self.spare_tile = Tile(TileShape.LINE, 0, default_gems)

    def test_name(self):
        self.assertEqual(self.player.name(), "Zoe")

    def test_invalid_board_dimensions(self):
        self.assertRaises(ValueError, lambda: self.player.propose_board0(0, 7))
        self.assertRaises(ValueError, lambda: self.player.propose_board0(-1, 7))
        self.assertRaises(ValueError, lambda: self.player.propose_board0(7, 0))
        self.assertRaises(ValueError, lambda: self.player.propose_board0(7, -1))

    def test_propose_board_must_not_follow_setup(self):
        game_state = RestrictedGameState(
            self.player_states,
            {color_to_json(self.color): PlayerSecret(Coord(3, 3), False)},
            self.spare_tile,
            self.concentric_board,
        )
        self.player.setup(game_state, Coord(3, 3))
        self.assertRaises(IncorrectPhaseError, lambda: self.player.propose_board0(7, 7))

    def test_propose_board_must_not_follow_win(self):
        game_state = RestrictedGameState(
            self.player_states,
            {color_to_json(self.color): PlayerSecret(Coord(3, 3), False)},
            self.spare_tile,
            self.concentric_board,
        )
        self.player.setup(game_state, Coord(3, 3))
        self.player.win(False)
        self.assertRaises(IncorrectPhaseError, lambda: self.player.propose_board0(7, 7))

    def test_propose_board(self):
        assert isinstance(self.player._implementation, PlayerSetupImpl)
        self.player._implementation._random = random.Random(0)
        board = self.player.propose_board0(7, 7)
        expected_tiles = [
            # 123456
            "┌└┤┘┤┐┐",  # 0
            "┘┴─┴─└┤",
            "─┤┐┌├┌─",  # 2
            "┌─┴├┬└─",
            "├─┐┴┘│┼",  # 4
            "┌┘─├├├└",
            "┌┴┴┐┌┼└",  # 6
        ]
        self.assertEqual(board_to_ascii(board), expected_tiles)
        self.assertEqual(
            [
                board.get_tile(Coord(0, 0)).gems,
                board.get_tile(Coord(1, 0)).gems,
                board.get_tile(Coord(2, 0)).gems,
                board.get_tile(Coord(3, 0)).gems,
                board.get_tile(Coord(4, 0)).gems,
                board.get_tile(Coord(5, 0)).gems,
                board.get_tile(Coord(6, 0)).gems,
            ],
            [
                (Gem.GRANDIDIERITE, Gem.MORGANITE_OVAL),
                (Gem.CLINOHUMITE, Gem.PADPARADSCHA_SAPPHIRE),
                (Gem.CITRINE, Gem.FANCY_SPINEL_MARQUISE),
                (Gem.AZURITE, Gem.PREHNITE),
                (Gem.APRICOT_SQUARE_RADIANT, Gem.LABRADORITE),
                (Gem.KUNZITE, Gem.RUBY_DIAMOND_PROFILE),
                (Gem.APLITE, Gem.STAR_CABOCHON),
            ],
        )

    def test_setup_needs_state_for_first_call(self):
        self.assertRaises(IncorrectPhaseError, lambda: self.player.setup(None, Coord(3, 3)))

    def test_setup_needs_no_state_for_second_call(self):
        game_state = RestrictedGameState(
            self.player_states,
            {color_to_json(self.color): PlayerSecret(Coord(3, 3), False)},
            self.spare_tile,
            self.concentric_board,
        )
        self.player.setup(game_state, Coord(3, 3))
        self.assertRaises(IncorrectPhaseError, lambda: self.player.setup(game_state, Coord(1, 1)))

    def test_setup_succeeds(self):
        game_state = RestrictedGameState(
            self.player_states,
            {color_to_json(self.color): PlayerSecret(Coord(3, 3), False)},
            self.spare_tile,
            self.concentric_board,
        )
        self.player.setup(game_state, Coord(3, 3))
        assert isinstance(self.player._implementation, PlayerGameplayImpl)
        self.assertEqual(
            self.player._implementation._player_state,
            self.player_states[color_to_json(self.color)],
        )
        self.assertEqual(self.player._implementation._player_secret, PlayerSecret(Coord(3, 3), False))
        self.player.setup(None, Coord(1, 1))
        # got treasure
        self.assertEqual(
            self.player._implementation._player_secret,
            PlayerSecret(Coord(3, 3), True, treasure_count=1),
        )

    def test_take_turn_must_follow_setup(self):
        game_state = RestrictedGameState(
            self.player_states,
            {color_to_json(self.color): PlayerSecret(Coord(3, 3), False)},
            self.spare_tile,
            self.concentric_board,
        )
        self.assertRaises(IncorrectPhaseError, lambda: self.player.take_turn(game_state))
        # setup should not change the phase unless it succeeds
        self.assertRaises(IncorrectPhaseError, lambda: self.player.setup(None, Coord(1, 1)))
        self.assertRaises(IncorrectPhaseError, lambda: self.player.take_turn(game_state))

    def test_take_turn_must_not_follow_win(self):
        game_state = RestrictedGameState(
            self.player_states,
            {color_to_json(self.color): PlayerSecret(Coord(3, 3), False)},
            self.spare_tile,
            self.concentric_board,
        )
        self.player.setup(game_state, Coord(3, 3))
        self.player.win(False)
        self.assertRaises(IncorrectPhaseError, lambda: self.player.take_turn(game_state))

    def test_take_turn_best_available(self):
        game_state = RestrictedGameState(
            self.player_states,
            {color_to_json(self.color): PlayerSecret(Coord(3, 3), False)},
            self.spare_tile,
            self.concentric_board,
        )
        self.player.setup(game_state, Coord(3, 3))
        # Middle of board will become
        #   start ↓
        #         ┌───┐
        #         ┌─┐││ ← (shifted row)
        #         ││┼││ ← end at cross
        #         │└─┘│
        #         └───┘
        self.assertEqual(
            self.player.take_turn(game_state),
            TurnWithMove(0, ShiftOp(Coord(6, 2), Direction.LEFT), Coord(3, 3)),
        )

    def test_take_turn_pass(self):
        game_state = RestrictedGameState(
            self.player_states,
            {color_to_json(self.color): PlayerSecret(Coord(3, 3), False)},
            self.spare_tile,
            self.inaccessible_board,
        )
        self.player.setup(game_state, Coord(3, 3))
        self.assertEqual(self.player.take_turn(game_state), TurnPass())

    def test_win_must_follow_setup(self):
        self.assertRaises(IncorrectPhaseError, lambda: self.player.win(False))
        self.assertRaises(IncorrectPhaseError, lambda: self.player.win(True))

    def test_win(self):
        game_state = RestrictedGameState(
            self.player_states,
            {color_to_json(self.color): PlayerSecret(Coord(3, 3), False)},
            self.spare_tile,
            self.concentric_board,
        )
        self.player.setup(game_state, Coord(3, 3))
        self.player.win(True)
        assert isinstance(self.player._implementation, PlayerScoringImpl)
        self.assertTrue(self.player._implementation._won)
        # must only be called once
        self.assertRaises(IncorrectPhaseError, lambda: self.player.win(True))

    def test_lost(self):
        game_state = RestrictedGameState(
            self.player_states,
            {color_to_json(self.color): PlayerSecret(Coord(3, 3), False)},
            self.spare_tile,
            self.concentric_board,
        )
        self.player.setup(game_state, Coord(3, 3))
        self.player.win(False)
        assert isinstance(self.player._implementation, PlayerScoringImpl)
        self.assertFalse(self.player._implementation._won)
        # must only be called once
        self.assertRaises(IncorrectPhaseError, lambda: self.player.win(False))
