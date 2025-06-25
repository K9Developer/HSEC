import time

import cv2
import numpy as np

from package.camera_server.movement_detection import MovementDetector

from ..socket_server_lib.socket_server import DefaultLogger, SocketServer, constants, SocketClient
from package.camera_server.constants import CATEGORY_TO_CLASS, Constants, Messages
import socket
from package.camera_server.database_manager import CameraDatabase, Camera
import threading
from Cryptodome.Util.Padding import pad, unpad
from Cryptodome.Cipher import AES
from queue import Queue
from package.camera_server.playback_manager import PlaybackManager

def filter_detections(detections, red_zone, alert_categories):
    red_poly = np.array(red_zone, dtype=np.int32)

    allowed_classes = [
        cls
        for cat in alert_categories
        for cls in CATEGORY_TO_CLASS[cat]
    ]

    filtered = []
    for det in detections:
        if det["class"] not in allowed_classes: continue

        x1, y1, x2, y2 = det["coordinates"]
        det_poly = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.int32)

        intersection_area, _ = cv2.intersectConvexConvex(red_poly, det_poly)
        if intersection_area > 0:
            filtered.append(det)

    return filtered
    

class CameraServer:
    def __init__(self, callbacks: dict, logger=DefaultLogger()):
        self.logger = logger
        self.connected_cameras: dict[str, Camera] = {}
        self.movement_detector = MovementDetector(logger, threshold=Constants.RED_ZONE_DETECTION_THRESHOLD)

        # This server listens for camera pairing mode broadcasts
        self.camera_discover_server = SocketServer(
            host="0.0.0.0",
            port=Constants.CAMERA_HEARTBEAT_LISTENER_PORT,
            protocol=constants.ServerProtocol.UDP,
            logger=logger,
        )

        # This server registers new cameras and handles camera data
        self.camera_server = SocketServer(
            host="0.0.0.0",
            port=Constants.CAMERA_HANDLER_PORT,
            protocol=constants.ServerProtocol.TCP,
            logger=logger,
        )

        self.callbacks = callbacks
        self.discovering_cameras = True
        self.cameras_awaiting_pairing = set()
        self.streaming_cameras = set()
        self.last_frame_update_time = {}

        self.frame_queue = Queue()
        self.last_redzones = {} # {mac: (hash, frames_passed)}
        self.timelapse_info = {} # {mac: (start_time, frames_passed)}

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

        threading.Thread(
            target=self.__handle_frame_queue,
            daemon=True,
        ).start()

        self.camera_discover_server.start(no_loop=True)
        self.camera_server.start()


    @staticmethod
    def __does_match_pattern(data, pattern):
        if len(data) != len(pattern):
            return False
        
        for i in range(len(data)):
            if data[i] != pattern[i] and pattern[i] != constants.Options.ANY_VALUE_TEMPLATE:
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
        self.discovering_cameras = True
        def func():
            self.logger.info("Starting camera discovery...")
            start = time.time()
            if self.camera_discover_server.server_socket is None:
                self.logger.error("Camera discover server socket is None")
                return
            self.camera_discover_server.server_socket.settimeout(1)
            while self.discovering_cameras and (timeout == -1 or time.time() - start < timeout):
                try:
                    data, addr = self.camera_discover_server.server_socket.recvfrom(1024)
                    data = data.split(constants.Options.MESSAGE_SEPARATOR)
                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f"Error receiving data: {e}")
                    continue
                
                print(f"Received data from {addr}: {data}")

                if CameraServer.__does_match_pattern(data, Messages.CAMERA_PAIRING_QUERY):
                    fields = data
                    if len(fields) != 2:
                        self.logger.error(f"Invalid camera pairing message: {data}")
                        continue

                    camera_mac = fields[1].decode()
                    if not self.__validate_camera_mac(camera_mac):
                        self.logger.error(f"Invalid camera MAC address: {camera_mac}")
                        continue

                    self.callbacks["on_camera_discovered"](addr, camera_mac)
                elif CameraServer.__does_match_pattern(data, Messages.CAMERA_WRONG_CODE):
                    self.__handle_bad_code(self.__build_camera_client(addr, self.camera_discover_server.server_socket), data)
        t = threading.Thread(target=func, daemon=True)
        t.start()
            
    
    def pair_camera(self, camera_addr, camera_code):
        self.camera_discover_server.send_data(
            self.__build_camera_client(camera_addr, self.camera_discover_server.server_socket),
            CameraServer.__handle_template(Messages.CAMERA_PAIRING_RESPONSE, Constants.CAMERA_HANDLER_PORT, camera_code),
            constants.DataTransferOptions.RAW
        )
        self.cameras_awaiting_pairing.add(camera_addr[0])

    def unpair_camera(self, camera_mac):
        if camera_mac not in self.connected_cameras:
            self.logger.error(f"Camera {camera_mac} not connected")
            return False
        
        camera = self.connected_cameras[camera_mac]
        if camera.client is None:
            self.logger.error(f"Camera {camera_mac} client is None")
            return False
        
        camera_ip = camera.client.addr[0]
        self.camera_discover_server.server_socket.sendto(
            constants.Options.MESSAGE_SEPARATOR.join(Messages.CAMERA_UNPAIR_REQUEST),
            (camera_ip, Constants.CAMERA_HEARTBEAT_LISTENER_PORT)
        )
        
        self.db.remove_camera(camera_mac)
        self.logger.info(f"Camera {camera_mac} unpaired successfully")
        return True

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
        return True
    
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
            # print(camera.client.addr, camera_ip)
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
        if camera.mac in self.last_frame_update_time: del self.last_frame_update_time[camera.mac]
        if camera.mac in self.last_redzones: del self.last_redzones[camera.mac]
        
        if camera is None:
            self.logger.error(f"Camera {camera_cli.addr[0]} not found in connected cameras")
            return
        
        if camera.mac in self.connected_cameras: del self.connected_cameras[camera.mac]
        self.callbacks["on_camera_disconnected"](camera_cli.addr, camera.mac)

    def __handle_bad_code(self, camera_cli, fields):
        if len(fields) != 2:
            self.logger.error(f"Invalid camera code message: {fields}")
            return
        
        camera_mac = fields[1].decode()
        if not self.__validate_camera_mac(camera_mac):
            self.logger.error(f"Invalid camera MAC address: {camera_mac}")
            return
        
        self.logger.warning(f"Sent bad code to camera {camera_mac} at {camera_cli.addr[0]}")
        if camera_cli.addr[0] in self.cameras_awaiting_pairing:
            self.cameras_awaiting_pairing.remove(camera_cli.addr[0])
            self.callbacks["on_camera_pairing_failed"](camera_cli.addr, camera_mac, "Invalid pairing code")
        else:
            self.logger.error(f"Camera {camera_mac} is not awaiting pairing, cannot handle bad code")
            return

    def __handle_frame_queue(self):
        while True:
            try:
                camera, frame = self.frame_queue.get()
                if camera is None or frame is None:
                    continue

                if camera.mac not in self.connected_cameras: continue
                
                cv2_image = cv2.imdecode(np.frombuffer(frame, np.uint8), cv2.IMREAD_COLOR)

                if camera.mac in self.last_redzones:
                    frame, detections = self.movement_detector.detect_frame(cv2_image, draw_box=True)

                    allowed_classes = []
                    for category in camera.alert_categories:
                        allowed_classes.extend(CATEGORY_TO_CLASS[category])

                    filtered_detections = filter_detections(detections, camera.red_zone, camera.alert_categories)
                    if len(filtered_detections) > 0:
                        del self.last_redzones[camera.mac]
                        self.callbacks["on_red_zone_trigger"](camera.mac, frame, filtered_detections)
                elif camera.mac not in self.last_redzones:
                    self.last_redzones[camera.mac] = 0
            except Exception as e:
                self.logger.error(f"Error processing frame queue: {e}")

    def __handle_frame(self, camera_cli, fields):
        frame = constants.Options.MESSAGE_SEPARATOR.join(fields[1:])
        camera = self.__get_camera_by_ip(camera_cli.addr[0])
        if camera is None:
            self.logger.error(f"Camera {camera_cli.addr[0]} not found in connected cameras")
            self.camera_server.disconnect_client(camera_cli)
            return
        
        if camera.mac in self.streaming_cameras:
            self.callbacks["on_camera_frame"](camera.mac, frame)
        
        check_red_zone = False
        if camera.mac in self.last_redzones: 
            self.last_redzones[camera.mac] += 1
            if self.last_redzones[camera.mac] >= Constants.FRAMES_BETWEEN_RED_ZONE_CHECKS:
                self.last_redzones[camera.mac] = 0
                check_red_zone = True
        else:
            check_red_zone = True
            self.last_redzones[camera.mac] = 0

        if camera.red_zone is not None and check_red_zone:
            self.frame_queue.put((camera, frame))

        threading.Thread(target=PlaybackManager.add_frame, args=(camera.mac, frame)).start()

        if self.last_frame_update_time.get(camera.mac) and time.time() - self.last_frame_update_time.get(camera.mac, 0) < Constants.STATIC_CAMERA_FRAME_UPDATE_INTERVAL:
            self.logger.debug(f"Skipping frame update for camera {camera.mac} due to rate limiting")
            return
        camera.last_frame = frame
        self.db.update_camera(camera.mac, frame)
        self.last_frame_update_time[camera.mac] = time.time()

    def __handle_repair_request(self, camera_cli, fields):
        def __handle_repair(camera_mac):
            try:
                camera_cli.auto_recv = False
                self.logger.info(f"Received repair request from camera {camera_mac} at {camera_cli.addr[0]}")
                if self.db.get_camera(camera_mac) is None:
                    self.logger.error(f"Camera {camera_mac} not found in database")
                    return
                
                camera = self.db.get_camera(camera_mac)
                if camera is None:
                    self.logger.error(f"Camera {camera_mac} not found in database")
                    return
                
                camera.client = camera_cli
                camera.client.transfer_options = constants.DataTransferOptions.WITH_SIZE | constants.DataTransferOptions.ENCRYPT_AES
                camera.client.random = camera.key

                # TODO: susceptible to replay attacks
                encrypted_confirm = camera.client.get_aes().encrypt(pad(b"confirm-pair", AES.block_size))
                self.camera_server.send_data(camera.client, CameraServer.__handle_template(Messages.CAMERA_REPAIR_CONFIRM, encrypted_confirm))
                data = self.camera_server.receive_data_with_pattern(camera.client, Messages.CAMERA_REPAIR_CONFIRM_ACK)
                if data is None:
                    self.logger.error(f"Failed to receive repair confirmation from camera {camera_mac}")
                    self.callbacks["on_camera_repair_failed"](camera_cli.addr, camera_mac, "Failed to receive repair confirmation")
                    self.camera_server.disconnect_client(camera.client)
                    return
                
                decrypted_data = unpad(camera.client.get_aes().decrypt(data[1]), AES.block_size)
                if len(data) != 2 or decrypted_data != b"confirm-pair-ack":
                    self.logger.error(f"Invalid repair confirmation message received from camera {camera_mac}")
                    self.callbacks["on_camera_repair_failed"](camera_cli.addr, camera_mac, "Invalid repair confirmation message")
                    self.camera_server.disconnect_client(camera.client)
                    return
                    
                self.logger.info(f"Camera {camera_mac} repaired successfully")
                camera_cli.auto_recv = True
                self.db.update_camera_ip(camera_mac, camera_cli.addr[0])
                self.connected_cameras[camera_mac] = camera
                self.callbacks["on_camera_paired"](camera_cli.addr, camera_mac)
            except Exception as e:
                self.logger.error(f"Error handling repair request from camera {camera_mac}: {e}")
                self.callbacks["on_camera_repair_failed"](camera_cli.addr, camera_mac, str(e))
                self.camera_server.disconnect_client(camera_cli)

        thread = threading.Thread(target=__handle_repair, args=(fields[1].decode(),))
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
            
            camera_name = f"HSEC {''.join(camera_mac.split(':')[-3:])}"
            camera = self.db.add_camera(camera_mac, camera_name, camera_cli.random, camera_cli.addr[0])
            camera.client = camera_cli
            self.cameras_awaiting_pairing.remove(camera_cli.addr[0])
            self.connected_cameras[camera_mac] = camera
            self.callbacks["on_camera_paired"](camera_cli.addr, camera_mac)
            self.logger.info(f"Camera {camera_mac} paired successfully with IP {camera_cli.addr[0]}")

        thread = threading.Thread(target=__handle_pair, args=(fields[1].decode(),))
        thread.daemon = True
        thread.start()
        




