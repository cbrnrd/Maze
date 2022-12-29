# Milestone 9 Revisions

The changes we made to our codebase to meet the requirements of the Milestone are listed below.


### Referee
* Changed player ordering for scoring to reflect new requirement. [Commit](https://github.khoury.northeastern.edu/CS4500-F22/mysterious-whales/commit/9172f1e0f76b6831fd317c3ef2d8611a4bc605a7#diff-f31d943ecec5b9a4dc8e0914ef3f5722bda0bc19acb9271739df4e9e91612ac9L103-L104)
* Added a `goal_queue` instance variable to keep track of the future goal positions. [Commit](https://github.khoury.northeastern.edu/CS4500-F22/mysterious-whales/commit/52a392d410d9af4eb4cba935d06d2acc18853312#diff-f31d943ecec5b9a4dc8e0914ef3f5722bda0bc19acb9271739df4e9e91612ac9)
* Now have players get the first goal in the `goal_queue` for their next goal [Commit](https://github.khoury.northeastern.edu/CS4500-F22/mysterious-whales/commit/52a392d410d9af4eb4cba935d06d2acc18853312#diff-f31d943ecec5b9a4dc8e0914ef3f5722bda0bc19acb9271739df4e9e91612ac9R552-R568)
* Change `setup(F/State, Coord)` to send `None, Coord` as arguments when getting a new goal from the goal queue. [Commit](https://github.khoury.northeastern.edu/CS4500-F22/mysterious-whales/commit/f8a81a7131da55d3610a32ebeebde80b999f5b1a#diff-f31d943ecec5b9a4dc8e0914ef3f5722bda0bc19acb9271739df4e9e91612ac9L605-R605)
* Fix mapping players' names to their states, now use color. [Commit](https://github.khoury.northeastern.edu/CS4500-F22/mysterious-whales/commit/8e7a993786dab2a2ec16cdb65cbfc961be373cd9)

### State
* Added `set_current_player_new_goal(new_goal)`, which update's the current player's `PlayerSecret`. 
  * [State diff](https://github.khoury.northeastern.edu/CS4500-F22/mysterious-whales/commit/52a392d410d9af4eb4cba935d06d2acc18853312#diff-21759bb00a08d508bca4a3c4c4483e611c051ba7c539aa87ef2b33679ba94f91R625-R643)
  * [Referee diff](https://github.khoury.northeastern.edu/CS4500-F22/mysterious-whales/commit/52a392d410d9af4eb4cba935d06d2acc18853312#diff-b542ed53a91e64eac06c4ba6df49d4a437541df940e8ee98636aa324bdf8db1cR111-R113)
* Move polling Player secrets on player move to the Referee. [Commit](https://github.khoury.northeastern.edu/CS4500-F22/mysterious-whales/commit/52a392d410d9af4eb4cba935d06d2acc18853312#diff-21759bb00a08d508bca4a3c4c4483e611c051ba7c539aa87ef2b33679ba94f91L465-L524)
* Added a counter in `PlayerSecret` to keep track of the number of goals a player has reached so far. [Commit](https://github.khoury.northeastern.edu/CS4500-F22/mysterious-whales/commit/52a392d410d9af4eb4cba935d06d2acc18853312#diff-21759bb00a08d508bca4a3c4c4483e611c051ba7c539aa87ef2b33679ba94f91L138-R139)
* (BIG) Use color instead of name to keep track of players. This was very baked in, so it took a lot of changing.
  * [Commit](https://github.khoury.northeastern.edu/CS4500-F22/mysterious-whales/commit/ddaf2fa811ca90b3eef6fa4d10b5e60d91650a1d)
  * (Other commits for resulting unit test changes, no need to link)

---

# Changes unrelated to necessary revisions

### Remote referee
* Got rid of requesting player secrets from the actual players. We now get them from the state. [Commit](https://github.khoury.northeastern.edu/CS4500-F22/mysterious-whales/commit/bb5872d021018575b04e0acd129e74d463f3916a)

### Other
* Rewrote `Client`, `Server`, `RemoteReferee`, and `RemotePlayer` to use `asyncio` networking