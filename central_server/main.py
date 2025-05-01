import camera_server
from camera_server import camera_server
import threading

t = threading.Thread(target=lambda: camera_server.CameraServer().scan_for_cameras(timeout=5))
t.daemon = True
t.start()


import socket

print("Starting UDP server...")
s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s1.bind(("0.0.0.0", 5000))

while True:
    data, addr = s.recvfrom(1024)
    if addr == s.getsockname():
        continue
    print(f"2Received message: {data} from {addr}")
    print(f"3Sending ACK to {addr}")
    s.sendto(b"ACK", addr)