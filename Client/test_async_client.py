import asyncio
from collections import OrderedDict

import asynctest

from Maze.Client.async_client import AsyncClient
from Maze.Common.JSON.serializers import color_to_json
from Maze.Common.state import PlayerState, PlayerSecret, RestrictedGameState
from Maze.Common.test_board import ascii_board
from Maze.Common.test_tile import default_gems
from Maze.Common.tile import Tile, TileShape
from Maze.Common.utils import Coord
from Maze.Players.player import Player
from Maze.Players.strategy import EuclidStrategy
from Maze.Remote.player import ProxyPlayer


class TestAsyncClient(asynctest.TestCase):

    def setUp(self):
        self.name = "testplayer"
        self.player = Player(self.name, EuclidStrategy())
        self.host = "localhost"
        self.port = 12345
        self.client = AsyncClient(self.host, self.port)
        self.reader = asynctest.mock.Mock(asyncio.StreamReader)
        self.writer = asynctest.mock.Mock(asyncio.StreamWriter)
        self.client._server_connection = (self.reader, self.writer)
        self.proxy_player = ProxyPlayer("Zoe", self.reader, self.writer)
        self.num_read_calls = 0

        self.five_by_five_board = ascii_board(
            # 1234
            "┌┬┬┬┐",  # 0
            "├┼┼┼┤",
            "├┼┼┼┤",  # 2
            "├┼┼┼┤",
            "└┴┴┴┘",  # 4
        )
        self.color1 = (160, 0, 255)
        self.color2 = (0, 255, 255)
        self.player_states = OrderedDict(
            [
                (
                    color_to_json(self.color1),
                    PlayerState(Coord(1, 1), Coord(1, 1), self.color1, "Zoe"),
                ),
                (
                    color_to_json(self.color2),
                    PlayerState(Coord(3, 1), Coord(3, 1), self.color2, "Xena"),
                ),
            ]
        )
        self.player_secrets = {
            color_to_json(self.color1): PlayerSecret(Coord(1, 3), False),
        }
        self.spare_tile = Tile(TileShape.LINE, 0, default_gems)
        self.restricted_state = RestrictedGameState(
            self.player_states,
            self.player_secrets,
            self.spare_tile,
            self.five_by_five_board,
        )

    async def test_is_connected(self):
        self.assertTrue(self.client.is_connected)
        self.client._server_connection = None
        self.assertFalse(self.client.is_connected)

    async def test_connect_error_cases(self):
        self.client._server_connection = None
        with self.assertRaises(asyncio.exceptions.TimeoutError):
            await asyncio.wait_for(self.client.connect(), 1)  # No server running, so should time out

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        data = await reader.read(100)
        self.writer.write.assert_called_once_with(data)
        await self.writer.drain()
        self.writer.close()

    async def test_valid_connect(self):
        self.client._server_connection = None
        await asyncio.start_server(self._handle_connection, self.host, self.port)
        await self.client.connect()
        self.assertTrue(self.client.is_connected)

    async def test_start_remote_referee(self):
        # XXX: NOT WORKING
        # Send name on writer
        await self.client.send_name(self.name)
        await self.client.start_remote_referee(self.player)


    async def test_send_name(self):
        await self.client.send_name(self.name)
        self.writer.write.assert_called_once_with(b'"testplayer"')


"""
class TestClient(unittest.TestCase):
    def setUp(self):
        self.host = "localhost"
        self.port = 12345
        self.name = "testplayer"
        self.client_thread = Thread(target=self.connect_client_and_send_name, args=())
        self.client_thread.start()
        self.set_up_listener()

    def tearDown(self) -> None:
        self.client._server_connection.close()
        self.listener_sock.close()

    def connect_client_and_send_name(self):
        sleep(1)
        self.client = Client(self.host, self.port)
        self.client.send_name(self.name)

    def set_up_listener(self):
        self.listener_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener_sock.bind((self.host, self.port))
        self.listener_sock.listen(1)
        self.listener_client_sock, address = self.listener_sock.accept()

    def test_client_sends_name(self):
        self.assertEqual(
            self.listener_client_sock.recv(4096).decode("utf-8"), self.name
        )

    def test_is_connected(self):
        self.assertTrue(self.client.is_connected)
        # Try to connect to a server that doesn't exist, should fail
        with self.assertRaises(ConnectionError) as context:
            false_client = Client(self.host, self.port + 1)
            self.assertTrue("Could not connect to server" in str(context.exception))
            self.assertFalse(false_client.is_connected)

    def test_multiple_connection_attempts(self):
        # Try to connect to a server that doesn't exist, should fail
        with self.assertRaises(ConnectionError) as context:
            Client(self.host, self.port + 1)
            self.assertTrue("Could not connect to server" in str(context.exception))

    def test_connect_with_bad_hostname(self):
        with self.assertRaises(ConnectionError) as context:
            Client("!@#$%^&*(//..///", self.port)
            self.assertTrue("Invalid host name" in str(context.exception))

"""
