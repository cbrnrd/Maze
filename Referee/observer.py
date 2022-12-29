"""Observer implementation for the Maze game's GUI observer."""

import json
import sys
from typing import List

from Maze.Common.JSON.serializers import referee_game_state_to_json
from Maze.Common.state import GameState
from Maze.Common.utils import CompletableFuture
from Maze.Referee.view import UIApp, UIAppFactory, UIState


class Observer:
    """Represents a client of a Referee that receives the state at the end of each turn.

    The observer works with a UIApp. We don't initialize it until we have a state, because
    the size of the board would be unknown, and we also wouldn't know what to show in the view.

    This means that there are two phases that must complete for the Observer to be done with
    its job - making a GUI, and responding to user input. However, the `main` method needs to be
    able to await the completion of this Observer in a single call - to accomplish this, we wrote
    a CompletableFuture class.
    """

    # Invariant: `next_states` is non-empty IFF `gui_future` is present
    next_states: List[GameState]
    is_game_over: bool
    gui_future: CompletableFuture[UIApp]
    _factory: UIAppFactory

    def __init__(self, factory: UIAppFactory):
        self.next_states = []
        self.is_game_over = False
        self.gui_future = CompletableFuture()
        self._factory = factory

    async def receive_state(self, state: GameState) -> None:
        """Updates this observer when the game it's watching changes states.

        If the UIApp is not guaranteed to respond in a timely manner, this must be
        overridden to handle timeouts.
        """
        self.next_states.append(state)
        ui_state = UIState(
            game_state=self.next_states[0],
            enable_next_button=self._can_go_to_next(),
            show_file_dialog=False,
        )
        if not self.gui_future.is_present:
            self.gui_future.complete(self._factory.create(ui_state))
        else:
            gui = self.gui_future.get_now()
            # although state is unchanged, enable_next might have changed.
            await gui.push_state(ui_state)

    async def game_over(self) -> None:
        """Updates this observer when the game it's watching ends."""
        self.is_game_over = True

    async def wait_for_quit(self) -> None:
        """Waits for the resources of this observer to be released."""
        gui = await self.gui_future.get()
        await gui.run(self)

    def _can_go_to_next(self) -> bool:
        """Checks whether it is possible to advance to the next state."""
        return len(self.next_states) > 1

    async def _go_to_next(self) -> None:
        """Advances to the next state.

        Raises:
            ValueError: If the current state is the last state received so far
            ValueError: If the GUI has not been initialized
        """
        if not self._can_go_to_next():
            raise ValueError("No more states available")
        gui = self.gui_future.get_now()
        self.next_states = self.next_states[1:]
        await gui.push_state(
            UIState(
                game_state=self.next_states[0],
                enable_next_button=self._can_go_to_next(),
                show_file_dialog=False,
            )
        )

    def _save_to_file(self, filepath: str):
        """Saves the current state's JSON representation to `filepath`, if possible.

        Note:
            Prints to stderr if an error occurs when attempting to write to the file

        Raises:
            ValueError: If there is no current state (before `receive_state` is called)
        """
        if len(self.next_states) == 0:
            raise ValueError("Should only be called when GUI is ready")
        try:
            with open(filepath, "w", encoding="utf-8") as dest_file:
                json.dump(
                    referee_game_state_to_json(self.next_states[0]),
                    dest_file,
                    ensure_ascii=False,
                )
        except OSError as exc:
            print(f"Could not write to {filepath}: {exc}", file=sys.stderr)
