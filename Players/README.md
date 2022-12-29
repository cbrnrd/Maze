# Players
This directory contains all information relating to individual players and strategies.


## Table of Contents
| File | Purpose |
| ---- | ------- |
| [player.py](player.py) | Player implementation for the Maze game's player-referee protocol. |
| [strategy.py](strategy.py) | The strategy interface and sample implementations for Labyrinth on Maze.com |


## Relationship Diagrams
### relationship-player.txt
```ascii
                                                           +---------------------------------------------+
                                                           |                                             |
 +------------------------------+                          |          +--------------------+             |
 |        AbstractPlayer        |                          |          |   PlayerSetupImpl  |             |
 +------------------------------+                          |          +--------------------+             |
 | Methods:                     |                          |          | Fields:            |             |
 |                              |                          |          |                    |             |
 | + name()                     |                          |          | + phase            |             |
 | + propose_board0(rows, cols) |                          |          +--------------------+             |
 | + setup(state0, goal)        |                          |          | Methods:           |             |
 | + take_turn(state)           |                          |          |                    |             |
 | + win(w)                     |                          |          | + __init__(name)   |             |
 +---------------+--------------+                          |          | + propose_board0() |             |
                 |                                         |          | + setup()          |             |
                 v                                         |          +--------------------+             |
+---------------------------------+                        |                                             |
|      Player(AbstractPlayer)     |                        | +-----------------------------------------+ |
+---------------------------------+                        | |           PlayerGameplayImpl            | |
| Fields:                         |                        | +-----------------------------------------+ |
|                                 |       One of           | | Fields:                                 | | `phase` is a     +---------------------+
| + _implementation               +----------------------->| |                                         | +----------------->| ProtocolPhase(Enum) |
| + _name                         |                        | | + phase                                 | |                  +---------------------+
| + _strategy                     +--------+               | +-----------------------------------------+ |                  | Options:            |
+---------------------------------+        |               | | Methods:                                | |                  |                     |
| Additional Methods:             |        |               | |                                         | |                  | + SETUP             |
|                                 |        |               | | + __init__(name, strategy,              | |                  | + GAMEPLAY          |
| + _set_implementation(new_impl) |        |               | |            player_state, player_secret) | |                  | + SCORING           |
+---------------------------------+        |               | | + take_turn()                           | |                  +---------------------+
                                           |               | | + setup()                               | |
                                           |               | +-----------------------------------------+ |
                                           v               |                                             |
                                   +--------------+        |        +-----------------------+            |
                                   |   Strategy   |        |        |    PlayerScoringImpl  |            |
                                   +--------------+        |        +-----------------------+            |
                                   | See strategy |        |        | Fields:               |            |
                                   | diagram      |        |        |                       |            |
                                   +--------------+        |        | + phase               |            |
                                                           |        +-----------------------+            |
                                                           |        | Methods:              |            |
                                                           |        |                       |            |
                                                           |        | + __init__(name, won) |            |
                                                           |        +-----------------------+            |
                                                           |                                             |
                                                           +---------------------------------------------+
```

### relationship-strategy.txt
```ascii
                                              +-------------------+
                                              |                   |
                                              |   +----------+    |
+---------------------+                       |   | TurnPass |    |
|    Strategy(ABC)    |                       |   +----------+    |
+---------------------+                       |                   |
| Methods:            |                       | +---------------+ |
|                     |    returns one of     | |  TurnWithMove | |
| + get_action(state) +---------------------->| +---------------+ |
+---------+-----------+                       | | Fields:       | |
          |                                   | |               | |
          |                                   | | + degrees     | |
          +-----------+                       | | + shift       | |
                      |                       | | + movement    | |
                      v                       | +---------------+ |
    +-------------------------------------+   |                   |
    |        FirstViableMoveStrategy      |   +-------------------+
    +-------------------------------------+
    | Methods:                            |
    |                                     |
    | + movement_exploration_order(state) |
    | + shift_exploration_order(state)    |
    | + rotation_exploration_order(state) |
    | + get_action(state)                 |
    +------------------+------------------+
                       |
                       +-----------------------------------------------+
                       |                                               |
                       |                                               |
                       v                                               v
   +-------------------------------------+          +-------------------------------------+
   |            RiemannStrategy          |          |            EuclidStrategy           |
   +-------------------------------------+          +-------------------------------------+
   | Overridden methods:                 |          | Overridden methods:                 |
   |                                     |          |                                     |
   | + movement_exploration_order(state) |          | + movement_exploration_order(state) |
   | + shift_exploration_order(state)    |          | + shift_exploration_order(state)    |
   | + rotation_exploration_order(state) |          | + rotation_exploration_order(state) |
   +-------------------------------------+          +-------------------------------------+
```


