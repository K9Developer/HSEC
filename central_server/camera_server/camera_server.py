from socket_server_lib.socket_server import DefaultLogger, SocketServer, constants, SocketClient
from camera_server.constants import Constants, Messages
import time
import socket
import base64
from camera_server.database_manager import CameraDatabase, Camera

def handle_template(template: list, *args):
    inserted = []
    if len(args) != template.count(constants.Options.ANY_VALUE_TEMPLATE):
        raise ValueError("Not enough args")
    
    ai = 0
    for i in range(template):
        inserted.append(template[i] if template[i] != constants.Options.ANY_VALUE_TEMPLATE else args[ai])
        ai+=1
    return inserted

def does_match_template(data: list, template: list):
    if len(data) != len(template): return False
    for field, tem in zip(data, template):
        if tem == constants.Options.ANY_VALUE_TEMPLATE: continue
        if field != tem: return False
    return True

class CameraServer:
    def __init__(self, logger=DefaultLogger()):
        self.soc_server = SocketServer(
            host="0.0.0.0",
            port=None,
            logger=logger,
        )

        self.free_talker = SocketServer(
            host="0.0.0.0",
            port=None,
            protocol=constants.ServerProtocol.UDP,
            logger=0,
            reserve_port=False,
        )
        self.free_talker.start(no_loop=True)

        self.logger = logger
        self.db = CameraDatabase()
        self.streaming_camera = None
        self.stream_callback = None
        
        self.soc_server.add_custom_message_callback(
            Messages.LastFrame.CLIENT_RES,
            self.__handle_last_frame
        )
        
        self.soc_server.add_custom_message_callback(
            Messages.Streaming.CLIENT_RES,
            self.__handle_stream
        )
    
    def scan_for_cameras(self, timeout=5):
        self.logger.info("Scanning for cameras...")
        self.free_talker.broadcast(
            data=b"CAMSCAN-HSEC",
            target_port=Constants.DISCOVER_CAMERA_QUERY_PORT,
        )

        camera_addrs = []

        start_time = time.time()
        self.free_talker.server_socket.settimeout(timeout)
        try:
            while time.time() - start_time < timeout:
                data, addr = self.free_talker.server_socket.recvfrom(1024)
                if data == b"CAMACK-HSEC":
                    self.logger.info(f"Camera found at {addr}")
                    camera_addrs.append(addr)
        except socket.timeout:
            self.logger.info("Camera scan timed out.")
        
        self.logger.info(f"Camera scan complete. Found {len(camera_addrs)} cameras.")
        return camera_addrs
    
    def attempt_camera_link(self, camera_addr, camera_key, camera_name):
        """
        server ---> camera: CAMLINK-HSEC
        camera ---> server: CAMACK-HSEC
        RSA key exchange
        server ---> camera: CAMKEY-HSEC <camera key> 
        camera ---> server: CAMOK-HSEC <camera mac>
        """
        
        linker = SocketServer(
            host="0.0.0.0",
            port=None,
        )
        linker.start(no_loop=True)

        camera_cli = SocketClient(socket=None, addr=camera_addr)

        self.logger.info(f"Attempting to link with camera at {camera_addr}...")
        self.free_talker.send_data(
            camera_cli,
            handle_template(Messages.CameraLink.SERVER_LINK_SYN, Constants.CAMERA_LINK_PORT)
        )

        self.logger.info(f"Sent link request to {camera_addr}. Waiting for continuation...")
        linker.receive_data_with_pattern(camera_cli, [Messages.CameraLink.CLIENT_LINK_ACK])
        success = linker.exchange_aes_key_with_rsa(camera_cli)
        if not success:
            self.logger.error("Failed to exchange keys with camera.")
            return False
        
        self.logger.info("Key exchange successful. Sending CAMKEY-HSEC...")
        linker.send_data(
            camera_cli,
            handle_template(Messages.CameraLink.SERVER_KEY_VALDIATION, camera_key),
        )

        data = linker.receive_data(camera_cli, constants.DataTransferOptions.WITH_SIZE | constants.DataTransferOptions.ENCRYPT_AES)
        if does_match_template(data, Messages.CameraLink.CAMERA_LINK_SUCCESS):
            self.logger.info("Camera linked successfully.")
            self.db.add_camera(data[1], camera_name, camera_key, camera_addr[0])
            return True
        else:
            self.logger.error("Failed to link with camera.")
            return False
    
    def get_last_frame(self, camera: Camera):
        camera_cli = SocketClient(None, (camera.ip, Constants.CAMERA_COMMS_PORT))
        self.soc_server.send_data(camera_cli, Messages.LastFrame.SERVER_QUERY)

    def __get_camera_by_ip(self, ip: str):
        for camera in self.db.get_all_cameras():
            if camera.ip == ip:
                return camera
        return None

    def __handle_last_frame(self, cli: SocketClient, fields: list[bytes]):
        frame_data = base64.b64encode(constants.Options.MESSAGE_SEPARATOR.value.join(fields[1:]))
        camera = self.__get_camera_by_ip(cli.addr[0])
        if camera is None:
            self.logger.warning("Recieved frame from an unknown camera, ignoring...")
            return
        self.db.update_camera(camera.mac, frame_data)
    
    def __handle_stream(self, cli: SocketClient, fields: list[bytes]):
        frame_data = constants.Options.MESSAGE_SEPARATOR.value.join(fields[1:])
        camera = self.__get_camera_by_ip(cli.addr[0])
        if camera is None:
            self.logger.warning("Recieved frame from an unknown camera, ignoring...")
            return
        
        if camera.mac != self.streaming_camera.mac:
            self.logger.warning("Recieved frame from a camera that shouldnt be streaming, ignoring...")
            return
        
        if self.stream_callback:
            self.stream_callback(camera, frame_data)
        else:
            self.logger.warning("Recieved frame without having a callback")
            
        
    def request_streaming(self, camera: Camera):
        self.streaming_camera = camera
        camera_cli = SocketClient(None, (camera.ip, Constants.CAMERA_COMMS_PORT))
        self.soc_server.send_data(camera_cli, Messages.Streaming.SERVER_QUERY)
    
    def stream_callback(self, camera: Camera, frame: bytes):
        # send to client handler
        # connect em first