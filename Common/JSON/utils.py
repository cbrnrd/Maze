"""Conversion functions for JSON structures which don't correspond directly to our chosen
representations."""

from typing import Tuple

from typing_extensions import assert_never

from Maze.Common.tile import Direction
from Maze.Common.utils import Coord


def calculate_insert_location(index: int, direction: Direction, board_width: int, board_height: int) -> Coord:
    """Calculates the insert location for a tile shift at row/column `index` in `direction`.

    Args:
        index (int): The row or column index; row if direction is horizontal, column otherwise.
        direction (Direction): The direction to shift tiles
        board_width (int): The width of the board the insert and shift will be performed on
        board_height (int): The height of the board the insert and shift will be performed on
    """
    if direction is Direction.LEFT:
        # horizontal shift === index represents row
        return Coord(board_width - 1, index)
    if direction is Direction.RIGHT:
        return Coord(0, index)
    if direction is Direction.UP:
        return Coord(index, board_height - 1)
    if direction is Direction.DOWN:
        return Coord(index, 0)
    assert_never(direction)


def order_coords_by_row_column(coord: Coord) -> Tuple[int, int]:
    """Computes a key to sort the given `coord` in row-column order."""
    column, row = coord.col, coord.row
    return (row, column)
