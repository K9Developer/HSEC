import time
from ..socket_server_lib.socket_server import DefaultLogger, SocketServer, constants, SocketClient
from package.camera_server.constants import Constants, Messages
import socket
from package.camera_server.database_manager import CameraDatabase, Camera
import threading
from Cryptodome.Util.Padding import pad, unpad
from Cryptodome.Cipher import AES

# TODO: How could we make a re-pair? we need to battle arp spoofing too0
# TODO: Make the frames sent over UDP


class CameraServer:
    def __init__(self, callbacks: dict, logger=DefaultLogger()):
        self.logger = logger
        self.connected_cameras: dict[str, Camera] = {}

        # This server listens for camera pairing mode broadcasts
        self.camera_discover_server = SocketServer(
            host="0.0.0.0",
            port=Constants.DISCOVER_CAMERA_QUERY_PORT,
            protocol=constants.ServerProtocol.UDP,
            logger=logger,
        )
        self.camera_discover_server.start(no_loop=True)

        # This server registers new cameras and handles camera data
        self.camera_server = SocketServer(
            host="0.0.0.0",
            port=Constants.CAMERA_HANDLER_PORT,
            protocol=constants.ServerProtocol.TCP,
            logger=logger,
        )
        self.camera_server.start()

        self.callbacks = callbacks
        self.discovering_cameras = True
        self.cameras_awaiting_pairing = set()
        self.streaming_cameras = set()

        self.db = CameraDatabase()

        self.camera_server.set_callback(
            constants.SocketServerCallbacks.ON_DISCONNECT,
            self.__on_camera_disconnect,
        )

        self.camera_server.add_custom_message_callback(
            Messages.CAMERA_PAIR_REQUEST,
            self.__handle_pair_request,
        )
        
        self.camera_server.add_custom_message_callback(
            Messages.CAMERA_REPAIR_REQUEST,
            self.__handle_repair_request,
        )

        self.camera_server.add_custom_message_callback(
            Messages.CAMERA_FRAME,
            self.__handle_frame,
        )

    @staticmethod
    def __does_match_pattern(data, pattern):
        if len(data) != len(pattern):
            print(f"Data length {len(data)} does not match pattern length {len(pattern)}")
            return False
        
        for i in range(len(data)):
            if data[i] != pattern[i] and pattern[i] != constants.Options.ANY_VALUE_TEMPLATE:
                print(f"Data {data[i]} does not match pattern {pattern[i]}")
                return False
            
        return True

    @staticmethod
    def __handle_template(template, *args):
        if template.count(constants.Options.ANY_VALUE_TEMPLATE) != len(args):
            raise ValueError("Number of arguments does not match the number of template placeholders")
        
        new_template = []
        placeholder_ind = 0
        for i in range(len(template)):
            if template[i] == constants.Options.ANY_VALUE_TEMPLATE:
                new_template.append(args[placeholder_ind])
                placeholder_ind += 1
            else:
                new_template.append(template[i])
        
        return new_template

    def __validate_camera_mac(self, camera_mac):
        return camera_mac.startswith(Constants.CAMERA_MAC_PREFIX)

    def __build_camera_client(self, camera_addr, soc=None):
        return SocketClient(
            addr=camera_addr,
            socket=soc
        )

    def discover_cameras(self, timeout=-1):
        start = time.time()
        if self.camera_discover_server.server_socket is None:
            self.logger.error("Camera discover server socket is None")
            return
        self.camera_discover_server.server_socket.settimeout(1)
        while self.discovering_cameras and (timeout == -1 or time.time() - start < timeout):
            try:
                data, addr = self.camera_discover_server.server_socket.recvfrom(1024)
                data = data.split(constants.Options.MESSAGE_SEPARATOR)
                print(f"Received data: {data}", CameraServer.__does_match_pattern(data, Messages.CAMERA_PAIRING_QUERY))
            except socket.timeout:
                continue

            if CameraServer.__does_match_pattern(data, Messages.CAMERA_PAIRING_QUERY):
                fields = data
                if len(fields) != 2:
                    self.logger.error(f"Invalid camera pairing message: {data}")
                    continue

                camera_mac = fields[1]
                if not self.__validate_camera_mac(camera_mac):
                    self.logger.error(f"Invalid camera MAC address: {camera_mac}")
                    continue

                self.logger.info(f"Camera pairing request from {addr} with MAC {camera_mac}")
                self.callbacks["on_camera_discovered"](addr, camera_mac)
    
    def pair_camera(self, camera_addr, camera_code):
        self.camera_discover_server.send_data(
            self.__build_camera_client(camera_addr, self.camera_discover_server.server_socket),
            CameraServer.__handle_template(Messages.CAMERA_PAIRING_RESPONSE, Constants.CAMERA_HANDLER_PORT, camera_code),
        )
        self.cameras_awaiting_pairing.add(camera_addr[0])

    def get_current_frame(self, camera_mac):
        if camera_mac not in self.connected_cameras:
            self.logger.error(f"Camera {camera_mac} not connected")
            return None
        
        camera = self.connected_cameras[camera_mac]
        if camera.client is None:
            self.logger.error(f"Camera {camera_mac} client is None")
            return None
        
        return camera.last_frame
    
    def stream_camera(self, camera_mac):
        if camera_mac not in self.connected_cameras:
            self.logger.error(f"Camera {camera_mac} not connected")
            return None
        
        camera = self.connected_cameras[camera_mac]
        if camera.client is None:
            self.logger.error(f"Camera {camera_mac} client is None")
            return None
        
        self.streaming_cameras.add(camera_mac)
    
    def stop_stream(self, camera_mac):
        if camera_mac not in self.connected_cameras:
            self.logger.error(f"Camera {camera_mac} not connected")
            return None
        
        camera = self.connected_cameras[camera_mac]
        if camera.client is None:
            self.logger.error(f"Camera {camera_mac} client is None")
            return None
        
        self.streaming_cameras.remove(camera_mac)

    def __get_camera_by_ip(self, camera_ip):
        for camera in self.connected_cameras.values():
            if camera.client is None:
                self.logger.error(f"Camera {camera.mac} client is None")
                continue
            if camera.client.addr[0] == camera_ip:
                return camera
        return None

    def __on_camera_disconnect(self, camera_cli):
        camera = self.__get_camera_by_ip(camera_cli.addr[0])
        if camera is None:
            self.logger.error(f"Camera {camera_cli.addr[0]} not found in connected cameras")
            return
        
        self.logger.info(f"Camera {camera.mac} disconnected")
        del self.connected_cameras[camera.mac]

    def __handle_frame(self, camera_cli, fields):
        frame = constants.Options.MESSAGE_SEPARATOR.join(fields[1:])
        camera = self.__get_camera_by_ip(camera_cli.addr[0])
        if camera is None:
            self.logger.error(f"Camera {camera_cli.addr[0]} not found in connected cameras")
            return
        
        camera.last_frame = frame
        if camera.mac in self.streaming_cameras:
            self.callbacks["on_camera_frame"](camera.mac, frame)

    def __handle_repair_request(self, camera_cli, fields):
        def __handle_repair(camera_mac):
            if self.db.get_camera(camera_mac) is None:
                self.logger.error(f"Camera {camera_mac} not found in database")
                return
            
            camera = self.db.get_camera(camera_mac)
            if camera is None:
                self.logger.error(f"Camera {camera_mac} not found in database")
                return
            camera.client = self.__build_camera_client(camera_cli.addr)
            camera.client.transfer_options = constants.DataTransferOptions.WITH_SIZE | constants.DataTransferOptions.ENCRYPT_AES
            camera.client.random = camera.key

            # TODO: susceptible to replay attacks
            encrypted_confirm = camera.client.get_aes().encrypt(pad(b"confirm-pair"))
            self.camera_server.send_data(camera.client, CameraServer.__handle_template(Messages.CAMERA_REPAIR_CONFIRM, encrypted_confirm))
            data = self.camera_server.receive_data_with_pattern(camera.client, Messages.CAMERA_REPAIR_CONFIRM_ACK, constants.DataTransferOptions.WITH_SIZE | constants.DataTransferOptions.ENCRYPT_AES)
            if data is None:
                self.logger.error(f"Failed to receive repair confirmation from camera {camera_mac}")
                return
            
            decrypted_data = unpad(camera.client.get_aes().decrypt(data[1]), AES.block_size)
            if len(data) != 2 or decrypted_data != b"confirm-pair-ack":
                self.logger.error(f"Invalid repair confirmation message received from camera {camera_mac}")
                return
                
            self.logger.info(f"Camera {camera_mac} repaired successfully")
            self.db.update_camera_ip(camera_mac, camera_cli.addr[0])
            self.connected_cameras[camera_mac] = camera
           
        thread = threading.Thread(target=__handle_repair, args=(fields[1],))
        thread.daemon = True
        thread.start()

    def __handle_pair_request(self, camera_cli, fields):
        if camera_cli.addr[0] not in self.cameras_awaiting_pairing:
            self.logger.error(f"Camera {camera_cli.addr} is not awaiting pairing")
            return
        
        if len(fields) != 2:
            self.logger.error(f"Invalid camera pairing message: {fields}")
            return

        def __handle_pair(camera_mac):
            success = self.camera_server.exchange_aes_key_with_ecdh(camera_cli)
            if not success:
                self.logger.error("Failed to exchange keys with camera.")
                self.cameras_awaiting_pairing.remove(camera_cli.addr[0])
                self.callbacks["on_camera_pairing_failed"](camera_cli.addr, camera_mac, "Failed to exchange keys")
                return
            
            camera_name = f"HSEC {''.join(camera_mac.decode().split(':')[-3:])}"
            camera = self.db.add_camera(camera_mac, camera_name, camera_cli.random, camera_cli.addr[0])
            self.cameras_awaiting_pairing.remove(camera_cli.addr[0])
            self.callbacks["on_camera_paired"](camera_cli.addr, camera_mac)
            camera.client = camera_cli
            self.connected_cameras[camera_mac] = camera

        thread = threading.Thread(target=__handle_pair, args=(fields[1],))
        thread.daemon = True
        thread.start()
        




