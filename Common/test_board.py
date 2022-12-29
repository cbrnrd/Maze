# pylint: disable=missing-function-docstring,missing-module-docstring,protected-access
import itertools
import unittest
from typing import Dict, List, Tuple

from Maze.Common.board import Board, ShiftNotAllowedError
from Maze.Common.gem import Gem
from Maze.Common.test_tile import default_gems
from Maze.Common.tile import Direction, Tile, TileShape
from Maze.Common.utils import Coord

all_treasures = list(Gem.unordered_pairs())


def list_replace(lst, index, item):
    return [*lst[:index], item, *lst[index + 1 :]]


def list_insert(lst, index, item):
    return [*lst[:index], item, *lst[index:]]


def list_delete(lst, index):
    return [*lst[:index], *lst[index + 1 :]]


def canonize(tile_shape_char: str) -> Tuple[TileShape, int]:
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
    return table[tile_shape_char]


def tile_to_unicode(tile: Tile) -> str:
    table = {
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


def ascii_tiles(*lines, treasures=all_treasures) -> Dict[Coord, Tile]:
    result = {}
    for y, line in enumerate(lines):
        if len(line) != len(lines[0]):
            raise ValueError("Board must be perfectly rectangular")
        for x, character in enumerate(line):
            # space signifies a hole
            if character != " ":
                shape, rotation = canonize(character)
                gem1, gem2 = treasures[y * len(line) + x]
                result[Coord(x, y)] = Tile(shape, rotation, (gem1, gem2))
    return result


def board_to_ascii(board: Board) -> List[str]:
    result = []
    for row in range(board.height):
        acc = ""
        for col in range(board.width):
            acc += tile_to_unicode(board.get_tile(Coord(col, row)))
        result.append(acc)
    return result


def ascii_board(*lines, treasures=all_treasures) -> Board:
    return Board(ascii_tiles(*lines, treasures=treasures), width=len(lines[0]), height=len(lines))


class TestBoard(unittest.TestCase):
    """Tests for the `Board` class."""

    ### copy-paste bank
    ###
    ### │─ ### └┌┐┘ ### ┬┤┴├ ### ┼
    ###

    def test_invalid_dimensions_board(self):
        self.assertRaises(ValueError, lambda: Board({}, -1, -1))
        self.assertRaises(ValueError, lambda: Board({}, 0, 7))
        self.assertRaises(ValueError, lambda: Board({}, 7, 0))

    def test_extra_tiles_board(self):
        normal_tiles = ascii_tiles(
            # 1
            "┘└",  # 0
            "┐┌",  # 1
        )
        overflowing_tiles = {
            **normal_tiles,
            Coord(1, 2): Tile(TileShape.LINE, 0, default_gems),
        }
        self.assertRaises(ValueError, lambda: Board(overflowing_tiles, 2, 2))

    def test_missing_tile_board(self):
        too_few_tiles = ascii_tiles(
            # 1
            "┘└",  # 0
            "┐ ",  # 1
        )
        self.assertRaises(ValueError, lambda: Board(too_few_tiles, 2, 2))

    def test_missing_tiles_board(self):
        too_few_tiles = ascii_tiles(
            # 1
            "┘└",  # 0
            "  ",  # 1
        )
        self.assertRaises(ValueError, lambda: Board(too_few_tiles, 2, 2))

    def test_nonunique_gems_board(self):
        nonunique_gem_tiles = ascii_tiles(
            # 1
            "┘└",  # 0
            "┐┌",  # 1
            treasures=[
                (Gem.ALEXANDRITE, Gem.AMETHYST),
                (Gem.ALEXANDRITE, Gem.AMETHYST),
                (Gem.ALEXANDRITE, Gem.APLITE),
                (Gem.ALEXANDRITE, Gem.APATITE),
            ],
        )
        self.assertRaises(ValueError, lambda: Board(nonunique_gem_tiles, 2, 2))

    def test_validate_tile_gems(self):
        self.assertRaises(
            ValueError,
            lambda: Board.validate_tile_gems(
                [
                    Tile(TileShape.LINE, 0, default_gems),
                    Tile(TileShape.LINE, 0, default_gems),
                ]
            ),
        )

    def test_reachable_destinations_on_fully_connected_board(self):
        board = ascii_board(
            # 123456
            "┌┬┬┬┬┬┐",  # 0
            "├┼┼┼┼┼┤",
            "├┼┼┼┼┼┤",  # 2
            "├┼┼┼┼┼┤",
            "├┼┼┼┼┼┤",  # 4
            "├┼┼┼┼┼┤",
            "└┴┴┴┴┴┘",  # 6
        )
        self.assertEqual(board.width, 7)
        self.assertEqual(board.height, 7)
        every_position = set(itertools.product(range(7), range(7)))
        every_position = set(map(lambda t: Coord(t[0], t[1]), every_position))
        for pos in sorted(every_position):
            # can reach any tile
            self.assertEqual(board.reachable_destinations(pos), every_position)
        self.assertRaises(IndexError, lambda: board.reachable_destinations(Coord(0, -1)))
        self.assertRaises(IndexError, lambda: board.reachable_destinations(Coord(7, 0)))

    def test_reachable_destinations_on_unconnected_board(self):
        board = ascii_board(
            # 1
            "┘└",  # 0
            "┐┌",  # 1
        )
        self.assertEqual(board.width, 2)
        self.assertEqual(board.height, 2)
        every_position = {Coord(0, 0), Coord(0, 1), Coord(1, 0), Coord(1, 1)}
        for pos in sorted(every_position):
            # can only reach self
            self.assertEqual(board.reachable_destinations(pos), {pos})

    def test_reachable_destinations_on_all_vertical_board(self):
        board = ascii_board(
            # 123
            "││││",  # 0
            "││││",  # 1
            "││││",  # 2
            "││││",  # 3
        )
        self.assertEqual(board.width, 4)
        self.assertEqual(board.height, 4)
        every_position = set(itertools.product(range(4), range(4)))
        every_position = set(map(lambda t: Coord(t[0], t[1]), every_position))
        for pos in sorted(every_position):
            # can only reach own column
            own_column = {c for c in every_position if c.col == pos.col}
            self.assertEqual(board.reachable_destinations(pos), own_column)

    def test_get_all_fixed_tiles(self):
        board = ascii_board(
            # 1234
            "┌┬┬┬┐",  # 0
            "├┼┼┼┤",
            "├┼┼┼┤",  # 2
            "├┼┼┼┤",
            "└┴┴┴┘",  # 4
        )
        self.assertEqual(
            board.get_all_fixed_tiles(),
            [Coord(1, 1), Coord(3, 1), Coord(1, 3), Coord(3, 3)],
        )

    def test_get_valid_insert_locations(self):
        board = ascii_board(
            # 1234
            "┌┬┬┬┐",  # 0
            "├┼┼┼┤",
            "├┼┼┼┤",  # 2
            "├┼┼┼┤",
            "└┴┴┴┘",  # 4
        )
        self.assertEqual(
            board.get_valid_insert_locations(Direction.RIGHT),
            {Coord(0, 0), Coord(0, 2), Coord(0, 4)},
        )
        self.assertEqual(
            board.get_valid_insert_locations(Direction.LEFT),
            {Coord(4, 0), Coord(4, 2), Coord(4, 4)},
        )
        self.assertEqual(
            board.get_valid_insert_locations(Direction.DOWN),
            {Coord(0, 0), Coord(2, 0), Coord(4, 0)},
        )
        self.assertEqual(
            board.get_valid_insert_locations(Direction.UP),
            {Coord(0, 4), Coord(2, 4), Coord(4, 4)},
        )

    def test_slide_and_insert_tile_invalid(self):
        board = ascii_board(
            # 123456
            "┌┬┬┬┬┬┐",  # 0
            "├┼┼┼┼┼┤",
            "├┼┼┼┼┼┤",  # 2
            "├┼┼┼┼┼┤",
            "├┼┼┼┼┼┤",  # 4
            "├┼┼┼┼┼┤",
            "└┴┴┴┴┴┘",  # 6
        )
        spare_tile = Tile(TileShape.LINE, 1, default_gems)
        self.assertEqual(board.width, 7)
        self.assertEqual(board.height, 7)
        # out of bounds
        self.assertRaises(
            IndexError,
            lambda: board.slide_and_insert_tile(Coord(-1, -1), Direction.UP, spare_tile),
        )
        self.assertRaises(
            IndexError,
            lambda: board.slide_and_insert_tile(Coord(7, 7), Direction.UP, spare_tile),
        )
        # left edge, upward shift
        self.assertRaises(
            ValueError,
            lambda: board.slide_and_insert_tile(Coord(0, 2), Direction.UP, spare_tile),
        )
        # top edge, right shift
        self.assertRaises(
            ValueError,
            lambda: board.slide_and_insert_tile(Coord(2, 0), Direction.RIGHT, spare_tile),
        )
        # non-edge
        self.assertRaises(
            ValueError,
            lambda: board.slide_and_insert_tile(Coord(2, 2), Direction.RIGHT, spare_tile),
        )
        # fixed row
        self.assertRaises(
            ShiftNotAllowedError,
            lambda: board.slide_and_insert_tile(Coord(6, 1), Direction.LEFT, spare_tile),
        )
        # fixed column
        self.assertRaises(
            ShiftNotAllowedError,
            lambda: board.slide_and_insert_tile(Coord(5, 0), Direction.DOWN, spare_tile),
        )

    def test_slide_and_insert_tile_rows(self):
        board = ascii_board(
            # 12
            "┼┼┼",  # 0
            "└┼┼",  # 1
            "│──",  # 2
        )
        spare_tile = Tile(TileShape.LINE, 1, default_gems)
        self.assertEqual(board.width, 3)
        self.assertEqual(board.height, 3)
        self.assertEqual(board.reachable_destinations(Coord(0, 2)), {Coord(0, 2)})
        board2, dropped_tile, _edits = board.slide_and_insert_tile(Coord(0, 2), Direction.RIGHT, spare_tile)
        self.assertEqual(dropped_tile.shape, TileShape.LINE)
        self.assertEqual(dropped_tile.rotation, 1)
        expected_board2 = ascii_board(
            # 12
            "┼┼┼",  # 0
            "└┼┼",  # 1
            "─│─",  # 2
            treasures=list_insert(all_treasures, 6, default_gems),
        )
        self.assertEqual(board2, expected_board2)
        top_two_rows = set(itertools.product(range(3), range(2)))
        top_two_rows = set(map(lambda t: Coord(t[0], t[1]), top_two_rows))

        self.assertEqual(board2.reachable_destinations(Coord(1, 2)), {*top_two_rows, Coord(1, 2)})

    def test_slide_and_insert_tile_columns(self):
        board = ascii_board(
            # 12
            "┼┼│",  # 0
            "┼┼│",  # 1
            "┼┘─",  # 2
        )
        spare_tile = Tile(TileShape.LINE, 1, default_gems)
        self.assertEqual(board.width, 3)
        self.assertEqual(board.height, 3)
        self.assertEqual(board.reachable_destinations(Coord(2, 2)), {Coord(2, 2)})
        board2, dropped_tile, _edits = board.slide_and_insert_tile(Coord(2, 2), Direction.UP, spare_tile)
        self.assertEqual(dropped_tile.shape, TileShape.LINE)
        self.assertEqual(dropped_tile.rotation, 0)
        # Construct new treasures by performing the relevant column shift
        new_treasures = all_treasures[:9].copy()
        new_treasures[2] = all_treasures[5]
        new_treasures[5] = all_treasures[8]
        new_treasures[8] = default_gems
        expected_board2 = ascii_board(
            # 12
            "┼┼│",  # 0
            "┼┼─",  # 1
            "┼┘─",  # 2
            treasures=new_treasures,
        )
        self.assertEqual(board2, expected_board2)
        left_two_cols = set(itertools.product(range(2), range(3)))
        left_two_cols = set(map(lambda t: Coord(t[0], t[1]), left_two_cols))

        self.assertEqual(board2.reachable_destinations(Coord(2, 1)), {*left_two_cols, Coord(2, 1)})
