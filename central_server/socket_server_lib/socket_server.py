import ipaddress
from socket_server_lib import constants
import socket
import threading
from socket_server_lib.client import SocketClient

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

class EmptyLogger:
    def info(self, message: str): pass
    def error(self, message: str): pass
    def debug(self, message: str): pass
    def warning(self, message: str): pass

class DefaultLogger(EmptyLogger):
    def info(self, message: str):
        print(f"INFO: {message}")
        pass
    
    def error(self, message: str):
        print(f"ERROR: {message}")
        pass
    
    def debug(self, message: str):
        print(f"DEBUG: {message}")
        pass
    
    def warning(self, message: str):
        print(f"WARNING: {message}")
        pass

class SocketServer:
    def __init__(self, host: str = '127.0.0.1', port: int = 8080, accept_buffer: int =1000, protocol: constants.ServerProtocol = constants.ServerProtocol.TCP, logger = None, reserve_port=True):
        self.host = host
        self.port = port
        self.logger = (logger if logger else DefaultLogger()) if logger != 0 else EmptyLogger()
    
        if port is None:
            self.logger.warning(f"Port is None, using a random port.")
            self.port = self.__get_free_port()

        self.accept_buffer = accept_buffer
        self.server_socket = None
        self.protocol = protocol
        self.reserve_port = reserve_port

        self.clients = []
        self.callbacks: dict[constants.SocketServerCallbacks, callable] = {}
        self.message_callbacks: dict[tuple, callable] = {}

        self.logger.debug(f"SocketServer initialized with host={self.host}, port={self.port}, protocol={self.protocol}")

    def __get_broadcast_address(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            net = ipaddress.IPv4Network(f"{ip}/24", strict=False)
            return str(net.broadcast_address)

    def __get_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, 0))
            return s.getsockname()[1]

    def start(self, no_loop=False):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM if self.protocol == constants.ServerProtocol.TCP else socket.SOCK_DGRAM)
        if not self.reserve_port:
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        if self.protocol != constants.ServerProtocol.UDP:
            self.server_socket.listen(self.accept_buffer)
        self.logger.info(f"Server started on {self.host}:{self.port} with protocol {self.protocol}")

        if no_loop: return
        thread = threading.Thread(target=self.main_loop)
        thread.daemon = True
        thread.start()
        self.logger.debug("Server thread started")


    def set_callback(self, callback: constants.SocketServerCallbacks, func: callable):
        if callback in self.callbacks:
            self.logger.warning(f"Callback {callback} is already set. Overwriting.")
        self.callbacks[callback] = func
        self.logger.debug(f"Callback {callback} set to {func.__name__}")
    
    def add_custom_message_callback(self, message_pattern: list, callback: callable):
        if not isinstance(message_pattern, list):
            raise TypeError("Message pattern must be a list")
        if not callable(callback):
            raise TypeError("Callback must be callable")
        
        self.message_callbacks[tuple(message_pattern)] = callback

    def disconnect_client(self, client: SocketClient):
        if client in self.clients:
            self.__handle_callback(constants.SocketServerCallbacks.ON_DISCONNECT, client)
            client.socket.close()
            self.clients.remove(client)
            client.is_connected = False
            self.logger.info(f"Client {client.addr} disconnected")
        else:
            self.logger.error(f"Client {client.addr} not found in connected clients")

    def __handle_callback(self, callback: constants.SocketServerCallbacks, *args):
        if callback in self.callbacks:
            self.logger.debug(f"Executing callback {callback} with args {args}")
            thread = threading.Thread(target=self.callbacks[callback], args=args)
            thread.daemon = True
            thread.start()
            return True

        return constants.SocketServerCallbacks.NO_CALLBACK

    def get_client(self, ip: str, port: int) -> SocketClient:
        for client in self.clients:
            if client.addr[0] == ip and client.addr[1] == port:
                return client
        return None
    
    def __send_raw_bytes(self, client: SocketClient, data: bytes):

        if not client.is_connected:
            self.logger.error(f"Client {client.addr} is not connected")
            return
        try:
            if self.protocol == constants.ServerProtocol.UDP:
                client.socket.sendto(data, client.addr)
            else:
                client.socket.sendall(data)
            self.logger.debug(f"Sent raw bytes to {client.addr}")
        except Exception as e:
            self.logger.error(f"Error sending raw bytes to {client.addr}: {e}")
    
    def __data_to_bytes(self, data, strip_msg_sep_fields=False) -> bytes:
        def encoding(d):
            if strip_msg_sep_fields and d == constants.Options.ANY_VALUE_TEMPLATE.value: return None
            if isinstance(d, str): return d.encode('utf-8')
            if isinstance(d, bytes): return d
            if isinstance(d, int): return str(d).encode('utf-8')
            if isinstance(d, list): return constants.Options.MESSAGE_SEPARATOR.value.join([encoding(item) for item in d if item != constants.Options.ANY_VALUE_TEMPLATE.value])
            raise TypeError(f"Unsupported data type: {type(d)}")
        
        return encoding(data)
    
    def broadcast(self, data, target_port: int, options: constants.DataTransferOptions = constants.DataTransferOptions.WITH_SIZE):
        data = self.__data_to_bytes(data, constants.DataTransferOptions.IS_PATTERN in options)
        modified_data = data
        if constants.DataTransferOptions.ENCRYPT_AES in options:
            cipher = AES.new(self.random, AES.MODE_CBC)
            iv = cipher.iv
            modified_data = iv + cipher.encrypt(pad(data, AES.block_size))
            self.logger.debug("Data encrypted with AES for broadcast")
        
        if constants.DataTransferOptions.WITH_SIZE in options:
            message_size = len(modified_data).to_bytes(constants.Options.MESSAGE_SIZE_BYTE_LENGTH.value, 'big')
            modified_data = message_size + modified_data
            self.logger.debug(f"Data size prepended for broadcast: {len(modified_data)} bytes")
        
        broad_ip = self.__get_broadcast_address()
        tmp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        tmp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        tmp_socket.sendto(modified_data, (broad_ip, target_port))
        tmp_socket.close()
        self.logger.debug(f"Broadcasted data to port {target_port}")

    def send_data(self, client: SocketClient, data, options: constants.DataTransferOptions = constants.DataTransferOptions.WITH_SIZE):
        data = self.__data_to_bytes(data, constants.DataTransferOptions.IS_PATTERN in options)
        modified_data = data
        if constants.DataTransferOptions.ENCRYPT_AES in options:
            cipher = AES.new(client.random, AES.MODE_CBC)
            iv = cipher.iv
            modified_data = iv + cipher.encrypt(pad(data, AES.block_size))
            self.logger.debug(f"Data encrypted with AES for {client.addr}")
        
        if constants.DataTransferOptions.WITH_SIZE in options:
            message_size = len(modified_data).to_bytes(constants.Options.MESSAGE_SIZE_BYTE_LENGTH.value, 'big')
            modified_data = message_size + modified_data
            self.logger.debug(f"Data size prepended for {client.addr}: {len(modified_data)} bytes")
        
        self.__send_raw_bytes(client, modified_data)

    def __receive_raw_bytes(self, client: SocketClient, size: int) -> bytes:
        if not client.is_connected:
            self.logger.error(f"Client {client.addr} is not connected")
            return b""
        try:
            data = b""
            for _ in range(size):
                chunk = client.socket.recv(1)
                if not chunk:
                    self.logger.error(f"Client {client.addr} disconnected while receiving data")
                    break
                data += chunk
          
            self.logger.debug(f"Received raw bytes from {client.addr}: {data}")
            return data
        except Exception as e:
            self.logger.error(f"Error receiving raw bytes from {client.addr}: {e}")
            return b""

    def receive_data(self, client: SocketClient, options: constants.DataTransferOptions = constants.DataTransferOptions.WITH_SIZE, optional_buffer_size = None) -> list[bytes]:
        if constants.DataTransferOptions.WITH_SIZE not in options and optional_buffer_size is None:
            self.logger.error("Buffer size must be specified if WITH_SIZE option is not set")
            return b""
        
        message = None
        if constants.DataTransferOptions.WITH_SIZE in options:
            message_size = int.from_bytes(self.__receive_raw_bytes(client, constants.Options.MESSAGE_SIZE_BYTE_LENGTH.value), 'big')
            self.logger.debug(f"Message size received from {client.addr}: {message_size} bytes")
            message = self.__receive_raw_bytes(client, message_size)
        
        if message is None:
            message = self.__receive_raw_bytes(client, optional_buffer_size)

        if constants.DataTransferOptions.ENCRYPT_AES in options:
            cipher = AES.new(client.random, AES.MODE_CBC, client.random[:AES.block_size])
            message = unpad(cipher.decrypt(message), AES.block_size)
            self.logger.debug(f"Data decrypted with AES for {client.addr}")
        
        return message.split(constants.Options.MESSAGE_SEPARATOR.value)

    def receive_data_with_pattern(self, client: SocketClient, pattern: constants.SocketMessages, options: constants.DataTransferOptions = constants.DataTransferOptions.WITH_SIZE):
        if not isinstance(pattern, list):
            raise TypeError("Pattern must be a list of bytes")
        
        data = self.receive_data(client, options)
        if not data:
            self.logger.error(f"No data received from {client.addr}")
            return None

        if len(data) != len(pattern) and not constants.Options.ANY_VALUE_ANY_LENGTH_TEMPLATE:
            return False

        for i in range(len(pattern)):
            if pattern[i] == constants.Options.ANY_VALUE_ANY_LENGTH_TEMPLATE: break
            if pattern[i] != constants.Options.ANY_VALUE_TEMPLATE.value and data[i] != pattern[i]:
                return False

        return data

    def exchange_aes_key_with_rsa(self, client: SocketClient):
        """
        PKCS1_OAEP is used for RSA encryption/decryption

        server -> client: exch,rsa
        client -> server: exch,rsa,client_rsa_pubkey
        server -> client: client_rsa_pubkey&data
        client -> server: confirm&data
        """
        client.auto_recv = False
        self.send_data(client, constants.SocketMessages.AesKeyExchange.SERVER_HELLO, constants.DataTransferOptions.WITH_SIZE | constants.DataTransferOptions.IS_PATTERN)
        self.logger.debug(f"Sent server hello to {client.addr}")
        client_hello = self.receive_data_with_pattern(client, constants.SocketMessages.AesKeyExchange.CLIENT_HELLO, constants.DataTransferOptions.WITH_SIZE)
        if not client_hello:
            self.logger.error(f"Client hello not received from {client.addr}")
            return False
        
        client_rsa_pubkey = client_hello[3]
        client_rsa_pubkey = PKCS1_OAEP.new(RSA.import_key(client_rsa_pubkey))
        self.logger.debug(f"Received client RSA public key from {client.addr}")
        encrypted_random = client_rsa_pubkey.encrypt(client.random)
        self.logger.debug(f"Encrypted random value with client RSA public key for {client.addr}")
        self.send_data(client, encrypted_random, constants.DataTransferOptions.WITH_SIZE | constants.DataTransferOptions.IS_PATTERN)
        self.logger.debug(f"Sent encrypted random value to {client.addr}")
        client_confirm = self.receive_data_with_pattern(client, constants.SocketMessages.AesKeyExchange.CLIENT_KEY_CONFIRM, constants.DataTransferOptions.WITH_SIZE | constants.DataTransferOptions.IS_PATTERN | constants.DataTransferOptions.ENCRYPT_AES)
        if not client_confirm or client_confirm[0] != b"confirm":
            self.logger.error(f"Client confirmation not received from {client.addr}")
            return False
        
        self.logger.debug(f"Client confirmation received from {client.addr}")
        client.transfer_options = client.transfer_options | constants.DataTransferOptions.ENCRYPT_AES
        client.auto_recv = True
        return True

    def match_message(self, data: list[bytes], client: SocketClient) -> callable:
        for pattern, callback in self.message_callbacks.items():
            if len(data) != len(pattern) and not constants.Options.ANY_VALUE_ANY_LENGTH_TEMPLATE:
                return False
            
            for i in range(len(pattern)):
                if pattern[i] == constants.Options.ANY_VALUE_ANY_LENGTH_TEMPLATE: break
                if pattern[i] != constants.Options.ANY_VALUE_TEMPLATE and data[i] != pattern[i]: break
            else:
                self.logger.debug(f"Matching message found for {client.addr}: {pattern}")
                return callback
        
        self.logger.warning(f"No matching message found for {client.addr}")
        return None        

    def __handle_client(self, client: SocketClient):
        while client.is_connected:
            if not client.auto_recv: continue
            try:
                data = self.receive_data(client, client.transfer_options)
                if not data:
                    self.logger.info(f"No data received from {client.addr}, disconnecting")
                    self.disconnect_client(client)
                    break

                self.logger.debug(f"Data received from {client.addr}: {data}")
                callback = self.match_message(data, client)
                if callback:
                    self.logger.debug(f"Executing callback for message from {client.addr}")
                    die = callback(client, data)
                    if die:
                        self.logger.info(f"Client {client.addr} disconnected due to callback execution")
                        self.disconnect_client(client)
                        break
                else:
                    self.logger.warning(f"No matching callback for message from {client.addr}")
                    self.__handle_callback(constants.SocketServerCallbacks.UNRECOGNIZED_MESSAGE, client, data)
            except Exception as e:
                self.logger.error(f"Error handling client {client.addr}: {e}")
                self.__handle_callback(constants.SocketServerCallbacks.CLIENT_ERROR, client, e)

    def main_loop(self):
        self.logger.info("Entering main loop")
        while True:
            try:
                client_socket, addr = self.server_socket.accept()
                self.__handle_callback(constants.SocketServerCallbacks.ON_BEFORE_CONNECT, client_socket, addr)

                client = SocketClient(client_socket, addr)
                self.__handle_callback(constants.SocketServerCallbacks.ON_CONNECT, client)

                transfer_options = constants.DataTransferOptions.WITH_SIZE
                self.logger.debug(f"Default transfer options set to {transfer_options}")

                thread = threading.Thread(target=self.__handle_client, args=(client,))
                thread.daemon = True
                thread.start()
                client.client_thread = thread

                self.clients.append(client)
                self.logger.info(f"Accepted connection from {addr}")

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                break