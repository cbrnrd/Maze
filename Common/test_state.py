# pylint: disable=missing-function-docstring,missing-module-docstring,protected-access
import unittest
from collections import OrderedDict
from typing import Dict, Set

from Maze.Common.JSON.serializers import color_to_json
from Maze.Common.board import Board, ShiftNotAllowedError
from Maze.Common.gem import Gem
from Maze.Common.state import (
    EmptyPrevAction,
    GameState,
    NoMorePlayersError,
    OffroadingError,
    PartialTurnPrevAction,
    PlayerListModificationError,
    PlayerSecret,
    PlayerState,
    PrevAction,
    RefereeGameState,
    RestrictedGameState,
    SecretAccessError,
    ShiftOp,
    TurnContractViolation,
    UndoNotAllowedError,
    ZeroMovementError,
)
from Maze.Common.test_board import all_treasures, ascii_board, list_delete, list_insert
from Maze.Common.test_tile import default_gems
from Maze.Common.tile import Direction, Tile, TileShape
from Maze.Common.utils import Coord


class TestGameState(unittest.TestCase):
    """Tests for the `GameState` class."""

    def setUp(self):
        """Create a basic board and starting tile for testing."""
        self.initial_board = ascii_board(
            # 123456
            "┌┬┬┬┬┬┐",  # 0
            "├┼┼┼┼┼┤",
            "├┼┼┼┼┼┤",  # 2
            "├┼┼┼┼┼┤",
            "├┼┼┼┼┼┤",  # 4
            "├┼┼┼┼┼┤",
            "└┴┴┴┴┴┘",  # 6
        )
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
        self.spare_tile = Tile(TileShape.LINE, 0, default_gems)
        self.treasure_location1 = Coord(3, 5)
        self.treasure_location2 = Coord(5, 5)
        self.color1 = (255, 0, 0)
        self.color2 = (0, 100, 100)
        self.individual_secrets = [
            {color_to_json(self.color1): PlayerSecret(self.treasure_location1, False)},
            {color_to_json(self.color2): PlayerSecret(self.treasure_location2, False)},
        ]
        self.player_secrets = {
            **self.individual_secrets[0],
            **self.individual_secrets[1],
        }
        self.player_states = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 1), Coord(1, 1), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(5, 1), Coord(5, 1), self.color2, "Xena"),
                ),
            ]
        )

    @classmethod
    def setUpClass(cls):
        # This is an abstract test class for our two implementations
        # RestrictedGameState and RefereeGameState
        raise unittest.SkipTest("Abstract")

    def pick_player_secrets(self, color: Set[str]) -> Dict[str, PlayerSecret]:
        raise NotImplementedError()

    def construct_state(
        self,
        player_states: "OrderedDict[str, PlayerState]",
        player_secrets: Dict[str, PlayerSecret],
        spare_tile: Tile,
        board: Board,
        prev_action: PrevAction = EmptyPrevAction(),
        starting_player_index: int = 0,
    ) -> GameState:
        raise NotImplementedError()

    def test_nonunique_spare_tile_gems(self):
        self.assertRaises(
            ValueError,
            lambda: self.construct_state(
                OrderedDict(),
                self.pick_player_secrets({color_to_json(self.color1)}),
                Tile(TileShape.LINE, 0, (Gem.ALEXANDRITE_PEAR_SHAPE, Gem.ALEXANDRITE)),
                self.initial_board,
            ),
        )

    def test_not_enough_players(self):
        self.assertRaises(
            ValueError,
            lambda: self.construct_state(
                OrderedDict(),
                self.pick_player_secrets({color_to_json(self.color1)}),
                self.spare_tile,
                self.initial_board,
            ),
        )

    def test_out_of_bounds_player_locations(self):
        updated_players1 = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 1), Coord(-1, -1), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(5, 1), Coord(5, 1), self.color2, "Xena"),
                ),
            ]
        )
        self.assertRaises(
            IndexError,
            lambda: self.construct_state(
                updated_players1,
                self.pick_player_secrets({color_to_json(self.color1)}),
                self.spare_tile,
                self.initial_board,
            ),
        )
        updated_players2 = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 1), Coord(1, 1), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(5, 1), Coord(7, 1), self.color2, "Xena"),
                ),
            ]
        )
        self.assertRaises(
            IndexError,
            lambda: self.construct_state(
                updated_players2,
                self.pick_player_secrets({color_to_json(self.color1)}),
                self.spare_tile,
                self.initial_board,
            ),
        )

    def test_out_of_bounds_player_home_locations(self):
        updated_players1 = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(-1, -1), Coord(1, 1), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(5, 1), Coord(5, 1), self.color1, "Xena"),
                ),
            ]
        )
        self.assertRaises(
            IndexError,
            lambda: self.construct_state(
                updated_players1,
                self.pick_player_secrets({color_to_json(self.color1)}),
                self.spare_tile,
                self.initial_board,
            ),
        )
        updated_players2 = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 1), Coord(1, 1), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(7, 1), Coord(5, 1), self.color1, "Xena"),
                ),
            ]
        )
        self.assertRaises(
            IndexError,
            lambda: self.construct_state(
                updated_players2,
                self.pick_player_secrets({color_to_json(self.color1)}),
                self.spare_tile,
                self.initial_board,
            ),
        )

    def test_nonfixed_player_home_locations(self):
        updated_players1 = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(2, 2), Coord(1, 1), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(5, 1), Coord(5, 1), self.color1, "Xena"),
                ),
            ]
        )
        self.assertRaises(
            ValueError,
            lambda: self.construct_state(
                updated_players1,
                self.pick_player_secrets({color_to_json(self.color1)}),
                self.spare_tile,
                self.initial_board,
            ),
        )
        updated_players2 = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 1), Coord(1, 1), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(6, 6), Coord(5, 1), self.color1, "Xena"),
                ),
            ]
        )
        self.assertRaises(
            ValueError,
            lambda: self.construct_state(
                updated_players2,
                self.pick_player_secrets({color_to_json(self.color1)}),
                self.spare_tile,
                self.initial_board,
            ),
        )

    def test_out_of_bounds_player_treasure_location(self):
        raise NotImplementedError()

    def test_bad_starting_index(self):
        self.assertRaises(
            IndexError,
            lambda: self.construct_state(
                self.player_states,
                self.pick_player_secrets({color_to_json(self.color1)}),
                self.spare_tile,
                self.initial_board,
                starting_player_index=-1,
            ),
        )
        self.assertRaises(
            IndexError,
            lambda: self.construct_state(
                self.player_states,
                self.pick_player_secrets({color_to_json(self.color1)}),
                self.spare_tile,
                self.initial_board,
                starting_player_index=2,
            ),
        )

    def test_rotate_spare_tile_zero_degrees(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        state2 = state.rotate_spare_tile(0)
        self.assertEqual(state2.player_states, state.player_states)
        self.assertEqual(state2.board, state.board)
        self.assertEqual(state2.spare_tile, state.spare_tile)
        self.assertEqual(state2.current_player_index, state.current_player_index)

    def test_rotate_spare_tile_invalid_degrees(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertRaises(ValueError, lambda: state.rotate_spare_tile(30))
        self.assertRaises(ValueError, lambda: state.rotate_spare_tile(-40))

    def test_rotate_spare_tile_after_shifting(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        state = state.shift_tiles(ShiftOp(Coord(4, 0), Direction.DOWN))
        self.assertRaises(TurnContractViolation, lambda: state.rotate_spare_tile(90))
        state = state.move_current_player(Coord(2, 2))
        state.rotate_spare_tile(90)

    def test_rotate_spare_tile_multiples_of_90_degrees(self):
        # Numbers of degrees to rotate by
        rotations = [-360, -270, -180, -90, 0, 90, 180, 270, 360, 450]
        # Pairs of start rotation and results of rotating by each of the `rotations`
        params = [
            (0, [0, 1, 2, 3, 0, 1, 2, 3, 0, 1]),
            (1, [1, 2, 3, 0, 1, 2, 3, 0, 1, 2]),
            (2, [2, 3, 0, 1, 2, 3, 0, 1, 2, 3]),
            (3, [3, 0, 1, 2, 3, 0, 1, 2, 3, 0]),
        ]
        for starting, expected in params:
            with self.subTest(msg=f"Checking rotations of spare tile with starting rotation {starting}"):
                for r, e in zip(rotations, expected):
                    state = self.construct_state(
                        self.player_states,
                        self.pick_player_secrets({color_to_json(self.color1)}),
                        Tile(TileShape.CORNER, starting, default_gems),
                        self.initial_board,
                    )
                    self.assertEqual(
                        state.rotate_spare_tile(r).spare_tile,
                        Tile(TileShape.CORNER, e, default_gems),
                    )

    def test_shift_tiles_invalid_args(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        # out of bounds
        self.assertRaises(IndexError, lambda: state.shift_tiles(ShiftOp(Coord(-1, -1), Direction.UP)))
        self.assertRaises(IndexError, lambda: state.shift_tiles(ShiftOp(Coord(7, 7), Direction.UP)))
        # left edge, upward shift
        self.assertRaises(ValueError, lambda: state.shift_tiles(ShiftOp(Coord(0, 2), Direction.UP)))
        # top edge, right shift
        self.assertRaises(ValueError, lambda: state.shift_tiles(ShiftOp(Coord(2, 0), Direction.RIGHT)))
        # non-edge
        self.assertRaises(ValueError, lambda: state.shift_tiles(ShiftOp(Coord(2, 2), Direction.RIGHT)))
        # fixed row
        self.assertRaises(
            ShiftNotAllowedError,
            lambda: state.shift_tiles(ShiftOp(Coord(6, 1), Direction.LEFT)),
        )
        # fixed column
        self.assertRaises(
            ShiftNotAllowedError,
            lambda: state.shift_tiles(ShiftOp(Coord(5, 0), Direction.DOWN)),
        )

    def test_shift_tiles_invalid_state(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            prev_action=PartialTurnPrevAction(ShiftOp(Coord(4, 0), Direction.DOWN)),
        )
        self.assertRaises(
            TurnContractViolation,
            lambda: state.shift_tiles(ShiftOp(Coord(4, 0), Direction.DOWN)),
        )
        state = state.move_current_player(Coord(2, 2))
        # undo column
        self.assertRaises(
            UndoNotAllowedError,
            lambda: state.shift_tiles(ShiftOp(Coord(4, 6), Direction.UP)),
        )
        state = state.shift_tiles(ShiftOp(Coord(0, 4), Direction.RIGHT)).move_current_player(Coord(3, 3))
        # undo row
        self.assertRaises(
            UndoNotAllowedError,
            lambda: state.shift_tiles(ShiftOp(Coord(6, 4), Direction.LEFT)),
        )

    def test_shift_row_without_player(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        state2 = state.shift_tiles(ShiftOp(Coord(0, 0), Direction.RIGHT))
        expected_treasures = list_insert(list_delete(all_treasures, 6), 0, default_gems)
        expected_board = ascii_board(
            # 123456
            "│┌┬┬┬┬┬",  # 0
            "├┼┼┼┼┼┤",
            "├┼┼┼┼┼┤",  # 2
            "├┼┼┼┼┼┤",
            "├┼┼┼┼┼┤",  # 4
            "├┼┼┼┼┼┤",
            "└┴┴┴┴┴┘",  # 6
            treasures=expected_treasures,
        )
        self.assertEqual(state.board, self.initial_board)
        self.assertEqual(state2.board, expected_board)
        self.assertEqual(state2.player_states, self.player_states)
        spare_treasure = all_treasures[6]
        self.assertEqual(
            state2.spare_tile,
            Tile(TileShape.CORNER, 2, spare_treasure),
        )

    def test_shift_row_with_player(self):
        updated_players = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 1), Coord(0, 2), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(5, 1), Coord(1, 2), self.color2, "Xena"),
                ),
            ]
        )
        state = self.construct_state(
            updated_players,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        state = state.shift_tiles(ShiftOp(Coord(6, 2), Direction.LEFT))
        expected_treasures = list_insert(list_delete(all_treasures, 14), 20, default_gems)
        expected_board = ascii_board(
            # 123456
            "┌┬┬┬┬┬┐",  # 0
            "├┼┼┼┼┼┤",
            "┼┼┼┼┼┤│",  # 2
            "├┼┼┼┼┼┤",
            "├┼┼┼┼┼┤",  # 4
            "├┼┼┼┼┼┤",
            "└┴┴┴┴┴┘",  # 6
            treasures=expected_treasures,
        )
        self.assertEqual(state.board, expected_board)
        self.assertEqual(
            state.player_states,
            {
                color_to_json(self.color1): PlayerState(Coord(1, 1), Coord(6, 2), self.color1, "Zoe"),
                color_to_json(self.color2): PlayerState(Coord(5, 1), Coord(0, 2), self.color2, "Xena"),
            },
        )
        # must not change order
        self.assertEqual(
            list(state.player_states.keys()),
            [color_to_json(self.color1), color_to_json(self.color2)],
        )
        spare_treasure = all_treasures[14]
        self.assertEqual(state.spare_tile, Tile(TileShape.TEE, 3, spare_treasure))

    def test_shift_column_without_player(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        state2 = state.shift_tiles(ShiftOp(Coord(0, 6), Direction.UP))
        expected_treasures = all_treasures.copy()
        # column shift: [0]=[7] [7]=[14] ... [35]=[42]
        expected_treasures[0:42:7] = expected_treasures[7:49:7]
        expected_treasures[42] = default_gems
        expected_board = ascii_board(
            # 123456
            "├┬┬┬┬┬┐",  # 0
            "├┼┼┼┼┼┤",
            "├┼┼┼┼┼┤",  # 2
            "├┼┼┼┼┼┤",
            "├┼┼┼┼┼┤",  # 4
            "└┼┼┼┼┼┤",
            "│┴┴┴┴┴┘",  # 6
            treasures=expected_treasures,
        )
        self.assertEqual(state.board, self.initial_board)
        self.assertEqual(state2.board, expected_board)
        self.assertEqual(state2.player_states, self.player_states)
        spare_treasure = all_treasures[0]
        self.assertEqual(
            state2.spare_tile,
            Tile(TileShape.CORNER, 1, spare_treasure),
        )

    def test_shift_column_with_player(self):
        updated_players = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 1), Coord(2, 6), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(5, 1), Coord(2, 5), self.color2, "Xena"),
                ),
            ]
        )
        state = self.construct_state(
            updated_players,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        state = state.shift_tiles(ShiftOp(Coord(2, 0), Direction.DOWN))
        expected_treasures = all_treasures.copy()
        # column shift: [9]=[2] [16]=[9] ... [44]=[37]
        expected_treasures[9 : 9 + 42 : 7] = expected_treasures[2 : 2 + 42 : 7]
        expected_treasures[2] = default_gems
        expected_board = ascii_board(
            # 123456
            "┌┬│┬┬┬┐",  # 0
            "├┼┬┼┼┼┤",
            "├┼┼┼┼┼┤",  # 2
            "├┼┼┼┼┼┤",
            "├┼┼┼┼┼┤",  # 4
            "├┼┼┼┼┼┤",
            "└┴┼┴┴┴┘",  # 6
            treasures=expected_treasures,
        )
        self.assertEqual(state.board, expected_board)
        self.assertEqual(
            state.player_states,
            {
                color_to_json(self.color1): PlayerState(Coord(1, 1), Coord(2, 0), self.color1, "Zoe"),
                color_to_json(self.color2): PlayerState(Coord(5, 1), Coord(2, 6), self.color2, "Xena"),
            },
        )
        # must not change order
        self.assertEqual(
            list(state.player_states.keys()),
            [color_to_json(self.color1), color_to_json(self.color2)],
        )
        spare_treasure = all_treasures[44]
        self.assertEqual(state.spare_tile, Tile(TileShape.TEE, 2, spare_treasure))

    def test_move_player_invalid_args(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            prev_action=PartialTurnPrevAction(ShiftOp(Coord(4, 0), Direction.DOWN)),
        )
        self.assertRaises(IndexError, lambda: state.move_current_player(Coord(-1, -1)))
        self.assertRaises(ZeroMovementError, lambda: state.move_current_player(Coord(1, 1)))

    def test_move_player_invalid_state(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertRaises(TurnContractViolation, lambda: state.move_current_player(Coord(1, 5)))
        state = state.shift_tiles(ShiftOp(Coord(0, 4), Direction.RIGHT)).move_current_player(Coord(1, 5))
        self.assertRaises(TurnContractViolation, lambda: state.move_current_player(Coord(1, 1)))

    def test_move_player_unreachable(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.concentric_board,
            prev_action=PartialTurnPrevAction(ShiftOp(Coord(4, 0), Direction.DOWN)),
        )
        self.assertRaises(OffroadingError, lambda: state.move_current_player(Coord(3, 3)))
        self.assertRaises(OffroadingError, lambda: state.move_current_player(Coord(0, 0)))

    def test_move_player_to_tile_without_treasure(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.concentric_board,
            prev_action=PartialTurnPrevAction(ShiftOp(Coord(4, 0), Direction.DOWN)),
        )
        state = state.move_current_player(Coord(5, 5))
        self.assertEqual(
            state.player_states,
            {
                color_to_json(self.color1): PlayerState(Coord(1, 1), Coord(5, 5), self.color1, "Zoe"),
                color_to_json(self.color2): PlayerState(Coord(5, 1), Coord(5, 1), self.color2, "Xena"),
            },
        )
        self.assertEqual(
            state.get_current_player_secret(),
            PlayerSecret(self.treasure_location1, False),
        )

    def test_move_player_to_tile_with_treasure(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.concentric_board,
            prev_action=PartialTurnPrevAction(ShiftOp(Coord(4, 0), Direction.DOWN)),
        )
        state = state.move_current_player(Coord(3, 5))
        self.assertEqual(
            state.player_states,
            {
                color_to_json(self.color1): PlayerState(Coord(1, 1), Coord(3, 5), self.color1, "Zoe"),
                color_to_json(self.color2): PlayerState(Coord(5, 1), Coord(5, 1), self.color2, "Xena"),
            },
        )
        self.assertEqual(
            state.get_current_player_secret(),
            PlayerSecret(self.treasure_location1, False),
        )

    def test_get_legal_shift_ops(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        all_shifts = {
            ShiftOp(Coord(0, 0), Direction.RIGHT),
            ShiftOp(Coord(0, 2), Direction.RIGHT),
            ShiftOp(Coord(0, 4), Direction.RIGHT),
            ShiftOp(Coord(0, 6), Direction.RIGHT),
            ShiftOp(Coord(6, 0), Direction.LEFT),
            ShiftOp(Coord(6, 2), Direction.LEFT),
            ShiftOp(Coord(6, 4), Direction.LEFT),
            ShiftOp(Coord(6, 6), Direction.LEFT),
            ShiftOp(Coord(0, 0), Direction.DOWN),
            ShiftOp(Coord(2, 0), Direction.DOWN),
            ShiftOp(Coord(4, 0), Direction.DOWN),
            ShiftOp(Coord(6, 0), Direction.DOWN),
            ShiftOp(Coord(0, 6), Direction.UP),
            ShiftOp(Coord(2, 6), Direction.UP),
            ShiftOp(Coord(4, 6), Direction.UP),
            ShiftOp(Coord(6, 6), Direction.UP),
        }
        self.assertEqual(state.get_legal_shift_ops(), all_shifts)
        state = state.shift_tiles(ShiftOp(Coord(4, 0), Direction.DOWN))
        # Can't shift twice in a row
        self.assertEqual(state.get_legal_shift_ops(), set())
        state = state.move_current_player(Coord(2, 2))
        self.assertEqual(
            state.get_legal_shift_ops(),
            all_shifts - {ShiftOp(Coord(4, 6), Direction.UP)},
        )

    def test_can_get_first_player_secret(self):
        raise NotImplementedError()

    def test_can_get_second_player_secret(self):
        raise NotImplementedError()

    def test_can_get_player_secret_invalid_name(self):
        raise NotImplementedError()

    def test_get_first_player_secret(self):
        raise NotImplementedError()

    def test_get_second_player_secret(self):
        raise NotImplementedError()

    def test_get_first_player_goal(self):
        raise NotImplementedError()

    def test_get_second_player_goal(self):
        raise NotImplementedError()

    def test_get_player_secret_invalid_name(self):
        raise NotImplementedError()

    def test_is_reachable_by_current_player_connected_board(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        for x in range(7):
            for y in range(7):
                with self.subTest(msg=f"Checking reachability of tile {(x, y)} for current player"):
                    self.assertTrue(state.is_reachable_by_current_player(Coord(x, y)))
        self.assertFalse(state.is_reachable_by_current_player(Coord(-1, -1)))
        self.assertFalse(state.is_reachable_by_current_player(Coord(8, 8)))

    def test_is_reachable_by_current_player_disconnected_board(self):
        updated_players = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 1), Coord(3, 3), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(5, 1), Coord(5, 1), self.color2, "Xena"),
                ),
            ]
        )
        state = self.construct_state(
            updated_players,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.concentric_board,
        )
        for x in range(7):
            for y in range(7):
                with self.subTest(msg=f"Checking reachability of tile {(x, y)} for current player"):
                    if (x, y) == (3, 3):
                        self.assertTrue(state.is_reachable_by_current_player(Coord(x, y)))
                    else:
                        self.assertFalse(state.is_reachable_by_current_player(Coord(x, y)))

    def test_is_first_player_at_treasure(self):
        raise NotImplementedError()

    def test_is_second_player_at_treasure(self):
        raise NotImplementedError()

    def test_is_current_player_at_home(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            prev_action=PartialTurnPrevAction(ShiftOp(Coord(6, 6), Direction.LEFT)),
        )
        self.assertTrue(state.is_current_player_at_home())
        state2 = state.move_current_player(Coord(1, 5))
        self.assertFalse(state2.is_current_player_at_home())

    def test_eject_current_player_for_first_player(self):
        raise NotImplementedError()

    def test_eject_current_player_for_last_player(self):
        raise NotImplementedError()

    def test_eject_player_for_nonexistent_player(self):
        raise NotImplementedError

    def test_eject_player_for_final_player(self):
        raise NotImplementedError

    def test_eject_player_for_player_before_current(self):
        raise NotImplementedError()

    def test_eject_player_for_current_and_last_player(self):
        raise NotImplementedError()

    def test_eject_player_for_current_and_not_last_player(self):
        raise NotImplementedError()

    def test_eject_player_for_player_after_current(self):
        raise NotImplementedError()

    def test_end_current_turn(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertEqual(state.current_player_index, 0)
        state = state.end_current_turn()
        self.assertEqual(state.current_player_index, 1)
        state = state.end_current_turn()
        self.assertEqual(state.current_player_index, 0)


class TestRestrictedGameState(TestGameState):
    """Tests for the `RestrictedGameState` class."""

    @classmethod
    def setUpClass(cls):
        # This is overriding our abstract test class
        return

    def pick_player_secrets(self, colors: Set[str]) -> Dict[str, PlayerSecret]:
        result = {}
        for color, secret in self.player_secrets.items():
            if color in colors:
                result[color] = secret
        return result

    def construct_state(
        self,
        player_states: "OrderedDict[str, PlayerState]",
        player_secrets: Dict[str, PlayerSecret],
        spare_tile: Tile,
        board: Board,
        prev_action: PrevAction = EmptyPrevAction(),
        starting_player_index: int = 0,
    ) -> RestrictedGameState:
        return RestrictedGameState(
            player_states,
            player_secrets,
            spare_tile,
            board,
            prev_action,
            starting_player_index,
        )

    def test_out_of_bounds_player_treasure_location(self):
        self.assertRaises(
            IndexError,
            lambda: self.construct_state(
                self.player_states,
                {color_to_json(self.color1): PlayerSecret(Coord(-1, -1), False)},
                self.spare_tile,
                self.initial_board,
            ),
        )
        self.assertRaises(
            IndexError,
            lambda: self.construct_state(
                self.player_states,
                {color_to_json(self.color1): PlayerSecret(Coord(7, 7), False)},
                self.spare_tile,
                self.initial_board,
            ),
        )

    def test_can_get_first_player_secret(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertTrue(state.can_get_current_player_secret())
        self.assertTrue(state.can_get_player_secret(color_to_json(self.color1)))

    def test_can_get_second_player_secret(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            starting_player_index=1,
        )
        self.assertFalse(state.can_get_current_player_secret())
        self.assertFalse(state.can_get_player_secret(color_to_json(self.color2)))

    def test_can_get_player_secret_invalid_name(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertFalse(state.can_get_player_secret(""))
        self.assertFalse(state.can_get_player_secret("asdf"))

    def test_get_first_player_secret(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertEqual(
            state.get_current_player_secret(),
            PlayerSecret(self.treasure_location1, False),
        )
        self.assertEqual(
            state.get_player_secret(color_to_json(self.color1)),
            PlayerSecret(self.treasure_location1, False),
        )

    def test_get_second_player_secret(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            starting_player_index=1,
        )
        self.assertRaises(
            SecretAccessError,
            lambda: state.get_current_player_secret(),
        )
        self.assertRaises(
            SecretAccessError,
            lambda: state.get_player_secret(color_to_json(self.color2)),
        )

    def test_get_player_secret_invalid_name(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertRaises(SecretAccessError, lambda: state.get_player_secret(""))
        self.assertRaises(SecretAccessError, lambda: state.get_player_secret("asdf"))

    def test_get_first_player_goal(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertEqual(state.get_current_player_treasure_location(), Coord(3, 5))

    def test_get_second_player_goal(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            starting_player_index=1,
        )
        self.assertRaises(
            SecretAccessError,
            lambda: state.get_current_player_treasure_location(),
        )

    def test_is_first_player_at_treasure(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            prev_action=PartialTurnPrevAction(ShiftOp(Coord(6, 6), Direction.LEFT)),
        )
        self.assertFalse(state.is_current_player_at_treasure())
        state2 = state.move_current_player(Coord(3, 5))
        self.assertTrue(state2.is_current_player_at_treasure())

    def test_is_second_player_at_treasure(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            starting_player_index=1,
        )
        self.assertRaises(SecretAccessError, lambda: state.is_current_player_at_treasure())

    def test_eject_current_player_for_first_player(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertRaises(
            PlayerListModificationError,
            lambda: state.eject_current_player(),
        )

    def test_eject_current_player_for_last_player(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            starting_player_index=1,
        )
        self.assertRaises(
            PlayerListModificationError,
            lambda: state.eject_current_player(),
        )

    def test_eject_player_for_nonexistent_player(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertRaises(
            PlayerListModificationError,
            lambda: state.eject_player("Yana"),
        )

    def test_eject_player_for_final_player(self):
        state = self.construct_state(
            {color_to_json(self.color1): self.player_states[color_to_json(self.color1)]},
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertRaises(
            PlayerListModificationError,
            lambda: state.eject_player(color_to_json(self.color1)),
        )

    def test_eject_player_for_player_before_current(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            starting_player_index=1,
        )
        self.assertRaises(
            PlayerListModificationError,
            lambda: state.eject_player(color_to_json(self.color1)),
        )

    def test_eject_player_for_current_and_last_player(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            starting_player_index=1,
        )
        self.assertRaises(
            PlayerListModificationError,
            lambda: state.eject_player(color_to_json(self.color2)),
        )

    def test_eject_player_for_current_and_not_last_player(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertRaises(
            PlayerListModificationError,
            lambda: state.eject_player(color_to_json(self.color1)),
        )

    def test_eject_player_for_player_after_current(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertRaises(
            PlayerListModificationError,
            lambda: state.eject_player(color_to_json(self.color2)),
        )


class TestRefereeGameState(TestGameState):
    """Tests for the `RefereeGameState` class."""

    @classmethod
    def setUpClass(cls):
        # This is overriding our abstract test class
        return

    def pick_player_secrets(self, colors: Set[str]) -> Dict[str, PlayerSecret]:
        return self.player_secrets

    def construct_state(
        self,
        player_states: "OrderedDict[str, PlayerState]",
        player_secrets: Dict[str, PlayerSecret],
        spare_tile: Tile,
        board: Board,
        prev_action: PrevAction = EmptyPrevAction(),
        starting_player_index: int = 0,
    ) -> RefereeGameState:
        return RefereeGameState(
            player_states,
            player_secrets,
            spare_tile,
            board,
            prev_action,
            starting_player_index,
        )

    def test_out_of_bounds_player_treasure_location(self):
        updated_secrets1 = {
            color_to_json(self.color1): PlayerSecret(Coord(-1, -1), False),
            color_to_json(self.color2): self.player_secrets[color_to_json(self.color2)],
        }
        self.assertRaises(
            IndexError,
            lambda: self.construct_state(
                self.player_states,
                updated_secrets1,
                self.spare_tile,
                self.initial_board,
            ),
        )
        updated_secrets2 = {
            color_to_json(self.color1): self.player_secrets[color_to_json(self.color1)],
            color_to_json(self.color2): PlayerSecret(Coord(7, 7), False),
        }
        self.assertRaises(
            IndexError,
            lambda: self.construct_state(
                self.player_states,
                updated_secrets2,
                self.spare_tile,
                self.initial_board,
            ),
        )

    def test_can_get_first_player_secret(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertTrue(state.can_get_current_player_secret())
        self.assertTrue(state.can_get_player_secret(color_to_json(self.color1)))

    def test_can_get_second_player_secret(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            starting_player_index=1,
        )
        self.assertTrue(state.can_get_current_player_secret())
        self.assertTrue(state.can_get_player_secret(color_to_json(self.color2)))

    def test_can_get_player_secret_invalid_name(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertFalse(state.can_get_player_secret(""))
        self.assertFalse(state.can_get_player_secret("asdf"))

    def test_get_first_player_secret(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertEqual(
            state.get_current_player_secret(),
            PlayerSecret(self.treasure_location1, False),
        )
        self.assertEqual(
            state.get_player_secret(color_to_json(self.color1)),
            PlayerSecret(self.treasure_location1, False),
        )

    def test_get_second_player_secret(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            starting_player_index=1,
        )
        self.assertEqual(
            state.get_current_player_secret(),
            PlayerSecret(self.treasure_location2, False),
        )
        self.assertEqual(
            state.get_player_secret(color_to_json(self.color2)),
            PlayerSecret(self.treasure_location2, False),
        )

    def test_get_player_secret_invalid_name(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertRaises(KeyError, lambda: state.get_player_secret(""))
        self.assertRaises(KeyError, lambda: state.get_player_secret("asdf"))

    def test_get_first_player_goal(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        self.assertEqual(state.get_current_player_treasure_location(), Coord(3, 5))

    def test_get_second_player_goal(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            starting_player_index=1,
        )
        self.assertEqual(state.get_current_player_treasure_location(), Coord(5, 5))

    def test_is_first_player_at_treasure(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            prev_action=PartialTurnPrevAction(ShiftOp(Coord(6, 6), Direction.LEFT)),
        )
        self.assertFalse(state.is_current_player_at_treasure())
        state2 = state.move_current_player(Coord(3, 5))
        self.assertTrue(state2.is_current_player_at_treasure())

    def test_is_second_player_at_treasure(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            prev_action=PartialTurnPrevAction(ShiftOp(Coord(6, 6), Direction.LEFT)),
            starting_player_index=1,
        )
        self.assertFalse(state.is_current_player_at_treasure())
        state2 = state.move_current_player(Coord(5, 5))
        self.assertTrue(state2.is_current_player_at_treasure())

    def test_eject_current_player_for_first_player(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        state = state.eject_current_player()
        self.assertEqual(state.num_players, 1)
        self.assertEqual(state.player_colors, [color_to_json(self.color2)])
        self.assertEqual(
            state.player_states,
            {color_to_json(self.color2): PlayerState(Coord(5, 1), Coord(5, 1), self.color2, "Xena")},
        )
        self.assertEqual(state.current_player_index, 0)

        self.assertRaises(
            NoMorePlayersError,
            lambda: state.eject_current_player(),
        )

    def test_eject_current_player_for_last_player(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            starting_player_index=1,
        )
        state = state.eject_current_player()
        self.assertEqual(state.num_players, 1)
        self.assertEqual(state.player_colors, [color_to_json(self.color1)])
        self.assertEqual(
            state.player_states,
            {color_to_json(self.color1): PlayerState(Coord(1, 1), Coord(1, 1), self.color1, "Zoe")},
        )
        self.assertEqual(state.current_player_index, 0)

        self.assertRaises(
            NoMorePlayersError,
            lambda: state.eject_current_player(),
        )

    def test_eject_player_for_nonexistent_player(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        new_state = state.eject_player("Yana")

        self.assertEqual(new_state.num_players, state.num_players)
        self.assertEqual(new_state.player_colors, state.player_colors)
        self.assertEqual(new_state.player_states, state.player_states)
        self.assertEqual(new_state.player_secrets, state.player_secrets)

    def test_eject_player_for_final_player(self):
        state = self.construct_state(
            {color_to_json(self.color1): self.player_states[color_to_json(self.color1)]},
            {color_to_json(self.color1): self.player_secrets[color_to_json(self.color1)]},
            self.spare_tile,
            self.initial_board,
        )
        self.assertRaises(
            NoMorePlayersError,
            lambda: state.eject_player(color_to_json(self.color1)),
        )

    def test_eject_player_for_player_before_current(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            starting_player_index=1,
        )
        state = state.eject_player(color_to_json(self.color1))

        self.assertEqual(state.num_players, 1)
        self.assertEqual(state.player_colors, [color_to_json(self.color2)])
        self.assertEqual(
            state.player_states,
            {color_to_json(self.color2): PlayerState(Coord(5, 1), Coord(5, 1), self.color2, "Xena")},
        )
        self.assertEqual(state.current_player_index, 0)

    def test_eject_player_for_current_and_last_player(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
            starting_player_index=1,
        )
        state = state.eject_player(color_to_json(self.color2))

        self.assertEqual(state.num_players, 1)
        self.assertEqual(state.player_colors, [color_to_json(self.color1)])
        self.assertEqual(
            state.player_states,
            {color_to_json(self.color1): PlayerState(Coord(1, 1), Coord(1, 1), self.color1, "Zoe")},
        )
        self.assertEqual(state.current_player_index, 0)

    def test_eject_player_for_current_and_not_last_player(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        state = state.eject_player(color_to_json(self.color1))

        self.assertEqual(state.num_players, 1)
        self.assertEqual(state.player_colors, [color_to_json(self.color2)])
        self.assertEqual(
            state.player_states,
            {color_to_json(self.color2): PlayerState(Coord(5, 1), Coord(5, 1), self.color2, "Xena")},
        )
        self.assertEqual(state.current_player_index, 0)

    def test_eject_player_for_player_after_current(self):
        state = self.construct_state(
            self.player_states,
            self.pick_player_secrets({color_to_json(self.color1)}),
            self.spare_tile,
            self.initial_board,
        )
        state = state.eject_player(color_to_json(self.color2))

        self.assertEqual(state.num_players, 1)
        self.assertEqual(state.player_colors, [color_to_json(self.color1)])
        self.assertEqual(
            state.player_states,
            {color_to_json(self.color1): PlayerState(Coord(1, 1), Coord(1, 1), self.color1, "Zoe")},
        )
        self.assertEqual(state.current_player_index, 0)
