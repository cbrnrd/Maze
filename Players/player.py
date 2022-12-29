"""Player implementation for the Maze game's player-referee protocol."""

# pylint: disable=invalid-name
# ^ allows camel case to match spec interface

import os
import random
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Tuple, Union, Any

from typing_extensions import Literal

from Maze.Common.board import Board
from Maze.Common.gem import Gem
from Maze.Common.state import (
    GameState,
    PlayerSecret,
    PlayerState,
    GameStateBuilder,
    RestrictedGameState,
)
from Maze.Common.tile import Tile, TileShape
from Maze.Common.utils import Coord
from Maze.Players.strategy import Strategy, TurnAction


class IncorrectPhaseError(Exception):
    """Referee sent a message for the wrong phase of the game (setup vs. play)."""


class ProtocolPhase(Enum):
    """Represents a stage of the Labyrinth game protocol."""

    SETUP = 0
    GAMEPLAY = 1
    SCORING = 2


class PlayerSetupImpl:
    """Implementation for player operations valid when a Labyrinth game has not yet started."""

    phase: Literal[ProtocolPhase.SETUP] = ProtocolPhase.SETUP
    _name: str
    _random: random.Random

    def __init__(self, name: str):
        """Creates a setup implementation for the given player, using a random board generator."""
        self._name = name
        # By default, seed is 8 OS-provided random bytes
        # Avoiding using time so other players can't exploit knowledge of the seed
        self._random = random.Random(os.urandom(8))

    def propose_board0(self, rows: int, columns: int) -> Board:
        """Proposes an initial board of the given size.

        Raises:
            ValueError: If `rows` or `columns` is less than 1
        """
        if rows < 1 or columns < 1:
            raise ValueError("Expected dimensions for board with at least 1 tile")
        tile_choices: List[Tuple[TileShape, int]] = []
        for shape in TileShape:
            for rotation in shape.unique_rotations():
                tile_choices.append((shape, rotation))
        total_tiles = rows * columns
        tiles = {}
        treasures = self._random.sample(list(Gem.unordered_pairs()), total_tiles)
        for col in range(columns):
            for row in range(rows):
                shape, rotation = self._random.choice(tile_choices)
                tiles[Coord(col, row)] = Tile(shape, rotation, treasures[col * columns + row])
        return Board(tiles, columns, rows)

    def setup(self, state0: GameState, goal: Coord) -> Tuple[PlayerState, PlayerSecret]:
        """Updates this player with an initial state and a goal position.

        Returns:
            Tuple[PlayerState, PlayerSecret]: The player's initial state and secret
        """
        player_state = list(state0.player_states.values())[0]
        return player_state, PlayerSecret(goal, False)


class PlayerGameplayImpl:
    """Implementation for player operations valid when a Labyrinth game is ongoing."""

    phase: Literal[ProtocolPhase.GAMEPLAY] = ProtocolPhase.GAMEPLAY
    _name: str
    _strategy: Strategy
    _player_state: PlayerState
    _player_secret: PlayerSecret

    def __init__(
        self,
        name: str,
        strategy: Strategy,
        player_state: PlayerState,
        player_secret: PlayerSecret,
    ):
        """Creates a gameplay implementation for the given player using `strategy`."""
        self._name = name
        self._strategy = strategy
        self._player_state = player_state
        self._player_secret = player_secret

    def setup(self, new_goal: Coord) -> Coord:
        """Updates this player with their goal position after finding treasure.

        Returns:
            Coord: The player's new goal position
        """
        if new_goal != self._player_state.home_location:
            self._player_secret = self._player_secret.set_new_goal(new_goal)
        else:
            self._player_secret = self._player_secret.set_is_going_home()
        return new_goal

    def take_turn(self, s: GameState) -> TurnAction:
        """Selects an action for this turn using the player's strategy."""
        new_state = (
            GameStateBuilder(s, RestrictedGameState)
            .set_player_secrets({s.current_player_color: self._player_secret})
            .build()
        )
        return self._strategy.get_action(new_state)


class PlayerScoringImpl:
    """Implementation for player operations valid when a Labyrinth game has ended."""

    phase: Literal[ProtocolPhase.SCORING] = ProtocolPhase.SCORING
    _name: str
    _won: bool

    def __init__(self, name: str, won: bool):
        """Creates an implementation for the post-game phase of Labyrinth."""
        self._name = name
        self._won = won


class AbstractPlayer(ABC):
    """Represents an abstract player of one Labyrinth game."""

    @abstractmethod
    def name(self) -> str:
        """Returns the name of this player, for display purposes."""
        raise NotImplementedError()

    @abstractmethod
    def propose_board0(self, rows: int, columns: int) -> Board:
        """Proposes an initial board of the given size."""
        raise NotImplementedError()

    @abstractmethod
    def setup(self, state0: Optional[GameState], goal: Coord) -> Any:
        """Updates this player with an initial state (or None), and a goal position."""
        raise NotImplementedError()

    @abstractmethod
    def take_turn(self, s: GameState) -> TurnAction:
        """Selects an action for this turn using the player's strategy."""
        raise NotImplementedError()

    @abstractmethod
    def win(self, w: bool) -> Any:
        """Updates this player to indicate whether they won the game."""
        raise NotImplementedError()

    # @abstractmethod
    # def get_player_secret(self) -> PlayerSecret:
    #     raise NotImplementedError()


class Player(AbstractPlayer):
    """Represents a player of one Labyrinth game."""

    _name: str
    _strategy: Strategy
    _implementation: Union[PlayerSetupImpl, PlayerGameplayImpl, PlayerScoringImpl]

    def __init__(self, name: str, strategy: Strategy):
        """Creates a Player in the SETUP phase with `name` and `strategy`."""
        self._name = name
        self._strategy = strategy
        self._implementation = PlayerSetupImpl(name)

    def _set_implementation(self, new_impl: Union[PlayerSetupImpl, PlayerGameplayImpl, PlayerScoringImpl]) -> None:
        """Transitions this player to the protocol phase implemented by `new_impl`"""
        self._implementation = new_impl

    def name(self) -> str:
        """Returns the name of this player, for display purposes."""
        return self._name

    def propose_board0(self, rows: int, columns: int) -> Board:
        """Proposes an initial board of the given size.

        Raises:
            IncorrectPhaseError: If this player isn't in the SETUP phase
            ValueError: If `rows` or `columns` is less than 1
        """
        if self._implementation.phase is not ProtocolPhase.SETUP:
            raise IncorrectPhaseError()
        return self._implementation.propose_board0(rows, columns)

    def setup(self, state0: Optional[GameState], goal: Coord) -> Union[Tuple[PlayerState, PlayerSecret], Coord]:
        """Updates this player with an initial state (or None), and a goal position.

        Note:
            Side effect: Transitions player to GAMEPLAY phase if `state0` is not None

        Raises:
            IncorrectPhaseError: If this player is in the SETUP phase and `state0` is not provided
            IncorrectPhaseError: If this player is in the GAMEPLAY phase and `state0` is provided
            ValueError: If `state0` is not provided and `goal` is different from the player's
                home location

        Returns:
            Union[Tuple[PlayerState, PlayerSecret], Coord]: The player's initial state and secret,
                if this is the first setup call, or the player's new goal position otherwise
        """
        if state0 is not None:
            if self._implementation.phase is not ProtocolPhase.SETUP:
                raise IncorrectPhaseError()
            player_state, player_secret = self._implementation.setup(state0, goal)
            self._set_implementation(PlayerGameplayImpl(self._name, self._strategy, player_state, player_secret))
            return player_state, player_secret
        else:
            if self._implementation.phase is not ProtocolPhase.GAMEPLAY:
                raise IncorrectPhaseError()
            return self._implementation.setup(goal)

    def take_turn(self, s: GameState) -> TurnAction:
        """Selects an action for this turn using the player's strategy.

        Raises:
            IncorrectPhaseError: If this player is not in the GAMEPLAY phase.
        """
        if self._implementation.phase is not ProtocolPhase.GAMEPLAY:
            raise IncorrectPhaseError()
        return self._implementation.take_turn(s)

    def win(self, w: bool) -> bool:
        """Stores whether this player has won the game.

        Note:
            Side effect: Transitions player to SCORING phase

        Raises:
            IncorrectPhaseError: If this player is not in the GAMEPLAY phase.

        Returns:
            bool: Whether the player has won the game
        """
        if self._implementation.phase is not ProtocolPhase.GAMEPLAY:
            raise IncorrectPhaseError()
        self._set_implementation(PlayerScoringImpl(self._name, w))
        return w

    # def get_player_secret(self) -> PlayerSecret:
    #     if self._implementation.phase is not ProtocolPhase.GAMEPLAY:
    #         raise IncorrectPhaseError()
    #     return self._implementation._player_secret
