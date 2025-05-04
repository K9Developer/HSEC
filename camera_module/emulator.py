import ipaddress
import socket
import time
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


class Constants:
    CAMERA_DISCOVER_PORT = 5000
    CAMERA_HANDLER_PORT = 5001

    MESSAGE_SEPARATOR = b"\0"
    MESSAGE_LENGTH_BYTES = 4

class Camera:
    def __init__(self):
        self.CAMERA_MAC = "12:34:56:78:90:AB"
        self.CAMERA_CODE = "1234"

        self.server_ip = ""
        self.server_port = 0
        self.server_socket = None
        self.aes_code = None

        self.pairing_mode = False

        self.discover_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if self.server_ip == "":
            self.discover_ping_loop()
            self.listen_for_pairing()
        else:
            # re pair
            pass

    def __get_broadcast_ip(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            net = ipaddress.IPv4Network(f"{ip}/24", strict=False)
            return str(net.broadcast_address)

    def __recv_fields(self, soc: socket.socket, decrypt=False):
        recv_func = soc.recvfrom if soc.type == socket.SOCK_DGRAM else soc.recv

        len_bytes, addr = recv_func(Constants.MESSAGE_LENGTH_BYTES)
        if len(len_bytes) != Constants.MESSAGE_LENGTH_BYTES:
            raise ValueError("Invalid length bytes received")
        
        length = int.from_bytes(len_bytes, byteorder='big')
        data = recv_func(length)
        if len(data) != length:
            raise ValueError("Invalid data length received")
        
        if decrypt and self.aes_code:
            aes = AES.new(self.aes_code, AES.MODE_CBC, self.aes_code)
            data = unpad(aes.decrypt(data), AES.block_size)

        return data.split(Constants.MESSAGE_SEPARATOR), addr

    def __send_fields(self, soc: socket.socket, addr, fields, encrypt=False):
        data = Constants.MESSAGE_SEPARATOR.join(fields)
        
        if encrypt and self.aes_code:
            aes = AES.new(self.aes_code, AES.MODE_CBC, self.aes_code)
            data = aes.encrypt(pad(data, AES.block_size))

        length = len(data).to_bytes(Constants.MESSAGE_LENGTH_BYTES, byteorder='big')
        if soc.type == socket.SOCK_DGRAM:
            soc.sendto(length + data, addr)
        else:
            soc.send(length + data)

    def __handle_aes_key_exchange(self, soc: socket.socket):
        server_hello = self.__recv_fields(soc)
        if len(server_hello) != 3 or \
           server_hello[0] != b"exch" or \
           server_hello[1] != b"rsa" or \
           server_hello[2] != b"aes":
            return False
        
        pubkey = PKCS1_OAEP.new(RSA.generate(2048))

        self.__send_fields(
            soc,
            (self.server_ip, self.server_port),
            [b"exch", b"rsa", b"aes", pubkey.export_key()],
        )

        server_encrypted_key = self.__recv_fields(soc)
        if len(server_encrypted_key) != 4 or \
           server_encrypted_key[0] != b"exch" or \
           server_encrypted_key[1] != b"rsa" or \
           server_encrypted_key[2] != b"aes":
            return False
        
        encrypted_aes_key = server_encrypted_key[3]
        aes_key = pubkey.decrypt(encrypted_aes_key)
        aes_key = aes_key[:16]
        self.aes_code = aes_key

        aes = AES.new(aes_key, AES.MODE_CBC, aes_key)
        encrypted_confirm = aes.encrypt(pad(b"confirm"))
        self.__send_fields(
            soc,
            (self.server_ip, self.server_port),
            [encrypted_confirm],
        )

        return True

    def link_to_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.connect((self.server_ip, self.server_port))
        self.__send_fields(
            self.server_socket,
            (self.server_ip, self.server_port),
            [b"CAMLINK-HSEC", self.CAMERA_MAC.encode()],
        )

        success = self.__handle_aes_key_exchange(self.server_socket)
        if not success:
            print("Failed to exchange keys with server.")
            return
        
        print("Successfully linked to server.")
        self.pairing_mode = False

    def discover_ping_loop(self):
        self.pairing_mode = True

        broadcast_ip = self.__get_broadcast_ip()
        last_ping = time.time()
        while self.pairing_mode and time.time() - last_ping < 3:
            self.__send_fields(
                self.discover_server,
                (broadcast_ip, Constants.CAMERA_DISCOVER_PORT),
                [b"CAMPAIR-HSEC", self.CAMERA_MAC.encode()],
            )
            print(f"Pairing mode: Sending discovery packet to {broadcast_ip}")
            last_ping = time.time()

    def listen_for_pairing(self):
        self.discover_server.settimeout(1)
        while self.pairing_mode:
            try:
                fields, addr = self.__recv_fields(self.discover_server)
                if len(fields) != 3:
                    print(f"Invalid pairing message: {fields}")
                    continue

                if fields[0] == b"CAMACK-HSEC" and fields[2] == self.CAMERA_CODE.encode():
                    self.server_ip = addr[0]
                    self.server_port = fields[1]
                    self.link_to_server()

            except socket.timeout:
                continue

    def repair_to_server(self):
        pass

    def send_frame(self):
        pass

    def take_picture(self):
        pass

