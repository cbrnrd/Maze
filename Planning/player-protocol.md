## Player-Referee Protocol

**DATE:** October 18, 2022

## Overview
The player-referee protocol is a client-server interaction protocol for coordinating a game of Labyrinth. Messages will be passed using the JSON data definitions provided in the spec for Milestones 3-4, as well as those defined here. The protocol has two phases: setup and gameplay.

## Data Definitions
`JoinRequest` = {"color": `Color`}\
`JoinResponse` = "SUCCESS" | "COLOR_TAKEN"\
`Treasure` = [`Gem`, `Gem`]\
`TurnResult` = `State` | `GameResult`\
`GameResult` = {"winner": `Color`} | "ALL_EJECTED" | "ALL_PASSED"

## Setup

Each player sends a `JoinRequest` to the referee indicating its intent to join a game. This includes its chosen color.

The referee will then respond with a `JoinResponse` to indicate whether the `JoinRequest` succeeded. If not, the connection to the referee will be closed.

Once the game is ready, the referee will announce the start of the game to all players. This announcement will contain the `State` of the game, which tells players their home tiles. Each player will also privately receive its own `Treasure`. This announcement concludes the setup phase.

## Gameplay

Each player takes its turn either by sending the following messages to the referee, in order:
- `rotate_spare_tile(Degree)`
- `shift_and_insert(Index, Direction)`
- `move_avatar(Coordinate)`

or by sending this message to the referee:
- `pass()`

The referee announces the end of a player's turn to all players with a `TurnResult`. 
- If the game is ongoing, this tells players the next `State`. It lets them determine whether any player has been ejected by comparing the player list with the previous state's list. It also lets each player determine whether its turn is next by checking whether it is the first player in the player list.
- If a player is being ejected, this is the last message they receive before the connection is closed.
- If the game is over, this tells players how it ended, either by revealing the color of the winning player or by giving the reason for a stalemate (that all players have passed on their most recent turn or that all players have been ejected).

## Information Gathering

To support players in determining their next moves, a player can request the following information from the referee:
- On its turn only: `get_legal_shift_ops()` or `get_legal_move_destinations()`
  - Note that a good player does not need these methods. It is not possible for a player to reverse a rotate or shift after sending the message, so relying on these for move selection would get the player ejected if it ends up without a valid avatar move to make. 
- At any time: `get_treasure_location()` or `get_current_state()`