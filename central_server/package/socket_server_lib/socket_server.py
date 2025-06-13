import ipaddress
from package.socket_server_lib import constants
import socket
import threading
from package.socket_server_lib.client import SocketClient
from Cryptodome.PublicKey import ECC
from Crypto.PublicKey.ECC import EccPoint
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
import inspect

sock_lock = threading.Lock()

class EmptyLogger:
    def info(self, message: str): pass
    def error(self, message: str): pass
    def debug(self, message: str): pass
    def warning(self, message: str): pass

import inspect

class DefaultLogger:
    def _prefix(self):
        frame = inspect.stack()[2]  # 0: _prefix, 1: error(), 2: caller
        filename = frame.filename.split("/")[-1]
        lineno = frame.lineno
        return f"[{filename}:{lineno}]"

    def info(self, message: str):
        print(f"INFO: {message}")

    def error(self, message: str):
        print(f"ERROR {self._prefix()}: {message}")

    def debug(self, message: str):
        pass  # or print(f"DEBUG: {message}")

    def warning(self, message: str):
        print(f"WARNING: {message}")


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

    def __handle_template(template: list, *args) -> list:
        if not isinstance(template, list):
            raise TypeError("Template must be a list")
        
        if template.count(constants.Options.ANY_VALUE_TEMPLATE) != len(args) and template.count(constants.Options.ANY_VALUE_ANY_LENGTH_TEMPLATE) == 0:
            raise ValueError("Template and args length mismatch")
        
        new_template = []
        arg_index = 0
        for i in range(len(template)):
            if template[i] == constants.Options.ANY_VALUE_TEMPLATE:
                new_template.append(args[arg_index])
                arg_index += 1
            elif template[i] == constants.Options.ANY_VALUE_ANY_LENGTH_TEMPLATE:
                new_template.extend(args[arg_index:])
                break
            else:
                new_template.append(template[i])

        return new_template
        

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
    
    def __send_raw_bytes(self, client: SocketClient, data: bytes, options):

        if not client.is_connected:
            self.logger.error(f"Client {client.addr} is not connected")
            return
        try:
            if self.protocol == constants.ServerProtocol.UDP:
                if constants.DataTransferOptions.WITH_SIZE in options:
                    client.socket.sendto(data[:constants.Options.MESSAGE_SIZE_BYTE_LENGTH], client.addr)
                    client.socket.sendto(data[constants.Options.MESSAGE_SIZE_BYTE_LENGTH:], client.addr)
                else:
                    client.socket.sendto(data, client.addr)
            else:
                client.socket.sendall(data)
            self.logger.debug(f"Sent raw bytes to {client.addr}")
        except Exception as e:
            self.logger.error(f"Error sending raw bytes to {client.addr}: {e}")
    
    def __data_to_bytes(self, data) -> bytes:
        def encoding(d):
            if isinstance(d, str): return d.encode('utf-8')
            if isinstance(d, bytes): return d
            if isinstance(d, int): return str(d).encode('utf-8')
            if isinstance(d, list): return constants.Options.MESSAGE_SEPARATOR.join([encoding(item) for item in d])
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
            message_size = len(modified_data).to_bytes(constants.Options.MESSAGE_SIZE_BYTE_LENGTH, 'big')
            modified_data = message_size + modified_data
            self.logger.debug(f"Data size prepended for broadcast: {len(modified_data)} bytes")
        
        broad_ip = self.__get_broadcast_address()
        tmp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        tmp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        tmp_socket.sendto(modified_data, (broad_ip, target_port))
        tmp_socket.close()
        self.logger.debug(f"Broadcasted data to port {target_port}")

    def send_data(self, client: SocketClient, data, options: constants.DataTransferOptions = constants.DataTransferOptions.WITH_SIZE):
        data = self.__data_to_bytes(data)
        modified_data = data
        if constants.DataTransferOptions.ENCRYPT_AES in options:
            cipher = client.get_aes()
            modified_data = cipher.encrypt(pad(data, AES.block_size))
            self.logger.debug(f"Data encrypted with AES for {client.addr}")
        
        if constants.DataTransferOptions.WITH_SIZE in options:
            message_size = len(modified_data).to_bytes(constants.Options.MESSAGE_SIZE_BYTE_LENGTH, 'big')
            modified_data = message_size + modified_data
            self.logger.debug(f"Data size prepended for {client.addr}: {len(modified_data)} bytes")
        
        self.__send_raw_bytes(client, modified_data, options)

    def __receive_raw_bytes(self, client: SocketClient, size: int) -> bytes:
        client.socket.settimeout(10)
        def enter():
            if not client.is_connected:
                self.logger.error(f"Client {client.addr} is not connected")
                return b""
            try:
                data = b""
                while len(data) < size:
                    chunk = client.socket.recv(size - len(data))
                    if not chunk:
                        self.logger.error(f"Client {client.addr} disconnected while receiving data")
                        return b""
                    data += chunk
            
                self.logger.debug(f"Received raw bytes from {client.addr}: {len(data)} bytes")
                return data
            except Exception as e:
                self.logger.error(f"Error receiving raw bytes from {client.addr}: {e}")
                return b""
        ret_val = enter()
        client.socket.settimeout(None)
        return ret_val

    def receive_data(self, client: SocketClient, options: constants.DataTransferOptions = constants.DataTransferOptions.WITH_SIZE, optional_buffer_size = None) -> list[bytes]:
        # while client.locked: pass
        # client.locked = True
        with sock_lock:
            if constants.DataTransferOptions.WITH_SIZE not in options and optional_buffer_size is None:
                self.logger.error("Buffer size must be specified if WITH_SIZE option is not set")
                return None
            
            message = None
            if constants.DataTransferOptions.WITH_SIZE in options:
                a = self.__receive_raw_bytes(client, constants.Options.MESSAGE_SIZE_BYTE_LENGTH)
                if not a:
                    self.logger.error(f"Failed to receive message size from {client.addr}")
                    return None
                message_size = int.from_bytes(a, 'big')
                self.logger.debug(f"Message size received from {client.addr}: {message_size} bytes")
                message = self.__receive_raw_bytes(client, message_size)
            
            if message is None:
                print("Before receiving raw bytes")
                message = self.__receive_raw_bytes(client, optional_buffer_size)
                print(f"After receiving raw bytes ({len(message)} bytes)")
            if not message:
                self.logger.error(f"No data received from {client.addr}")
                return None

            if constants.DataTransferOptions.ENCRYPT_AES in options:
                cipher = client.get_aes()
                message = unpad(cipher.decrypt(message), AES.block_size)
                self.logger.debug(f"Data decrypted with AES for {client.addr}")
            
            return message.split(constants.Options.MESSAGE_SEPARATOR)

    def receive_data_with_pattern(self, client: SocketClient, pattern: constants.SocketMessages, options: constants.DataTransferOptions = constants.DataTransferOptions.WITH_SIZE):
        if not isinstance(pattern, list):
            raise TypeError("Pattern must be a list of bytes")
        
        data = self.receive_data(client, options)
        if not data:
            self.logger.error(f"No data received from {client.addr}")
            self.disconnect_client(client)
            return None

        if len(data) != len(pattern) and not constants.Options.ANY_VALUE_ANY_LENGTH_TEMPLATE:
            return None

        for i in range(len(pattern)):
            if pattern[i] == constants.Options.ANY_VALUE_ANY_LENGTH_TEMPLATE: break
            if pattern[i] != constants.Options.ANY_VALUE_TEMPLATE and data[i] != pattern[i]:
                return None

        return data

    def __import_raw_pubkey(self, raw: bytes, curve='P-256'):
        x = int.from_bytes(raw[:32], 'big')
        y = int.from_bytes(raw[32:], 'big')
        return ECC.construct(curve=curve, point_x=x, point_y=y)

    def exchange_aes_key_with_ecdh(self, client: SocketClient):
        """
        Elliptic Curve Diffie-Hellman key exchange using pycryptodome

        server -> client: exch, ecdh, aes, server_pubkey
        client -> server: exch, ecdh, aes, client_pubkey
        client -> server: confirm & shared_secret
        """

        client.auto_recv = False
        server_privkey = ECC.generate(curve='P-256')
        server_pubkey = server_privkey.public_key()
        x = int(server_pubkey.pointQ.x).to_bytes(32, 'big')
        y = int(server_pubkey.pointQ.y).to_bytes(32, 'big')
        server_pubkey_bytes = x + y

        self.logger.debug(f"Server ECDH public key generated for {client.addr}")
        self.send_data(client, SocketServer.__handle_template(constants.SocketMessages.AesKeyExchange.SERVER_HELLO, server_pubkey_bytes), constants.DataTransferOptions.WITH_SIZE)
        self.logger.debug(f"Sent server ECDH public key ({server_pubkey_bytes.hex()})")

        client_pubkey = self.receive_data_with_pattern(client, constants.SocketMessages.AesKeyExchange.CLIENT_HELLO, constants.DataTransferOptions.WITH_SIZE)
        if not client_pubkey:
            self.logger.error(f"Client ECDH public key not received from {client.addr}")
            return False

        raw_client_pubkey = constants.Options.MESSAGE_SEPARATOR.join(client_pubkey[3:])
        client_pubkey_obj = self.__import_raw_pubkey(raw_client_pubkey)
        shared_point = server_privkey.d * client_pubkey_obj.pointQ
        shared_secret = int(shared_point.x).to_bytes(32, 'big')
        self.logger.info("Shared secret:" + shared_secret.hex())

        confirm_message = self.receive_data_with_pattern(client, constants.SocketMessages.AesKeyExchange.CLIENT_KEY_CONFIRM, constants.DataTransferOptions.WITH_SIZE)
        if not confirm_message:
            self.logger.error(f"Client confirmation not received from {client.addr}")
            return False

        client.random = shared_secret

        decrypted_message = unpad(client.get_aes().decrypt(confirm_message[0]), AES.block_size)
        if decrypted_message != b"confirm":
            self.logger.error(f"Client confirmation message not received correctly from {client.addr}")
            return False
        
        encrypted_message = client.get_aes().encrypt(pad(b"confirm", AES.block_size))
        self.send_data(client, SocketServer.__handle_template(constants.SocketMessages.AesKeyExchange.SERVER_KEY_CONFIRM, encrypted_message), constants.DataTransferOptions.WITH_SIZE)
        self.logger.debug(f"Client confirmation message sent to {client.addr}")

        self.logger.debug(f"Client confirmation message received from {client.addr}")
        client.transfer_options = client.transfer_options | constants.DataTransferOptions.ENCRYPT_AES
        client.auto_recv = True
        return True

    def match_message(self, data: list[bytes], client: SocketClient) -> callable:
        for pattern, callback in self.message_callbacks.items():
            if len(data) != len(pattern) and not constants.Options.ANY_VALUE_ANY_LENGTH_TEMPLATE in pattern:
                continue
            
            for i in range(len(pattern)):
                if pattern[i] == constants.Options.ANY_VALUE_ANY_LENGTH_TEMPLATE:
                    self.logger.debug(f"Matching message found (via ANY_VALUE_ANY_LENGTH_TEMPLATE) for {client.addr}: {pattern}")
                    return callback
                if pattern[i] != constants.Options.ANY_VALUE_TEMPLATE and data[i] != pattern[i]:
                    break
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
                    self.logger.debug(f"Executing callback ({callback.__name__}) for message from {client.addr}")
                    die = callback(client, data)
                    if die:
                        self.logger.info(f"Client {client.addr} disconnected due to callback execution")
                        self.disconnect_client(client)
                        break
                else:
                    self.logger.warning(f"No matching callback for message from {client.addr}")
                    self.__handle_callback(constants.SocketServerCallbacks.UNRECOGNIZED_MESSAGE, client, data)
            except socket.timeout:
                self.logger.warning(f"Socket timeout while receiving data from {client.addr}")
                break
            except Exception as e:
                self.logger.error(f"Error handling client {client.addr}: {e}")
                self.__handle_callback(constants.SocketServerCallbacks.CLIENT_ERROR, client, e)
                break
            # except Exception as e:
            #     self.logger.error(f"Error handling client {client.addr}: {e}")
            #     self.__handle_callback(constants.SocketServerCallbacks.CLIENT_ERROR, client, e)

    def main_loop(self):
          
        self.logger.info("Entering main loop")
        while True:
            # try:
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

            # except Exception as e:
            #     self.logger.error(f"Error in main loop: {e}")
            #     continue