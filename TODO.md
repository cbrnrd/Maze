# TODO

- [ ] Move valid move check to referee (currently in the state)
- [x] Use colors instead of names to identify players
- [ ] **_ASYNC TIMEOUT_**
- [ ] Observers are not trusted code, call them safely
- [ ] Get rid of player index and use queue of players instead
- [ ] Game over checking refactor (currently spread out in the referee game running methods)
- [x] Get rid of `get_player_secret()` in AbstractPlayer
- [ ] Add custom errors for player errors, observer errors, etc (currently using Exception/other builtins)
- [ ] Document PrevAction stuff in state


---


Milestone 8 specific tasks:
- Change strategy to take goal and gamestate
- Better handle constructing restricted game state with goal in remote ref’s take_turn method
- Improve recv chunks in remote player
- When kicking a player, close their socket somehow
- Improve random home generation


Pre-milestone 8 notes:
- Observers are not trusted code
- Get rid of player index and use queue of players
- Write helper to split Coords into non-goal and goal ones (strategy, share more code between Euclid and Riemann strategies)
- Move tests to new folder
- Possible error check: Too many goal reminders/changes(?) Revisit error checks in player
- Improve player randomness for testing
- Add game state with 0 secrets (would be used for setup call alongside playersecret; only playersecret is really needed here)
- (states sent by the referee would correspond with states in our application without a required second piece of info
- Only need playersecret for both setup and reminder calls
- Keep color on the outside and update it with the player each time
- Take_turn then needs to construct a restricted game state with the zero secret state + its goal
- Possibly move PlayerSecret to list of Coords, visited bools, but player would still only have one at a time
- Referee shouldn’t be able to access an unprotected player
- Prevent shift/move/rotate without end_turn first? (4th prevaction kind)
- Check winners for the single winner case (could do check_winners to return one logical step, should have method with it minus the composition; and make game outcome in run_round)

Future Assignments:
Players async? Probably good to pair this with proxy result
Spec may change so player will have multiple goals to visit
If homes become moveable, we don’t handle that yet in playerstate.move_with_board; same for goals w/ playersecret

