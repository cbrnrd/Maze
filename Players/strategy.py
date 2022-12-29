"""The strategy interface and sample implementations for Labyrinth on Maze.com"""

import itertools
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Union

from Maze.Common.state import GameState, ShiftOp
from Maze.Common.utils import Coord, squared_euclidean_distance


@dataclass(init=False)
class TurnWithMove:
    """Represents a turn in Labyrinth in which the player moves."""

    degrees: int
    shift: ShiftOp
    movement: Coord

    def __init__(self, degrees: int, shift: ShiftOp, movement: Coord):
        """Creates a record of a complete Labyrinth turn.

        Args:
            degrees (int): The number of degrees to rotate the spare tile, relative
                to its rotation at the end of the previous turn
            shift (ShiftOp): The shift and insert operation to make
            movement (Coord): The location where the player's avatar should go
        """
        self.degrees = degrees
        self.shift = shift
        self.movement = movement


@dataclass(init=False)
class TurnPass:
    """Represents a turn in Labyrinth on which the player passes."""


TurnAction = Union[TurnPass, TurnWithMove]


class Strategy:
    """A class which selects TurnActions for a player to perform in a Labyrinth game."""

    def get_action(self, state: GameState) -> TurnAction:
        """Selects an action for the player's turn, given the game state.

        Args:
            state (GameState): The current game state. The state's `current_player` must
                be the owner of this strategy.

        Returns:
            TurnAction: The spare tile rotation, tile shift, and avatar move to make, if any.
                Otherwise, returns a `TurnPass`
        """
        raise NotImplementedError()


class FirstViableMoveStrategy(Strategy):
    """A strategy which selects the first action in its exploration that it can make.

    Strategies of this type should override the `shift_exploration_order`,
    `rotation_exploration_order` and `movement_exploration_order` methods.

    The resulting exploration order looks like this:
        for each move destination:
            for each shift:
                for each rotation:
                    if move destination is reachable, return this complete move
    """

    def movement_exploration_order(self, state: GameState) -> List[Coord]:
        """Returns the destinations which this strategy should attempt to reach.

        Args:
            state (GameState): The current game state. The state's `current_player` must
                be the owner of this strategy.

        Returns:
            List[Coord]: The destinations in order, by preference
        """
        raise NotImplementedError()

    def shift_exploration_order(self, state: GameState) -> List[ShiftOp]:
        """Returns the shift explorations to perform, ordered from first to last.

        Args:
            state (GameState): The current game state. The state's `current_player` must
                be the owner of this strategy.
        """
        raise NotImplementedError()

    def rotation_exploration_order(self, state: GameState) -> List[int]:
        """Returns the rotation of the spare tile in each `movement_exploration` branch of
        the current `shift_exploration`.
        """
        raise NotImplementedError()

    def get_action(self, state: GameState) -> TurnAction:
        """Selects the first action that this strategy can make based on its exploration order.

        Note:
            See class docstring for exploration order

        Args:
            state (GameState): The current game state. The state's `current_player` must
                be the owner of this strategy.

        Returns:
            TurnAction: The spare tile rotation, tile shift, and avatar move to make, if any.
                Otherwise, returns a `TurnPass`
        """
        cache: Dict[Tuple[ShiftOp, int], Set[Coord]] = {}
        for dest in self.movement_exploration_order(state):
            for shift in self.shift_exploration_order(state):
                for degrees in self.rotation_exploration_order(state):
                    # Each shift and degrees results in the same board + player locations
                    # We use `cache` to remember them and not recalculate for each destination
                    cache_key = (shift, degrees)
                    if cache_key in cache:
                        reachable_destinations = cache[cache_key]
                    else:
                        reachable_destinations = (
                            state.rotate_spare_tile(degrees).shift_tiles(shift).get_legal_move_destinations()
                        )
                        cache[cache_key] = reachable_destinations
                    if dest in reachable_destinations:
                        return TurnWithMove(degrees, shift, dest)
        return TurnPass()


def order_shift_by_row_first(shift: ShiftOp) -> Tuple[int, int, int]:
    """Computes a key to sort the given `shift`.

    Returns:
        Tuple[int, int, int]: A key which, when used in `sorted`, sorts shifts by the
            following criteria:
            - Row shifts before column shifts
            - Indices from top to bottom or left to right
            - Left shifts before Right shifts, and Up shifts before Down shifts
    """
    is_horizontal = shift.direction.is_horizontal
    return (
        0 if is_horizontal else 1,
        shift.insert_location.row if is_horizontal else shift.insert_location.col,
        shift.direction.dy + shift.direction.dx,
    )


def order_coords_by_row_column(coord: Coord) -> Tuple[int, int]:
    """Computes a key to sort the given `coord` in row-column order."""
    column, row = coord.col, coord.row
    return (row, column)


class RiemannStrategy(FirstViableMoveStrategy):
    """A strategy which selects its action using the Riemann algorithm.

    The resulting exploration order looks like this:
        for each move destination in (goal, others in row-col order):
            for each shift (rows 0-n x [LEFT, RIGHT]; cols 0-n x [UP, DOWN]):
                for each rotation (degrees counterclockwise 0, 90, 180, 270):
                    if move destination is reachable, return this complete move

    If no move is found, pass
    """

    def movement_exploration_order(self, state: GameState) -> List[Coord]:
        """Returns the destinations which this strategy should attempt to reach.

        Args:
            state (GameState): The current game state. The state's `current_player` must
                be the owner of this strategy.

        Returns:
            List[Coord]: The destinations in order, by preference
        """
        all_coords: List[Coord] = []
        has_treasure = state.get_current_player_secret().is_going_home
        goal_location = (
            state.current_player_state.home_location if has_treasure else state.get_current_player_treasure_location()
        )
        all_coords.append(goal_location)
        for row, col in itertools.product(range(state.board.height), range(state.board.width)):
            if Coord(col, row) != goal_location:
                all_coords.append(Coord(col, row))
        return all_coords

    def shift_exploration_order(self, state: GameState) -> List[ShiftOp]:
        """Returns the shift explorations to perform, ordered from first to last.

        Note:
            The shift exploration order is rows 0-n x [LEFT, RIGHT], then cols 0-n x [UP, DOWN]

        Args:
            state (GameState): The current game state. The state's `current_player` must
                be the owner of this strategy.
        """
        legal_shifts = state.get_legal_shift_ops()
        return sorted(legal_shifts, key=order_shift_by_row_first)

    def rotation_exploration_order(self, state: GameState) -> List[int]:
        """Returns the rotation of the spare tile in each `movement_exploration` branch of
        the current `shift_exploration`.

        Args:
            state (GameState): The current game state. The state's `current_player` must
                be the owner of this strategy.
        """
        return [0, 270, 180, 90]


class EuclidStrategy(FirstViableMoveStrategy):
    """A strategy which selects its action using the Euclid algorithm.

    The resulting exploration order looks like this:
        for each move destination in (goal, others in closest Euclidean distance order*):
            for each shift (rows 0-n x [LEFT, RIGHT]; cols 0-n x [UP, DOWN]):
                for each rotation (degrees counterclockwise 0, 90, 180, 270):
                    if move destination is reachable, return this complete move

    Ties in the Euclidean distance order are broken using row-colum order
    If no move is found, pass
    """

    def movement_exploration_order(self, state: GameState) -> List[Coord]:
        """Returns the destinations which this strategy should attempt to reach.

        Args:
            state (GameState): The current game state. The state's `current_player` must
                be the owner of this strategy.

        Returns:
            List[Coord]: The destinations in order, by preference
        """
        non_goal_coords: List[Coord] = []
        has_treasure = state.get_current_player_secret().is_going_home
        goal_location = (
            state.current_player_state.home_location if has_treasure else state.get_current_player_treasure_location()
        )
        for row, col in itertools.product(range(state.board.height), range(state.board.width)):
            if Coord(col, row) != goal_location:
                non_goal_coords.append(Coord(col, row))
        # Re-use `order_coords_by_row_column`, but combine it as the second part of the key.
        # Python's tuple lexicographic ordering will only use it to break ties from the first
        # key element.
        non_goal_coords.sort(
            key=lambda coord: (
                squared_euclidean_distance(goal_location, coord),
                *order_coords_by_row_column(coord),
            )
        )
        return [goal_location, *non_goal_coords]

    def shift_exploration_order(self, state: GameState) -> List[ShiftOp]:
        """Returns the shift explorations to perform, ordered from first to last.

        Note:
            The shift exploration order is rows 0-n x [LEFT, RIGHT], then cols 0-n x [UP, DOWN]

        Args:
            state (GameState): The current game state. The state's `current_player` must
                be the owner of this strategy.
        """
        legal_shifts = state.get_legal_shift_ops()
        return sorted(legal_shifts, key=order_shift_by_row_first)

    def rotation_exploration_order(self, state: GameState) -> List[int]:
        """Returns the rotation of the spare tile in each `movement_exploration` branch of
        the current `shift_exploration`.

        Args:
            state (GameState): The current game state. The state's `current_player` must
                be the owner of this strategy.
        """
        return [0, 270, 180, 90]
