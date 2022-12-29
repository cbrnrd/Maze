# Labyrinth

This repo contains the code for the game Labyrinth for CS4500.

## Getting Started

### Installing Dependencies
This project uses [Python 3.6.8](https://www.python.org/downloads/release/python-368/). Use the Makefile in `9/` (or the most recent numbered directory) to install dependencies in a virtual environment, then activate that environment using `. venv/bin/activate` or your system's equivalent in the terminal.

### Running Unit Tests
This project uses `pytest` for unit testing. To install it, run `pip3 install pytest` in the terminal or use the aforementioned venv. To run the tests, run `pytest` in the terminal.


## Architecture Overview
```ascii
+----------------------+                           +-------------------------+
|        Server        |<~~~~~~~~~~~~~~~~~~~~~~~~~>|          Client         |
+----------------------+       Connects via        +-------------------------+
| Remote player module |           TCP             | Async client module     |
|                      |                           |                         |
| Player signup module |                           | Remote referee module   |
|                      |                           |                         |
| Client handler       |                           | Player implementation   |
|                      |                           |                         |
| Async Referee        |                           | Strategy implementation |
+---------+------------+                           +------------+------------+
          |                                                     |
          |relies on                                            |relies on
          |               +--------------------+                |
          +-------------->| Common components  |<---------------+
                          +--------------------+
                          | Player interface   |
                          |                    |
                          | Strategy interface |
                          |                    |
                          | Referee rules      |
                          |                    |
                          | Board components   |
                          |                    |
                          | Observer interface |
                          +--------------------+
```

## Components
| Component                  | Description                                                                                                   |
|----------------------------|---------------------------------------------------------------------------------------------------------------|
| [`Client/`](Client/)       | Contains implementations of a client for the Maze game.                                                       |
| [`Common/`](Common/)       | Contains components shared between the client(s) and the server.                                              |
| [`Planning/`](Planning/)   | Contains planning documents.                                                                                  |
| [`Players/`](Players/)     | Contains all information relating to individual players and strategies.                                       |
| [`Referee/`](Referee/)     | Contains a referee implementation for the Maze game, as well as components relating to observers and the GUI. |
| [`Remote/`](Remote/)       | Contains the implementations of all components relating to remote play.                                       |
| [`Resources/`](Resources/) | Contains resources for the game, such as images.                                                              |
| [`Server/`](Server/)       | Contains implementations of the Maze.com game server.                                                         |