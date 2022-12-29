## Distributed Labyrinth Game Protocol

**DATE:** November 2, 2022

## Overview
The distributed Labyrinth game protocol is a client-server interaction protocol for coordinating a game of Labyrinth. The server side of this protocol will be implemented using a new `GameManager` component. Messages will be passed using the JSON data definitions provided in the spec for Milestones 3-6, as well as those defined here. The protocol has three phases: setup, gameplay, and cleanup.

## Data Definitions

A `ProxyResult[T]` is one of:
- `Success[T]` representing a successful proxied response of the type `T`
- `Timeout` representing a timeout on the proxied response
- `NetworkFailure` representing a disconnection before the proxied response was received
- `BadJSONFailure` representing a badly formed JSON response from the proxy
- `TypeFailure` representing an invalid JSON response from the proxy (i.e. one that doesn't conform to the spec for the method)

We refer to any `ProxyResult` other than a `Success` as a failure variant.

## Remote Proxy

Each player will have a remote proxy for the referee which, for each method call:
1. Serializes the method identity and arguments into a JSON message tagged with a unique ID e.g. `["UP.1", "join", {"name": "TheirName"}]`
2. Sends the message to the server via TCP
3. Waits up to `timeout` seconds for a response with the same unique ID
4. Deserializes the resulting JSON response e.g. `["REPLY.UP.1", "SUCCESS"]`

The remote proxy on the player side is allowed to throw exceptions.

The game manager will have a remote proxy for each player which, for each method call:
1. Serializes the method identity and arguments into a JSON message tagged with a unique ID e.g. `["DOWN.1", "setup", null, {"row#": 1, "column#": 1}]`
2. Sends the message to the player via TCP
3. Waits up to `timeout` seconds for a response with the same unique ID
4. Deserializes the resulting JSON response e.g. `["REPLY.DOWN.1", "ACK"]`

If the remote proxy on the game manager side fails to complete steps 2-4, the game manager will handle any exceptions, close the TCP connection, and return a failure variant of the method response. If a game is currently running, the referee can use the method response to decide whether a player must be ejected from the game.

## Setup
The game manager provides the following interface:

```
public: join(name: str) -> "SUCCESS" | "NAME_TAKEN"
// Used by the player to indicate its intent to join a game
// with the chosen name
// SUCCESS indicates that they have joined and NAME_TAKEN
// indicates that they were not allowed to join
// If NAME_TAKEN is received, the connection will be closed
```

Each time the desired number of players for a game has been reached, the game manager will ask each player to `proposeBoard0`, randomly select one of these boards, create a referee, and ask the referee to start a game with the players and board. It then resumes listening for players for the next game.

## Gameplay

Gameplay proceeds according to the standard player-referee protocol described in "Logical Interactions". Once the game has ended, players are notified of the results with the `won` method.


## Cleanup

After the conclusion of a game, the game manager receives all remaining remote player proxies from the referee, along with the game outcome. It will then disconnect the surviving players. It may also use the winners to update a leaderboard and use the ejected players to update a banned IP list.