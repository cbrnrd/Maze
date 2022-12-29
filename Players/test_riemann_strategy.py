# pylint: disable=missing-function-docstring,missing-module-docstring,protected-access
import unittest
from collections import OrderedDict

from Maze.Common.JSON.serializers import color_to_json
from Maze.Common.state import PlayerSecret, PlayerState, RestrictedGameState, ShiftOp
from Maze.Common.test_board import ascii_board
from Maze.Common.test_tile import default_gems
from Maze.Common.tile import Direction, Tile, TileShape
from Maze.Common.utils import Coord
from Maze.Players.strategy import RiemannStrategy, TurnPass, TurnWithMove


class TestRiemannStrategy(unittest.TestCase):
    """Tests for the `RiemannStrategy` class."""

    def setUp(self):
        self.strategy = RiemannStrategy()
        five_by_five_board = ascii_board(
            # 1234
            "┌┐│┌┐",  # 0
            "└┘│└┘",
            "──└──",  # 2
            "┌└│┌┐",
            "├┘│└┤",  # 4
        )
        spare_tile = Tile(TileShape.LINE, 1, default_gems)
        self.treasure_location = Coord(3, 3)
        self.color1 = (255, 0, 0)
        self.color2 = (0, 100, 100)
        self.player_secrets = [
            {color_to_json(self.color1): PlayerSecret(self.treasure_location, False)},
            {color_to_json(self.color2): PlayerSecret(self.treasure_location, False)},
        ]
        self.player_states = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 1), Coord(4, 0), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(1, 3), Coord(0, 0), self.color2, "Xena"),
                ),
            ]
        )
        self.p1_state = RestrictedGameState(
            self.player_states,
            self.player_secrets[0],
            spare_tile,
            five_by_five_board,
        )
        self.p2_state = RestrictedGameState(
            self.player_states,
            self.player_secrets[1],
            spare_tile,
            five_by_five_board,
            starting_player_index=1,
        )

    def test_movement_exploration_order(self):
        self.assertEqual(
            self.strategy.movement_exploration_order(self.p1_state),
            [
                Coord(3, 3),
                Coord(0, 0),
                Coord(1, 0),
                Coord(2, 0),
                Coord(3, 0),
                Coord(4, 0),
                Coord(0, 1),
                Coord(1, 1),
                Coord(2, 1),
                Coord(3, 1),
                Coord(4, 1),
                Coord(0, 2),
                Coord(1, 2),
                Coord(2, 2),
                Coord(3, 2),
                Coord(4, 2),
                Coord(0, 3),
                Coord(1, 3),
                Coord(2, 3),
                Coord(4, 3),
                Coord(0, 4),
                Coord(1, 4),
                Coord(2, 4),
                Coord(3, 4),
                Coord(4, 4),
            ],
        )

    def test_shift_exploration_order(self):
        all_shift_ops_in_order = [
            ShiftOp(Coord(4, 0), Direction.LEFT),
            ShiftOp(Coord(0, 0), Direction.RIGHT),
            ShiftOp(Coord(4, 2), Direction.LEFT),
            ShiftOp(Coord(0, 2), Direction.RIGHT),
            ShiftOp(Coord(4, 4), Direction.LEFT),
            ShiftOp(Coord(0, 4), Direction.RIGHT),
            ShiftOp(Coord(0, 4), Direction.UP),
            ShiftOp(Coord(0, 0), Direction.DOWN),
            ShiftOp(Coord(2, 4), Direction.UP),
            ShiftOp(Coord(2, 0), Direction.DOWN),
            ShiftOp(Coord(4, 4), Direction.UP),
            ShiftOp(Coord(4, 0), Direction.DOWN),
        ]
        self.assertEqual(self.strategy.shift_exploration_order(self.p1_state), all_shift_ops_in_order)
        next_state = self.p1_state.shift_tiles(ShiftOp(Coord(4, 4), Direction.UP))
        next_state = next_state.move_current_player(Coord(4, 3))
        # last shift op is the one we just did, reversed
        self.assertEqual(
            self.strategy.shift_exploration_order(next_state),
            all_shift_ops_in_order[:-1],
        )

    def test_rotation_exploration_order(self):
        self.assertEqual(self.strategy.rotation_exploration_order(self.p1_state), [0, 270, 180, 90])

    def test_get_action_can_reach_treasure_goal(self):
        self.assertEqual(
            self.strategy.get_action(self.p1_state),
            TurnWithMove(0, ShiftOp(Coord(4, 4), Direction.UP), Coord(3, 3)),
        )

    def test_get_action_cannot_reach_treasure_goal(self):
        self.assertEqual(
            self.strategy.get_action(self.p2_state),
            # rotate horizontal line to vertical line
            #              end ↓↓ start
            # top rows become: │┌┐│┌
            #                  └┘│└┘
            TurnWithMove(270, ShiftOp(Coord(0, 0), Direction.RIGHT), Coord(0, 0)),
        )

    def test_get_action_can_reach_home_goal(self):
        updated_secrets = {
            color_to_json(self.color1): self.player_secrets[0][color_to_json(self.color1)].set_is_going_home()
        }
        goal_is_home_state = self.p1_state._copy_builder.set_player_secrets(updated_secrets).build()
        self.assertEqual(
            self.strategy.get_action(goal_is_home_state),
            # rotate horizontal line to vertical line
            #            start ↓
            # top rows become: │┌┐│┌
            #                  └┘│└┘
            #                   ↑ end
            TurnWithMove(270, ShiftOp(Coord(0, 0), Direction.RIGHT), Coord(1, 1)),
        )

    def test_get_action_cannot_reach_home_goal(self):
        updated_players = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    self.player_states[color_to_json(self.color1)],
                ),
                (
                    color_to_json(self.color2),
                    self.player_states[color_to_json(self.color2)].with_location(Coord(3, 3)),
                ),
            ]
        )
        updated_secrets = {
            color_to_json(self.color2): self.player_secrets[1][color_to_json(self.color2)].set_is_going_home()
        }
        goal_is_home_state = (
            self.p2_state._copy_builder.set_player_states(updated_players).set_player_secrets(updated_secrets).build()
        )
        self.assertEqual(
            self.strategy.get_action(goal_is_home_state),
            # rotation doesn't matter
            #                end ↓
            # right cols become: │┌┘
            #                    │└─
            #                    └─┐
            #                    │┌┤ ← start=┌ (shifted to row above)
            #                    │└─
            #                      ↑ inserted
            TurnWithMove(0, ShiftOp(Coord(4, 4), Direction.UP), Coord(2, 0)),
        )

    def test_get_action_cannot_move(self):
        stranded_state = self.p2_state._copy_builder.set_player_states(
            OrderedDict(
                [
                    (
                        color_to_json(self.color1),
                        self.player_states[color_to_json(self.color1)],
                    ),
                    (
                        color_to_json(self.color2),
                        self.player_states[color_to_json(self.color2)].with_location(Coord(1, 3)),
                    ),
                ]
            )
        ).build()
        self.assertEqual(self.strategy.get_action(stranded_state), TurnPass())
