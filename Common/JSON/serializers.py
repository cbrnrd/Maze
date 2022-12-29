"""Organizes converters from our data structures to JSON."""

from typing import Dict, Iterator, List, cast

from Maze.Common.JSON.definitions import (
    ActionJson,
    BoardJson,
    ChoiceJson,
    ColorJson,
    ConnectorJson,
    CoordinateJson,
    DirectionJson,
    MNameJson,
    PlayerJson,
    RefereePlayerJson,
    RefereeStateJson,
    StateJson,
    TreasureJson,
)
from Maze.Common.board import Board
from Maze.Common.state import Color, GameState, PlayerSecret, PlayerState, ShiftOp
from Maze.Common.tile import Direction, Tile, TileShape, TileShapeWithRotation
from Maze.Common.utils import Coord
from Maze.Players.strategy import TurnAction, TurnPass


def coord_to_json(coord: Coord) -> CoordinateJson:
    """Creates the JSON representation of the coordinate pair."""
    return {"row#": coord.row, "column#": coord.col}


def direction_to_json(direction: Direction) -> DirectionJson:
    """Creates the JSON representation of the direction."""
    return cast(DirectionJson, direction.name)


def shift_op_to_json(shift_op: ShiftOp) -> ActionJson:
    """Creates the JSON representation of the shift operation."""
    is_vertical = shift_op.direction.is_vertical
    col, row = shift_op.insert_location.col, shift_op.insert_location.row
    index = col if is_vertical else row
    return [index, direction_to_json(shift_op.direction)]


def turn_action_to_json(turn_action: TurnAction) -> ChoiceJson:
    """Creates the JSON representation of the turn action."""
    if isinstance(turn_action, TurnPass):
        return "PASS"
    index, direction_json = shift_op_to_json(turn_action.shift)
    # Degrees is clockwise in our representation
    degrees = -turn_action.degrees % 360
    return [
        index,
        direction_json,
        degrees,
        coord_to_json(turn_action.movement),
    ]


def _get_tile_connector(tile: Tile) -> ConnectorJson:
    """Returns the unicode character corresponding to the tile's shape and rotation."""
    table: Dict[TileShapeWithRotation, ConnectorJson] = {
        (TileShape.LINE, 0): "│",
        (TileShape.LINE, 1): "─",
        (TileShape.LINE, 2): "│",
        (TileShape.LINE, 3): "─",
        # =
        (TileShape.CORNER, 0): "└",
        (TileShape.CORNER, 1): "┌",
        (TileShape.CORNER, 2): "┐",
        (TileShape.CORNER, 3): "┘",
        # =
        (TileShape.TEE, 0): "┬",
        (TileShape.TEE, 1): "┤",
        (TileShape.TEE, 2): "┴",
        (TileShape.TEE, 3): "├",
        # =
        (TileShape.CROSS, 0): "┼",
        (TileShape.CROSS, 1): "┼",
        (TileShape.CROSS, 2): "┼",
        (TileShape.CROSS, 3): "┼",
    }
    return table[tile.shape, tile.rotation]


def _get_board_connectors(board: Board) -> List[List[ConnectorJson]]:
    """Serializes the tile shapes of the board."""
    result = []
    for row in range(board.height):
        result.append([_get_tile_connector(board.get_tile(Coord(col, row))) for col in range(board.width)])
    return result


def _get_tile_treasure(tile: Tile) -> TreasureJson:
    """Returns a 2-item list containing the names of the tile's gems."""
    gem1, gem2 = tile.gems
    return [gem1.value, gem2.value]


def _get_board_treasures(board: Board) -> List[List[TreasureJson]]:
    """Serializes the treasures on each tile of the board."""
    result = []
    for row in range(board.height):
        result.append([_get_tile_treasure(board.get_tile(Coord(col, row))) for col in range(board.width)])
    return result


def board_to_json(board: Board) -> BoardJson:
    """Creates the JSON representation of the board."""
    return {
        "connectors": _get_board_connectors(board),
        "treasures": _get_board_treasures(board),
    }


def color_to_json(color: Color) -> ColorJson:
    """Creates the JSON representation of the color."""
    red, green, blue = color
    stacked_int = red * 0x10000 + green * 0x100 + blue
    # need to remove the first two chars since Python puts a "0x" at the beginning
    hex_str = hex(stacked_int)[2:].upper()
    # need to add zeros to left in case red < 0x10
    return hex_str.zfill(6)


def player_state_to_json(player_state: PlayerState) -> PlayerJson:
    """Creates the JSON representation of the player state."""
    return {
        "current": coord_to_json(player_state.location),
        "home": coord_to_json(player_state.home_location),
        "color": color_to_json(player_state.color),
    }


def referee_player_state_to_json(player_state: PlayerState, player_secret: PlayerSecret) -> RefereePlayerJson:
    """Creates the JSON representation of the player state with the player's current goal."""
    goal_location = player_state.home_location if player_secret.is_going_home else player_secret.treasure_location
    player_state_json: RefereePlayerJson = cast(RefereePlayerJson, player_state_to_json(player_state))
    player_state_json["goto"] = coord_to_json(goal_location)
    return player_state_json


def _iter_rotated(lst: List[str], start_index: int) -> Iterator[str]:
    """Iterates through the list from `start_index` to end, then 0 to `start_index - 1`."""
    yield from lst[start_index:]
    yield from lst[:start_index]


def referee_game_state_to_json(state: GameState) -> RefereeStateJson:
    """Creates the JSON representation of the given `state`, including players' goal coordinates.

    Raises:
        SecretAccessError: If the given state does not have permission to access all players' goals
    """
    spare_gem1, spare_gem2 = _get_tile_treasure(state.spare_tile)
    ref_players: List[RefereePlayerJson] = []
    for color in _iter_rotated(state.player_colors, state.current_player_index):
        ref_players.append(referee_player_state_to_json(state.player_states[color], state.get_player_secret(color)))
    last_shift = state.get_last_shift_op()
    last_shift_json = shift_op_to_json(last_shift) if last_shift is not None else None
    return {
        "board": board_to_json(state.board),
        "spare": {
            "tilekey": _get_tile_connector(state.spare_tile),
            "1-image": spare_gem1,
            "2-image": spare_gem2,
        },
        "plmt": ref_players,
        "last": last_shift_json,
    }


def game_state_to_json(state: GameState) -> StateJson:
    """Creates the JSON representation of the given public `state`."""
    spare_gem1, spare_gem2 = _get_tile_treasure(state.spare_tile)
    players: List[PlayerJson] = []
    for name in _iter_rotated(state.player_colors, state.current_player_index):
        players.append(player_state_to_json(state.player_states[name]))
    last_shift = state.get_last_shift_op()
    last_shift_json = shift_op_to_json(last_shift) if last_shift is not None else None
    return {
        "board": board_to_json(state.board),
        "spare": {
            "tilekey": _get_tile_connector(state.spare_tile),
            "1-image": spare_gem1,
            "2-image": spare_gem2,
        },
        "plmt": players,
        "last": last_shift_json,
    }


def mname_to_json(mname: str) -> MNameJson:
    "Creates the JSON representation of the given method name."
    if mname == "setup":
        return "setup"
    elif mname == "take_turn":
        return "take-turn"
    else:
        return "win"
