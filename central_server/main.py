from package.camera_server.camera_server import CameraServer, CameraServerCallbacks

class Callbacks(CameraServerCallbacks):
    def on_camera_discovered(self, camera_mac, camera_name, camera_key, last_known_ip):
        print(f"Camera discovered: {camera_mac}, Name: {camera_name}, Key: {camera_key}, IP: {last_known_ip}")

    def on_camera_frame_received(self, camera_mac, frame_data):
        print(f"Frame received from {camera_mac}")

    def on_camera_repair_request(self, camera_mac):
        print(f"Repair request from {camera_mac}")

    def on_camera_repair_confirmed(self, camera_mac):
        print(f"Repair confirmed for {camera_mac}")

cs = CameraServer(Callbacks)
cs.discover_cameras(30)