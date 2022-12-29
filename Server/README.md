# Server
Contains implementations of the Maze.com game server. The preferred implementation is AsyncReferee, which uses asyncio to run the game in a non-blocking manner. 


## Table of Contents
| File | Purpose |
| ---- | ------- |
| [async_server.py](async_server.py) | An implementation of the Maze.com server using `asyncio` |
| [server.py](server.py) | (deprecated) A synchronous server implementation for Maze.com. |


## Relationship Diagrams
### class-async-server.txt
```ascii
   +---------------------------------------+
   |           AsyncServerWrapper          |
   +---------------------------------------+
   |  Fields:                              |
   |  + loop: asycio.AbstractEventLoop     |
   |  + wrapped: AsyncServer               |
   +---------------------------------------+
   |  Public methods:                      |
   |  + __init__(loop, wrapped)            |
   |  + start(state, observers, goal_queue)|
   +---------------------------------------+


+---------------------------------------------+
|                  AsyncServer                |
+---------------------------------------------+
| Fields:                                     |
| + host                                      |
| + port                                      |
| + read_write_stream_pairs                   |
| + server_socket                             |
| + player_names                              |
+---------------------------------------------+
| Public methods:                             |
| + __init__(host, port)                      |
| + start(state, observers)                   |
| + wait_for_signups_and_run_game(state,      |
|                                 observers,  |
|                                 goal_queue) |
+---------------------------------------------+
```

### relationship-client-server.txt
```ascii
                                         ~> Internet/network communication
                                          % Comment
                                         // Internet barrier



   Game host server                                                              Client machine
+-------------------------------------+                                  //   +----------------------------------+
|                                     |                                  //   |                                  |
|  +-------------------------------+  |        % Connects and sends name //   |    +--------------------+        |
|  |          AsyncServer          |<~|~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~//~~~|~~~~|     AsyncClient    |        |
|  +--------------+----------------+  |                                  //   |    +---------+----------+        |
|                 |                   |                                  //   |              |                   |
|                 |                   |                                  //   |              |                   |
|        +--------+                   |                                  //   |              |                   |
|        |        |                   |                                  //   |              |                   |
| Wait for signups|                   |                                  //   |              | % Once connection |
|        |        |                   |                                  //   |              | % is established, |
|        +------->|                   |                                  //   |              | % create a        |
|                 |                   |                                  //   |              | % RemoteReferee   |
|                 |                   |                                  //   |              |                   |
|                 | % Start game with |                                  //   |              |                   |
|                 | % list of         |                                  //   |              |                   |
|                 | % ProxyPlayers    |                                  //   |              |                   |
|                 v                   |                                  //   |              v                   |
|  +-------------------------------+  |        % JSON RPC call/response  //   |    +---------------------+       |
|  |          ProxyPlayer          |<~|~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~//~~~|~~~>|    RemoteReferee    |       |
|  +-------------------------------+  |                                  //   |    +---------------------+       |
|                                     |                                  //   |                                  |
+-------------------------------------+                                  //   +----------------------------------+
```


