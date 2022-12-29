# Common
Contains components shared between the client(s) and the server


## Table of Contents
| File | Purpose |
| ---- | ------- |
| [board.py](board.py) | The board representation for Labyrinth on Maze.com. |
| [gem.py](gem.py) | The gem representation for Labyrinth on Maze.com. |
| [state.py](state.py) | A game state representation for the referee of a Labyrinth game. |
| [tile.py](tile.py) | Tile, tile shape, and direction models for Labyrinth. |
| [utils.py](utils.py) | Utility functions. |


## Relationship Diagrams
### relationship-board.txt
```ascii

+---------------------------+
|           Board           |
+---------------------------+
| Fields:                   |
| + width                   |
| + height                  |             +-----------+
| + tiles: Dict[Coord, Tile]|---+-------->|   Coord   |
+---------------------------+   |         +-----------+
                                |         | Fields:   |
                                |         +-----------+
                                |         | + col     |
                                |         | + row     |
                                |         +-----------+
                                |
                                |
                                |         +------------+
                                +-------->| Tile       |
                                          +------------+
                                          | Fields:    |
                                          +------------+
                                          | + shape    |
                                          | + rotation |       +-----------+
                                          | + gems     +------>| Gem(Enum) |
                                          +------------+       +-----------+
                                                               | __lt__()  |
                                                               +-----------+
```

### relationship-state.txt
```ascii
                             +-------------------------+
                             |     GameStateBuilder    |
                             +-------------------------+
                             | Fields:                 |
                             |                         |
                             | + player_states         |
                             | + starting_player_index |
                             | + spare_tile            |
                             | + subclass              |
                             | + player_secrets        |
                             | + board                 |
                             | + prev_action           |
                             +-------------------------+
                             | Methods:                |
                             |                         |
                             | + set_[field]()         |
                             | + build()               |
                             +-----------+-------------+
                                         |
                                         |builds
                                         v
                        +-----------------------------------+
                        |             GameState             |
                        +-----------------------------------+
                        |  Fields:                          |
                        |                                   |
                        |  + num_players                    |
                        |  + player_states                  +------------------------------------------------------------------------------+
                        |  + spare_tile                     |                                                                              |
                        |  + player_colors                  |                                                                              |
                        |  + player_secrets                 +---------------------------------------------+                                |
                        |  + current_player_index           |                                             v                                v
                        |  + board                          |           +------------------+    +---------------------+        +---------------------+
                        |  + prev_action                    +---------->|  ShiftOp         |    |    PlayerSecret     |        |    PlayerState      |
                        +-----------------------------------+           +------------------+    +---------------------+        +---------------------+
                        |  Relevant methods:                |           | Fields:          |    | Fields:             |        | Fields:             |
                        |                                   |           |                  |    |                     |        |                     |
                        |  + rotate_spare_tile()            |           | + insert_location|    | + treasure_location |        | + home_location     |
                        |  + shift_tiles()                  |           | + direction      |    | + is_going_home     |        | + location          |
                        |  + move_current_player()          |           +------------------+    | + treasure_count    |        | + color             |
                        |  + get_legal_shift_ops()          |           | Methods:         |    +---------------------+        | + name              |
                        |  + get_legal_move_destinations()  |           |                  |    | Methods:            |        +---------------------+
                        |  + associate_players()            |           | + reverse()      |    |                     |        | Methods:            |
                        |  + eject_player()                 |           +------------------+    | setters             |        |                     |
                        |  + set_current_player_new_goal()  |                                   +---------------------+        | + with_location()   |
                        +----------------+------------------+                                                                  | + move_with_board() |
                                         |                                                                                     +---------------------+
                                         |
                                         |
                                         |
                                         |
              +--------------------------+------------------------+
              | is subclass of                                    | is subclass of
              |                                                   |
+-------------+-------------+                       +-------------+-------------+
|    RestrictedGameState    |                       |    RefereeGameState       |
+---------------------------+                       +---------------------------+
| Additional fields:        |                       | Additional fields:        |
|                           |                       |                           |
| + player_color            |                       | + player_secrets          |
+---------------------------+                       +---------------------------+
| Overridden methods:       |                       | Overridden methods:       |
|                           |                       |                           |
| + can_get_player_secret() |                       | + can_get_player_secret() |
| + get_player_secret()     |                       | + get_player_secret()     |
| + eject_current_player()  |                       | + eject_current_player()  |
| + eject_player()          |                       | + eject_player()          |
+---------------------------+                       +---------------------------+
```


