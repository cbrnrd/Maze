## Impact of Possible Changes on Codebase

**DATE:** November 9, 2022

### Blank Tiles for the Board

We would rate this change as a 2 in terms of impact. It would be fairly straightforward to create a `AbstractTile` superclass, make the current `Tile` a subclass of `AbstractTile`, and add an additional subclass `BlankTile` to represent a blank tile. Most of the code that uses a tile relies on its `connected_directions()` method, which could simply return an empty list for a blank tile. The few places that access a tile's gems could be handled by checking whether the tile is an instance of `Tile` before attempting to access gems.

### Use Moveable Tiles as Goals

We would rate this change as a 1 in terms of impact. We don't currently enforce the rule that goals must be on fixed tiles, so we would just need to account for the edge case of a player's goal being off the board when considering its reachability or Euclidean distance from another tile. We would also need to update players' goal locations after slides are performed, which can be done using our existing `BoardEdit` class that maps from old to new `Coord`s after a slide.

### Ask Player to Sequentially Pursue Several Goals

We would rate this change as a 2 in terms of impact. We could adjust the state to hold a list of goal `Coord`s for each player, but the player would still hold only a single `Coord` representing their current goal. The referee would then send another `setup(None, new_goal)` call each time the player reaches their current goal. Lastly, we would update our `Player` implementation to not throw an error upon receiving a new goal and our strategy implementations to always pursue the player's current goal.