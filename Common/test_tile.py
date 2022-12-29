# pylint: disable=missing-function-docstring,missing-module-docstring,protected-access
import unittest

from Maze.Common.gem import Gem
from Maze.Common.tile import Direction, Tile, TileShape

default_gems = (Gem.RUBY, Gem.DIAMOND)


class TestTile(unittest.TestCase):
    """Tests for the `Tile` class"""

    def test_line(self):
        tile = Tile(TileShape.LINE, 0, default_gems)
        self.assertEqual(tile.connected_directions(), {Direction.UP, Direction.DOWN})
        self.assertEqual(tile.rotate(1).connected_directions(), {Direction.LEFT, Direction.RIGHT})
        self.assertEqual(tile.rotate(2).connected_directions(), {Direction.UP, Direction.DOWN})
        self.assertEqual(tile.rotate(3).connected_directions(), {Direction.LEFT, Direction.RIGHT})

    def test_corner(self):
        tile = Tile(TileShape.CORNER, 0, default_gems)
        self.assertEqual(tile.connected_directions(), {Direction.UP, Direction.RIGHT})
        self.assertEqual(tile.rotate(1).connected_directions(), {Direction.RIGHT, Direction.DOWN})
        self.assertEqual(tile.rotate(2).connected_directions(), {Direction.DOWN, Direction.LEFT})
        self.assertEqual(tile.rotate(3).connected_directions(), {Direction.LEFT, Direction.UP})

    def test_tee(self):
        tile = Tile(TileShape.TEE, 0, default_gems)
        self.assertEqual(
            tile.connected_directions(),
            {Direction.RIGHT, Direction.DOWN, Direction.LEFT},
        )
        self.assertEqual(
            tile.rotate(1).connected_directions(),
            {Direction.DOWN, Direction.LEFT, Direction.UP},
        )
        self.assertEqual(
            tile.rotate(2).connected_directions(),
            {Direction.LEFT, Direction.UP, Direction.RIGHT},
        )
        self.assertEqual(
            tile.rotate(3).connected_directions(),
            {Direction.UP, Direction.RIGHT, Direction.DOWN},
        )

    def test_cross(self):
        tile = Tile(TileShape.CROSS, 0, default_gems)
        all_directions = {Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT}
        self.assertEqual(tile.connected_directions(), all_directions)
        self.assertEqual(tile.rotate(1).connected_directions(), all_directions)
        self.assertEqual(tile.rotate(2).connected_directions(), all_directions)
        self.assertEqual(tile.rotate(3).connected_directions(), all_directions)

    def test_invalid_rotation(self):
        self.assertRaises(
            ValueError,
            lambda: Tile(TileShape.LINE, -1, default_gems),
        )
        self.assertRaises(
            ValueError,
            lambda: Tile(TileShape.LINE, 4, default_gems),
        )
        tile = Tile(TileShape.LINE, 2, default_gems)
        self.assertRaises(
            ValueError,
            lambda: tile.rotate(-1),
        )
        self.assertRaises(
            ValueError,
            lambda: tile.rotate(4),
        )

    def test_tile_shape_unique_rotations(self):
        # Map of the outward directions of a TileShape-rotation pair to its shape and rotation
        # a Set[Direction] is not a valid dict key, but a FrozenSet is because it prohibits add/remove
        tile_choices = {}
        for shape in TileShape:
            unique_rotations = shape.unique_rotations()
            for rotation in [0, 1, 2, 3]:
                key = {dir.rotated(rotation) for dir in shape.connected_directions()}
                if rotation in unique_rotations:
                    # if it is a unique rotation, the direction set should be new
                    self.assertFalse(frozenset(key) in tile_choices)
                else:
                    # if it's not a unique rotation, the direction set should have already been seen
                    self.assertTrue(frozenset(key) in tile_choices)
                tile_choices.setdefault(frozenset(key), (shape, rotation))
