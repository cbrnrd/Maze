"""Tile, tile shape, and direction models for Labyrinth."""

import enum
import itertools
from typing import Any, ClassVar, Dict, List, Set, Tuple

from Maze.Common.gem import Gem
from Maze.Common.utils import assert_never

# Represents a pair of gems
Treasure = Tuple[Gem, Gem]


class Direction(enum.Enum):
    """One of the four cardinal directions: `UP`, `RIGHT`, `DOWN`, or `LEFT`."""

    UP = (0, -1)
    RIGHT = (1, 0)
    DOWN = (0, 1)
    LEFT = (-1, 0)

    def flip(self) -> "Direction":
        """Returns the opposite direction."""
        return self.rotated(2)

    def rotated(self, rotation: int) -> "Direction":
        """Computes the direction resulting from the given number of rotations.

        Args:
            rotation (int): The number of 90-degree clockwise rotations to perform

        Raises:
            ValueError: If the rotation is not between 0 and 3 inclusive
        """
        all_directions = [Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.LEFT]
        start = all_directions.index(self)
        # `all_directions` is in clockwise order, so moving the index by
        # +1 == one 90-deg rotation
        return all_directions[(start + rotation) % len(all_directions)]

    @property
    def dx(self) -> int:
        """The change in x-position represented by moving 1 unit this direction."""
        return self.value[0]

    @property
    def dy(self) -> int:
        """The change in y-position represented by moving 1 unit this direction."""
        return self.value[1]

    @property
    def is_vertical(self) -> bool:
        """True if this direction is UP or DOWN."""
        return self in (Direction.UP, Direction.DOWN)

    @property
    def is_horizontal(self) -> bool:
        """True if this direction is LEFT or RIGHT."""
        return self in (Direction.LEFT, Direction.RIGHT)


class TileShape(enum.Enum):
    """One of the four canonical tile shapes in Labyrinth."""

    LINE = "│"
    CORNER = "└"
    TEE = "┬"
    CROSS = "┼"

    def connected_directions(self) -> Set[Direction]:
        """Computes the set of directions which this tile shape points in."""
        if self is TileShape.LINE:
            return {Direction.UP, Direction.DOWN}
        elif self is TileShape.CORNER:
            return {Direction.UP, Direction.RIGHT}
        elif self is TileShape.TEE:
            return {Direction.RIGHT, Direction.DOWN, Direction.LEFT}
        elif self is TileShape.CROSS:
            return {Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.LEFT}
        else:
            # At runtime, this is equivalent to raising a TypeError
            # The function call can be typechecked by mypy to detect a missing case above
            assert_never(self)

    def unique_rotations(self) -> List[int]:
        """Lists the rotations of this canonical shape which result in a new shape.

        Returns:
            List[int]: The list of numbers of clockwise quarter-turns
        """
        if self is TileShape.LINE:
            return [0, 1]
        elif self is TileShape.CORNER:
            return [0, 1, 2, 3]
        elif self is TileShape.TEE:
            return [0, 1, 2, 3]
        elif self is TileShape.CROSS:
            return [0]
        else:
            assert_never(self)


# Represents a tile shape with a rotation
TileShapeWithRotation = Tuple[TileShape, int]


class Tile:
    """A tile on the board."""

    # Maps each possible TileShapeWithRotation to the set of directions it points in
    _connected_direction_map: ClassVar[Dict[TileShapeWithRotation, Set[Direction]]] = {
        (shape, rotation): {d.rotated(rotation) for d in shape.connected_directions()}
        for shape, rotation in itertools.product(TileShape, range(4))
    }

    shape: TileShape
    rotation: int
    gems: Treasure

    def __init__(self, shape: TileShape, rotation: int, gems: Treasure):
        """Creates a tile, with no association to the board.

        Args:
            shape (TileShape): The shape of the tile
            rotation (int): A number of 90-degree clockwise rotations for this tile,
                relative to its canonical shape
            gems (Treasure): The pair of gems to place on the tile

        Raises:
            ValueError: If the rotation is not between 0 and 3 inclusive
        """
        if rotation < 0 or rotation > 3:
            raise ValueError("Expected 0 <= rotation <= 3")
        self.shape = shape
        self.rotation = rotation
        # This will be checked for un-ordered uniqueness, so we make sure that swapping
        # the argument order has no effect on the stored tuple.
        gem1, gem2 = gems
        min_gem, max_gem = min(gem1, gem2), max(gem1, gem2)
        self.gems = (min_gem, max_gem)

    def connected_directions(self) -> Set[Direction]:
        """Computes the set of directions which this tile points in."""
        return Tile._connected_direction_map[self.shape, self.rotation]

    def rotate(self, new_rotation: int) -> "Tile":
        """Creates a copy of this tile with a new rotation.

        Args:
            new_rotation (int):  A number of 90-degree clockwise rotations for this tile,
                relative to its canonical shape

        Raises:
            ValueError: If the rotation is not between 0 and 3 inclusive
        """
        return Tile(self.shape, new_rotation, self.gems)

    def __eq__(self, other: Any) -> bool:
        """Tests whether this tile is equivalent to `other`.

        Note:
            Tiles of the same shape but different rotations can be equivalent, if their
            `connected_directions` are the same.
        """
        if not isinstance(other, Tile):
            return False
        return (
            (self.shape is other.shape)
            and (self.connected_directions() == other.connected_directions())
            and (self.gems == other.gems)
        )

    def __repr__(self) -> str:
        """Returns a string representation of the tile."""
        return f"Tile({self.shape!r}, {self.rotation}, {self.gems[0]!r}, {self.gems[1]!r})"
