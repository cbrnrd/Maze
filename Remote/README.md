# Remote
Contains the implementations of all components relating to remote play. Note the actual client and server implementations are in `Maze.Client` and `Maze.Server`, respectively.


## Table of Contents
| File | Purpose |
| ---- | ------- |
| [player.py](player.py) | Proxy player implementation for Maze.com. |
| [referee.py](referee.py) | Implements the proxy referee for the players of Maze.com |


## Relationship Diagrams
### relationship-remote.txt
```ascii
+------------------------------------------------+                      +---------------------------------------+
|           ProxyPlayer(AbstractPlayer)          |                      |             RemoteReferee             |
+------------------------------------------------+                      +---------------------------------------+
| Fields:                                        |                      | Fields:                               |
|                                                |                      |                                       |
| + client_reader: asyncio.StreamReader          |<-------------------->| + server_reader: asyncio.StreamReader |
| + client_writer: asyncio.StreamWriter          |   readers/writers    | + server_writer: asyncio.StreamWriter |
| + _name                                        |   established by     | + player: AbstractPlayer              |
+------------------------------------------------+   client and server  +---------------------------------------+
| Overridden methods:                            |                      | Public methods:                       |
|                                                |                      |                                       |
| + __init__(name, client_reader, client_writer) |                      | + __init__(player, reader, writer)    |
| + name()                                       |                      | + listen_and_handle_messages()        |
| + setup(state0, goal)                          |                      +---------------------------------------+
| + take_turn(state)                             |
| + win(w)                                       |
+------------------------------------------------+
```


