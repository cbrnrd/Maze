"""A game state representation for the referee of a Labyrinth game."""

from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Generic, List, Optional, Set, Type, TypeVar, Union

from typing_extensions import Literal

from Maze.Common.board import Board, BoardEdit
from Maze.Common.tile import Direction, Tile
from Maze.Common.utils import Color, Coord


class NoMorePlayersError(Exception):
    """Ejecting the last player is prohibited, as the GameState would be unusable.

    The referee should handle this error, and most likely end the game.
    """


class UndoNotAllowedError(Exception):
    """Shifting this row or column would undo the previous move, which is not allowed."""


class OffroadingError(Exception):
    """The player attempted to travel to a tile they couldn't reach via roads."""


class ZeroMovementError(Exception):
    """The player gave its current location as an avatar move destination."""


class TurnContractViolation(Exception):
    """If a player opts not to pass, they must shift tiles and then move their avatar.

    It is illegal to move any avatar twice without shifting tiles, or to shift tiles
    twice without moving an avatar.

    It is also illegal to rotate the spare tile between shifting tiles and moving.
    """


class SecretAccessError(Exception):
    """The player cannot access the secrets of other players."""


class PlayerListModificationError(Exception):
    """The player cannot modify the list of other players in the game."""


@dataclass(init=False)
class ShiftOp:
    """A record of a tile insertion and the accompanying row or column shift."""

    insert_location: Coord
    direction: Direction

    def __init__(self, insert_location: Coord, direction: Direction):
        """Create a record of a shift operation.

        Args:
            insert_location (Coord): The insert position for the spare tile
            direction (Direction): The direction tiles are shifted during the operation
        """
        self.insert_location = insert_location
        self.direction = direction

    def reverse(self, board: Board) -> "ShiftOp":
        """Returns a shift operation that would undo the tile movements of this one on `board`."""
        if self.direction.is_vertical:
            # Undo a column shift
            col = self.insert_location.col
            row = board.height - 1 if (self.insert_location.row == 0) else 0
        else:
            # Undo a row shift
            col = board.width - 1 if (self.insert_location.col == 0) else 0
            row = self.insert_location.row
        return ShiftOp(Coord(col, row), self.direction.flip())

    def __hash__(self) -> int:
        """Computes a hash of this ShiftOp so it can be used as a dict key or set element."""
        return hash((self.insert_location, self.direction))


class PrevActionKind(Enum):
    """Represents the kinds of `PrevAction`."""

    EMPTY = 0
    PARTIAL_TURN = 1
    COMPLETE_TURN = 2


@dataclass(init=False)
class EmptyPrevAction:
    """States with no previous action allow any shift, but avatars can't be moved."""

    kind: Literal[PrevActionKind.EMPTY]

    def __init__(self):
        self.kind = PrevActionKind.EMPTY


@dataclass(init=False)
class PartialTurnPrevAction:
    """States with a partial turn (shift) previous action only allow avatars to be moved."""

    kind: Literal[PrevActionKind.PARTIAL_TURN]
    shift: ShiftOp

    def __init__(self, shift: ShiftOp):
        self.kind = PrevActionKind.PARTIAL_TURN
        self.shift = shift

    def complete(self) -> "PrevAction":
        """Returns a CompleteTurnPrevAction with the same shift as this PrevAction."""
        return CompleteTurnPrevAction(self.shift)


@dataclass(init=False)
class CompleteTurnPrevAction:
    """States with a complete previous action allow any shift, but avatars can't be moved."""

    kind: Literal[PrevActionKind.COMPLETE_TURN]
    shift: ShiftOp

    def __init__(self, shift: ShiftOp):
        self.kind = PrevActionKind.COMPLETE_TURN
        self.shift = shift


PrevAction = Union[EmptyPrevAction, PartialTurnPrevAction, CompleteTurnPrevAction]


@dataclass
class PlayerSecret:
    """Private player-specific information within the game."""

    treasure_location: Coord
    is_going_home: bool
    treasure_count: int = 0

    def set_is_going_home(self) -> "PlayerSecret":
        """Copies the current state and marks that the player has found its treasure(s) and is going home."""
        return PlayerSecret(self.treasure_location, True, self.treasure_count + 1)

    def set_new_goal(self, new_goal):
        return PlayerSecret(new_goal, False, self.treasure_count + 1)


@dataclass(init=False)
class PlayerState:
    """Public player-specific information within the game."""

    home_location: Coord
    location: Coord
    color: Color
    name: str

    def __init__(
        self,
        home_location: Coord,
        location: Coord,
        color: Color,
        name: str,
    ):
        """Combines public information about a player's state"""
        self.home_location = home_location
        self.location = location
        self.color = color
        self.name = name

    def with_location(self, new_location: Coord) -> "PlayerState":
        """Copies the current state with a new location for the player."""
        return PlayerState(self.home_location, new_location, self.color, self.name)

    def move_with_board(self, edit: BoardEdit, position_if_deleted: Coord) -> "PlayerState":
        """Copies the current state, with an updated location if this player's tile moved.

        Args:
            edit (BoardEdit): The coordinate updates from the board
            position_if_deleted (Coord): The end of the portal that players enter when they fall
                off the board
        """
        if self.location in edit.deletions:
            return self.with_location(position_if_deleted)
        elif self.location in edit.replacements:
            return self.with_location(edit.replacements[self.location])
        return self


TGameState = TypeVar("TGameState", bound="GameState")


class GameStateBuilder(Generic[TGameState]):
    """Represents a builder for a game state.

    This is a convenience class to make copying a state with only a few changes more readable.
    """

    player_states: "OrderedDict[str, PlayerState]"
    player_secrets: Dict[str, PlayerSecret]
    spare_tile: Tile
    board: Board
    prev_action: PrevAction
    starting_player_index: int
    subclass: Type[TGameState]

    def __init__(self, state: "GameState", subclass: Type[TGameState]):
        """Creates a game state builder, initally set to build a copy of the given class.

        Args:
            state (GameState): The state to copy
            subclass (Type[TGameState]): The type of `GameState` to build. Its constructor
                must be compatible with the `build` method
        """
        self.player_states = state.player_states
        self.player_secrets = state.player_secrets
        self.spare_tile = state.spare_tile
        self.board = state.board
        self.prev_action = state.prev_action
        self.starting_player_index = state.current_player_index
        self.subclass = subclass

    def set_player_states(self, player_states: "OrderedDict[str, PlayerState]") -> "GameStateBuilder":
        """Sets the `player_states` of the class to be built."""
        self.player_states = player_states
        return self

    def set_player_secrets(self, player_secrets: Dict[str, PlayerSecret]) -> "GameStateBuilder":
        """Sets the `player_secrets` of the class to be built."""
        self.player_secrets = player_secrets
        return self

    def set_spare_tile(self, spare_tile: Tile) -> "GameStateBuilder":
        """Sets the `spare_tile` of the class to be built."""
        self.spare_tile = spare_tile
        return self

    def set_board(self, board: Board) -> "GameStateBuilder":
        """Sets the `board` of the class to be built."""
        self.board = board
        return self

    def set_prev_action(self, prev_action: PrevAction) -> "GameStateBuilder":
        """Sets the `prev_action` of the class to be built."""
        self.prev_action = prev_action
        return self

    def set_starting_player_index(self, starting_player_index: int) -> "GameStateBuilder":
        """Sets the `starting_player_index` of the class to be built."""
        self.starting_player_index = starting_player_index
        return self

    def build(self) -> "GameState":
        """Builds a GameState."""
        return self.subclass(
            self.player_states,
            self.player_secrets,
            self.spare_tile,
            self.board,
            self.prev_action,
            self.starting_player_index,
        )


class GameState:
    """Abstract class for the game state used by players and referee of Labyrinth.

    This is immutable because we foresee 3 possible state transitions that make up a move:
    1. `next <- state` if the player passes
    2. `next <- state.[rotate_spare_tile(...)].shift_tiles(...).move_player(...)`
    3. `next <- state.eject_current_player()`

    If the game must be presentable to a player in the intermediate state (e.g. after
    the `shift_tiles` call, to find out where it can move), then we need to be able to
    change course at any time from option 2 to option 3. This is easy if we have the
    original `state` and can guarantee that it hasn't been mutated.
    """

    num_players: int
    current_player_index: int
    # Sorted by turn order

    player_colors: List[str]
    player_states: "OrderedDict[str, PlayerState]"
    player_secrets: Dict[str, PlayerSecret]
    # Only contains players that the owner of this GameState should know the secrets of

    spare_tile: Tile
    board: Board

    # Holds [most recent action, 2nd most recent action]
    # Invariant: len(actions) <= 2
    # Invariant: if len(actions) == 2, it must be a [ShiftOp, Coord] or a [Coord, ShiftOp]
    prev_action: PrevAction

    def __init__(
        self,
        player_states: "OrderedDict[str, PlayerState]",
        player_secrets: Dict[str, PlayerSecret],
        spare_tile: Tile,
        board: Board,
        prev_action: PrevAction = EmptyPrevAction(),
        starting_player_index: int = 0,
    ):
        """Create a game state for an unfinished game.

        Args:
            player_states (OrderedDict[str, PlayerState]): A dictionary from players to a tuple
                containing their home location, current location, and color
            player_secrets (Dict[str, PlayerSecret]): A dictionary from players to a tuple
                containing their treasure to find and whether or not they've found it yet
            spare_tile (Tile): The spare tile for the next turn of the game
            board (Board): The board for the next turn of the game
            prev_action (PrevAction, optional): The previous actions
            starting_player_index (int, optional): The index of the player whose turn it is
                next, in `player_states`. Defaults to 0

        Raises:
            ValueError: If `spare_tile` has the same (unordered) gem pair as any tile on `board`
            ValueError: If there is less than 1 player
            IndexError: If any player state has a home location or current location out of bounds
            ValueError: If any player has a home location on a movable tile
            IndexError: If any player secret has a treasure not found on the board
            IndexError: If the `starting_player_index` is out of bounds
        """
        GameState.validate_spare_tile_gems(board, spare_tile)
        GameState._validate_player_states(board, player_states)
        # GameState._validate_player_secrets(board, player_secrets)
        if not 0 <= starting_player_index < len(player_states):
            raise IndexError(f"Starting player index out of bounds: {starting_player_index}")

        self.num_players = len(player_states)
        self.player_colors = list(player_states.keys())
        self.player_states = player_states
        self.player_secrets = player_secrets
        self.spare_tile = spare_tile
        self.board = board
        self.prev_action = prev_action
        self.current_player_index = starting_player_index

    @staticmethod
    def validate_spare_tile_gems(board: Board, spare_tile: Tile) -> None:
        """Checks that `spare_tile` has a pair of gems not present on `board`.

        Raises:
            ValueError: If `spare_tile` has the same (unordered) gem pair as any tile on `board`
        """
        all_tiles = list(board.tiles.values()) + [spare_tile]
        Board.validate_tile_gems(all_tiles)

    @staticmethod
    def _validate_player_states(board: Board, player_states: "OrderedDict[str, PlayerState]") -> None:
        """Validates the players' current locations and home locations.

        Raises:
            ValueError: If there is less than 1 player
            IndexError: If any player state has a home location or current location out of bounds
            ValueError: If any player has a home location on a movable tile
        """
        if len(player_states) < 1:
            raise ValueError("Game state expects non-empty player list")
        for player_state in player_states.values():
            board.assert_in_bounds(player_state.location)
            board.assert_in_bounds(player_state.home_location)
            col, row = player_state.home_location.col, player_state.home_location.row
            if board.is_moveable_row_or_column(col) or board.is_moveable_row_or_column(row):
                raise ValueError("Player home must be on a fixed tile")

    @staticmethod
    def _validate_player_secrets(board: Board, player_secrets: Dict[str, PlayerSecret]) -> None:
        """Validates the players' treasure locations.

        Raises:
            IndexError: If any player secret has a treasure location out of bounds
        """
        for player_secret in player_secrets.values():
            board.assert_in_bounds(player_secret.treasure_location)

    @property
    def _copy_builder(self) -> GameStateBuilder["GameState"]:
        """Returns a builder which would initially build a copy of this state."""
        raise NotImplementedError()

    def rotate_spare_tile(self, degrees: int) -> "GameState":
        """Rotates the spare tile by a given number of degrees, relative to its current rotation.

        Raises:
            ValueError: If `degrees` is not evenly divisible by 90
            TurnContractViolation: If there has not been an avatar move since the last tile shift
        """
        if degrees % 90 != 0:
            raise ValueError(f"Expected integer degrees divisible by 90, got {degrees}")
        if self.prev_action.kind is PrevActionKind.PARTIAL_TURN:
            raise TurnContractViolation("Expecting avatar move before spare tile can be rotated")
        # calculate the number of 90-degree rotations to perform
        # the `/` operator is (int, int) -> float. the `//` operator returns an
        # int by truncating the quotient
        relative_rotation = degrees // 90
        new_rotation = (relative_rotation + self.spare_tile.rotation) % 4
        new_spare = self.spare_tile.rotate(new_rotation)
        return self._copy_builder.set_spare_tile(new_spare).build()

    def shift_tiles(self, operation: ShiftOp) -> "GameState":
        """Shift a row or column by inserting the spare tile as described by `operation`.

        Note: if any player is on the tile which will be shifted off of the board,
            it moves to the just inserted one.

        Raises:
            IndexError: If the given position is out of bounds
            ValueError: If the given position is not on the edge of the board
            ShiftNotAllowedError: If the given position is on a fixed row or column
            UndoNotAllowedError: If this shift undoes the previous one
            TurnContractViolation: If no player has been moved since the last shift operation

        Returns:
            GameState: The state with a new spare tile and board, players in new positions
                if their tiles moved, and the shift operation logged as the last action
        """
        if self.prev_action.kind is PrevActionKind.PARTIAL_TURN:
            raise TurnContractViolation("Can't shift tiles twice in a row")
        if (
            self.prev_action.kind is not PrevActionKind.EMPTY
            and operation.reverse(self.board) == self.prev_action.shift
        ):
            raise UndoNotAllowedError()

        new_board, new_spare, edit = self.board.slide_and_insert_tile(
            operation.insert_location, operation.direction, self.spare_tile
        )
        new_players = OrderedDict(
            [
                (color, state.move_with_board(edit, operation.insert_location))
                for color, state in self.player_states.items()
            ]
        )
        return (
            self._copy_builder.set_player_states(new_players)
            .set_spare_tile(new_spare)
            .set_board(new_board)
            .set_prev_action(PartialTurnPrevAction(operation))
            .build()
        )

    def move_current_player(self, dest_coord: Coord) -> "GameState":
        """Move the current player to the given location.

        Note:
            If the owner of this state can access the current player's secret
            and this move ends on the current player's treasure location,
            `has_treasure` will be True in the resulting GameState

        Raises:
            IndexError: If the destination is not on the board
            ZeroMovementError: If the player is already at their destination
            OffroadingError: If the destination is not reachable from the current
                player's location
            TurnContractViolation: If the previous action was not a tile shift

        Returns:
            GameState: The state with the player moved and the movement logged
        """
        self.board.assert_in_bounds(dest_coord)
        if self.prev_action.kind is not PrevActionKind.PARTIAL_TURN:
            raise TurnContractViolation("Expecting shift operation before move can be made")
        if dest_coord == self.current_player_state.location:
            raise ZeroMovementError()
        if not self.is_reachable_by_current_player(dest_coord):
            raise OffroadingError()
        player_color = self.current_player_color
        new_players = OrderedDict()
        # preserve order
        for color, state in self.player_states.items():
            if color == player_color:
                new_players[color] = state.with_location(dest_coord)
            else:
                new_players[color] = state
        moved_state = (
            self._copy_builder.set_player_states(new_players).set_prev_action(self.prev_action.complete()).build()
        )
        return moved_state

    def get_legal_shift_ops(self) -> Set[ShiftOp]:
        """Returns the tile shift operations that the current player can legally perform."""
        if self.prev_action.kind is PrevActionKind.PARTIAL_TURN:
            # Just shifted, can't shift again
            return set()
        legal_shift_ops: Set[ShiftOp] = set()
        for direction in Direction:
            for coord in self.board.get_valid_insert_locations(direction):
                legal_shift_ops.add(ShiftOp(coord, direction))
        if self.prev_action.kind is not PrevActionKind.EMPTY:
            # Remove the shift operation which would undo the previous one
            legal_shift_ops.discard(self.prev_action.shift.reverse(self.board))
        return legal_shift_ops

    def get_legal_move_destinations(self) -> Set[Coord]:
        """Returns the set of coordinates that the current player can legally move to."""
        current_player_location = self.current_player_state.location
        if self.prev_action.kind is not PrevActionKind.PARTIAL_TURN:
            # No shift yet, can't move
            return set()
        result = self.board.reachable_destinations(current_player_location)
        result.discard(current_player_location)
        return result

    def get_last_shift_op(self) -> Optional[ShiftOp]:
        """Returns the last shift operation performed, or None if there haven't been any."""
        if self.prev_action.kind is PrevActionKind.EMPTY:
            return None
        return self.prev_action.shift

    @property
    def current_player_name(self) -> str:
        """Returns the name of the current player."""
        return self.current_player_state.name

    @property
    def current_player_color(self) -> str:
        """Returns the color of the current player"""
        return self.player_colors[self.current_player_index]

    @property
    def current_player_state(self) -> PlayerState:
        """Returns the state of the current player."""
        player_color = self.current_player_color
        return self.player_states[player_color]

    def can_get_player_secret(self, color: str) -> bool:
        """Checks whether the secrets of the given player can be accessed."""
        raise NotImplementedError()

    def can_get_current_player_secret(self) -> bool:
        """Checks whether the secrets of the current player can be accessed."""
        return self.can_get_player_secret(self.current_player_color)

    def get_player_secret(self, color: str) -> PlayerSecret:
        """Returns the secrets of the given player, if allowed.

        Raises:
            SecretAccessError: If the player's secrets can't be accessed
            KeyError: If `color` is not one of the players in this state
        """
        raise NotImplementedError()

    def get_current_player_secret(self) -> PlayerSecret:
        """Returns the secrets of the current player, if allowed.

        Raises:
            SecretAccessError: If the active player's secrets can't be accessed
        """
        return self.get_player_secret(self.current_player_color)

    def get_current_player_treasure_location(self) -> Coord:
        """Gets the location of the current player's treasure.

        Raises:
            SecretAccessError: If the active player's secrets can't be accessed
        """
        return self.get_current_player_secret().treasure_location

    def is_reachable_by_current_player(self, which_coord: Coord) -> bool:
        """Determines whether the currently active player can reach a given tile."""
        return which_coord in self.board.reachable_destinations(self.current_player_state.location)

    def is_current_player_at_treasure(self) -> bool:
        """Checks whether the active player's move has placed it on the tile with its treasure.

        Raises:
            SecretAccessError: If the active player's secrets can't be accessed
        """
        player_state = self.current_player_state
        return player_state.location == self.get_current_player_treasure_location()

    def is_current_player_at_home(self) -> bool:
        """Checks whether the active player's move has placed it on its home tile."""
        player_state = self.current_player_state
        return player_state.location == player_state.home_location

    def eject_current_player(self) -> "GameState":
        """Kicks out the currently active player.

        Raises:
            NoMorePlayersError: If the currently active player is the last one
            PlayerListModificationError: If a player attempts to perform this action
        """
        raise NotImplementedError()

    def eject_player(self, color: str) -> "GameState":
        """Kicks out the player with the given `color`, if they're in the game.

        Raises:
            NoMorePlayersError: If the player is present and the last one
            PlayerListModificationError: If a player attempts to perform this action
        """
        raise NotImplementedError()

    def end_current_turn(self) -> "GameState":
        """Ends the current player's turn."""
        new_player_index = self.current_player_index + 1
        if new_player_index >= len(self.player_states):
            new_player_index = 0
        return self._copy_builder.set_starting_player_index(new_player_index).build()

    def set_current_player_new_goal(self, new_goal: Coord):
        player_color = self.current_player_color
        if (not self.can_get_player_secret(player_color)) or (not self.is_current_player_at_treasure()):
            return self
        new_secrets = self.player_secrets
        if new_goal == self.player_states[player_color].home_location:
            new_secrets = {
                **new_secrets,
                player_color: new_secrets[player_color].set_is_going_home(),
            }
        else:
            new_secrets = {
                **new_secrets,
                player_color: new_secrets[player_color].set_new_goal(new_goal),
            }
        return self._copy_builder.set_player_secrets(new_secrets).build()

    def associate_players(self, taken_player_names: List[str]) -> "GameState":
        """Associates the given list of player names with the PlayerStates (in order)."""
        new_states = self.player_states  # color -> PlayerState
        for idx, color in enumerate(self.player_colors):
            new_states[color].name = taken_player_names[idx]
        return self._copy_builder.set_player_states(new_states).build()


class RestrictedGameState(GameState):
    """The game state used by a player of Labyrinth."""

    def __init__(
        self,
        player_states: "OrderedDict[str, PlayerState]",
        player_secrets: Dict[str, PlayerSecret],
        spare_tile: Tile,
        board: Board,
        prev_action: PrevAction = EmptyPrevAction(),
        starting_player_index: int = 0,
    ):
        """Create a restricted game state for an unfinished game.

        Args:
            player_states (OrderedDict[str, PlayerState]): A dictionary from players to a tuple
                containing their home location, current location, and color
            player_secrets (Dict[str, PlayerSecret]): A dictionary from players to a tuple
                containing their treasure to find and whether or not they've found it yet
            spare_tile (Tile): The spare tile for the next turn of the game
            board (Board): The board for the next turn of the game
            prev_action (PrevAction, optional): The previous actions
            starting_player_index (int, optional): The index of the player whose turn it is
                next, in `player_states`. Defaults to 0

        Raises:
            ValueError: If there is less than 1 player
            IndexError: If any player state has a home location or current location out of bounds
            ValueError: If any player has a home location on a movable tile
            IndexError: If any player secret has a treasure not found on the board
            IndexError: If the `starting_player_index` is out of bounds
            ValueError: If `player_secrets` does not have exactly 1 key
            KeyError: If the key in `player_secrets` is not in `player_states`
        """
        super().__init__(
            player_states,
            player_secrets,
            spare_tile,
            board,
            prev_action,
            starting_player_index,
        )
        if len(player_secrets) != 1:
            raise ValueError(f"Expected 1 player with secret, got {len(player_secrets)}")
        self._validate_player_secrets(board, player_secrets)
        player_color = next(iter(player_secrets.keys()))
        if player_color not in player_states:
            raise KeyError(f"The player {player_color!r} does not exist")
        self.player_color = player_color

    @property
    def _copy_builder(self) -> GameStateBuilder["GameState"]:
        """Returns a builder which would initially build a copy of this state."""
        return GameStateBuilder(self, RestrictedGameState)

    def can_get_player_secret(self, color: str) -> bool:
        """Checks whether the secrets of the given player can be accessed."""
        return color == self.player_color

    def get_player_secret(self, color: str) -> PlayerSecret:
        """Returns the secrets of the given player, if allowed.

        Raises:
            SecretAccessError: If the given player's secrets can't be accessed
            KeyError: If `color` is not one of the players in this state
        """
        if not self.can_get_player_secret(color):
            raise SecretAccessError()
        return self.player_secrets[self.player_color]

    def eject_current_player(self) -> "GameState":
        """Kicks out the currently active player.

        Raises:
            PlayerListModificationError
        """
        raise PlayerListModificationError()

    def eject_player(self, color: str) -> "GameState":
        """Kicks out the player with the given `color`, if they're in the game.

        Raises:
            PlayerListModificationError
        """
        raise PlayerListModificationError()


class RefereeGameState(GameState):
    """The game state used by the referee of Labyrinth."""

    player_secrets: Dict[str, PlayerSecret]

    def __init__(
        self,
        player_states: "OrderedDict[str, PlayerState]",
        player_secrets: Dict[str, PlayerSecret],
        spare_tile: Tile,
        board: Board,
        prev_action: PrevAction = EmptyPrevAction(),
        starting_player_index: int = 0,
    ):
        """Create a referee game state for an unfinished game.

        Args:
            player_states (OrderedDict[str, PlayerState]): A dictionary from players to a tuple
                containing their home location, current location, and color
            player_secrets (Dict[str, PlayerSecret]): A dictionary from players to a tuple
                containing their treasure to find and whether or not they've found it yet
            spare_tile (Tile): The spare tile for the next turn of the game
            board (Board): The board for the next turn of the game
            prev_action (PrevAction, optional): The previous actions
            starting_player_index (int, optional): The index of the player whose turn it is
                next, in `player_states`. Defaults to 0

        Raises:
            ValueError: If there is less than 1 player
            IndexError: If any player state has a home location or current location out of bounds
            ValueError: If any player has a home location on a movable tile
            IndexError: If any player secret has a treasure not found on the board
            IndexError: If the `starting_player_index` is out of bounds
            ValueError: If `player_secrets` has extra or missing keys compared to `player_states`
        """
        super().__init__(
            player_states,
            player_secrets,
            spare_tile,
            board,
            prev_action,
            starting_player_index,
        )
        if set(player_secrets.keys()) != set(player_states.keys()):
            raise ValueError("All players must have secrets, and all secrets must have players")
        self._validate_player_secrets(board, player_secrets)
        self.player_secrets = player_secrets

    @property
    def _copy_builder(self) -> GameStateBuilder["GameState"]:
        """Returns a builder which would initially build a copy of this state."""
        return GameStateBuilder(self, RefereeGameState)

    def can_get_player_secret(self, color: str) -> bool:
        """Checks whether the secrets of the given player can be accessed."""
        return color in self.player_secrets

    def get_player_secret(self, color: str) -> PlayerSecret:
        """Returns the secrets of the given player, if allowed.

        Raises:
            KeyError: If `color` is not one of the players in this state
        """
        return self.player_secrets[color]

    def eject_current_player(self) -> "GameState":
        """Kicks out the currently active player.

        Raises:
            NoMorePlayersError: If the currently active player is the last one
        """
        if self.num_players == 1:
            raise NoMorePlayersError()
        current_player_color = self.current_player_color
        new_player_states = self.player_states.copy()
        new_player_states.pop(current_player_color)
        new_player_secrets = self.player_secrets.copy()
        new_player_secrets.pop(current_player_color)
        # `current_player_index` will already point to the next player, unless
        # we kicked out the last player in the order.
        new_player_index = self.current_player_index
        if new_player_index >= len(new_player_states):
            new_player_index = 0
        return (
            self._copy_builder.set_player_states(new_player_states)
            .set_player_secrets(new_player_secrets)
            .set_starting_player_index(new_player_index)
            .build()
        )

    def eject_player(self, color: str) -> "GameState":
        """Kicks out the player with the given `color`, if they're in the game.

        Raises:
            NoMorePlayersError: If the player is present and the last one
            PlayerListModificationError: If a player attempts to perform this action
        """
        if not color in self.player_colors:
            return self
        if self.num_players == 1:
            raise NoMorePlayersError()
        new_player_states = self.player_states.copy()
        new_player_states.pop(color)
        new_player_secrets = self.player_secrets.copy()
        new_player_secrets.pop(color)
        ejected_player_index = self.player_colors.index(color)
        new_player_index = self.current_player_index
        # If the ejected player is before the current player, reduce `current_player_index` by 1
        if ejected_player_index < self.current_player_index:
            new_player_index = self.current_player_index - 1
        # If the ejected player is the current player and also the last player
        # in the turn order, set `current_player_index` back to 0
        elif ejected_player_index == self.current_player_index and new_player_index >= len(new_player_states):
            new_player_index = 0
        return (
            self._copy_builder.set_player_states(new_player_states)
            .set_player_secrets(new_player_secrets)
            .set_starting_player_index(new_player_index)
            .build()
        )
