# Note: All uses of sys.stdout redirection to StringIO() were adapted from https://stackoverflow.com/a/1218951
import asyncio
import random
import socket
import sys
import time
import unittest
from collections import OrderedDict
from io import StringIO
from threading import Thread
from time import perf_counter, sleep
from typing import List

import pytest

from Maze.Common.JSON.serializers import color_to_json
from Maze.Common.state import GameState, PlayerSecret, PlayerState, RefereeGameState
from Maze.Common.test_board import ascii_board
from Maze.Common.test_tile import default_gems
from Maze.Common.tile import Tile, TileShape
from Maze.Common.utils import Coord
from Maze.Server.async_server import AsyncServer
from Maze.Server.server import Server


class TestServer:
    @pytest.fixture
    def port(self) -> int:
        return random.randint(10000, 60000)

    @pytest.fixture
    def server(self, port) -> AsyncServer:
        return AsyncServer("localhost", port)

    @pytest.fixture
    def game_state(self) -> GameState:
        color1 = (160, 0, 255)
        color2 = (0, 255, 255)
        concentric_board = ascii_board(
            # 123456
            "┌─────┐",  # 0
            "│┌───┐│",
            "││┌─┐││",  # 2
            "│││┼│││",
            "││└─┘││",  # 4
            "│└───┘│",
            "└─────┘",  # 6
        )
        player_states = OrderedDict(
            [
                (
                    color_to_json(color1),
                    PlayerState(Coord(1, 1), Coord(1, 1), color1, "Zoe"),
                ),
                (
                    color_to_json(color2),
                    PlayerState(Coord(5, 1), Coord(5, 1), color2, "Xena"),
                ),
            ]
        )
        player_secrets = {
            color_to_json(color1): PlayerSecret(Coord(1, 5), False),
            color_to_json(color2): PlayerSecret(Coord(5, 5), False),
        }
        spare_tile = Tile(TileShape.LINE, 0, default_gems)
        return RefereeGameState(
            player_states,
            player_secrets,
            spare_tile,
            concentric_board,
        )

    async def sleep_and_connect_with_name(
        self, port: int, name: str, sleep: float = 1.0, sleep_after_connect=False
    ) -> socket.socket:
        if not sleep_after_connect:
            await asyncio.sleep(sleep)
        await asyncio.sleep(0.1)  # Needed to let server start
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("localhost", port))
        if sleep_after_connect:
            await asyncio.sleep(sleep)
        sock.sendall(name.encode("utf-8"))
        return sock

    @pytest.mark.asyncio
    async def test_client_connect(
        self,
        server,
        port,
    ):
        server.PLAYER_SIGNUP_WAIT = 4
        server.CLIENT_NAME_WAIT = 2
        result = server.start()
        assert server.player_names == []
        results = await asyncio.gather(result, self.sleep_and_connect_with_name(port, '"Zoe"', 1.0))
        assert results[0] == [[], []]
        assert server.player_names == ["Zoe"]
        assert len(server.remote_player_proxies) == 1

    @pytest.mark.asyncio
    async def test_waiting_periods(self, server, port):
        start_time = perf_counter()
        server.PLAYER_SIGNUP_WAIT = 2
        server.CLIENT_NAME_WAIT = 1
        result = await server.start()
        assert result == [[], []]
        assert perf_counter() - start_time > 2

    @pytest.mark.asyncio
    async def test_server_rejects_on_name_timeout(self, server, port):
        server.PLAYER_SIGNUP_WAIT = 2
        server.CLIENT_NAME_WAIT = 1
        result = server.start()
        await asyncio.gather(result, self.sleep_and_connect_with_name(port, '"Zoe"', 2, True))
        assert server.player_names == []
        assert len(server.remote_player_proxies) == 0

    @pytest.mark.asyncio
    async def test_server_rejects_player_connection_on_illegal_name(self, server, port):
        server.PLAYER_SIGNUP_WAIT = 2
        server.CLIENT_NAME_WAIT = 1
        result = server.start()
        results = await asyncio.gather(
            result,
            self.sleep_and_connect_with_name(port, '"lllllllllllllllllllllllllllllllll"', 0.5),
        )
        assert server.player_names == []
        assert len(server.remote_player_proxies) == 0

    @pytest.mark.asyncio
    async def test_same_name_clients(self, server, port):
        server.PLAYER_SIGNUP_WAIT = 2
        server.CLIENT_NAME_WAIT = 1
        result = server.start()
        await asyncio.gather(
            result,
            self.sleep_and_connect_with_name(port, '"Zoe"', 1),
            self.sleep_and_connect_with_name(port, '"Zoe"', 1),
        )
        assert server.player_names == ["Zoe", "Zoe"]
        assert len(server.remote_player_proxies) == 2

    @pytest.mark.asyncio
    async def test_game_starts_when_max_players_connected(self, server, port, game_state):
        server.PLAYER_SIGNUP_WAIT = 20
        server.CLIENT_NAME_WAIT = 1
        server.MAX_PLAYERS = 2
        server.MIN_PLAYERS = 1
        result = server.start()
        results = await asyncio.gather(
            result,
            self.sleep_and_connect_with_name(port, '"Zoe"', 0.1),
            self.sleep_and_connect_with_name(port, '"Xena"', 0.2),
            self.sleep_and_connect_with_name(port, '"Alice"', 0.3),
        )
        assert server.player_names == ["Zoe", "Xena"]
        assert len(server.remote_player_proxies) == 2
        assert results[0] == [[], ["Xena", "Zoe"]]
