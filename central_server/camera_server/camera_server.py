from socket_server_lib.socket_server import DefaultLogger, SocketServer, constants, SocketClient
from camera_server.constants import Constants, Messages
import time
import socket
from camera_server.database_manager import CameraDatabase
import threading

# TODO: How could we make a re-pair? we need to battle arp spoofing too

class CameraServerCallbacks:
    def on_camera_discovered(self, camera_addr, camera_mac):
        raise NotImplementedError("on_camera_discovered method not implemented")

    def on_camera_paired(self, camera_addr, camera_mac):
        raise NotImplementedError("on_camera_paired method not implemented")

    def on_camera_pairing_failed(self, camera_addr, camera_mac, reason):
        raise NotImplementedError("on_camera_pairing_failed method not implemented")
    
def __does_match_pattern(data, pattern):
    if len(data) != len(pattern):
        return False
    
    for i in range(len(data)):
        if data[i] != pattern[i] and pattern[i] != Constants.TEMPLATE_ANY_VALUE:
            return False
        
    return True

def __handle_template(template, *args):
    if template.count(Constants.TEMPLATE_ANY_VALUE) != len(args):
        raise ValueError("Number of arguments does not match the number of template placeholders")
    
    new_template = []
    placeholder_ind = 0
    for i in range(len(template)):
        if template[i] == Constants.TEMPLATE_ANY_VALUE:
            new_template.append(args[placeholder_ind])
            placeholder_ind += 1
        else:
            new_template.append(template[i])
    
    return new_template

class CameraServer:
    def __init__(self, callbacks: CameraServerCallbacks, logger=DefaultLogger()):
        self.logger = logger
        
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

        self.db = CameraDatabase()

        self.camera_server.add_custom_message_callback(
            Messages.CAMERA_PAIR_REQUEST,
            self.__handle_pair_request,
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
                fields = data.split(Constants.SEPARATOR)
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

    def __handle_pair_request(self, camera_cli, fields):
        if camera_cli.addr[0] not in self.cameras_awaiting_pairing:
            self.logger.error(f"Camera {camera_cli.addr} is not awaiting pairing")
            return
        
        def __handle_pair(camera_mac):
            camera_client = self.__build_camera_client(camera_cli.addr)

            success = self.camera_server.exchange_aes_key_with_rsa(camera_client)
            if not success:
                self.logger.error("Failed to exchange keys with camera.")
                self.cameras_awaiting_pairing.remove(camera_cli.addr[0])
                self.callbacks.on_camera_pairing_failed(camera_cli.addr, camera_mac, "Failed to exchange keys")
                return
            
            camera_name = f"HSEC {''.join(camera_mac.split(':')[-3:])}"
            self.db.add_camera(camera_mac, camera_name, camera_client.random)
            self.cameras_awaiting_pairing.remove(camera_cli.addr[0])
            self.callbacks.on_camera_paired(camera_cli.addr, camera_mac)

        thread = threading.Thread(target=__handle_pair, args=(fields[1],))
        thread.daemon = True
        thread.start()
        




