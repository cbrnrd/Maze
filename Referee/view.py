"""Interfaces and data definitions for Labyrinth views."""

from typing import TYPE_CHECKING
from dataclasses import dataclass

from Maze.Common.state import GameState

if TYPE_CHECKING:
    # Only needed for type - keeping circular import for now
    from Maze.Referee.observer import Observer


@dataclass(init=False)
class UIState:
    """Combines information for the UI to render."""

    game_state: GameState
    enable_next_button: bool
    show_file_dialog: bool

    def __init__(self, game_state: GameState, enable_next_button: bool, show_file_dialog: bool):
        self.game_state = game_state
        self.enable_next_button = enable_next_button
        self.show_file_dialog = show_file_dialog


class UIApp:
    """Abstract class for a view for a Labyrinth game, controlled by an Observer."""

    async def push_state(self, ui_state: UIState) -> None:
        """Enqueues `ui_state` to be rendered."""
        raise NotImplementedError()

    async def run(self, observer: "Observer") -> None:
        """Displays the UI, and responds to events.

        Args:
            observer (Observer): The controller of this view.
        """
        raise NotImplementedError()


class UIAppFactory:
    """Abstract class for a GameState -> UIApp function."""

    def create(self, initial_state: UIState) -> UIApp:
        """Creates a UIApp for the initial state."""
        raise NotImplementedError()
