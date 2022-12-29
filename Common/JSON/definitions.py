"""Organizes JSON data definitions from the test harness spec."""

import re
from typing import List, Optional, Tuple, Union

from typing_extensions import Literal, TypedDict

from Maze.Common.gem import Gem

# Describes the possible shapes of a tile
ConnectorJson = Union[
    Literal["│"],
    Literal["─"],
    Literal["└"],
    Literal["┌"],
    Literal["┐"],
    Literal["┘"],
    Literal["┬"],
    Literal["┤"],
    Literal["┴"],
    Literal["├"],
    Literal["┼"],
]

# Describes the color of a player's avatar as an English name
NamedColorJson = Union[
    Literal["purple"],
    Literal["orange"],
    Literal["pink"],
    Literal["red"],
    Literal["blue"],
    Literal["green"],
    Literal["yellow"],
    Literal["white"],
    Literal["black"],
]

# Describes the color of a player's avatar in hex format
HexColorJson = str
HexColorRegex = re.compile(r"^[A-F|\d][A-F|\d][A-F|\d][A-F|\d][A-F|\d][A-F|\d]$")

# Describes the color of a player's avatar in hex format or as an English name
ColorJson = Union[NamedColorJson, HexColorJson]

# Describes the four possible counter-clockwise rotations around
# the center of a tile.
DegreeJson = Union[
    Literal[0],
    Literal[90],
    Literal[180],
    Literal[270],
]

# Describes the direction in which a player may slide the tiles of a row
# or column. "LEFT" means that the spare tile is inserted on the *right*
DirectionJson = Union[
    Literal["LEFT"],
    Literal["RIGHT"],
    Literal["UP"],
    Literal["DOWN"],
]

# Specifies the last sliding action that an actor
# performed; None indicates that no sliding action has been performed yet
# Validation: this list must contain two elements:
#     the first an `int` and the second a `DirectionJson`
ActionJson = List[Union[int, DirectionJson]]


# TreasureJson would be a list of strings, but this enforces
# valid gems from the spec
Treasure = Tuple[Gem, Gem]

# Invariant: Must have length 2
TreasureJson = List[str]

# Describes a row-column coordinate on the board
CoordinateJson = TypedDict("CoordinateJson", {"row#": int, "column#": int})

# Designation for a choice of strategy implementation
StrategyJson = Union[Literal["Euclid"], Literal["Riemann"]]

# Describes a player's choice of move on their turn
# Validation: this list must contain four elements:
#     the first an `int` (index of column or row to slide);
#     the second a `DirectionJson` (direction to slide);
#     the third a `DegreeJson` (number of degrees to rotate the spare tile counter-clockwise before inserting)
#     and the last a `CoordinateJson` (destination for the player's avatar)
ChoiceWithMoveJson = List[Union[int, DirectionJson, DegreeJson, CoordinateJson]]

# Describes a player's decision to either pass or make a move
ChoiceJson = Union[Literal["PASS"], ChoiceWithMoveJson]

# A player's name; must be 1-20 characters, and only consist of numbers and letters A-Z (either case)
NameJson = str
NameRegex = re.compile(r"^[a-zA-Z0-9]+$")

# Specifies which strategy the named player of the given name employs.
# Validation: this list must contain two elements:
#    the first a `NameJson` and the second a `StrategyJson`
PSJson = List[Union[NameJson, StrategyJson]]

# Lists players with their strategies
PlayerSpecJson = List[PSJson]

# Designation for a choice of method on which the bad player wil error
BadFMJson = Union[Literal["setUp"], Literal["takeTurn"], Literal["win"]]

# Specifies which strategy the named player of the given name employs
#   and on which method the player throws an error
# Validation: this list must contain three elements:
#    the first a `NameJson`, the second a `StrategyJson`, and the third a `BadFMJson`
BadPSJson = List[Union[NameJson, StrategyJson, BadFMJson]]

# Specifies which strategy the named player of the given name employs
#   and on which method the player enters an infinite loop
#   after which number of calls
# Validation: this list must contain four elements:
#    the first a `NameJson`, the second a `StrategyJson`, the third a `BadFMJson`, and the fourth an `int`
BadPS2Json = List[Union[NameJson, StrategyJson, BadFMJson, int]]

# Lists well-behaved and badly-behaved players with their strategies
BadPlayerSpecJson = List[Union[PSJson, BadPSJson]]

# Lists well-behaved and badly-behaved players with their strategies
BadPlayerSpec2Json = List[Union[PSJson, BadPSJson, BadPS2Json]]

# Describes a tile in the game
# Validation: `1-image` and `2-image` must both be valid Gem names as documented in
#     Maze.Common.Gem
TileJson = TypedDict("TileJson", {"tilekey": ConnectorJson, "1-image": str, "2-image": str})


class BoardJson(TypedDict):
    """Represents a Board JSON input."""

    connectors: List[List[ConnectorJson]]
    treasures: List[List[TreasureJson]]


class PlayerJson(TypedDict):
    """Represents a Player JSON input."""

    current: CoordinateJson
    home: CoordinateJson
    color: ColorJson


class RefereePlayerJson(TypedDict):
    """Represents a RefereePlayer JSON input."""

    current: CoordinateJson
    home: CoordinateJson
    goto: CoordinateJson
    color: ColorJson


class StateJson(TypedDict):
    """Represents the current state of a Maze game known to the observers/players as JSON."""

    # The current state of the board
    board: BoardJson
    # The spare tile
    spare: TileJson
    # The list of players in the game; the current player is first
    # Validation: this must be a non-empty list
    # Validation: all players must have a unique `color`
    plmt: List[PlayerJson]
    # The last sliding action performed, or None if no sliding actions
    # have been performed.
    last: Optional[ActionJson]


class RestrictedStateJson(TypedDict):
    """Represents the current state of a Maze game known to the observers/players as JSON."""

    # The current state of the board
    board: BoardJson
    # The spare tile
    spare: TileJson
    # The list of players in the game; the current player is first
    # Validation: this must be a non-empty list
    # Validation: all players must have a unique `color`
    plmt: List[RefereePlayerJson]  # length 1
    # The last sliding action performed, or None if no sliding actions
    # have been performed.
    last: Optional[ActionJson]


class RefereeStateJson(TypedDict):
    """Represents the current state of a Maze game known to the referee as JSON."""

    # The current state of the board
    board: BoardJson
    # The spare tile
    spare: TileJson
    # The list of players in the game; the current player is first
    # Validation: this must be a non-empty list
    # Validation: all players must have a unique `color`
    plmt: List[RefereePlayerJson]
    # The last sliding action performed, or None if no sliding actions
    # have been performed.
    last: Optional[ActionJson]


class RefereeState2Json(TypedDict):
    board: BoardJson
    spare: TileJson
    goals: List[CoordinateJson]
    plmt: List[RefereePlayerJson]
    last: Optional[ActionJson]


# A method to call on the player
MNameJson = Union[Literal["setup"], Literal["take-turn"], Literal["win"]]
