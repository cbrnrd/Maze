# Client
Contains implementations of a client for the Maze game. Note that `async_referee.py` is the preferred client. 


## Table of Contents
| File | Purpose |
| ---- | ------- |
| [async_client.py](async_client.py) | An `async` client for the Maze game. Handles a single player. |
| [client.py](client.py) | (Deprecated) A synchronous client for the Maze game. |


## Relationship Diagrams
### relationship-client.txt
```ascii
+--------------------------------+
|           AsyncClient          |
+--------------------------------+
| Fields:                        |
| + is_connected                 |
| + server_reader                |
| + server_writer                |
+--------------------------------+
| Public methods:                |
| +__init__(host, port)          |
| + connect()                    |
| + start_remote_referee(player) |
+--------------------------------+
```


