"""Organizes converters from JSON to our data structures."""
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union, cast

from typing_extensions import assert_never

from Maze.Common.board import Board
from Maze.Common.gem import Gem
from Maze.Common.JSON.definitions import (
    ActionJson,
    BadFMJson,
    BadPS2Json,
    BadPSJson,
    BoardJson,
    ChoiceJson,
    ColorJson,
    ConnectorJson,
    CoordinateJson,
    DegreeJson,
    DirectionJson,
    HexColorRegex,
    NamedColorJson,
    NameJson,
    NameRegex,
    PlayerJson,
    PlayerSpecJson,
    PSJson,
    RefereePlayerJson,
    RefereeState2Json,
    RefereeStateJson,
    StateJson,
    StrategyJson,
    TileJson,
)
from Maze.Common.JSON.serializers import color_to_json
from Maze.Common.JSON.utils import calculate_insert_location
from Maze.Common.state import (
    Color,
    CompleteTurnPrevAction,
    EmptyPrevAction,
    GameState,
    PlayerSecret,
    PlayerState,
    PrevAction,
    RefereeGameState,
    RestrictedGameState,
    ShiftOp,
)
from Maze.Common.tile import Direction, Tile, TileShape
from Maze.Common.utils import Coord
from Maze.Players.player import Player
from Maze.Players.strategy import EuclidStrategy, RiemannStrategy, Strategy, TurnAction, TurnPass, TurnWithMove


@dataclass
class BadPlayer(Player):
    """Creates a mock version of a Player that throws an error."""

    fail_method: str
    player: Player

    def name(self):
        return self.player.name()

    def setup(self, state0, goal):
        if self.fail_method == "setUp":
            return 1 / 0
        return self.player.setup(state0, goal)

    def take_turn(self, state):
        if self.fail_method == "takeTurn":
            return 1 / 0
        return self.player.take_turn(state)

    def win(self, w):
        if self.fail_method == "win":
            return 1 / 0
        return self.player.win(w)


@dataclass
class BadPlayer2(Player):
    """Creates a mock version of a Player that enters an infinite loop."""

    fail_method: str
    fail_countdown: int
    player: Player

    def name(self):
        return self.player.name()

    def setup(self, state0, goal):
        if self.fail_method == "setUp":
            self.fail_countdown -= 1
            if self.fail_countdown == 0:
                while True:
                    pass
        return self.player.setup(state0, goal)

    def take_turn(self, state):
        if self.fail_method == "takeTurn":
            self.fail_countdown -= 1
            if self.fail_countdown == 0:
                while True:
                    pass
        return self.player.take_turn(state)

    def win(self, w):
        if self.fail_method == "win":
            self.fail_countdown -= 1
            if self.fail_countdown == 0:
                while True:
                    pass
        return self.player.win(w)


def get_connector(connector: ConnectorJson) -> Tuple[TileShape, int]:
    """Converts the given connector to its canonical tile shape and rotation."""
    table = {
        "│": (TileShape.LINE, 0),
        "─": (TileShape.LINE, 1),
        # ===
        "└": (TileShape.CORNER, 0),
        "┌": (TileShape.CORNER, 1),
        "┐": (TileShape.CORNER, 2),
        "┘": (TileShape.CORNER, 3),
        # ===
        "┬": (TileShape.TEE, 0),
        "┤": (TileShape.TEE, 1),
        "┴": (TileShape.TEE, 2),
        "├": (TileShape.TEE, 3),
        # ===
        "┼": (TileShape.CROSS, 0),
    }
    return table[connector]


def get_board(board_json: BoardJson) -> Board:
    """Creates the game board represented by board_json."""
    height = len(board_json["connectors"])
    width = len(board_json["connectors"][0])
    tiles = {}
    treasures = board_json["treasures"]
    for y, row in enumerate(board_json["connectors"]):
        for x, connector in enumerate(row):
            shape, rotation = get_connector(connector)
            gem1 = Gem.from_string(treasures[y][x][0])
            gem2 = Gem.from_string(treasures[y][x][1])
            tiles[Coord(x, y)] = Tile(shape, rotation, (gem1, gem2))
    return Board(tiles, width, height)


def get_coord(coord_json: CoordinateJson) -> Coord:
    """Creates the coordinate pair represented by coord_json."""
    return Coord(coord_json["column#"], coord_json["row#"])


def get_color(color_json: ColorJson) -> Color:
    """Creates the Color represented by color_json."""
    named_color_map: Dict[NamedColorJson, Color] = {
        "purple": (0x80, 0x00, 0x80),
        "orange": (0xFF, 0xA5, 0x00),
        "pink": (0xFF, 0xC0, 0xCB),
        "red": (0xFF, 0x00, 0x00),
        "blue": (0x00, 0x00, 0xFF),
        "green": (0x00, 0x80, 0x00),
        "yellow": (0xFF, 0xFF, 0x00),
        "white": (0xFF, 0xFF, 0xFF),
        "black": (0, 0, 0),
    }
    if color_json in named_color_map:
        return named_color_map[cast(NamedColorJson, color_json)]
    assert len(color_json) == 6
    assert HexColorRegex.match(color_json) is not None
    red = int(color_json[:2], base=16)
    green = int(color_json[2:4], base=16)
    blue = int(color_json[4:], base=16)
    return (red, green, blue)


def get_direction(dir_json: DirectionJson) -> Direction:
    """Creates the Direction represented by dir_json."""
    if dir_json == "LEFT":
        return Direction.LEFT
    if dir_json == "RIGHT":
        return Direction.RIGHT
    if dir_json == "UP":
        return Direction.UP
    if dir_json == "DOWN":
        return Direction.DOWN
    assert_never(dir_json)


def get_action(action_json: Optional[ActionJson], board: Board) -> Optional[ShiftOp]:
    """Creates the ShiftOp action represented by action_json."""
    if action_json is None:
        return None
    # assume len(action_json) == 2
    # assume type(action_json[0]) is int
    # assume action_json[1] is a valid direction
    index = cast(int, action_json[0])
    direction = get_direction(cast(DirectionJson, action_json[1]))
    insert_location = calculate_insert_location(index, direction, board.width, board.height)
    return ShiftOp(insert_location, direction)


def get_turn_action_from_json(choice_json: ChoiceJson, board: Board) -> TurnAction:
    """Creates the TurnAction represented by `choice_json` on `board`.

    Raises:
        ValueError: If `choice_json` is not a valid TurnAction
            or if `choice_json[0]` cannot be converted to an int.
    """
    if choice_json == "PASS":
        return TurnPass()
    try:
        assert len(choice_json) == 4
        index = int(cast(int, choice_json[0]))
        direction = get_direction(cast(DirectionJson, choice_json[1]))
        degree = get_degree(cast(DegreeJson, choice_json[2]))
        coord = get_coord(cast(CoordinateJson, choice_json[3]))
        insert_location = calculate_insert_location(index, direction, board.width, board.height)
        return TurnWithMove(degree, ShiftOp(insert_location, direction), coord)
    except AssertionError:
        raise ValueError("Invalid choice JSON")


def get_tile(tile_json: TileJson) -> Tile:
    """Creates the Tile represented by tile_json."""
    tile_shape, rotation = get_connector(tile_json["tilekey"])
    gem1 = Gem.from_string(tile_json["1-image"])
    gem2 = Gem.from_string(tile_json["2-image"])
    return Tile(tile_shape, rotation, (gem1, gem2))


def get_degree(degree_json: DegreeJson) -> int:
    """Calculates the clockwise degree rotation represented by degree_json."""
    if degree_json == 0:
        return 0
    if degree_json == 90:
        return 270
    if degree_json == 180:
        return 180
    if degree_json == 270:
        return 90
    assert_never(degree_json)


def get_player_state(player_json: PlayerJson, name: str = "") -> PlayerState:
    """Creates the PlayerState represented by player_json."""
    home = get_coord(player_json["home"])
    current = get_coord(player_json["current"])
    color = get_color(player_json["color"])
    return PlayerState(home, current, color, name)


def get_player_state_and_secret(
    referee_player_json: RefereePlayerJson,
) -> Tuple[PlayerState, PlayerSecret]:
    """Creates the PlayerState and PlayerSecret represented by referee_player_json."""
    home = get_coord(referee_player_json["home"])
    current = get_coord(referee_player_json["current"])
    goto = get_coord(referee_player_json["goto"])
    color = get_color(referee_player_json["color"])
    return PlayerState(home, current, color, ""), PlayerSecret(goto, False)


def _convert_state_last_to_prev_action(state_json: Union[StateJson, RefereeStateJson], board: Board) -> PrevAction:
    """Converts the state's `last` property to the type used by GameState."""
    prev_shiftop = get_action(state_json["last"], board)
    if prev_shiftop is None:
        return EmptyPrevAction()
    return CompleteTurnPrevAction(prev_shiftop)


def get_state(state_json: StateJson) -> GameState:
    """Creates the GameState represented by state_json."""
    board = get_board(state_json["board"])
    player_state = get_player_state(state_json["plmt"][0])
    color = color_to_json(player_state.color)
    prev_action = _convert_state_last_to_prev_action(state_json, board)
    spare_tile = get_tile(state_json["spare"])
    return GameState(
        OrderedDict({color: player_state}),
        player_secrets=None,
        spare_tile=spare_tile,
        board=board,
        prev_action=prev_action,
    )


def get_restricted_state(state_json: StateJson, goal_location: Coord = Coord(1, 1), goal_reached=False) -> GameState:
    """Creates the RestrictedGameState represented by `state_json`.

    Args:
        state_json (StateJson): The board, spare tile, list of players, and last sliding action.
            The owner of the state is assumed to be the first player in the list.
        goal_location (Coord): The treasure location for the owner of this state
    """
    board = get_board(state_json["board"])
    spare = get_tile(state_json["spare"])
    player_states = [get_player_state(player_json) for player_json in state_json["plmt"]]
    prev_action = _convert_state_last_to_prev_action(state_json, board)
    # Each player needs a unique name
    player_names = [str(i) for i in range(len(player_states))]
    # TODO: see if we can avoid this
    player_secrets = {player_names[0]: PlayerSecret(goal_location, goal_reached)}
    assert len(player_states) >= 1
    assert len({pl.color for pl in player_states}) == len(player_states)
    return RestrictedGameState(
        OrderedDict(zip(player_names, player_states)),
        player_secrets,
        spare,
        board,
        prev_action,
    )


def get_referee_state(state_json: RefereeStateJson, player_spec_json: PlayerSpecJson) -> GameState:
    """Creates the RefereeGameState represented by `state_json`.

    Args:
        state_json (RefereeStateJson): The board, spare tile, list of players, and
            last sliding action.
        player_spec_json (PlayerSpecJson): The players for this board; the names in the spec
            are expected to correspond with the colors identifying the players in the state's
            `plmt` field.
    """
    board = get_board(state_json["board"])
    spare = get_tile(state_json["spare"])
    prev_action = _convert_state_last_to_prev_action(state_json, board)
    player_names = [pl[0] for pl in player_spec_json]
    player_states: "OrderedDict[str, PlayerState]" = OrderedDict()
    player_secrets: Dict[str, PlayerSecret] = {}
    # Loop through player names along with player knowledge items (PlayerState, PlayerSecret)
    knowledge_iter = map(get_player_state_and_secret, state_json["plmt"])
    for name, knowledge in zip(player_names, knowledge_iter):
        pl_state, pl_secret = knowledge
        player_states[name] = pl_state
        player_secrets[name] = pl_secret

    assert len(player_states) >= 1
    assert len({pl.color for pl in player_states.values()}) == len(player_states)
    assert len(set(player_names)) == len(player_names)
    assert len(player_spec_json) == len(state_json["plmt"])
    return RefereeGameState(
        player_states,
        player_secrets,
        spare,
        board,
        prev_action,
    )


def get_referee_state_2(state_json: RefereeState2Json) -> Tuple[GameState, List[Coord]]:
    """Get the game state represented by `state_json` and the list of treasure locations.

    Args:
        state_json (RefereeState2Json): The board, spare tile, list of players, and
            last sliding action.
    """
    referee_state = get_referee_state_no_players(state_json)
    try:
        treasure_locations = [get_coord(coord_json) for coord_json in state_json["goals"]]
    except KeyError:
        treasure_locations = []
    return referee_state, treasure_locations


def get_referee_state_no_players(state_json: RefereeStateJson) -> GameState:
    board = get_board(state_json["board"])
    spare = get_tile(state_json["spare"])
    prev_action = _convert_state_last_to_prev_action(state_json, board)
    player_colors = [pl["color"] for pl in state_json["plmt"]]
    player_states: "OrderedDict[str, PlayerState]" = OrderedDict()
    player_secrets: Dict[str, PlayerSecret] = {}
    knowledge_iter = map(get_player_state_and_secret, state_json["plmt"])
    for color, knowledge in zip(player_colors, knowledge_iter):
        pl_state, pl_secret = knowledge
        player_states[color] = pl_state
        player_secrets[color] = pl_secret

    return RefereeGameState(
        player_states,
        player_secrets,
        spare,
        board,
        prev_action,
    )


def get_strategy(strategy_json: StrategyJson) -> Strategy:
    """Creates the Strategy described by `strategy_json`."""
    if strategy_json == "Euclid":
        return EuclidStrategy()
    elif strategy_json == "Riemann":
        return RiemannStrategy()
    else:
        assert_never(strategy_json)


def get_player(ps_json: PSJson) -> Player:
    """Creates a Player conforming to the referee-player protocol, based on `ps_json`."""
    name, strategy_json = ps_json
    strategy_json = cast(StrategyJson, strategy_json)
    # invariant: NameRegex.match(name) is not None
    # invariant: 1 <= len(name) <= 20
    return Player(name, get_strategy(strategy_json))


def get_bad_player(bad_ps_json: BadPSJson) -> Player:
    """Creates a bad Player that errors on a certain method, based on `bad_ps_json`."""
    name, strategy_json, bad_fm_json = bad_ps_json
    strategy_json = cast(StrategyJson, strategy_json)
    bad_fm_json = cast(BadFMJson, bad_fm_json)
    assert NameRegex.match(name) is not None
    assert 1 <= len(name) <= 20
    wrapped_player = Player(name, get_strategy(strategy_json))
    return BadPlayer(bad_fm_json, wrapped_player)


def get_bad_player2(bad_ps2_json: BadPS2Json) -> Player:
    """Creates a bad Player that infinite loops on a certain method, based on `bad_ps2_json`."""
    name, strategy_json, bad_fm_json, count = bad_ps2_json
    name = cast(NameJson, name)
    strategy_json = cast(StrategyJson, strategy_json)
    bad_fm_json = cast(BadFMJson, bad_fm_json)
    count = cast(int, count)
    assert NameRegex.match(name) is not None
    assert 1 <= len(name) <= 20
    wrapped_player = Player(name, get_strategy(strategy_json))
    return BadPlayer2(bad_fm_json, count, wrapped_player)
