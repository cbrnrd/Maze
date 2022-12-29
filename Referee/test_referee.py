# pylint: disable=missing-function-docstring,missing-module-docstring,protected-access
import time
import unittest
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List
from unittest.mock import MagicMock

from Maze.Common.JSON.serializers import color_to_json
from Maze.Common.state import GameState, PlayerSecret, PlayerState, RefereeGameState, ShiftOp
from Maze.Common.test_board import ascii_board
from Maze.Common.test_tile import default_gems
from Maze.Common.tile import Direction, Tile, TileShape
from Maze.Common.utils import Coord
from Maze.Players.player import Player
from Maze.Players.strategy import EuclidStrategy, RiemannStrategy, Strategy, TurnPass, TurnWithMove
from Maze.Referee.referee import GameOutcome, Referee


class MockStrategy(Strategy):
    """Creates a mock version of a Strategy."""

    mock: MagicMock

    def __init__(self, mock: MagicMock):
        self.mock = mock

    def get_action(self, state):
        return self.mock(state)


@dataclass(init=False, unsafe_hash=True)
class MockPlayer(Player):
    """Creates a mock version of a Player."""

    mock: MagicMock
    fail_method: str
    player: Player

    def __init__(self, mock: MagicMock, fail_method: str, player: Player):
        self.mock = mock
        self.fail_method = fail_method
        self.player = player

    def name(self):
        if self.fail_method == "name":
            return self.mock()
        return self.player.name()

    def setup(self, state0, goal):
        if self.fail_method == "setup":
            return self.mock()
        return self.player.setup(state0, goal)

    def take_turn(self, state):
        if self.fail_method == "take_turn":
            return self.mock()
        return self.player.take_turn(state)

    def win(self, w):
        if self.fail_method == "win":
            return self.mock()
        return self.player.win(w)


@dataclass
class SpyMockPlayer(Player):
    """Creates a mock version of a Player."""

    spy_method: str
    player: Player
    spy_count: int = 0
    goals: List[Coord] = field(default_factory=list)
    previous_move_to: Coord = None

    def name(self):
        if self.spy_method == "name":
            self.spy_count += 1
        return self.player.name()

    def setup(self, state0, goal):
        if self.spy_method == "setup":
            self.spy_count += 1
        self.goals.append(goal)
        return self.player.setup(state0, goal)

    def take_turn(self, state):
        if self.spy_method == "take_turn":
            self.spy_count += 1
        move = self.player.take_turn(state)
        self.previous_move_to = move.movement
        return move

    def win(self, w):
        if self.spy_method == "win":
            self.spy_count += 1
        return self.player.win(w)


class TestReferee(unittest.TestCase):
    """Tests for the `Referee` class"""

    def setUp(self):
        self.color1 = (160, 0, 255)
        self.color2 = (0, 255, 255)
        self.player1 = Player("Zoe", EuclidStrategy())
        self.player2 = Player("Xena", RiemannStrategy())
        self.goal_queue = []
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
        self.flat_lines_board = ascii_board(
            # 123456
            "───────",  # 0
            "───────",
            "───────",  # 2
            "───────",
            "───────",  # 4
            "───────",
            "───────",  # 6
        )
        self.ten_by_ten_board = ascii_board(
            "┌────────┐",
            "│┌──────┐│",
            "││┌────┐││",
            "│││┌──┐│││",
            "││││┌┐││││",
            "││││└┘││││",
            "│││└──┘│││",
            "││└────┘││",
            "│└──────┘│",
            "└────────┘",
        )
        self.five_by_five_board = ascii_board(
            # 1234
            "┌┬┬┬┐",  # 0
            "├┼┼┼┤",
            "├┼┼┼┤",  # 2
            "├┼┼┼┤",
            "└┴┴┴┘",  # 4
        )
        self.six_by_five_board = ascii_board(
            # 12345
            "┌┬┬┬┐│",  # 0
            "├┼┼┼┤│",
            "├┼┼┼┤│",  # 2
            "├┼┼┼┤│",
            "└┴┴┴┘│",  # 4
        )

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
        self.player_secrets = {
            color_to_json(self.color1): PlayerSecret(Coord(1, 5), False),
            color_to_json(self.color2): PlayerSecret(Coord(5, 5), False),
        }
        self.spare_tile = Tile(TileShape.LINE, 0, default_gems)
        self.referee = Referee(self.concentric_board, self.spare_tile)
        self.referee_state = RefereeGameState(
            self.player_states,
            self.player_secrets,
            self.spare_tile,
            self.concentric_board,
        )

    def test_create_initial_game_state(self):
        players = [self.player1, self.player2]
        state = self.referee.create_initial_game_state(players)
        possible_homes = state.board.get_all_fixed_tiles()
        self.assertEqual(state.board, self.concentric_board)
        self.assertEqual(state.spare_tile, self.spare_tile)
        self.assertEqual(len(state.player_colors), 2)
        self.color1, self.color2 = state.player_colors
        self.assertEqual(
            state.player_states[self.color1].home_location,
            state.player_states[self.color1].location,
        )
        self.assertTrue(state.player_states[self.color1].home_location in possible_homes)
        self.assertTrue(0 <= state.player_states[self.color1].color[0] <= 255)
        self.assertTrue(0 <= state.player_states[self.color1].color[1] <= 255)
        self.assertTrue(0 <= state.player_states[self.color1].color[2] <= 255)
        self.assertEqual(
            state.player_states[self.color2].home_location,
            state.player_states[self.color2].location,
        )
        self.assertTrue(state.player_states[self.color2].home_location in possible_homes)
        self.assertTrue(0 <= state.player_states[self.color2].color[0] <= 255)
        self.assertTrue(0 <= state.player_states[self.color2].color[1] <= 255)
        self.assertTrue(0 <= state.player_states[self.color2].color[2] <= 255)
        self.assertNotEqual(
            state.player_states[self.color1].home_location,
            state.player_states[self.color2].home_location,
        )
        self.assertNotEqual(
            state.player_states[self.color1].color,
            state.player_states[self.color2].color,
        )
        self.assertEqual(
            state.player_secrets,
            {
                self.color1: PlayerSecret(Coord(1, 1), False),
                self.color2: PlayerSecret(Coord(3, 1), False),
            },
        )

    def test_create_initial_game_state_too_many_players(self):
        player3 = Player("Yana", EuclidStrategy())
        player4 = Player("Alice", RiemannStrategy())
        player5 = Player("Bob", RiemannStrategy())
        players = [self.player1, self.player2, player3, player4, player5]
        referee = Referee(self.five_by_five_board, self.spare_tile)
        self.assertRaises(ValueError, lambda: referee.create_initial_game_state(players))

    def test_players_missing_from_state(self):
        players = [self.player1, self.player2]
        missing_player1_state = self.referee_state.eject_current_player()
        self.assertRaises(
            ValueError,
            lambda: self.referee.start_game_from_state(missing_player1_state, players, goal_queue=self.goal_queue),
        )

    def test_players_in_state_have_shared_home_disabled(self):
        player_states = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(5, 1), Coord(1, 1), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(5, 1), Coord(5, 1), self.color2, "Xena"),
                ),
            ]
        )
        shared_homes_referee_state = RefereeGameState(
            player_states,
            self.player_secrets,
            self.spare_tile,
            self.concentric_board,
        )
        players = [self.player1, self.player2]
        self.assertRaises(
            ValueError,
            lambda: self.referee.start_game_from_state(shared_homes_referee_state, players, goal_queue=self.goal_queue),
        )

    def test_players_in_state_have_shared_home_enabled(self):
        player_states = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(5, 1), Coord(1, 1), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(5, 1), Coord(5, 1), self.color2, "Xena"),
                ),
            ]
        )
        shared_homes_referee_state = RefereeGameState(
            player_states,
            self.player_secrets,
            self.spare_tile,
            self.concentric_board,
        )
        players = [self.player1, self.player2]
        try:
            self.referee.start_game_from_state(
                shared_homes_referee_state,
                players,
                enforce_distinct_homes=False,
                goal_queue=self.goal_queue,
            )
        except Exception:
            self.fail("Players should be allowed to share a home when enforce_distinct_homes is false")

    def test_game_ends_when_all_pass(self):
        # Mock strategies that always pass
        strategy1 = MockStrategy(MagicMock(return_value=TurnPass()))
        strategy2 = MockStrategy(MagicMock(return_value=TurnPass()))
        player1 = Player("Zoe", strategy1)
        player2 = Player("Xena", strategy2)
        # Players are equidistant from their goal, so they tie
        outcome = self.referee.start_game_from_state(self.referee_state, [player1, player2], goal_queue=self.goal_queue)
        self.assertEqual(outcome, GameOutcome([player1, player2], []))
        # Each player was asked to take one turn
        strategy1.mock.assert_called_once()
        strategy2.mock.assert_called_once()

    def test_game_ends_when_all_pass_or_get_ejected(self):
        # Mock strategy that always passes
        strategy1 = MockStrategy(MagicMock(return_value=TurnPass()))
        bad_move = TurnWithMove(45, ShiftOp(Coord(-1, -1), Direction.LEFT), Coord(7, 7))
        # Mock strategy that always makes an invalid move
        strategy2 = MockStrategy(MagicMock(return_value=bad_move))
        player1 = Player("Zoe", strategy1)
        player2 = Player("Xena", strategy2)
        # Xena is kicked out, Zoe wins by default
        outcome = self.referee.start_game_from_state(self.referee_state, [player1, player2], goal_queue=self.goal_queue)
        self.assertEqual(outcome, GameOutcome([player1], [player2]))
        # Each player was asked to take one turn
        strategy1.mock.assert_called_once()
        strategy2.mock.assert_called_once()

    def test_game_ends_after_1000_rounds(self):
        spare_tile = Tile(TileShape.LINE, 1, default_gems)
        player_states = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 1), Coord(0, 0), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(5, 1), Coord(0, 0), self.color2, "Xena"),
                ),
            ]
        )
        # Mock strategies that always make the same move
        the_move = TurnWithMove(0, ShiftOp(Coord(0, 0), Direction.RIGHT), Coord(0, 0))
        strategy1 = MockStrategy(MagicMock(return_value=the_move))
        strategy2 = MockStrategy(MagicMock(return_value=the_move))
        player1 = Player("Zoe", strategy1)
        player2 = Player("Xena", strategy2)
        referee_state = (
            self.referee_state._copy_builder.set_board(self.flat_lines_board)
            .set_spare_tile(spare_tile)
            .set_player_states(player_states)
            .build()
        )
        # First player is on (1, 0), so they are closer to the goal and win
        outcome = self.referee.start_game_from_state(referee_state, [player1, player2], goal_queue=self.goal_queue)
        self.assertEqual(outcome, GameOutcome([player1], []))
        # Each player was asked to take 1000 turns
        self.assertEqual(strategy1.mock.call_count, 1000)
        self.assertEqual(strategy2.mock.call_count, 1000)

    def test_game_ends_when_player_wins(self):
        def winning_strategy_for_zoe(state: GameState):
            col, row = (
                state.current_player_state.location.col,
                state.current_player_state.location.row,
            )
            # always swap between (home_column, 1) and (home_column, 5)
            destination = Coord(col, 5 if (row == 1) else 1)
            return TurnWithMove(0, ShiftOp(Coord(0, 0), Direction.RIGHT), destination)

        strategy1 = MockStrategy(MagicMock(wraps=winning_strategy_for_zoe))
        strategy2 = MockStrategy(MagicMock(wraps=winning_strategy_for_zoe))
        player1 = Player("Zoe", strategy1)
        player2 = Player("Xena", strategy2)
        # First player returned home and won
        outcome = self.referee.start_game_from_state(self.referee_state, [player1, player2], goal_queue=self.goal_queue)
        self.assertEqual(outcome, GameOutcome([player1], []))
        # First player won on their second turn
        self.assertEqual(strategy1.mock.call_count, 2)
        self.assertEqual(strategy2.mock.call_count, 1)

    def test_game_ends_when_all_players_ejected_for_bad_move(self):
        # Mock strategies that always make the same illegal move
        bad_strategies = {
            "offroading": lambda _: (TurnWithMove(0, ShiftOp(Coord(0, 0), Direction.RIGHT), Coord(3, 3))),
            "movement_index_error": lambda _: (TurnWithMove(0, ShiftOp(Coord(0, 0), Direction.RIGHT), Coord(-1, -1))),
            "shift_index_error": lambda _: (TurnWithMove(0, ShiftOp(Coord(0, 8), Direction.RIGHT), Coord(2, 1))),
            "shift_fixed_error": lambda _: (TurnWithMove(0, ShiftOp(Coord(0, 1), Direction.RIGHT), Coord(2, 1))),
            "shift_edge_error": lambda _: (TurnWithMove(0, ShiftOp(Coord(0, 1), Direction.UP), Coord(2, 1))),
            "invalid_rotation": lambda _: (TurnWithMove(45, ShiftOp(Coord(0, 0), Direction.RIGHT), Coord(2, 1))),
            "unsafe": lambda _: (None).get_action(),
        }
        for kind, strat in bad_strategies.items():
            with self.subTest(msg=kind):
                strategy1 = MockStrategy(MagicMock(wraps=strat))
                strategy2 = MockStrategy(MagicMock(wraps=strat))
                player1 = Player("Zoe", strategy1)
                player2 = Player("Xena", strategy2)
                outcome = self.referee.start_game_from_state(
                    self.referee_state, [player1, player2], goal_queue=self.goal_queue
                )
                # Both players were ejected, so no one won
                # self.assertEqual(outcome, GameOutcome([], [player1, player2]))
                self.assertTrue(all([player1 in outcome.ejected, player2 in outcome.ejected]))
                # Each player was asked to take 1 turn before being ejected
                self.assertEqual(strategy1.mock.call_count, 1)
                self.assertEqual(strategy2.mock.call_count, 1)

    def test_game_continues_when_one_player_ejected(self):
        def winning_strategy_for_xena(state: GameState):
            col, row = (
                state.current_player_state.location.col,
                state.current_player_state.location.row,
            )
            # always swap between (home_column, 1) and (home_column, 5)
            destination = Coord(col, 5 if (row == 1) else 1)
            return TurnWithMove(0, ShiftOp(Coord(0, 0), Direction.RIGHT), destination)

        # Mock strategy that always makes the same illegal move
        the_move = TurnWithMove(0, ShiftOp(Coord(0, 0), Direction.RIGHT), Coord(3, 3))
        strategy1 = MockStrategy(MagicMock(return_value=the_move))
        strategy2 = MockStrategy(MagicMock(wraps=winning_strategy_for_xena))
        player1 = Player("Zoe", strategy1)
        player2 = Player("Xena", strategy2)
        outcome = self.referee.start_game_from_state(self.referee_state, [player1, player2], goal_queue=self.goal_queue)
        # Zoe was ejected and Xena won
        self.assertEqual(outcome, GameOutcome([player2], [player1]))
        # Zoe was asked to take 1 turn before being ejected
        self.assertEqual(strategy1.mock.call_count, 1)
        # Xena took 2 turns before winning
        self.assertEqual(strategy2.mock.call_count, 2)

    def test_player_on_the_way_home_wins(self):
        def procrastination_strategy_for_zoe(state: GameState):
            col, row = (
                state.current_player_state.location.col,
                state.current_player_state.location.row,
            )
            # first go to (home_column, 4), then swap between there and (home_column, 5)
            destination = Coord(col, 4 if (row == 5) else 5)
            return TurnWithMove(0, ShiftOp(Coord(0, 0), Direction.RIGHT), destination)

        strategy1 = MockStrategy(MagicMock(wraps=procrastination_strategy_for_zoe))
        # Mock strategy that always passes
        strategy2 = MockStrategy(MagicMock(return_value=TurnPass()))
        player1 = Player("Zoe", strategy1)
        player2 = Player("Xena", strategy2)
        outcome = self.referee.start_game_from_state(self.referee_state, [player1, player2], goal_queue=self.goal_queue)
        # Zoe is on the way home, so they are closer to the goal and win
        self.assertEqual(outcome, GameOutcome([player1], []))
        # Zoe was asked to take 1000 turns before winning
        self.assertEqual(strategy1.mock.call_count, 1000)
        # Xena passed 1000 turns before losing
        self.assertEqual(strategy2.mock.call_count, 1000)

    def test_game_ends_when_all_players_ejected_for_timeout(self):
        # Mock players that always time out on the given method
        timeout_methods = {
            "name": lambda _: (time.sleep(4)),
            "setup": lambda _: (time.sleep(4)),
            "take_turn": lambda _: (time.sleep(5)),
            "win": lambda _: (time.sleep(4)),
        }
        for name, timeout_method in timeout_methods.items():
            with self.subTest(msg=name):
                player1 = MockPlayer(
                    MagicMock(wraps=timeout_method),
                    name,
                    Player("Zoe", RiemannStrategy()),
                )
                player2 = MockPlayer(
                    MagicMock(wraps=timeout_method),
                    name,
                    Player("Xena", RiemannStrategy()),
                )
                outcome = self.referee.start_game_from_state(
                    self.referee_state, [player1, player2], goal_queue=self.goal_queue
                )
                # Both players were ejected, so no one won
                # self.assertEqual(outcome, GameOutcome([], [player1, player2]))
                self.assertTrue(all([player1 in outcome.ejected, player2 in outcome.ejected]))

    def test_game_ends_when_all_players_ejected_for_exception(self):
        # Mock players that always throw an exception on the given method
        error_methods = {
            "name": lambda _: (1 / 0),
            "setup": lambda _: (1 / 0),
            "take_turn": lambda _: (1 / 0),
            "win": lambda _: (1 / 0),
        }
        for name, error_method in error_methods.items():
            with self.subTest(msg=name):
                player1 = MockPlayer(
                    MagicMock(wraps=error_method),
                    name,
                    Player("Zoe", RiemannStrategy()),
                )
                player2 = MockPlayer(
                    MagicMock(wraps=error_method),
                    name,
                    Player("Xena", RiemannStrategy()),
                )
                outcome = self.referee.start_game_from_state(
                    self.referee_state, [player1, player2], goal_queue=self.goal_queue
                )
                # Both players were ejected, so no one won
                # self.assertEqual(outcome, GameOutcome([], [player1, player2]))
                self.assertTrue(all([player1 in outcome.ejected, player2 in outcome.ejected]))

    def test_game_ends_when_all_players_ejected_for_missing_return(self):
        # Mock players that always return nothing on the given method
        no_return_methods = {
            "name": lambda _: (),
            "setup": lambda _: (),
            "take_turn": lambda _: (),
            "win": lambda _: (),
        }
        for name, no_return_method in no_return_methods.items():
            with self.subTest(msg=name):
                player1 = MockPlayer(
                    MagicMock(wraps=no_return_method),
                    name,
                    Player("Zoe", RiemannStrategy()),
                )
                player2 = MockPlayer(
                    MagicMock(wraps=no_return_method),
                    name,
                    Player("Xena", RiemannStrategy()),
                )
                outcome = self.referee.start_game_from_state(
                    self.referee_state, [player1, player2], goal_queue=self.goal_queue
                )
                # Both players were ejected, so no one won
                # self.assertEqual(outcome, GameOutcome([], [player1, player2]))
                self.assertTrue(all([player1 in outcome.ejected, player2 in outcome.ejected]))

    def test_game_runs_on_larger_board(self):
        player_states = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 1), Coord(1, 1), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(9, 1), Coord(9, 1), self.color2, "Xena"),
                ),
            ]
        )
        player_secrets = {
            color_to_json(self.color1): PlayerSecret(Coord(1, 5), False),
            color_to_json(self.color2): PlayerSecret(Coord(7, 7), False),
        }
        large_board_referee_state = RefereeGameState(
            player_states,
            player_secrets,
            self.spare_tile,
            self.ten_by_ten_board,
        )
        player1 = Player("Zoe", EuclidStrategy())
        player2 = Player("Xena", RiemannStrategy())
        # First player returned home and won
        outcome = self.referee.start_game_from_state(
            large_board_referee_state, [player1, player2], goal_queue=self.goal_queue
        )
        self.assertEqual(outcome, GameOutcome([player1], []))

    def test_game_runs_on_smaller_board(self):
        player_states = OrderedDict(
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
        player_secrets = {
            color_to_json(self.color1): PlayerSecret(Coord(1, 3), False),
            color_to_json(self.color2): PlayerSecret(Coord(3, 3), False),
        }
        small_board_referee_state = RefereeGameState(
            player_states,
            player_secrets,
            self.spare_tile,
            self.five_by_five_board,
        )
        player1 = Player("Zoe", EuclidStrategy())
        player2 = Player("Xena", RiemannStrategy())
        # First player returned home and won
        outcome = self.referee.start_game_from_state(
            small_board_referee_state, [player1, player2], goal_queue=self.goal_queue
        )
        self.assertEqual(outcome, GameOutcome([player1], []))

    def test_game_runs_on_uneven_board(self):
        player_states = OrderedDict(
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
        player_secrets = {
            color_to_json(self.color1): PlayerSecret(Coord(1, 3), False),
            color_to_json(self.color2): PlayerSecret(Coord(3, 3), False),
        }
        uneven_board_referee_state = RefereeGameState(
            player_states,
            player_secrets,
            self.spare_tile,
            self.six_by_five_board,
        )
        player1 = Player("Zoe", EuclidStrategy())
        player2 = Player("Xena", RiemannStrategy())
        # First player returned home and won
        outcome = self.referee.start_game_from_state(
            uneven_board_referee_state, [player1, player2], goal_queue=self.goal_queue
        )
        self.assertEqual(outcome, GameOutcome([player1], []))

    def test_start_game_fails_with_too_many_players(self):
        player3 = Player("Yana", EuclidStrategy())
        player4 = Player("Alice", RiemannStrategy())
        player5 = Player("Bob", RiemannStrategy())
        players = [self.player1, self.player2, player3, player4, player5]
        referee = Referee(self.five_by_five_board, self.spare_tile)
        self.assertRaises(ValueError, lambda: referee.start_game(players))

    def test_start_game_from_state_fails_with_too_many_players(self):
        player3 = Player("Yana", EuclidStrategy())
        player4 = Player("Alice", RiemannStrategy())
        player5 = Player("Bob", RiemannStrategy())
        players = [self.player1, self.player2, player3, player4, player5]
        referee = Referee(self.five_by_five_board, self.spare_tile)
        player_states = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 1), Coord(1, 1), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(1, 3), Coord(1, 3), self.color2, "Xena"),
                ),
                (
                    color_to_json((0, 0, 0)),
                    PlayerState(Coord(3, 1), Coord(3, 1), (0, 0, 0), "Yana"),
                ),
                (
                    color_to_json((255, 255, 255)),
                    PlayerState(Coord(3, 3), Coord(3, 3), (255, 255, 255), "Alice"),
                ),
                (
                    color_to_json((40, 40, 40)),
                    PlayerState(Coord(1, 1), Coord(1, 1), (40, 40, 40), "Bob"),
                ),
            ]
        )
        player_secrets = {
            color_to_json(self.color1): PlayerSecret(Coord(1, 3), False),
            color_to_json(self.color2): PlayerSecret(Coord(3, 3), False),
            color_to_json((0, 0, 0)): PlayerSecret(Coord(1, 3), False),
            color_to_json((255, 255, 255)): PlayerSecret(Coord(3, 3), False),
            color_to_json((40, 40, 40)): PlayerSecret(Coord(1, 3), False),
        }
        referee_state = RefereeGameState(
            player_states,
            player_secrets,
            self.spare_tile,
            self.five_by_five_board,
        )
        self.assertRaises(
            ValueError,
            lambda: referee.start_game_from_state(referee_state, players, goal_queue=self.goal_queue),
        )

    def test_player_gets_next_goal_in_queue(self):
        player_states = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 1), Coord(1, 5), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(5, 1), Coord(5, 5), self.color2, "Xena"),
                ),
            ]
        )

        referee_state = RefereeGameState(
            player_states,
            self.player_secrets,
            self.spare_tile,
            self.concentric_board,
        )

        player1 = SpyMockPlayer("setup", Player("Zoe", EuclidStrategy()))
        player2 = SpyMockPlayer("setup", Player("Xena", EuclidStrategy()))

        self.goal_queue = [Coord(3, 3)]

        outcome = self.referee.start_game_from_state(referee_state, [player1, player2], goal_queue=self.goal_queue)
        self.assertEqual(self.goal_queue, [])
        self.assertEqual(player1.spy_count, 3)
        self.assertEqual(player1.goals, [Coord(1, 5), Coord(3, 3), Coord(1, 1)])
        self.assertEqual(player2.goals, [Coord(5, 5), Coord(5, 1)])
        self.assertEqual(player2.previous_move_to, Coord(5, 1))  # Here Xena moves home but does not win
        self.assertEqual(player2.spy_count, 2)
        self.assertEqual(outcome, GameOutcome([player1], []))

    def test_accurate_scoring(self):
        """Test that the referee correctly scores the game"""
        player_states = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 3), Coord(1, 5), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(5, 1), Coord(4, 5), self.color2, "Xena"),
                ),
            ]
        )

        referee_state = RefereeGameState(
            player_states,
            self.player_secrets,
            self.spare_tile,
            self.concentric_board,
        )

        player1 = SpyMockPlayer("setup", Player("Zoe", EuclidStrategy()))
        player2 = SpyMockPlayer("setup", Player("Xena", EuclidStrategy()))

        self.goal_queue = [Coord(3, 3), Coord(3, 5)]

        outcome = self.referee.start_game_from_state(referee_state, [player1, player2], goal_queue=self.goal_queue)
        self.assertEqual(outcome, GameOutcome([player2], []))
        self.assertEqual(player1.spy_count, 3)
        self.assertEqual(player2.spy_count, 3)
        self.assertEqual(player1.goals, [Coord(1, 5), Coord(3, 5), Coord(1, 3)])
        self.assertEqual(player2.previous_move_to, Coord(5, 1))  # Xena makes it home to end the game and win
        self.assertEqual(player2.goals, [Coord(5, 5), Coord(3, 3), Coord(5, 1)])
