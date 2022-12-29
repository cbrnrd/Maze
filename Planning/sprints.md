## Memorandum

**TO:**      CS 4500 Teaching Staff\
**FROM:**    Dylan Burati, Katherine Payne\
**DATE:**    September 28, 2022\
**SUBJECT:** First 3 sprints of development on Maze project

#### Sprint 1

The main goal of Sprint 1 will be to develop data representations
for the state of the Maze game. A secondary goal will
be to develop an initial version of the `Referee` component which
only deals with creating the initial state of the game, and a `Server`
component that sends a JSON representation of the board to any connecting TCP client.

The data representations for the Maze game are: `Tile`, `Gem`,
`Board`, `Castle`, and `Avatar`. There should also be a top-level
`MazeGame` component, which tracks the overall game state and 
defines a `toJSON` method.


#### Sprint 2

In Sprint 2, we will add functionality to the `Referee`, define the
`Player-Referee` interface, and upgrade the `Server` to allow JSON 
communication between the players and referee via this interface.

The central purpose of the `Referee` is to validate each player's decision
on their turn, which will be represented by a list of `Actions`.  This must be either an empty list or a sequence denoting a
`TileGroupSlide`, `TileInsert`, and `AvatarMove`. The `Player-Referee`
interface will take in player turns and communicate acceptances or
rejections.

In this sprint, we will also write a simplified `Player` implementation, 
which makes a predefined JSON list of moves. We will use this player in
integration tests, where we can verify that the referee matches the
Maze game rules in the spec.


#### Sprint 3

In Sprint 3, we will write an `Observer` interface to which the `Referee` 
can dispatch game state updates. We will implement this interface in a
`GUIObserver` component that can render the current state of the game. We
will also add some additional `Referee` functionality to reduce the pace of
the players when an `Observer` is present.
