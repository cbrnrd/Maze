## Memorandum

**TO:**      CS 4500 Teaching Staff\
**FROM:**    Dylan Burati, Katherine Payne\
**DATE:**    October 5, 2022\
**SUBJECT:** Design for Maze game state

After signup is complete, the game state receives the game's players (with unique names), turn order, initial board, and special tile locations. Thus, the Maze game state needs the following pieces:

#### Helper Data Types
Let `Coord` be an (x, y) coordinate pair (`Tuple[int, int]`).
Let `Tile`, `Board`, and `Action` be our canonical data representations for the respective game constructs.

#### Data Representations
Number of players (`int`)\
Player names sorted by turn order (`List[str]`)\
Dictionaries mapping from player name to:
- Player home location (`Dict[str, Coord]`)
- Player goal location (`Dict[str, Coord]`)
- Whether player has reached its goal yet (`Dict[str, bool]`)

Index of name of player whose turn it is (`int`)\
Index of name of winner, if any (`int`)\
Width and height of board (`int`s)\
Current spare tile (`Tile`)\
Current board (`Board`)\
Board from start of previous turn (`Board`)

#### Operations
Check whether it's the given player's turn (`str -> bool`)\
Check whether a given action is valid (`Action -> bool`)\
Perform a given action (`Action -> Board`)\
Check for winner (`void -> Optional[str]`)