# pylint: disable=missing-function-docstring,missing-module-docstring,protected-access

import asyncio
import builtins
import io
from collections import OrderedDict
from contextlib import contextmanager
import json
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from Maze.Common.JSON.serializers import color_to_json
from Maze.Common.state import GameState, PlayerSecret, PlayerState, RefereeGameState
from Maze.Common.test_board import ascii_board
from Maze.Common.test_tile import default_gems
from Maze.Common.tile import Tile, TileShape
from Maze.Common.utils import CompletableFuture, Coord
from Maze.Referee.observer import Observer
from Maze.Referee.view import UIApp, UIAppFactory, UIState


async def do_nothing_async(*args, **kwargs):
    """This method doesn't do anything."""


async def pair_with_async(val, coro):
    """Awaits the coroutine passed in, then returns `(val, result)`."""
    return (val, await coro)


class MockUIApp:
    """Mock a UIApp."""

    initial_state: UIState
    got_count: int
    stop_count: int
    completion: CompletableFuture[int]
    push_state: Any
    run: Any

    def __init__(self, initial_state: UIState, stop_count: int):
        self.initial_state = initial_state
        self.got_count = 1
        self.stop_count = stop_count
        self.completion = CompletableFuture()
        self.push_state = MagicMock(wraps=self._push_state)
        self.run = MagicMock(wraps=self._run)

    async def _push_state(self, *args):
        """Increments `states_received`"""
        self.got_count += 1
        if self.got_count == self.stop_count:
            self.completion.complete(self.got_count)

    async def _run(self, *args):
        """Waits for a preconfigured number of states to be received."""
        await self.completion.get()


class MockUIAppFactory(UIAppFactory):
    """Factory that returns a MockUIApp."""

    stop_count: int

    def __init__(self, stop_count: int = 1_000_000):
        self.stop_count = stop_count

    def create(self, initial_state: UIState) -> UIApp:
        return MockUIApp(initial_state, self.stop_count)  # type: ignore


class TestObserver:

    # Invariant: `next_states` is non-empty IFF `gui_future` is present

    @pytest.fixture
    def game_state(self) -> GameState:
        color1 = (160, 0, 255)
        color2 = (0, 255, 255)
        concentric_board = ascii_board(
            # 123456
            "┌─────┐",  # 0
            "│┌───┐│",
            "││┌─┐││",  # 2
            "│││┼│││",
            "││└─┘││",  # 4
            "│└───┘│",
            "└─────┘",  # 6
        )
        player_states = OrderedDict(
            [
                (
                    color_to_json(color1),
                    PlayerState(Coord(1, 1), Coord(1, 1), color1, "Zoe"),
                ),
                (
                    color_to_json(color2),
                    PlayerState(Coord(5, 1), Coord(5, 1), color2, "Xena"),
                ),
            ]
        )
        player_secrets = {
            color_to_json(color1): PlayerSecret(Coord(1, 5), False),
            color_to_json(color2): PlayerSecret(Coord(5, 5), False),
        }
        spare_tile = Tile(TileShape.LINE, 0, default_gems)
        return RefereeGameState(
            player_states,
            player_secrets,
            spare_tile,
            concentric_board,
        )

    @pytest.mark.asyncio
    async def test_receive_state(self, game_state: GameState) -> None:
        observer = Observer(MockUIAppFactory())
        await observer.receive_state(game_state)

        mock_app = cast(MockUIApp, observer.gui_future.get_now())
        app_init_game_state = mock_app.initial_state.game_state
        assert app_init_game_state.board == game_state.board
        assert app_init_game_state.spare_tile == game_state.spare_tile
        assert app_init_game_state.player_states == game_state.player_states
        assert app_init_game_state.current_player_index == game_state.current_player_index
        for name in game_state.player_colors:
            can_get_secret = game_state.can_get_player_secret(name)
            assert app_init_game_state.can_get_player_secret(name) == can_get_secret
            if can_get_secret:
                actual_secret = app_init_game_state.get_player_secret(name)
                assert actual_secret == game_state.get_player_secret(name)

    @pytest.mark.asyncio
    async def test_next_states_empty_iff_no_gui(self, game_state: GameState) -> None:
        observer = Observer(MockUIAppFactory())
        assert observer.gui_future.is_present is False
        assert len(observer.next_states) == 0
        # send a state; the UI should then be initialized
        await observer.receive_state(game_state)
        assert observer.gui_future.is_present is True
        assert len(observer.next_states) == 1
        mock_app = cast(MockUIApp, observer.gui_future.get_now())
        assert mock_app.initial_state.game_state.board == game_state.board
        assert mock_app.initial_state.enable_next_button is False
        assert mock_app.initial_state.show_file_dialog is False

    @pytest.mark.asyncio
    async def test_can_go_to_next(self, game_state: GameState) -> None:
        observer = Observer(MockUIAppFactory())
        assert observer._can_go_to_next() is False
        await observer.receive_state(game_state)
        assert observer._can_go_to_next() is False
        state2 = game_state.rotate_spare_tile(90)

        await observer.receive_state(state2)
        assert observer._can_go_to_next() is True
        mock_app = cast(MockUIApp, observer.gui_future.get_now())
        ui_state = cast(UIState, mock_app.push_state.call_args[0][0])
        # Should be on first state, not most recently received
        assert ui_state.game_state == game_state
        assert ui_state.enable_next_button is True

    @pytest.mark.asyncio
    async def test_go_to_next_errors(self, game_state: GameState) -> None:
        observer = Observer(MockUIAppFactory())
        assert len(observer.next_states) == 0
        with pytest.raises(ValueError):
            await observer._go_to_next()
        assert len(observer.next_states) == 0

        await observer.receive_state(game_state)
        assert len(observer.next_states) == 1
        with pytest.raises(ValueError):
            await observer._go_to_next()
        assert len(observer.next_states) == 1

    @pytest.mark.asyncio
    async def test_go_to_next(self, game_state: GameState) -> None:
        observer = Observer(MockUIAppFactory())
        state2 = game_state.rotate_spare_tile(90)
        await observer.receive_state(game_state)
        await observer.receive_state(state2)

        next_states_before = observer.next_states[:]
        assert len(next_states_before) == 2
        await observer._go_to_next()
        assert observer.next_states[0] == next_states_before[1]
        assert len(observer.next_states) == 1

        mock_app = cast(MockUIApp, observer.gui_future.get_now())
        ui_state = cast(UIState, mock_app.push_state.call_args[0][0])
        assert ui_state.game_state == next_states_before[1]
        assert ui_state.enable_next_button is False

    @pytest.mark.asyncio
    async def test_wait_for_quit_does_not_exit_immediately(self) -> None:
        observer = Observer(MockUIAppFactory())
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(observer.wait_for_quit(), 0.2)

    @pytest.mark.asyncio
    async def test_wait_for_quit_does_not_exit_before_app(self, game_state: GameState) -> None:
        observer = Observer(MockUIAppFactory(stop_count=5))
        send_state_coros = [
            pair_with_async(f"recv{i}", observer.receive_state(game_state.rotate_spare_tile(90 * i))) for i in range(4)
        ]
        wait_for_quit_coro = pair_with_async("wait", observer.wait_for_quit())
        for idx, future in enumerate(asyncio.as_completed([wait_for_quit_coro, *send_state_coros])):
            if idx < 4:
                name, _ = await future
                assert name.startswith("recv")
            else:
                # Waiting for quit that will not occur
                with pytest.raises(asyncio.TimeoutError):
                    await asyncio.wait_for(future, 0.2)

    @pytest.mark.asyncio
    async def test_wait_for_quit_exits_after_app(self, game_state: GameState) -> None:
        observer = Observer(MockUIAppFactory(stop_count=5))
        send_state_coros = [
            pair_with_async(f"recv{i}", observer.receive_state(game_state.rotate_spare_tile(90 * i))) for i in range(5)
        ]
        wait_for_quit_coro = pair_with_async("wait", observer.wait_for_quit())
        for idx, future in enumerate(asyncio.as_completed([wait_for_quit_coro, *send_state_coros])):
            name, _ = await future
            if idx < 5:
                assert name.startswith("recv")
            else:
                assert name == "wait"

    @pytest.mark.asyncio
    async def test_game_over(self) -> None:
        observer = Observer(MockUIAppFactory())
        assert observer.is_game_over is False
        await observer.game_over()
        assert observer.is_game_over is True

    @pytest.mark.asyncio
    async def test_save_to_file_before_state_arrives(self) -> None:
        observer = Observer(MockUIAppFactory())
        with pytest.raises(ValueError):
            observer._save_to_file("tmp")

    @pytest.mark.asyncio
    async def test_save_to_file_catches_io_error(self, monkeypatch, game_state: GameState) -> None:
        observer = Observer(MockUIAppFactory())
        await observer.receive_state(game_state)
        broken_open_call_count = 0

        @contextmanager
        def broken_open(*args, **kwargs):
            nonlocal broken_open_call_count
            broken_open_call_count += 1
            raise OSError("Permissions or something")

        monkeypatch.setattr(builtins, "open", broken_open)
        observer._save_to_file("tmp")
        assert broken_open_call_count == 1

    @pytest.mark.asyncio
    async def test_save_to_file(self, monkeypatch, game_state: GameState) -> None:
        observer = Observer(MockUIAppFactory())
        await observer.receive_state(game_state)
        mock_open_file = io.StringIO()
        mock_open_call_count = 0

        @contextmanager
        def mock_open(*args, **kwargs):
            nonlocal mock_open_file, mock_open_call_count
            mock_open_call_count += 1
            yield mock_open_file

        monkeypatch.setattr(builtins, "open", mock_open)
        observer._save_to_file("tmp")
        assert mock_open_call_count == 1
        json_written = mock_open_file.getvalue()
        serialized_state = json.loads(json_written)
        for key in ["board", "spare", "plmt", "last"]:
            assert key in serialized_state
        for key in ["connectors", "treasures"]:
            assert key in serialized_state["board"]
        for key in ["tilekey", "1-image", "2-image"]:
            assert key in serialized_state["spare"]
        for key in ["current", "home", "goto", "color"]:
            for player_obj in serialized_state["plmt"]:
                assert key in player_obj
        assert serialized_state["last"] is None
