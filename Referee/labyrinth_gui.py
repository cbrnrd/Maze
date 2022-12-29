"""A Labyrinth observer GUI written using Pygame and Pygame GUI."""

import asyncio
import time
from typing import (
    AsyncIterator,
    Iterable,
    List,
    Tuple,
    cast,
)

import pygame
import pygame_gui
from pygame import Color
from pygame.event import Event as PygameEvent
from pygame.math import Vector2
from pygame.rect import Rect
from pygame.surface import Surface
from pygame_gui.elements import UIButton, UIImage
from pygame_gui.ui_manager import UIManager
from pygame_gui.windows import UIFileDialog

from Maze.Common.board import Board
from Maze.Common.gem import Gem
from Maze.Common.tile import Direction, Tile
from Maze.Common.state import GameState, PlayerState
from Maze.Common.utils import Coord, StreamQueue
from Maze.Referee.observer import Observer
from Maze.Referee.view import UIApp, UIAppFactory, UIState
from Maze.Resources import get_path_to_resource

BACKGROUND_COLOR = Color(0, 0, 0)
TILE_WIDTH = 64
TILE_HEIGHT = 64
TILE_SIZE = Vector2(TILE_WIDTH, TILE_HEIGHT)
TILE_ROAD_WIDTH = 11
TILE_BORDER_WIDTH = 2
TILE_BORDER_COLOR = Color(90, 90, 90)
TILE_BACKGROUND = Color(150, 150, 150)
TILE_ROAD = Color(255, 255, 255)
BUTTON_BORDER_RADIUS = 4
AVATAR_RADIUS = 12
GEM_WIDTH = 18
GEM_HEIGHT = 18
PLAYER_HOME_WIDTH = 24
PLAYER_HOME_HEIGHT = 24
EVENT_LOOP_MIN_SLEEP = 0.001
TARGET_FRAME_DURATION = 1 / 60


# Notes about Pygame coordinate system
# - a Vector2 is an (x, y) pair -- if used as a position or size, it is measured in pixels
# - `x` is 0 at the left edge of a Surface and increases to the right
# - `y` is 0 at the top edge of a Surface and increases downwards
# - a Rect is constructed from a (left_x, top_y) and (width, height), which can each be
#   a Vector2 or Tuple[int, int]


class UITile:
    """Display component for a fixed position on the board."""

    rect: Rect
    ui_manager: UIManager

    def __init__(self, rect: Rect, ui_manager: UIManager):
        """Creates a tile with a given position and size."""
        self.rect = rect
        self.ui_manager = ui_manager

    @staticmethod
    def quadrant_center(left: bool, top: bool) -> Vector2:
        """Returns the center of a quadrant within the rect with `pos = (0, 0)` and
        `size = (TILE_WIDTH, TILE_HEIGHT)`.

        Args:
            left (bool): True to choose a quadrant on the left half of the tile
            top (bool): True to choose a quadrant on the top half of the tile
        """
        relative_x = 0.25 if left else 0.75
        relative_y = 0.25 if top else 0.75
        return Vector2(relative_x, relative_y) * TILE_SIZE.elementwise()

    @staticmethod
    def centered_quadrant_rect(size: Vector2, left: bool, top: bool) -> Rect:
        """Returns the rect with size `size`, centered on `quadrant_center(left, top)`.

        Args:
            size (Vector2): The size of the requested Rect.
            left (bool): True to choose a quadrant on the left half of the tile
            top (bool): True to choose a quadrant on the top half of the tile
        """
        result_pos = UITile.quadrant_center(left, top) - 0.5 * size
        return Rect(result_pos, size)

    def draw_background(self, surface: Surface) -> None:
        """Draws a gray rectangle on `surface` covering this UITile's rect."""
        color = TILE_BACKGROUND
        pygame.draw.rect(surface, color, self.rect)

    def draw_border(self, surface: Surface) -> None:
        """Draws a dark gray outline around the edges of this UITile's rect."""
        corners = [
            self.rect.topleft,
            self.rect.topright,
            self.rect.bottomright,
            self.rect.bottomleft,
        ]
        pygame.draw.lines(
            surface,
            TILE_BORDER_COLOR,
            closed=True,
            points=corners,
            width=TILE_BORDER_WIDTH,
        )

    def draw_roads(self, surface: Surface, tile: Tile) -> None:
        """Draws the paths of `tile` on `surface` in white."""
        color = TILE_ROAD
        center = Vector2(self.rect.center)
        mid_west = (self.rect.left, self.rect.centery)
        mid_east = (self.rect.right, self.rect.centery)
        mid_north = (self.rect.centerx, self.rect.top)
        mid_south = (self.rect.centerx, self.rect.bottom)
        directions = tile.connected_directions()
        if Direction.LEFT in directions:
            pygame.draw.line(surface, color, center, mid_west, width=TILE_ROAD_WIDTH)
        if Direction.RIGHT in directions:
            pygame.draw.line(surface, color, center, mid_east, width=TILE_ROAD_WIDTH)
        if Direction.UP in directions:
            pygame.draw.line(surface, color, center, mid_north, width=TILE_ROAD_WIDTH)
        if Direction.DOWN in directions:
            pygame.draw.line(surface, color, center, mid_south, width=TILE_ROAD_WIDTH)
        center_road_size = Vector2(TILE_ROAD_WIDTH, TILE_ROAD_WIDTH)
        center_road_pos = (center - 0.5 * center_road_size) + Vector2(1, 1)
        pygame.draw.rect(surface, color, (center_road_pos, center_road_size))

    def get_gem_image_surface(self, gem: Gem) -> Surface:
        """Creates a surface with the given gem drawn on it."""
        surface_cache = self.ui_manager.ui_theme.shape_cache
        cached = surface_cache.find_surface_in_cache(gem.value)
        if cached is not None:
            return cached
        gem_path = get_path_to_resource(f"{gem.value}.png")
        gem_image_surface = pygame.image.load(gem_path).convert_alpha()
        gem_image_surface = pygame.transform.scale(gem_image_surface, (GEM_WIDTH, GEM_HEIGHT))
        surface_cache.add_surface_to_cache(gem_image_surface, gem.value)
        return gem_image_surface

    def draw_gem(self, surface: Surface, gem: Gem, left: bool, top: bool) -> None:
        """Draws `gem` on `surface` in the quadrant indicated by `top` and `left`"""
        gem_size = Vector2(GEM_WIDTH, GEM_HEIGHT)
        gem_rect = self.centered_quadrant_rect(gem_size, left, top)
        # Moves the rect by the offset for this tile
        gem_rect = gem_rect.move(self.rect.topleft)
        surface.blit(self.get_gem_image_surface(gem), gem_rect.topleft)

    def render(self, surface: Surface, tile: Tile) -> None:
        """Draws `tile` on `surface`."""
        self.draw_background(surface)
        self.draw_roads(surface, tile)
        self.draw_border(surface)
        # gems; center 1st on the center of the top-left quadrant and 2nd on bottom-right
        self.draw_gem(surface, tile.gems[0], top=True, left=True)
        self.draw_gem(surface, tile.gems[1], top=False, left=False)


class UIBoard:
    """Display component for a Labyrinth board."""

    container: UIImage
    ui_manager: UIManager

    def __init__(self, container: UIImage, ui_manager: UIManager):
        """Creates a board which draws itself on `container`."""
        self.container = container
        self.ui_manager = ui_manager

    def render(self, game_state: GameState) -> None:
        """Draws the tiles, homes, avatars, and goals of `game_state`.

        Note:
            TODO: Display homes side by side when there are multiple on the same tile;
                same with avatars; goals are borders, so they should be concentric
        """
        surface = cast(Surface, self.container.image)
        self.draw_tiles(surface, game_state.board)
        self.draw_player_homes(surface, game_state.player_states.values())
        self.draw_player_avatars(surface, game_state.player_states.values())
        self.draw_player_goals(surface, game_state)

    def draw_tiles(self, surface: Surface, board: Board) -> None:
        """Draws all tiles of `board` onto `surface`."""
        for col in range(board.width):
            for row in range(board.height):
                tile = board.get_tile(Coord(col, row))
                tile_pos = UIBoard.get_tile_top_left(Coord(col, row))
                UITile(Rect(tile_pos, TILE_SIZE), self.ui_manager).render(surface, tile)

    def draw_player_homes(self, surface: Surface, player_states: Iterable[PlayerState]) -> None:
        """Draws all player homes from `player_states` onto `surface`."""
        home_size = Vector2(PLAYER_HOME_WIDTH, PLAYER_HOME_HEIGHT)
        for player in player_states:
            home_rect = UITile.centered_quadrant_rect(home_size, top=False, left=True)
            # Moves the rect by the offset for this tile
            home_rect = home_rect.move(UIBoard.get_tile_top_left(player.home_location))
            pygame.draw.rect(surface, Color(player.color), home_rect)

    def draw_player_avatars(self, surface: Surface, player_states: Iterable[PlayerState]) -> None:
        """Draws all player avatars from `player_states` onto `surface`."""
        for player in player_states:
            center = (
                # The player avatars are displayed in the top-right quarter
                UIBoard.get_tile_top_left(player.location)
                + UITile.quadrant_center(top=True, left=False)
            )
            pygame.draw.circle(surface, Color(player.color), center, AVATAR_RADIUS)

    def draw_player_goals(self, surface: Surface, game_state: GameState) -> None:
        """Draws player goals from `game_state` onto `surface`.

        Note:
            If the implementation of `game_state` prevents reading some secrets,
            those players' goals will not be retrieved or drawn.
        """
        for color in game_state.player_colors:
            if not game_state.can_get_player_secret(color):
                continue
            secret = game_state.get_player_secret(color)
            color = game_state.player_states[color].color
            tile_rect = Rect(
                UIBoard.get_tile_top_left(secret.treasure_location),
                (TILE_WIDTH, TILE_HEIGHT),
            )
            pygame.draw.rect(surface, Color(color), tile_rect, width=TILE_BORDER_WIDTH)

    @staticmethod
    def get_tile_top_left(pos: Coord) -> Vector2:
        """Calculates the pixel location of the top left corner of a tile given its position."""
        tile_pos = Vector2(pos.col, pos.row) * TILE_SIZE.elementwise()
        return tile_pos


class UILabyrinth:
    """The top-level UI element for observing a Labryinth game.

    The layout is arranged like this (dimensions are in "tile" units)
    ```ascii
    |0.5|   W   |1|   1   |0.5|
    |   +-------+             |_
    |   | board |  [spare]    |_  1
    |   |       |             |_  1
    |   |       |  [ next]    |_  0.5
    |   |       |             |_  0.5
    |   |       |  [ save]    |_  0.5
    ```
    """

    ui_manager: UIManager
    board: UIBoard
    spare_tile: UITile
    spare_tile_image: UIImage
    next_button: UIButton
    save_button: UIButton

    @staticmethod
    def calculate_size(initial_state: UIState) -> Tuple[int, int]:
        """Calculate the size of the window needed to display all UI elements with appropriate padding."""
        board = initial_state.game_state.board
        px_width = (board.width + 3) * TILE_WIDTH
        px_height = (board.height + 1) * TILE_HEIGHT
        return px_width, px_height

    @staticmethod
    def board_rect(board: Board) -> Rect:
        """Positions and sizes `board`."""
        board_size = Vector2(board.width, board.height) * TILE_SIZE.elementwise()
        ui_origin = 0.5 * TILE_SIZE
        return Rect(ui_origin, board_size)

    @staticmethod
    def spare_tile_rect() -> Rect:
        """Positions and sizes the spare tile element, relative to the top-right corner."""
        result = Rect((0, 0), TILE_SIZE)
        result = result.move((0, TILE_HEIGHT / 2))  # top padding
        # make right equal to anchor `x`, then add padding
        result = result.move((-result.width - TILE_WIDTH / 2, 0))
        return result

    @staticmethod
    def button_rect(which: int) -> Rect:
        """Positions and sizes a button element, relative to the top-right corner.

        Args:
            which (int): The index of the button - the topmost is 0, then 1, etc.
        """
        result = Rect((0, 0), (TILE_WIDTH, TILE_HEIGHT / 2))
        # top padding, spare tile, padding btwn spare & first button
        result = result.move((0, TILE_HEIGHT * (0.5 + 1 + 0.5 + which)))
        # make right equal to anchor `x`, then add padding
        result = result.move((-result.width - TILE_WIDTH / 2, 0))
        return result

    def __init__(self, ui_manager: UIManager, initial_state: UIState):
        """Initializes the Labyrinth window.

        Note:
            1. Sets up the child UI elements for board, spare tile, buttons, and file picking dialog.
            2. Renders the initial state in the window.
        """
        self.ui_manager = ui_manager
        board_rect = UILabyrinth.board_rect(initial_state.game_state.board)
        board_image_element = UIImage(
            relative_rect=UILabyrinth.board_rect(initial_state.game_state.board),
            image_surface=Surface(board_rect.size).convert(),
            manager=ui_manager,
        )
        self.board = UIBoard(board_image_element, ui_manager)

        self.spare_tile = UITile(Rect((0, 0), TILE_SIZE), self.ui_manager)
        # anchor the right image edge to the right edge of the screen, same w top/top
        self.spare_tile_image = UIImage(
            relative_rect=UILabyrinth.spare_tile_rect(),
            image_surface=Surface(TILE_SIZE).convert(),
            manager=ui_manager,
            anchors={"top": "top", "right": "right"},
        )
        self.next_button = UIButton(
            relative_rect=UILabyrinth.button_rect(0),
            text="Next",
            manager=ui_manager,
            anchors={"top": "top", "right": "right"},
        )
        self.save_button = UIButton(
            relative_rect=UILabyrinth.button_rect(1),
            text="Save",
            manager=ui_manager,
            anchors={"top": "top", "right": "right"},
        )

        # file_dialog is None to indicate that one needs to be created
        # we considered using pygame's .kill() to replace setting to None and
        # .is_alive() to replace checking for None, but that seemed more confusing
        self.file_dialog = None
        self.render(initial_state)

    def render(self, state: UIState) -> None:
        """Draws the board, spare tile, and UI buttons; shows/hides the file dialog."""
        self.board.render(state.game_state)
        self.spare_tile.render(self.spare_tile_image.image, state.game_state.spare_tile)
        if state.enable_next_button:
            self.next_button.enable()
        else:
            self.next_button.disable()
        if state.show_file_dialog:
            if self.file_dialog is None:
                self.file_dialog = UIFileDialog(
                    Rect((0, 0), self.ui_manager.get_root_container().get_size()),
                    self.ui_manager,
                    window_title="Choose location for output",
                    allow_picking_directories=False,
                    allow_existing_files_only=False,
                )
        else:
            if self.file_dialog is not None:
                self.file_dialog.kill()
                self.file_dialog = None


class PygameUIApp(UIApp):
    """A view for a Labyrinth game.

    The user of this view can step through the game states and save the current state
    to a file.
    """

    is_running: bool
    background: Surface
    display_surface: Surface
    update_queue: StreamQueue[UIState]
    ui_manager: UIManager
    labyrinth_window: UILabyrinth
    initial_state: UIState

    def __init__(self, initial_state: UIState):
        """Initializes the GUI app's update queue, and renders `initial_state`."""
        self.is_running = False
        self.update_queue = StreamQueue(asyncio.Queue(16))
        self.initial_state = initial_state
        self._setup()

    def _setup(self) -> None:
        """Creates a desktop window and the UILabyrinth for this app."""
        pygame.init()
        window_size = UILabyrinth.calculate_size(self.initial_state)
        self.display_surface = pygame.display.set_mode(window_size, flags=pygame.HWSURFACE | pygame.RESIZABLE)
        self.background = Surface(window_size)
        self.background.fill(BACKGROUND_COLOR)
        self.ui_manager = UIManager(window_size)
        self.labyrinth_window = UILabyrinth(self.ui_manager, self.initial_state)

    async def push_state(self, ui_state: UIState) -> None:
        """Enqueues `ui_state` to be rendered."""
        await self.update_queue.put(ui_state)

    async def _event_loop(
        self,
    ) -> AsyncIterator[Tuple[float, List[PygameEvent], List[UIState]]]:
        """Attempts to send the consumer a chunk of events every `TARGET_FRAME_DURATION` seconds.

        One chunk of events is (time_delta, pygame_events, ui_states). The `time_delta` is
        the number of seconds since the previous chunk of events was sent, or 0 in the case
        of the first one.
        """
        prev_time = time.time()
        while self.is_running:
            ui_events = pygame.event.get()
            referee_events = self.update_queue.get()
            curr_time = time.time()
            wait_time = max(
                EVENT_LOOP_MIN_SLEEP,
                prev_time + TARGET_FRAME_DURATION - curr_time,
            )
            yield curr_time - prev_time, ui_events, referee_events
            # prev_time is the last time we sent a chunk of events
            prev_time = curr_time
            await asyncio.sleep(wait_time)

    async def run(self, observer: "Observer") -> None:
        """Displays the UI, and responds to events.

        Args:
            observer (Observer): The controller of this view.
        """
        self.is_running = True
        state = self.initial_state
        async for time_delta, ui_events, referee_events in self._event_loop():
            for ui_state in referee_events:
                state = ui_state
                self.labyrinth_window.render(ui_state)
            for ui_event in ui_events:
                # Built-in event types - https://www.pygame.org/docs/ref/event.html
                # ...
                # MOUSEBUTTONDOWN   pos, button, touch
                self.ui_manager.process_events(ui_event)
                if ui_event.type == pygame_gui.UI_BUTTON_PRESSED:
                    if ui_event.ui_element == self.labyrinth_window.next_button:
                        await self._on_next_button_clicked(observer, state)
                    elif ui_event.ui_element == self.labyrinth_window.save_button:
                        await self._on_save_button_clicked(observer, state)
                elif ui_event.type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
                    await self._on_save_location_selected(observer, state, ui_event.text)
                elif ui_event.type == pygame_gui.UI_WINDOW_CLOSE:
                    if ui_event.ui_element == self.labyrinth_window.file_dialog:
                        await self._on_file_dialog_closed(observer, state)
                elif ui_event.type == pygame.QUIT:
                    self.is_running = False

            self.ui_manager.update(time_delta)
            self.display_surface.blit(self.background, (0, 0))
            self.ui_manager.draw_ui(self.display_surface)
            pygame.display.update()

        pygame.quit()

    async def _on_next_button_clicked(self, observer: "Observer", state: UIState) -> None:
        """Advances to the next state, if possible."""
        if observer._can_go_to_next():
            await observer._go_to_next()

    async def _on_save_button_clicked(self, observer: "Observer", state: UIState) -> None:
        """Shows the file dialog."""
        await self.push_state(UIState(state.game_state, state.enable_next_button, show_file_dialog=True))

    async def _on_file_dialog_closed(self, observer: "Observer", state: UIState) -> None:
        """Hides the file dialog."""
        await self.push_state(UIState(state.game_state, state.enable_next_button, show_file_dialog=False))

    async def _on_save_location_selected(self, observer: "Observer", state: UIState, filename: str) -> None:
        """Hides the file dialog and saves to the selected file."""
        await self.push_state(UIState(state.game_state, state.enable_next_button, False))
        observer._save_to_file(filename)


class PygameUIAppFactory(UIAppFactory):
    """Implementation for a GameState -> UIApp function."""

    def create(self, initial_state: UIState) -> UIApp:
        """Creates a UIApp for the initial state."""
        return PygameUIApp(initial_state)
