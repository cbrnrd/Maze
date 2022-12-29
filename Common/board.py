"""The board representation for Labyrinth on Maze.com."""

from typing import Any, Dict, Iterator, List, Set, Tuple

from Maze.Common.tile import Direction, Tile
from Maze.Common.utils import Coord


class ShiftNotAllowedError(Exception):
    """Shifting this row or column is not allowed by Labyrinth rules."""


class BoardEdit:
    """A standard record for coordinate edits."""

    # Every entry in this map represents a move from the key coordinates to the value
    # coordinates
    replacements: Dict[Coord, Coord]

    # The tiles which were at the coordinates in this set were removed from the board
    deletions: Set[Coord]

    def __init__(self, replacements: Dict[Coord, Coord], deletions: Set[Coord]):
        """Combines information about an atomic group of coordinate edits."""
        self.replacements = replacements
        self.deletions = deletions


class Board:
    """A board for Labyrinth."""

    # Invariant: tiles is always full (i.e. all keys in the width x height rectangle are present)
    tiles: Dict[Coord, Tile]
    width: int
    height: int

    def __init__(self, tiles: Dict[Coord, Tile], width: int, height: int):
        """Creates a board with the specified tiles, width, and height.

        Args:
            tiles (Dict[Coord, Tile]): A map from positions to `Tiles`
            width (int): A positive integer
            height (int): A positive integer

        Raises:
            ValueError: If `width` is not positive or `height` is not positive
            ValueError: If keys outside of 0..width × 0..height are present
            ValueError: If any key in 0..width × 0..height is missing
            ValueError: If any two Tiles have the same gem pair (unordered)
        """
        if width <= 0 or height <= 0:
            raise ValueError("Invalid board shape")
        missing_keys = Board._count_missing_keys(tiles, width, height)
        if missing_keys > 0:
            raise ValueError(f"Expected full tile grid, got {missing_keys} holes")
        if len(tiles) + missing_keys > width * height:
            raise ValueError("Extra keys encountered")
        Board.validate_tile_gems(list(tiles.values()))

        self.tiles = tiles
        self.width = width
        self.height = height

    @staticmethod
    def _count_missing_keys(tiles: Dict[Coord, Tile], width: int, height: int) -> int:
        """Counts the missing keys in the rectangle [0, width) × [0, height) not present in `tiles`.

        Args:
            tiles (Dict[Coord, Tile]): A map from positions to `Tiles`
            width (int): A positive integer
            height (int): A positive integer
        """
        missing_keys = 0
        for x in range(width):
            for y in range(height):
                if Coord(x, y) not in tiles:
                    missing_keys += 1
        return missing_keys

    @staticmethod
    def validate_tile_gems(tiles: List[Tile]) -> None:
        """Checks that all `tiles` have a unique pair of gems.

        Raises:
            ValueError: If any two Tiles have the same (unordered) gem pair
        """
        gem_set = set([tile.gems for tile in tiles])
        if len(gem_set) != len(tiles):
            raise ValueError("Non-unique gems present on board")

    def with_tiles(self, new_tiles: Dict[Coord, Tile]) -> "Board":
        """Creates a copy of this board with a new arrangement of tiles."""
        return Board(new_tiles, self.width, self.height)

    def is_moveable_row_or_column(self, which_index: int) -> bool:
        """Checks whether the given row or column index is a moveable row or column."""
        return which_index % 2 == 0

    def get_all_fixed_tiles(self) -> List[Coord]:
        fixed_tiles = []
        for row in range(self.height):
            if not self.is_moveable_row_or_column(row):
                for col in range(self.width):
                    if not self.is_moveable_row_or_column(col):
                        fixed_tiles.append(Coord(col, row))
        return fixed_tiles

    def get_valid_insert_locations(self, direction: Direction) -> Set[Coord]:
        """Returns the valid locations for a shift-and-insert operation in `direction`."""
        # to slide up, need to insert on bottom edge; same for left and right
        if direction.is_vertical:
            row = 0 if direction is Direction.DOWN else (self.height - 1)
            if not self.is_moveable_row_or_column(row):
                # This is a guard in case we ever need to have even-width or height boards,
                # or the every-other-row/column rule changes
                return set()
            return {Coord(col, row) for col in range(self.width) if self.is_moveable_row_or_column(col)}
        else:
            col = 0 if direction is Direction.RIGHT else (self.width - 1)
            if not self.is_moveable_row_or_column(col):
                return set()
            return {Coord(col, row) for row in range(self.height) if self.is_moveable_row_or_column(row)}

    def assert_valid_shift_and_insert(self, which_coord: Coord, direction: Direction) -> None:
        """Checks that inserting at `which_coord` and shifting in `direction` is valid.

        Raises:
            IndexError: If the given position is out of bounds
            ValueError: If the given position is not on the edge of the board
            ShiftNotAllowedError: If the given position is on a fixed row or column
        """
        self.assert_in_bounds(which_coord)
        if not (self.is_moveable_row_or_column(which_coord.col) and self.is_moveable_row_or_column(which_coord.row)):
            raise ShiftNotAllowedError(f"Position {(which_coord.col, which_coord.row)} is fixed")

        if which_coord not in self.get_valid_insert_locations(direction):
            raise ValueError(f"Can't slide {direction.value} from {which_coord.col}, {which_coord.row}")

    def _slide_row(self, which_row: int, direction: Direction) -> Tuple[Dict[Coord, Tile], Tile, BoardEdit]:
        """Slides the given row in the given direction, dropping one tile off the board.

        Args:
            which_row (int): The row to slide
            direction (Direction): The direction to move (LEFT or RIGHT)

        Returns:
            Tuple[Dict[Coord, Tile], Tile, BoardEdit]: (The new tiles, the tile that was dropped,
                the coordinate operations that a tracking class should do)
        """
        if direction is Direction.LEFT:
            dropped_coord = Coord(0, which_row)
        else:
            dropped_coord = Coord(self.width - 1, which_row)
        dx = direction.dx
        coord_replacements = {
            Coord(x, which_row): Coord(x + dx, which_row) for x in range(self.width) if 0 <= x + dx < self.width
        }
        new_tiles = {
            coord_replacements.get(coord, coord): tile for (coord, tile) in self.tiles.items() if coord != dropped_coord
        }
        board_edit = BoardEdit(coord_replacements, {dropped_coord})
        return new_tiles, self.tiles[dropped_coord], board_edit

    def _slide_column(self, which_col: int, direction: Direction) -> Tuple[Dict[Coord, Tile], Tile, BoardEdit]:
        """Slides the given column in the given direction, dropping one tile off the board.

        Args:
            which_col (int): The column to slide
            direction (Direction): The direction to move (UP or DOWN)

        Returns:
            Tuple[Dict[Coord, Tile], Tile, BoardEdit]: (The new tiles, the tile that was dropped,
                the coordinate operations that a tracking class should do)
        """
        if direction is Direction.UP:
            dropped_coord = Coord(which_col, 0)
        else:
            dropped_coord = Coord(which_col, self.height - 1)
        dy = direction.dy
        coord_replacements = {
            Coord(which_col, y): Coord(which_col, y + dy) for y in range(self.height) if 0 <= y + dy < self.height
        }
        new_tiles = {
            coord_replacements.get(coord, coord): tile for (coord, tile) in self.tiles.items() if coord != dropped_coord
        }
        board_edit = BoardEdit(coord_replacements, {dropped_coord})
        return new_tiles, self.tiles[dropped_coord], board_edit

    def slide_and_insert_tile(
        self, which_coord: Coord, direction: Direction, tile: Tile
    ) -> Tuple["Board", Tile, BoardEdit]:
        """Shift a row or column in `direction` by inserting `tile` at `which_coord`.

        Raises:
            IndexError: If the given position is out of bounds
            ValueError: If the given position is not on the edge of the board
            ShiftNotAllowedError: If the given position is on a fixed row or column

        Returns:
            Tuple[Board, Tile, BoardEdit]: (The new board, the tile that was dropped,
                the coordinate operations that a tracking class should do)
        """
        self.assert_valid_shift_and_insert(which_coord, direction)

        if direction.is_vertical:
            new_tiles, new_spare, edit = self._slide_column(which_coord.col, direction)
        else:
            new_tiles, new_spare, edit = self._slide_row(which_coord.row, direction)

        new_tiles[which_coord] = tile
        return self.with_tiles(new_tiles), new_spare, edit

    def _adjacent_tiles(self, which_coord: Coord) -> Iterator[Tuple[Direction, Coord]]:
        """Generates the tiles adjacent to `which_coord`

        Args:
            which_coord (Coord): The coordinate to search from

        Yields:
            Iterator[Tuple[Direction, Coord]]: The (direction, position) pairs which the
                given tile can reach traveling "outwards".
        """
        current_tile = self.tiles.get(which_coord)
        if current_tile is None:
            return
        for direction in current_tile.connected_directions():
            other_row = which_coord.row + direction.dy
            other_col = which_coord.col + direction.dx
            other_coord = Coord(other_col, other_row)
            if other_coord in self.tiles:
                yield (direction, other_coord)

    def _neighbors(self, which_coord: Coord) -> Iterator[Coord]:
        """Gets the coordinates of the reachable immediate neighbors of a cell.

        Args:
            which_coord (Coord): The coordinate of the cell

        Yields:
            Iterator[Coord]: Coordinates for the cell's reachable neighbors
        """
        # Loop through reachable points traveling out on own tile's roads
        # If the adjacent tile can reach this one on *its* roads, that tile is a neighbor
        for direction, coordinates in self._adjacent_tiles(which_coord):
            opposite_dir = direction.flip()
            other_tile = self.tiles[coordinates]
            if opposite_dir in other_tile.connected_directions():
                yield coordinates

    def reachable_destinations(self, start_coord: Coord) -> Set[Coord]:
        """Gets the coordinates of all reachable tiles starting from the given cell.

        Args:
            start_coord (Coord): The coordinate of the given cell

        Raises:
            IndexError: If `start_coord` is out of bounds for this board
        """
        self.assert_in_bounds(start_coord)

        # Stack of unexplored positions
        frontier: List[Coord] = [start_coord]
        # Explored positions
        reachable: Set[Coord] = set()
        # Positions in stack to be explored (+ explored positions)
        seen: Set[Coord] = set()

        # Depth-first search the board and collect all reachable positions
        # The search will always terminate because no position can be added to `frontier`
        # more than once
        while len(frontier) > 0:
            current = frontier.pop()
            reachable.add(current)
            for neighbor in self._neighbors(current):
                if neighbor not in reachable and neighbor not in seen:
                    frontier.append(neighbor)
                    seen.add(neighbor)

        return reachable

    def get_tile(self, which_coord: Coord) -> Tile:
        """Gets the tile at the given position.

        Args:
            which_coord (Coord): The coordinate of the given cell

        Raises:
            IndexError: If `which_coord` is out of bounds for this board
        """
        self.assert_in_bounds(which_coord)
        return self.tiles[which_coord]

    def assert_in_bounds(self, which_coord: Coord) -> None:
        """Checks that the given position is on the board's `width × height` rectangle.

        Raises:
            IndexError: If the position is out of bounds
        """
        if not (0 <= which_coord.col < self.width):
            raise IndexError(f"Column out of bounds: {which_coord.col}")
        if not (0 <= which_coord.row < self.height):
            raise IndexError(f"Row out of bounds: {which_coord.row}")

    def __eq__(self, other: Any) -> bool:
        """Tests whether this board is equivalent to `other`."""
        if not isinstance(other, Board):
            return False
        return (self.tiles == other.tiles) and (self.width == other.width) and (self.height == other.height)
