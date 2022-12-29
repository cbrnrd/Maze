# TODO

# Completed

In priority order:

1. Handle player return values for setup/win and handle timeouts for all player methods
  - 92730b9 - Handle player timeouts and return values for all player methods
2. Enforce distinct player homes
  - a10053d - Enforce distinct player homes for create_initial_game_state
  - faed943 - Enforce distinct player homes in start_game_from_state
  - 363cb73 - Keep failing players from using up distinct homes and clean up start_game methods
  - 38dc85b - Turn off distinct home enforcement for test harness, misc code cleanup
3. Double check that we don't strictly enforce a 7x7 board
  - 91aaadb - Remove board size enforcement from deserializers and referee
  - e03e641 - Adjust default referee goal to accommodate flexible board size
4. Change Coord to a proper data class with row/col properties and use in all relevant methods
  - 20a69a5 - Create Coord data class and refactor code to use it
  - b0c4987 - Remove color from player and fix a few more Coords
  - 8d23a77 - Fix Coords in JSON serializers
5. Remove color from the player. When it receives a state, the player should know that it is the one at index 0. 
  - b0c4987 - Remove color from player and fix a few more Coords
  - 7e321c9 - Test distinct random colors in referee tests
6. Validate that all treasure pairs on the board are distinct
  - 0131420 - Validate gem pair uniqueness on board and spare tile
7. Add README.md with overview of code (ascii diagrams, etc)
  - f40443e - Add README with ASCII diagrams
