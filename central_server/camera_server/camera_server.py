from socket_server_lib.socket_server import DefaultLogger, SocketServer, constants, SocketClient
from camera_server.constants import Constants, Messages
import socket
from camera_server.database_manager import CameraDatabase, Camera
import threading
from Crypto.Util.Padding import pad, unpad
from Crypto.Cipher import AES

# TODO: How could we make a re-pair? we need to battle arp spoofing too

class CameraServerCallbacks:
    def on_camera_discovered(self, camera_addr, camera_mac):
        raise NotImplementedError("on_camera_discovered method not implemented")

    def on_camera_paired(self, camera_addr, camera_mac):
        raise NotImplementedError("on_camera_paired method not implemented")

    def on_camera_pairing_failed(self, camera_addr, camera_mac, reason):
        raise NotImplementedError("on_camera_pairing_failed method not implemented")
    
    def on_camera_frame(self, camera_mac, frame):
        raise NotImplementedError("on_camera_frame method not implemented")
    
def __does_match_pattern(data, pattern):
    if len(data) != len(pattern):
        return False
    
    for i in range(len(data)):
        if data[i] != pattern[i] and pattern[i] != constants.Options.TEMPLATE_ANY_VALUE:
            return False
        
    return True

def __handle_template(template, *args):
    if template.count(constants.Options.TEMPLATE_ANY_VALUE) != len(args):
        raise ValueError("Number of arguments does not match the number of template placeholders")
    
    new_template = []
    placeholder_ind = 0
    for i in range(len(template)):
        if template[i] == constants.Options.TEMPLATE_ANY_VALUE:
            new_template.append(args[placeholder_ind])
            placeholder_ind += 1
        else:
            new_template.append(template[i])
    
    return new_template

class CameraServer:
    def __init__(self, callbacks: CameraServerCallbacks, logger=DefaultLogger()):
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
            protocol=constants.ServerProtocol.UDP,
            logger=logger,
        )

        self.callbacks = callbacks
        self.discovering_cameras = True
        self.cameras_awaiting_pairing = set()
        self.streaming_camera = None

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

    def __validate_camera_mac(self, camera_mac):
        return camera_mac.startswith(Constants.CAMERA_MAC_PREFIX)

    def __build_camera_client(self, camera_addr):
        return SocketClient(
            addr=camera_addr,
            socket=None
        )

    def discover_cameras(self):
        self.camera_discover_server.server_socket.settimeout(1)
        while self.discovering_cameras:
            try:
                addr, data = self.camera_discover_server.server_socket.recvfrom(1024)
            except socket.timeout:
                continue
            if __does_match_pattern(data, Messages.CAMERA_PAIRING_QUERY):
                fields = data.split(constants.Options.MESSAGE_SEPARATOR)
                if len(fields) != 2:
                    self.logger.error(f"Invalid camera pairing message: {data}")
                    continue

                camera_mac = fields[1]
                if not self.__validate_camera_mac(camera_mac):
                    self.logger.error(f"Invalid camera MAC address: {camera_mac}")
                    continue

                self.logger.info(f"Camera pairing request from {addr} with MAC {camera_mac}")
                self.new_camera_callback(addr, camera_mac)
    
    def pair_camera(self, camera_addr, camera_code):
        self.camera_discover_server.send_data(
            self.__build_camera_client(camera_addr),
            __handle_template(Messages.CAMERA_PAIRING_RESPONSE, Constants.CAMERA_HANDLER_PORT, camera_code),
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
        
        self.streaming_camera = camera_mac

    def __get_camera_by_ip(self, camera_ip):
        for camera in self.connected_cameras.values():
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
        if self.streaming_camera == camera.mac:
            self.callbacks.on_camera_frame(camera.mac, frame)

    def __handle_repair_request(self, camera_cli, fields):
        def __handle_repair(camera_mac):
            if self.db.get_camera(camera_mac) is None:
                self.logger.error(f"Camera {camera_mac} not found in database")
                return
            
            camera = self.db.get_camera(camera_mac)
            camera.client = self.__build_camera_client(camera_cli.addr)
            camera.client.transfer_options = constants.DataTransferOptions.WITH_SIZE | constants.DataTransferOptions.ENCRYPT_AES
            camera.client.random = self.db.get_camera(camera_mac).key

            # TODO: susceptible to replay attacks
            encrypted_confirm = camera.client.get_aes().encrypt(pad(b"confirm-pair"))
            self.camera_server.send_data(camera.client, __handle_template(Messages.CAMERA_REPAIR_CONFIRM, encrypted_confirm))
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
            camera_client = self.__build_camera_client(camera_cli.addr)

            success = self.camera_server.exchange_aes_key_with_ecdh(camera_client)
            if not success:
                self.logger.error("Failed to exchange keys with camera.")
                self.cameras_awaiting_pairing.remove(camera_cli.addr[0])
                self.callbacks.on_camera_pairing_failed(camera_cli.addr, camera_mac, "Failed to exchange keys")
                return
            
            camera_name = f"HSEC {''.join(camera_mac.split(':')[-3:])}"
            camera = self.db.add_camera(camera_mac, camera_name, camera_client.random, camera_cli.addr[0])
            self.cameras_awaiting_pairing.remove(camera_cli.addr[0])
            self.callbacks.on_camera_paired(camera_cli.addr, camera_mac)
            camera.client = camera_client
            self.connected_cameras[camera_mac] = camera

        thread = threading.Thread(target=__handle_pair, args=(fields[1],))
        thread.daemon = True
        thread.start()
        




