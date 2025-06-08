from package.camera_server.camera_server import CameraServer

def discovered(camera_addr, camera_mac):
    print("Camera discovered!", camera_mac, camera_addr)
    cs.pair_camera(camera_addr, "1234")

# class Callbacks(CameraServerCallbacks):
#     def on_camera_discovered(self, camera_addr, camera_mac):
#         discovered(camera_addr, camera_mac)

#     def on_camera_paired(self, camera_addr, camera_mac):
#         print(f"Camera paired: {camera_addr}, {camera_mac}")

#     def on_camera_pairing_failed(self, camera_addr, camera_mac, reason):
#         print(f"Camera pairing failed: {camera_addr}, {camera_mac}, reason: {reason}")
    
#     def on_camera_frame(self, camera_mac, frame):
#         print(len(frame))

cbs = {
    "on_camera_discovered": discovered,
    "on_camera_paired": lambda camera_addr, camera_mac: print(f"Camera paired: {camera_addr}, {camera_mac}"),
    "on_camera_pairing_failed": lambda camera_addr, camera_mac, reason: print(f"Camera pairing failed: {camera_addr}, {camera_mac}, reason: {reason}"),
    "on_camera_frame": lambda camera_mac, frame: print(f"Received frame from {camera_mac}, size: {len(frame)} bytes")
}

cs = CameraServer(cbs)
cs.discover_cameras(30)
