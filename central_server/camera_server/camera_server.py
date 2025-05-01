from socket_server_lib.socket_server import DefaultLogger, SocketServer, constants, SocketClient
from camera_server.constants import Constants
import time
import socket
from camera_server.database_manager import CameraDatabase

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
        self.listener.start(no_loop=True)

        self.logger = logger
        self.db = CameraDatabase()
    
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
            port=Constants.CAMERA_LINK_PORT,
        )
        linker.start(no_loop=True)

        camera_cli = SocketClient(socket=None, addr=camera_addr)

        self.logger.info(f"Attempting to link with camera at {camera_addr}...")
        self.free_talker.send_data(
            camera_cli,
            data=[b"CAMLINK-HSEC", Constants.CAMERA_LINK_PORT],
        )

        self.logger.info(f"Sent CAMLINK-HSEC to {camera_addr}. Waiting for CAMACK-HSEC...")
        linker.receive_data_with_pattern(camera_cli, [b"CAMACK-HSEC"])
        success = linker.exchange_aes_key_with_rsa(camera_cli)
        if not success:
            self.logger.error("Failed to exchange keys with camera.")
            return False
        
        self.logger.info("Key exchange successful. Sending CAMKEY-HSEC...")
        linker.send_data(
            camera_cli,
            [b"CAMKEY-HSEC", camera_key],
        )

        data = linker.receive_data(camera_cli, constants.DataTransferOptions.WITH_SIZE | constants.DataTransferOptions.ENCRYPT_AES)
        if data[0] == b"CAMOK-HSEC":
            self.logger.info("Camera linked successfully.")
            self.db.add_camera(data[1], camera_name, camera_key)
            return True
        else:
            self.logger.error("Failed to link with camera.")
            return False
