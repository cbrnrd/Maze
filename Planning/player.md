## Memorandum

**TO:**      CS 4500 Teaching Staff\
**FROM:**    Dylan Burati, Katherine Payne\
**DATE:**    October 13, 2022\
**SUBJECT:** Design for Player data requirements and functionality

#### Helper Data Types

Let `Coord` be an (x, y) coordinate pair (`Tuple[int, int]`). Let
`Color`, `Direction`, `Tile`, and `Board` be our canonical data representations
for the respective game constructs.

Let `ShiftOp` be a tuple containing:
  - The direction of the shift operation (`Direction`)
  - The insert location of the spare tile (`Coord`)
  - The rotation of the spare tile (`int`)

Let `Action` be one of:
- a `Pass`
- a `Move` containing:
  - A `ShiftOp`
  - The cell the player landed on (`Coord`)

Let `PublicPlayerState` be a tuple containing:
  - Player avatar (`Color`)
  - Player home location (`Coord`)
  - Player current location (`Coord`)

Let `PublicGameState` be a data class containing:
  - The board (`Board`)
  - The spare tile (`Tile`)
  - The public player states (`OrderedDict[str, PublicPlayerState]`)

#### Data Representation

- Number of players, including self (`int`)
- Own name (`str`)
- Names of all players sorted by turn order (`List[str]`)
- Goal gems (`Treasure`)
- The current `PublicGameState`
- A dictionary from player name to move history with most recent move first (`Dict[str, List[Action]]`)

#### Functionality

- Update internal state after another player's move
  (`str, Action, PublicGameState -> void`)

- Update internal state after a player is kicked out (`str -> void`)

- Select an action for their move (` -> Action`). The following are
  helpers that can be used by a strategic player implementation:
  - From own data, determine whether passing this turn would end the
    game (` -> bool`)
  - From the context, get the legal shift operations (`-> List[ShiftOp]`)
  - From the context, simulate the state of the game following the first
    part of a move (`ShiftOp -> PublicGameState`).
    - The player can then use its computed position and `Board.reachable_destinations()`
      to determine all permissible actions.
