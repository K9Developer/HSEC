import os
import socket
from socket_server_lib import constants

class SocketClient:
    def __init__(self, socket: socket.socket, addr: tuple, transfer_options: constants.DataTransferOptions = None, client_thread=None, random=None):
        self.socket = socket
        self.addr = addr
        self.is_connected = True
        self.random = random if random else os.urandom(16)
        self.transfer_options = transfer_options if transfer_options else constants.DataTransferOptions.WITH_SIZE
        self.client_thread = client_thread
        self.auto_recv = True
        assert len(self.random) == 16, "Random value must be 16 bytes long"
        assert isinstance(self.random, bytes), "Random value must be of type bytes"
    