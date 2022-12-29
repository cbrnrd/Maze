## Interactive Player

**DATE:** October 26, 2022

## Overview

The interactive player component will use a model containing:
- a `Player` to interact with the referee;
- the "true" game state;
- a `DraftTurnAction`;
- and the viewable game state resulting from applying the draft action to the true state

## Data Definitions

A `DraftTurnAction` is one of:
- a `DraftPass`, indicating no change from the previous state
- a `DraftRotation(int)`, containing only a spare tile rotation
- a `DraftShift(int, ShiftOp)`, containing all parts of the turn action except movement
- a `DraftTurnWithMove(int, ShiftOp, Coord)`, containing a full move

## Model Functionality

The model has several mutating methods:

- Update the true game state (`GameState -> void`)
- Reset the draft action to a `DraftPass` (` -> void`)
- Rotate the spare tile by a number of degrees (`int -> void`)
- Shift a row or column by inserting the spare tile (`ShiftOp -> void`)
- Move own avatar (`Coord -> void`)
- Commit the draft action (` -> void`)

It also has methods to allow the GUI to present only the permissible interactions:

- Check if the spare tile can be rotated (` -> bool`, equivalent to `hasActiveTurn && draft is DraftPass | DraftRotation`)
- Check if a row or column can be shifted (` -> bool`, equivalent to `hasActiveTurn && draft is DraftPass | DraftRotation`)
- Check if the controller can move (` -> bool`, equivalent to `hasActiveTurn && draft is DraftShift | DraftTurnWithMove`)
- Check if the draft action is ready to commit (` -> bool`, equivalent to `hasActiveTurn && draft is DraftPass | DraftTurnWithMove`)
- Check if the draft action is a `DraftPass` (` -> bool`)

The viewable game state is public, which exposes the necessary methods to visualize the
board, spare tile, player homes, and player avatars.

## Graphical View

The GUI for the interactive player component should show the board,
spare tile, player homes, and player avatars at all times. There is an
indicator of whether the referee is waiting for the interactive player
to choose their turn action. The protocol defined in "Logical
Interactions" document limits this indicator to True/False, but it could
be amended to show which player is active.

The user can click one of two buttons (↶ or ↷) above the spare tile's
image to rotate it 90 degrees counterclockwise or clockwise,
respectively. When the user can perform a tile shift, there will be a
left/right arrow outside the edges of each movable row, and an up/down
arrow outside the edges of each movable column (pointing inwards).
Clicking one of these will insert the spare tile into the indicated
position with its current rotation, shifting the row/column in the
corresponding direction. The view will then have a new spare tile. 

When the user can move their player's avatar, small clickable circles
will appear on the center of each tile that they can reach. Clicking one
does not immediately submit the turn action. The circles will remain
as long as the turn action is a draft.

If the interactive player is choosing its turn, there will be two
buttons in the bottom right corner of the screen. The left button will
allow the user to **reset** the draft turn action and start over on
making their turn selection. The right button will allow the player to
**pass** if they haven't changed anything since their turn started, or
**submit** their rotation, shift, and movement as an atomic choice.
The bolded words above will be the text of the button.

In version 1 of the interactive player view, we will not attempt to
update the player-referee protocol. As a result, the user will only
see changes to the board immediately before they are granted a turn.
This will likely be jarring in games with more than 2 players, so
a future version of the protocol should send the interactive player
incremental updates for each turn, and include the most recent
player's turn action to allow animation.