"""Referee implementation for the Maze game's player-referee protocol."""

import asyncio
import random
import sys
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union, cast

from typing_extensions import Literal

from Maze.Common.board import Board
from Maze.Common.gem import Gem
from Maze.Common.JSON.serializers import color_to_json
from Maze.Common.state import (
    Color,
    GameState,
    NoMorePlayersError,
    PlayerSecret,
    PlayerState,
    RefereeGameState,
    RestrictedGameState,
)
from Maze.Common.tile import Tile, TileShape
from Maze.Common.utils import Coord, Timeout, get_random_color, squared_euclidean_distance
from Maze.Players.player import AbstractPlayer
from Maze.Players.strategy import TurnAction, TurnPass
from Maze.Referee.observer import Observer

MAX_ROUNDS: int = 1000
DEFAULT_BOARD_WIDTH: int = 7
DEFAULT_BOARD_HEIGHT: int = 7
PLAYER_TAKE_TURN_TIMEOUT: int = 4
PLAYER_TIMEOUT: int = 4


class Ejection:
    """Result which indicates that the current player should be ejected."""


@dataclass(init=False)
class GameOutcome:
    """Stores the list of winners and list of ejected players for a Labyrinth game."""

    winners: List[AbstractPlayer]
    ejected: List[AbstractPlayer]

    def __init__(self, winners: List[AbstractPlayer], ejected: List[AbstractPlayer]):
        self.winners = winners
        self.ejected = ejected


@dataclass(init=False)
class FinalRoundOutcome:
    """Represents a round outcome which ended the game of Labyrinth."""

    is_final: Literal[True]
    game_outcome: GameOutcome

    def __init__(self, game_outcome: GameOutcome):
        self.is_final = True
        self.game_outcome = game_outcome


@dataclass(init=False)
class NonFinalRoundOutcome:
    """Represents a round outcome which did not end the game of Labyrinth."""

    is_final: Literal[False]
    game_state: GameState

    def __init__(self, game_state: GameState):
        self.is_final = False
        self.game_state = game_state


# Represents a round outcome of a game of Labyrinth.
# A round is defined as a sequence of turns for each player in order.
RoundOutcome = Union[FinalRoundOutcome, NonFinalRoundOutcome]


def order_by_game_progress(player_info: Tuple[PlayerState, PlayerSecret]) -> Tuple[int, int]:
    """Computes a key to sort the given `player_info`.

    Returns:
        Tuple[int, int]: A key which, when used in `sorted` with reverse=True, sorts players
            by the following criteria:
            - Players that have the most gems are first
            - Players closer to their next goal first, by squared Euclidean distance
    """
    player_state, player_secret = player_info
    goal_location = player_state.home_location if player_secret.is_going_home else player_secret.treasure_location
    return (
        player_secret.treasure_count,
        -squared_euclidean_distance(player_state.location, goal_location),
    )


class AsyncReferee:
    """Component that supervises the gameplay and scoring of Labyrinth games.

    A game is *completed* if any of the following occur:
      - a player reaches its home after visiting all of its assigned goals
      - all players that survive a round opt to pass
      - the referee has run 1000 rounds

    For the first type of completion, there is 1 game winner. For the other two
    types, the winners are all players who have made the maximum game progress, as
    defined in `order_by_game_progress`.

    A game is *cancelled* if all players are ejected. This corresponds to a game outcome
    with no winners.

    Note:
        This referee implementation handles the following abnormal interactions:
        - The player breaks the game rules
        - The player raises an exception

        The remote communication phase must handle the following abnormal interactions:
        - The player takes too long for a computation
        - The player sends in badly formed or invalid (presumably JSON) data
        - The player disconnects in the middle of a game
    """

    initial_board: Board
    initial_spare_tile: Tile
    goal_queue: List[Coord]  # Not actually a queue because we need to peek at elements without removing them

    def __init__(
        self,
        board: Board = None,
        spare_tile: Tile = None,
        height: int = DEFAULT_BOARD_HEIGHT,
        width: int = DEFAULT_BOARD_WIDTH,
    ):
        """Creates a referee for a game.
        If no arguments are given, the referee will generate a game of size
        `DEFAULT_BOARD_WIDTH`x`DEFAULT_BOARD_HEIGHT with a random spare tile.

        If a game needs to be started from a specific state, pass in no
        arguments to this and then call `start_game_from_state`.

        Note:
            - If either board OR spare_tile is None, they will both be ignored and a
              random board and spare tile will be generated.
            - If a board and spare_tile are both given, height and width will be ignored.

        Args:
            board (Board, optional): The board to use for the game. Defaults to None.
            spare_tile (Tile, optional): The spare tile to use for the game. Defaults to None.
            height (int, optional): The height of the board to generate. Defaults to 7.
            width (int, optional): The width of the board to generate. Defaults to 7.
        """
        self.goal_queue = []

        if board is None or spare_tile is None:
            (
                self.initial_board,
                self.initial_spare_tile,
            ) = AsyncReferee._generate_random_board_and_spare(columns=width, rows=height)
        else:
            self.initial_board = board
            self.initial_spare_tile = spare_tile

    async def create_initial_game_state(self, players: List[AbstractPlayer]) -> Union[GameState, GameOutcome]:
        """Create a game state with default locations, homes, and goals for all `players`.

        Raises:
            ValueError: If the number of players is too large for all players to have unique homes

        Returns:
            Union[GameState, GameOutcome]: A state with this referee's default board and spare tile.
                All players will start on a distinct home and a distinct goal.
                If all players fail to provide their names, returns a GameOutcome
                with all players ejected instead
        """
        possible_homes = self.initial_board.get_all_fixed_tiles()
        if len(possible_homes) < len(players):
            raise ValueError("Too many players for the board size")
        self.goal_queue = possible_homes.copy()
        used_colors: List[Color] = []
        player_states: "OrderedDict[str, PlayerState]" = OrderedDict()
        for pl in players:
            random_home = random.choice(possible_homes)
            random_color = get_random_color(used_colors)
            player_name = self._request_player_name(pl)
            if player_name is not False:
                # Player has successfully provided their name
                player_states[color_to_json(random_color)] = PlayerState(
                    random_home, random_home, random_color, player_name
                )
                possible_homes.remove(random_home)
                used_colors.append(random_color)
        if len(player_states) == 0:
            # All players failed to provide name, so everyone is ejected
            # and there's no game left to run
            return GameOutcome([], players)
        player_secrets = {color: PlayerSecret(self.goal_queue.pop(0), False) for color in player_states.keys()}
        return RefereeGameState(player_states, player_secrets, self.initial_spare_tile, self.initial_board)

    async def start_game(
        self, players: List[AbstractPlayer], observers: Optional[List[Observer]] = None
    ) -> GameOutcome:
        """Starts a game with `players` from referee's default config and runs it until it ends.

        Note:
            The `observers`, if any, will be updated with each state change from this referee
        """
        game_observers = observers if (observers is not None) else []
        state_or_outcome = await self.create_initial_game_state(players)
        if isinstance(state_or_outcome, GameOutcome):
            # The game ended prematurely, so we notify observers and return this outcome
            await self._broadcast_game_over_to_observers(game_observers)
            return state_or_outcome
        state = state_or_outcome
        return await self.start_game_from_state(state, players, goal_queue=self.goal_queue, observers=observers)

    async def start_game_from_state(
        self,
        state: GameState,
        players: List[AbstractPlayer],
        goal_queue: List[Coord],
        observers: Optional[List[Observer]] = None,
        enforce_distinct_homes=True,
    ) -> GameOutcome:
        """Runs a game with `players` from a `state` until it is completed.

        Notes:
            The state can represent a game to start OR resume.
            The `observers`, if any, will be updated with each state change from this referee

        Raises:
            KeyError: If any of the `players` that successfully provide their name
                are not part of the state's player list
            ValueError: If `enforce_distinct_homes` and any of the `players` that
                successfully provide their name share a home
        """
        game_observers = observers if (observers is not None) else []
        self.goal_queue = goal_queue
        player_names_map = await self._construct_player_map(players)
        if len(player_names_map) == 0:
            # All players failed to provide name, so everyone is ejected
            # and there's no game left to run
            outcome = GameOutcome([], players)
            # Notify the observers that the game is over
            await self._broadcast_game_over_to_observers(game_observers)
            return outcome

        player_map = await self._create_player_color_map(player_names_map, state)
        state = await self._eject_bad_players_from_map(player_map, state)
        self._validate_initial_game_state(state, player_names_map, player_map, enforce_distinct_homes)
        state_or_outcome = await self._configure_game(state, player_map, game_observers)
        # TODO: this check feels unnecessary, if all players fail to setup, hopefully run_game will handle that case
        if isinstance(state_or_outcome, GameOutcome):
            # The game ended prematurely, so we return this outcome
            # print(f'Ending prematurely: {state_or_outcome}')
            return state_or_outcome
        state = state_or_outcome
        outcome = await self._run_game(state, player_map, game_observers)
        outcome = await self._notify_winners(state, outcome, player_map, game_observers)
        return outcome

    async def _create_player_color_map(
        self, player_names_map: Dict[str, AbstractPlayer], state: GameState
    ) -> Dict[str, AbstractPlayer]:
        """Creates a map from player name to player color for all players in the game.

        Args:
            player_names_map (Dict[str, AbstractPlayer]): A map from player name to player object
            state (GameState): The game state to create the map from

        Returns:
            Dict[str, AbstractPlayer]: A map from player name to player color
        """
        player_map = OrderedDict()
        for name, player_obj in player_names_map.items():
            for color in state.player_colors:
                if state.player_states[color].name == name:
                    player_map[color] = player_obj
                    break
        return player_map

    async def _eject_bad_players_from_map(self, player_map, state):
        for color in state.player_colors:
            if color not in player_map:
                state = state.eject_player(color)
        return state

    async def _construct_player_map(self, players):
        """Constructs a map from player name to player object for all players in the game."""
        player_map: Dict[str, AbstractPlayer] = {}
        for pl in players:
            player_name = self._request_player_name(pl)
            if player_name is not False:
                # Player has successfully provided their name
                player_map[cast(str, player_name)] = pl
        return player_map

    def _validate_initial_game_state(
        self,
        state: GameState,
        player_names_map: Dict[str, AbstractPlayer],
        player_map: Dict[str, AbstractPlayer],
        enforce_distinct_homes: bool,
    ) -> None:
        """Validates that a game `state` with players `player_map` follows the rules of Labyrinth.

        Raises:
            KeyError: If any of the players in `player_map` are not part of `state`'s player list
            ValueError: If `enforce_distinct_homes` and any of the players in `state` share a home
        """
        # TODO: when is this condition true?
        if len(player_names_map) != len(player_map):
            raise ValueError("Player client list doesn't match state's players")
        if set(state.player_colors) != set(player_map.keys()):
            raise KeyError("Player client list doesn't match state's players")
        if enforce_distinct_homes:
            distinct_player_homes = set(ps.home_location for ps in state.player_states.values())
            if len(distinct_player_homes) != len(state.player_states):
                raise ValueError("Players must have distinct homes")

    def _restrict_game_state(self, state: GameState, player_color: Color) -> RestrictedGameState:
        """Creates a RestrictedGameState from `state` for the player of `player_color` with that player first."""
        before_this_player_states = []
        after_this_player_states = []
        player_found = False
        for color, ps in state.player_states.items():
            if ps.color == player_color:
                player_color_str = color
                player_state = ps
                player_found = True
            elif player_found:
                after_this_player_states.append((color, ps))
            else:
                before_this_player_states.append((color, ps))
        new_player_states: OrderedDict[str, PlayerState] = OrderedDict(
            [
                (player_color_str, player_state),
                *after_this_player_states,
                *before_this_player_states,
            ]
        )
        return RestrictedGameState(
            new_player_states,
            {player_color_str: state.get_player_secret(player_color_str)},
            state.spare_tile,
            state.board,
            prev_action=state.prev_action,
        )

    async def _configure_game(
        self,
        state0: GameState,
        players: Dict[str, AbstractPlayer],
        observers: List[Observer],
    ) -> Union[GameState, GameOutcome]:
        """Configure the game by sending an initial `setup` message to all players in `state0`.

        Raises:
            KeyError: If any player in the given state is not in `players`

        Returns:
            Union[GameState, GameOutcome]: `state0` minus any players that failed to `setup`,
                or a GameOutcome where all players have been ejected if everyone failed to `setup`
        """
        ejected_player_colors = []
        for color in state0.player_colors:
            restricted_state = self._restrict_game_state(state0, state0.player_states[color].color)
            goal = state0.get_player_secret(color).treasure_location
            if not self._request_player_setup(players[color], restricted_state, goal):
                # Player threw an error, timed out, or failed to return anything on setup
                ejected_player_colors.append(color)
        # TODO: this check is unnecessary, players who fail to setup should be ejected and this condition should be
        # TODO checked in an is_game_over method of some kind. Seems to be here to satisfy returning game outcome
        if len(ejected_player_colors) == len(state0.player_colors):
            # All players failed to setup, so everyone is ejected
            # and there's no game left to run
            outcome = GameOutcome([], list(players.values()))
            # Notify the observers that the game is over
            # TODO: Use existing method to do this (single point of control)
            for observer in observers:
                await observer.game_over()
            return outcome
        state = state0
        for color in ejected_player_colors:
            state = state.eject_player(color)
        await self._broadcast_state_to_observers(state, observers)
        return state

    async def _run_game(
        self,
        state0: GameState,
        players: Dict[str, AbstractPlayer],
        observers: List[Observer],
    ) -> GameOutcome:
        """Run a game with `players` from starting `state0` until it is completed."""
        current_round = 0
        state = state0
        # TODO: main fix: add a central is_game_over method to avoid checking separate parts in separate places
        try:
            while current_round < MAX_ROUNDS:
                round_outcome = await self._run_round(state, players, observers)
                if round_outcome.is_final:
                    return round_outcome.game_outcome
                # if _run_round doesn't end the game, it returns the state for the start of
                # the next round
                state = round_outcome.game_state
                current_round += 1

            # 1000 rounds without an explicit win, check for ties and end game
            return self._check_winners(state, players)
        except NoMorePlayersError:
            # No players left, end the game with no winners
            return GameOutcome([], list(players.values()))

    async def _run_round(
        self,
        begin_state: GameState,
        players: Dict[str, AbstractPlayer],
        observers: List[Observer],
    ) -> RoundOutcome:
        """Run a round with `players` from starting `state0` until it is completed."""
        any_player_moved = False
        state = begin_state
        round_size = state.num_players
        # A round must go through every player that survived the previous round
        for _ in range(round_size):
            player_color = state.current_player_color
            player = players[player_color]
            option_next_state, did_move = await self._run_player_turn(state, player)
            # TODO: handle this in run_turn?
            if isinstance(option_next_state, Ejection):
                state = state.eject_current_player()
                await self._broadcast_state_to_observers(state, observers)
                continue

            prev_state = state
            state = option_next_state
            if did_move:
                any_player_moved = True
            if self._current_player_returned_home(state, prev_state):
                # Player has returned home, broadcast the final state to observers
                # and end the game with the correct amount of winners
                await self._broadcast_state_to_observers(state, observers)
                winners = self._check_winners(state, players, player_color)
                return FinalRoundOutcome(winners)
            state = state.end_current_turn()
            await self._broadcast_state_to_observers(state, observers)
        if not any_player_moved:
            # Every player passed on their turn, check for ties and end game
            return FinalRoundOutcome(self._check_winners(state, players))
        return NonFinalRoundOutcome(state)

    async def _run_player_turn(
        self, state: GameState, player: AbstractPlayer
    ) -> Tuple[Union[Ejection, GameState], bool]:
        """Attempts to run a player's turn and return the next state.

        Args:
            player (Player): The player who is expected to take a turn
            state (GameState): The current game state

        Returns:
            Tuple[Union[Ejection, GameState], bool]: The result of the turn (Ejection or
                GameState), paired with a boolean indicating whether the player successfully
                made a TurnWithMove.
        """
        next_state: GameState
        try:
            restricted_state = self._restrict_game_state(state, state.current_player_state.color)
            turn_action = self._request_player_take_turn(player, restricted_state)
            if isinstance(turn_action, TurnPass):
                return state, False
            else:
                next_state = (
                    state.rotate_spare_tile(turn_action.degrees)
                    .shift_tiles(turn_action.shift)
                    .move_current_player(turn_action.movement)
                )
        except Exception as e:
            # Player threw an error or tried to make an illegal move
            return Ejection(), False
        if next_state.is_current_player_at_treasure():
            return self._send_player_new_goal(player, state, next_state)
        else:
            return next_state, True

    def _current_player_returned_home(self, state: GameState, prev_state: GameState) -> bool:
        """Checks whether the current player in `state` had their treasure in `prev_state` and is now at their home."""
        # Already had treasure before the move `prev_state` -> `state` and is now at home
        return prev_state.get_current_player_secret().is_going_home and state.is_current_player_at_home()

    async def _broadcast_state_to_observers(self, state: GameState, observers: List[Observer]) -> None:
        """Informs all `observers` of the next `state`."""
        for observer in observers:
            await observer.receive_state(state)

    async def _broadcast_game_over_to_observers(self, observers: List[Observer]) -> None:
        """Informs all `observers` that the game is over."""
        for observer in observers:
            await observer.game_over()

    def _request_player_name(self, player: AbstractPlayer) -> Union[str, bool]:
        """Gets the player's name, or False if they error or time out when name() is called."""
        # TODO: would be nice to centralize timeouts but you can't have everything you want in life
        try:
            with Timeout(PLAYER_TIMEOUT):
                name = player.name()
        except Exception:
            # Player either timed out or threw an error
            return False
        return name

    def _request_player_setup(self, player: AbstractPlayer, state0: Optional[GameState], goal: Coord) -> bool:
        """Tells the `player` to setup(`state0`, `goal`).

        Returns:
            bool: Whether the player successfully performed setup without timeout or error
                and provided any return value
        """
        try:
            with Timeout(PLAYER_TIMEOUT):
                _ = player.setup(state0=state0, goal=goal)
        except Exception as e:
            print(f"Player raised exception: {e}", file=sys.stderr)
            # Player either timed out or threw an error
            return False
        return True

    def _request_player_take_turn(self, player: AbstractPlayer, state: GameState) -> TurnAction:
        """Tells the `player` to take_turn(`state`).

        Raises:
            PlayerTimeoutException: If the player times out
            Exception: If any other error is thrown by the player

        Returns:
            TurnAction: The player's move
        """

        with Timeout(PLAYER_TAKE_TURN_TIMEOUT):
            return player.take_turn(state)

    def _request_player_win(self, player: AbstractPlayer, w: bool) -> bool:
        """Tells the player whether they won.

        Returns:
            bool: Whether the player successfully performed win() without timeout or error
                and provided any return value
        """
        try:
            with Timeout(PLAYER_TIMEOUT):
                _ = player.win(w)
        except Exception:
            # Player either timed out or threw an error
            return False
        return True

    def _send_player_new_goal(
        self, player: AbstractPlayer, prev_state: GameState, state: GameState
    ) -> Tuple[Union[Ejection, GameState], bool]:
        """Informs the player of their new goal if they found treasure.

        Args:
            player (Player): The player to send an update to, if necessary.
            prev_state (GameState): The state before the last turn action
            state (GameState): The current state

        Returns:
            bool: Whether the player successfully performed setup without timeout or error
                and provided any return value, if setup was called (and True otherwise)

        Note:
            `player` must be current player in both states.
        """
        # Already had treasure before the move `prev_state` -> `state`
        if prev_state.get_current_player_secret().is_going_home:
            return state, True
        # Tell player their new goal (or home)
        has_more_goals = len(self.goal_queue) > 0
        if has_more_goals:
            new_goal = self.goal_queue.pop(0)
        else:
            new_goal = state.current_player_state.home_location
        new_state = state.set_current_player_new_goal(new_goal)
        if not self._request_player_setup(player, None, new_goal):
            return Ejection(), False
        return new_state, True

    def _outcome_with_winners(
        self, winners: List[str], state: GameState, players: Dict[str, AbstractPlayer]
    ) -> GameOutcome:
        """Returns the game outcome with the given winners and any ejected players."""
        # anyone that the state has dropped must have been ejected
        ejected_names = set(players.keys()) - set(state.player_colors)
        return GameOutcome(
            [players[winner] for winner in winners],
            [players[ejected] for ejected in ejected_names],
        )

    def _check_winners(
        self,
        state: GameState,
        players: Dict[str, AbstractPlayer],
        player_trigger_color: str = None,
    ) -> GameOutcome:
        """Returns the game outcome with the winners computed from the state.

        Args:
            state (GameState): The current state
            players (Dict[str, AbstractPlayer]): The players in the game
            player_color_trigger (str): The player that triggered the check, if any. This covers the edge case
                                  where one player with distinct home/goal tiles reaches home while the
                                  other player (with equivalent home/goal tiles) is on their home/goal
                                  immediately after it initially reaches its goal.
        """
        players_with_progress = [
            (
                color,
                order_by_game_progress((state.player_states[color], state.get_player_secret(color))),
            )
            for color in state.player_colors
        ]

        max_game_progress = max(pair[1] for pair in players_with_progress)
        winners = [color for color, progress in players_with_progress if progress == max_game_progress]

        # If there is a tie, and one of the players is the player that triggered the check, then
        # the player that triggered the check wins.
        if len(winners) > 1 and player_trigger_color is not None and player_trigger_color in winners:
            winners = [player_trigger_color]

        return self._outcome_with_winners(winners, state, players)

    async def _notify_winners(
        self,
        state: GameState,
        game_outcome: GameOutcome,
        players: Dict[str, AbstractPlayer],
        observers: List[Observer],
    ) -> GameOutcome:
        """Sends messages to the non-ejected players telling them whether they won.

        Returns:
            GameOutcome: `game_outcome` with any players that respond badly to win()
                moved to the ejected list
        """
        ejected_players = []
        # anyone that the state has dropped must have been ejected, so they don't get notified
        for name in state.player_colors:
            player_won = players[name] in game_outcome.winners
            graceful_win = self._request_player_win(players[name], player_won)
            if not graceful_win:
                # Player threw an error, timed out, or failed to return anything on win
                ejected_players.append(players[name])
        for observer in observers:
            await observer.game_over()
        updated_winners = [winner for winner in game_outcome.winners if winner not in ejected_players]
        updated_ejected_players = list(set(game_outcome.ejected + ejected_players))
        return GameOutcome(updated_winners, updated_ejected_players)

    @staticmethod
    def _generate_random_board_and_spare(columns: int = 7, rows: int = 7) -> Tuple[Board, Tile]:
        """Generates a random `columns`x`rows` board and a spare tile."""
        if rows < 1 or columns < 1:
            raise ValueError("Expected dimensions for board with at least 1 tile")
        tile_choices: List[Tuple[TileShape, int]] = []
        for shape in TileShape:
            for rotation in shape.unique_rotations():
                tile_choices.append((shape, rotation))
        total_tiles = rows * columns + 1
        tiles = {}
        treasures = random.sample(list(Gem.unordered_pairs()), total_tiles)
        for col in range(columns):
            for row in range(rows):
                shape, rotation = random.choice(tile_choices)
                tiles[Coord(col, row)] = Tile(shape, rotation, treasures[col * columns + row])
        shape, rotation = random.choice(tile_choices)
        spare_tile = Tile(shape, rotation, treasures[-1])
        return (Board(tiles, columns, rows), spare_tile)


class Referee:
    """Component that supervises the gameplay and scoring of Labyrinth games.

    See the docstring for AsyncReferee for more definitions.

    Note: Behaves like AsyncReferee but works synchronously.
    """

    wrapped: AsyncReferee
    loop: asyncio.AbstractEventLoop

    def __init__(self, board: Board, spare_tile: Tile):
        """Creates a referee for a game with the given `board` and `spare_tile`."""
        self.wrapped = AsyncReferee(board, spare_tile)
        self.loop = asyncio.get_event_loop()

    def create_initial_game_state(self, players: List[AbstractPlayer]) -> Union[GameState, GameOutcome]:
        """Create a game state with default locations, homes, and goals for all `players`.

        Raises:
            ValueError: If the number of players is too large for all players to have unique homes

        Returns:
             Union[GameState, GameOutcome]: A state with this referee's default board and spare tile.
                All players will start on a distinct home tile with a shared goal
                at (board_width - 2, board_height - 2)
                If all players fail to provide their names, returns a GameOutcome
                with all players ejected instead
        """
        return self.loop.run_until_complete(self.wrapped.create_initial_game_state(players))

    def start_game(self, players: List[AbstractPlayer], observers: Optional[List[Observer]] = None) -> GameOutcome:
        """Starts a game with `players` from referee's default config and runs it until it ends.

        Note:
            The `observers`, if any, will be updated with each state change from this referee
        """
        return self.loop.run_until_complete(self.wrapped.start_game(players, observers))

    def start_game_from_state(
        self,
        state: GameState,
        players: List[AbstractPlayer],
        goal_queue: List[Coord],
        observers: Optional[List[Observer]] = None,
        enforce_distinct_homes=True,
    ) -> GameOutcome:
        """Runs a game with `players` from a `state` until it is completed.

        Note:
            The state can represent a game to start OR resume.

        Raises:
            KeyError: If any of the `players` that successfully provide their name
                are not part of the state's player list
            ValueError: If `enforce_distinct_homes` and any of the `players` that
                successfully provide their name share a home
        """
        return self.loop.run_until_complete(
            self.wrapped.start_game_from_state(
                state,
                players,
                goal_queue=goal_queue,
                observers=observers,
                enforce_distinct_homes=enforce_distinct_homes,
            )
        )
