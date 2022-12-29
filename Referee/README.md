# Referee
Contains a referee implementation for the Maze game, as well as components relating to observers and the GUI.


## Table of Contents
| File | Purpose |
| ---- | ------- |
| [labyrinth_gui.py](labyrinth_gui.py) | A Labyrinth observer GUI written using Pygame and Pygame GUI. |
| [observer.py](observer.py) | Observer implementation for the Maze game's GUI observer. |
| [referee.py](referee.py) | Referee implementation for the Maze game's player-referee protocol. |
| [view.py](view.py) | Interfaces and data definitions for Labyrinth views. |


## Relationship Diagrams
### relationship-referee.txt
```ascii
+------------------------------------------------+
|                    Referee                     |
+------------------------------------------------+
| Fields:                                        |
|                                                |  This is useful
| + loop: asyncio.AbstractEventLoop              |  when the referee needs
| + wrapped: AsyncReferee                        |  to be run in a synchronous
+------------------------------------------------+  context.
| Methods:                                       |
|                                                |
| + __init__(board, spare)                       |
| + create_initial_game_state(players)           |
| + start_game(players, observers)               |
| + start_game_from_state(state, players,        |
|                         goal_queue, observers) |
+------------------------------------------------+


+------------------------------------------------+
|                   AsyncReferee                 |
+------------------------------------------------+
| Fields:                                        |
|                                                |
| + initial_spare_tile                           |
| + goal_queue                                   |
| + initial_board                                |
+------------------------------------------------+
| Public methods:                                |
|                                                |
| + __init__(board, spare, height, width)        |
| + create_initial_game_state(players)           |
| + start_game(players, observers)               +--------+         +------------------------------+
| + start_game_from_state(state, players,        +--------+-------->|           GameOutcome        |
|                         goal_queue, observers) |   returns        +------------------------------+
+------------------------------------------------+                  | Fields:                      |
                                                                    |                              |
                                                                    | + winners                    |
                                                                    | + ejected                    |
                                                                    +------------------------------+
                                                                    | Methods:                     |
                                                                    |                              |
                                                                    | + __init__(winners, ejected) |
                                                                    +------------------------------+
```


