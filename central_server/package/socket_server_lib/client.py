import os
import socket
from package.socket_server_lib import constants
from Cryptodome.Cipher import AES

class SocketClient:
    def __init__(self, socket: socket.socket | None, addr: tuple, transfer_options: constants.DataTransferOptions | None = None, client_thread=None, random=None):
        self.socket = socket
        self.addr = addr
        self.is_connected = True
        self.random = random if random else os.urandom(32)
        self.transfer_options = transfer_options if transfer_options else constants.DataTransferOptions.WITH_SIZE
        self.client_thread = client_thread
        self.auto_recv = True
        self.aes_obj = None
        self.locked = False
        assert len(self.random) == 32, "Random value must be 32 bytes long"
        assert isinstance(self.random, bytes), "Random value must be of type bytes"
    
    def get_aes(self):
        return AES.new(self.random, AES.MODE_CBC, self.random[:AES.block_size])