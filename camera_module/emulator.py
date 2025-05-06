import ipaddress
import socket
import time
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import enum
import cv2

class Constants:
    CAMERA_DISCOVER_PORT = 5000
    CAMERA_HANDLER_PORT = 5001

    MESSAGE_SEPARATOR = b"\0"
    MESSAGE_LENGTH_BYTES = 4

class State(enum.Flag):
    IDLE = enum.auto()
    DISCOVERING = enum.auto()
    LINKED = enum.auto()
    REPEAIRING = enum.auto()


class Task:
    def __init__(self, func, interval):
        self.func = func
        self.interval = interval
        self.last_run = 0
    
    def tick(self, *args):
        current_time = time.time()
        if current_time - self.last_run >= self.interval:
            self.last_run = current_time
            return self.func(*args)
    
    def force_run(self, *args):
        self.last_run = 0
        return self.func(*args)
        

class Camera:
    def __init__(self):
        self.CAMERA_MAC = "12:34:56:78:90:AB"
        self.CAMERA_CODE = "1234"

        self.server_ip = ""
        self.server_port = 0
        self.server_socket = None
        self.aes = None
        self.broadcast_ip = None

        self.camera_handle = cv2.VideoCapture(0)
        if not self.camera_handle.isOpened():
            print("Error: Could not open webcam.")
            return

        self.discover_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.current_state = State.IDLE
        if self.server_ip == "":
            self.current_state |= State.DISCOVERING
        else:
            self.current_state |= State.REPEAIRING

        self.ping_discover_task = Task(self.__discover_ping, 2)
        self.pair_check_task = Task(self.__check_pairing_request, 1)
        self.repair_task = Task(self.__repair_to_server, -1)
        self.stream_task = Task(self.__stream_frame, -1)

    def loop(self):
        if self.current_state & State.DISCOVERING:
            self.ping_discover_task.tick()
            self.pair_check_task.tick()

        if self.current_state & State.REPEAIRING:
            self.repair_task.tick()
        
        if self.current_state & State.LINKED:
            self.stream_task.tick()

    def __stream_frame(self):
        if self.server_socket is None:
            print("No server socket available for streaming.")
            return
        
        # grab from webcam
        ret, frame = self.camera_handle.read()
        if not ret:
            print("Error: Could not read frame from webcam.")
            return

        # encode frame as JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        data = buffer.tobytes()

        # send frame to server
        self.__send_fields(
            self.server_socket,
            (self.server_ip, self.server_port),
            [b"CAMFRAME-HSEC", data],
            encrypt=True,
        )
        

    def __repair_to_server(self):
        if self.server_socket is None:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.connect((self.server_ip, self.server_port))
        
        self.server_socket.sendall(
            Constants.MESSAGE_SEPARATOR.join([b"CAMRELINK-HSEC", self.CAMERA_MAC.encode()])
        )

        fields = self.__recv_fields(self.server_socket)
        if len(fields) != 2 or fields[0] != b"CAMREPAIR-HSEC":
            print(f"Invalid repair message: {fields}")
            return
        
        decrypted_confirm = self.aes.decrypt(unpad(fields[1], AES.block_size))
        if decrypted_confirm != b"confirm-pair":
            print("Invalid confirmation message received")
            return
        
        encrypted_confirm = self.aes.encrypt(pad(b"confirm-pair-ack", AES.block_size))
        self.__send_fields(
            self.server_socket,
            (self.server_ip, self.server_port),
            [b"CAMREPAIRACK-HSEC", encrypted_confirm],
        )

        print("Successfully repaired to server.")
        self.current_state &= ~State.REPEAIRING
        self.current_state |= State.LINKED

    def __discover_ping(self):
        self.broadcast_ip = self.__get_broadcast_ip() if self.broadcast_ip is None else self.broadcast_ip
        self.discover_server.sendto(
            Constants.MESSAGE_SEPARATOR.join([b"CAMPAIR-HSEC", self.CAMERA_MAC.encode()]),
            (self.broadcast_ip, Constants.CAMERA_DISCOVER_PORT),
        )
    
    def __check_pairing_request(self):
        self.discover_server.settimeout(1)
        try:
            fields, addr = self.discover_server.recvfrom(1024)
            if len(fields) != 3:
                print(f"Invalid pairing message: {fields}")
                return

            if fields[0] == b"CAMACK-HSEC" and fields[2] == self.CAMERA_CODE.encode():
                self.server_ip = addr[0]
                self.server_port = int(fields[1])
                self.__link_to_server()

        except socket.timeout:
            pass

    def __handle_aes_key_exchange(self, soc: socket.socket):
        server_hello = self.__recv_fields(soc)
        if len(server_hello) != 4 or \
           server_hello[0] != b"exch" or \
           server_hello[1] != b"ecdh" or \
           server_hello[2] != b"aes":
            return False

    def __link_to_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.connect((self.server_ip, self.server_port))
        self.server_socket.sendall(
            Constants.MESSAGE_SEPARATOR.join([b"CAMLINK-HSEC", self.CAMERA_MAC.encode()])
        )

        success, shared_secret = self.__handle_aes_key_exchange(self.server_socket)
        if not success:
            print("Failed to exchange keys with server.")
            return
        
        self.aes = AES.new(shared_secret, AES.MODE_CBC, shared_secret[:16])
        confirm_encrypted = self.aes.encrypt(pad(b"confirm"))
        self.__send_fields(
            self.server_socket,
            (self.server_ip, self.server_port),
            [confirm_encrypted],
        )

        confirm_encrypted = self.__recv_fields(self.server_socket, decrypt=True)
        if len(confirm_encrypted) != 1:
            print("Invalid confirmation message received")
            return
        
        decrypted_confirm = self.aes.decrypt(unpad(confirm_encrypted[0], AES.block_size))
        if decrypted_confirm != b"confirm":
            print("Invalid confirmation message received")
            return
        
        print("Successfully linked to server.")
        self.current_state &= ~State.DISCOVERING
        self.current_state |= State.LINKED

    def __get_broadcast_ip(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            net = ipaddress.IPv4Network(f"{ip}/24", strict=False)
            return str(net.broadcast_address)
   
    def __handle_aes_key_exchange(self, soc: socket.socket):
        server_hello = self.__recv_fields(soc)
        if len(server_hello) != 4 or \
           server_hello[0] != b"exch" or \
           server_hello[1] != b"ecdh" or \
           server_hello[2] != b"aes":
            return False, None
        
        raw_server_pubkey = server_hello[3]
        server_pubkey = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw_server_pubkey)
        private_key = ec.generate_private_key(ec.SECP256R1())
        shared_secret = private_key.exchange(ec.ECDH(), server_pubkey)
        pubkey = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )

        self.__send_fields(
            soc,
            (self.server_ip, self.server_port),
            [b"exch", b"ecdh", b"aes", pubkey],
        )

        aes = AES.new(shared_secret, AES.MODE_CBC, shared_secret[:16])
        encrypted_confirm = aes.encrypt(pad(b"confirm"))
        self.__send_fields(
            soc,
            (self.server_ip, self.server_port),
            [encrypted_confirm],
        )

        encrypted_confirm = self.__recv_fields(soc, decrypt=True)
        if len(encrypted_confirm) != 1:
            return False, None
        
        decrypted_confirm = aes.decrypt(unpad(encrypted_confirm[0], AES.block_size))
        if decrypted_confirm != b"confirm":
            return False, None

        return True, shared_secret

    
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
           data = unpad(self.aes.decrypt(data), AES.block_size)

       return data.split(Constants.MESSAGE_SEPARATOR), addr

    def __send_fields(self, soc: socket.socket, addr, fields, encrypt=False):
        data = Constants.MESSAGE_SEPARATOR.join(fields)
        
        if encrypt and self.aes_code:
            data = self.aes.encrypt(pad(data, AES.block_size))

        length = len(data).to_bytes(Constants.MESSAGE_LENGTH_BYTES, byteorder='big')
        if soc.type == socket.SOCK_DGRAM:
            soc.sendto(length + data, addr)
        else:
            soc.send(length + data)

if __name__ == "__main__":
    camera = Camera()
    while True:
        camera.loop()
        time.sleep(0.1)