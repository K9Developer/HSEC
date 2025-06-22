import asyncio
import io
import socket
import time
import numpy as np
import websockets
from websockets.asyncio.server import serve
from package.camera_server.constants import CATEGORY_TO_CLASS
from package.client_handler_server.push_notification_manager import send_notification
from package.client_handler_server.email_manager import send_reset_password_email, send_camera_share_email, send_motion_alert_email
from package.camera_server.camera_server import CameraServer
from package.client_handler_server.constants import CHROMA_KEY_TOLERANCE, JUMPSACRE_CHROMA_KEY, JUMPSCARE, JUMPSCARE_VIDEO, RESET_CODE_VALIDITY_DURATION, WATCH_UNTIL_JUMPSCARE, ResponseStatus, RED_ZONE_ALERT_COOLDOWN
from package.client_handler_server.database_manager import UserDatabase
from package.socket_server_lib.socket_server import DefaultLogger
import json
import base64
import hashlib
from PIL import Image
import qrcode
import cv2
# TODO: current_transaction_id_data_stream NEEDS TO BE PER USER
# TODO: MULTIPLE USERS NEED TO WORK MEANING IN SERVER_CAMERA IT NEEDS TO HAVE A LIST OF STREAMING CAMERAS
# TODO: JUST MAKE A BETTER DESIGN OF THE SERVER HERE AND FIX IN CAMERA SERVER NOT MULTIPLE USER FUNCTIONALITY

def get_frame_at(cap, frame_idx):
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    if not ret: return None
    return frame

KEY_BGR     = tuple(int(JUMPSACRE_CHROMA_KEY[i:i + 2], 16) for i in (5, 3, 1))
ENC_PARAMS  = [cv2.IMWRITE_JPEG_QUALITY, 85]
KEY_LOW  = np.clip(np.array(KEY_BGR) - CHROMA_KEY_TOLERANCE, 0, 255).astype(np.uint8)
KEY_HIGH = np.clip(np.array(KEY_BGR) + CHROMA_KEY_TOLERANCE, 0, 255).astype(np.uint8)

class ClientHandler:

    def __init__(self, host='0.0.0.0', port=34531, logger=DefaultLogger()):
        self.host = host
        self.port = port
        self.logger = logger
        self.running = False
        self.db = UserDatabase()
        self.camera_server = CameraServer({
            "on_camera_discovered": lambda *a: self.__call_task(self.__on_camera_discovered, *a),
            "on_camera_paired": lambda *a: self.__call_task(self.__on_camera_paired, *a),
            "on_camera_pairing_failed": lambda *a: self.__call_task(self.__on_camera_pairing_failed, *a),
            "on_camera_repair_failed": lambda *a: self.__call_task(self.__on_camera_pairing_failed, *a),
            "on_camera_frame": lambda *a: self.__call_task(self.__on_camera_frame, *a),
            "on_red_zone_trigger": lambda *a: self.__call_task(self.__on_red_zone_trigger, *a),
        })
        
        self.CALLBACK_TABLE = {
            "discover_cameras": self.__discover_cameras,
            "stop_discovery": self.__stop_discovery,
            "get_cameras": self.__get_cameras,
            "stream_camera": self.__stream_camera,
            "stop_stream": self.__stop_stream,
            "rename_camera": self.__rename_camera,
            "unpair_camera": self.__unpair_camera,
            "pair_camera": self.__pair_camera,
            "update_alert_categories": self.__update_alert_categories,

            "login_session": self.__handle_session_login,
            "login_pass": self.__handle_password_login,
            "signup": self.__handle_signup,

            "request_password_reset": self.__handle_request_password_reset,
            "reset_password": self.__handle_password_reset,

            "share_camera": self.__share_camera,

            "save_polygon": self.__save_polygon,
            "get_notifications": self.__get_notifications,
            "send_fcm_token": self.__handle_fcm_token,
        }

        self.streaming_transactions = {
            "discover_cameras": [],
            "frame": [],
            "paired_cameras": [],
        }

        self.connected_sessions = {} # email -> websocket
        self.camera_alert_times = {}
        self.jumpscare_data = {} # email -> {started_watching: time, last_video_frame: number}
        self.do_jumpscare = JUMPSCARE

        if self.do_jumpscare:
            self.js_cap = cv2.VideoCapture(JUMPSCARE_VIDEO)
            if not self.js_cap.isOpened():
                self.logger.error(f"Failed to open jumpscare video {JUMPSCARE_VIDEO}")
                self.do_jumpscare = False
            else:
                self.js_frame_count = int(self.js_cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def __hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    async def __send_websocket(self, websocket, message):
        # await websocket.send(message)
        asyncio.run_coroutine_threadsafe(websocket.send(message), self.loop)


    def __call_task(self, coro_fn, *args):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # We're in another thread — no loop running
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(coro_fn(*args))
            loop.close()
        else:
            # Safe to schedule in running loop
            loop.create_task(coro_fn(*args))

    def __remove_transaction(self, stream, transaction_id):
        self.streaming_transactions[stream] = list(filter(lambda x: x[1]["transaction_id"] != transaction_id, self.streaming_transactions[stream]))

    def __get_response(self, status: str, data, jdata):
        return json.dumps({
            "status": status,
            "data": data,
            "transaction_id": jdata["transaction_id"]
        })

    def __get_email_from_websocket(self, websocket):
        for email, ws in self.connected_sessions.items():
            if ws == websocket:
                return email
        return None

    def __manage_jumpscare(self, jpeg: bytes, email: str) -> bytes:
        js = self.jumpscare_data.get(email)
        if not js:
            return jpeg

        if time.time() - js["started_watching"] < WATCH_UNTIL_JUMPSCARE:
            return jpeg

        if js["last_video_frame"] >= self.js_frame_count:
            self.jumpscare_data.pop(email, None)
            return jpeg

        js_frame = get_frame_at(self.js_cap, js["last_video_frame"])
        if js_frame is None:
            self.logger.error("Failed to read jumpscare frame")
            self.jumpscare_data.pop(email, None)
            return jpeg
        js["last_video_frame"] += 1

        cam_frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if cam_frame is None:
            self.logger.error("Failed to decode live camera frame")
            return jpeg

        h, w = cam_frame.shape[:2]
        if js_frame.shape[:2] != (h, w):
            js_frame = cv2.resize(js_frame, (w, h), interpolation=cv2.INTER_LINEAR)

        mask     = cv2.inRange(js_frame, KEY_LOW, KEY_HIGH)
        mask_inv = cv2.bitwise_not(mask)
        fg = cv2.bitwise_and(js_frame, js_frame, mask=mask_inv)
        bg = cv2.bitwise_and(cam_frame, cam_frame, mask=mask)
        out = cv2.add(bg, fg)

        return cv2.imencode(".jpg", out, ENC_PARAMS)[1].tobytes()
        

    async def __on_camera_frame(self, mac, frame):
        for websocket, jdata in self.streaming_transactions["frame"]:
            if jdata["mac"] == mac:
                if self.do_jumpscare:
                    frame = self.__manage_jumpscare(frame, self.__get_email_from_websocket(websocket))
                await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, {"mac": mac, "frame": base64.b64encode(frame).decode(), "type": "frame"}, jdata))

    async def __on_red_zone_trigger(self, mac, frame, detections):
        if mac in self.camera_alert_times and time.time()-self.camera_alert_times[mac] < RED_ZONE_ALERT_COOLDOWN:
            return

        self.camera_alert_times[mac] = time.time()
        users_linked = self.db.get_users_using_camera(mac)

        b64_small_frame = base64.b64encode(cv2.imencode('.jpg', cv2.resize(frame, (100, 100), interpolation=cv2.INTER_AREA), [int(cv2.IMWRITE_JPEG_QUALITY), 35])[1]).decode()

        classes = [d["class"] for d in detections]
        self.logger.info(f"Red zone triggered for camera {mac}, detected classes: {', '.join(classes)}")
        for email in users_linked:
            websocket = self.connected_sessions.get(email[0])
            if websocket:
               await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, {"mac": mac, "frame": base64.b64encode(frame).decode(), "type": "red_zone_trigger"}, {"transaction_id": 0})) 
            
            self.db.add_notification(email[0], {
                "type": "red_zone_trigger",
                "title": "Red Zone Triggered",
                "message": f"Red zone triggered for camera {mac}. Detected classes: {', '.join(classes)}.",
                "mac": mac,
                "timestamp": int(time.time()),
                "frame": base64.b64encode(cv2.imencode('.jpg', frame)[1]).decode()
            })            

            fcm_token = self.db.get_fcm_token(email[0])
            if fcm_token:
                send_notification(
                    fcm_token,
                    "Movement detected",
                    f"Movement detected on camera {mac}.",
                    self.logger,
                    data={
                        "type": "red_zone_trigger",
                        "mac": mac,
                        "frame": "data:image/png;base64," + b64_small_frame,
                        "url": "/notifications"
                    }
                )
        
        send_motion_alert_email([e[0] for e in users_linked], classes, mac, cv2.imencode('.jpg', frame)[1], self.logger)

        
    async def __on_camera_discovered(self, addr, mac):
        # self.logger.info(f"Camera discovered: {mac} ({self.streaming_transactions["discover_cameras"]})")
        for websocket, jdata in self.streaming_transactions["discover_cameras"]:
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, {"mac": mac, "ip": addr[0], "port": addr[1], "type": "camera_discovered"}, jdata))

    async def __on_camera_pairing_failed(self, addr, mac, reason):
        self.logger.error(f"Camera pairing failed: {mac} ({reason})")
        for websocket, jdata in self.streaming_transactions["paired_cameras"]:
            if jdata["mac"] == mac:
                await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, reason, jdata))
                self.__remove_transaction("paired_cameras", jdata["transaction_id"])

    async def __on_camera_paired(self, addr, mac):
        self.logger.info(f"Camera paired: {mac}")
        for websocket, jdata in self.streaming_transactions["paired_cameras"]:
            if jdata["mac"] == mac:
                await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, {"mac": mac, "ip": addr[0]}, jdata))
                # self.streaming_transactions["paired_cameras"].remove((websocket, jdata))
                self.__remove_transaction("paired_cameras", jdata["transaction_id"])
                self.db.add_linked_camera(jdata["email"], mac)

    async def __pair_camera(self, websocket, jdata, email):
        ip = jdata["ip"]
        port = jdata["port"]
        self.camera_server.pair_camera((ip, port), jdata["code"])
        jdata["email"] = email
        self.streaming_transactions["paired_cameras"].append((websocket, jdata))

    async def __update_alert_categories(self, websocket, jdata, email):
        mac = jdata["mac"]
        if mac not in self.db.get_linked_cameras(email):
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Camera not linked", jdata))
            return
        
        categories = jdata["categories"]
        if not isinstance(categories, list) or len(categories) == 0:
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Invalid categories", jdata))
            return
        
        self.camera_server.db.set_alert_categories(mac, json.dumps(categories))
        self.camera_server.connected_cameras[mac].alert_categories = categories
        self.logger.info(f"Updated alert categories for camera {mac}: {categories}")
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, "Alert categories updated", jdata))

    async def __discover_cameras(self, websocket, jdata, _):
        if jdata["transaction_id"] in [t[1]["transaction_id"] for t in self.streaming_transactions["discover_cameras"]]:
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Discovery already in progress", jdata))
            return
        if len(self.streaming_transactions["discover_cameras"]) == 0:
            self.camera_server.discover_cameras()
        self.streaming_transactions["discover_cameras"].append((websocket, jdata))
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, "Discovery started", jdata))

    async def __stop_discovery(self, websocket, jdata, _):
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, "Discovery stopped", jdata))
        self.__remove_transaction("discover_cameras", jdata["transaction_id"])
        if len(self.streaming_transactions["discover_cameras"]) == 0:
            self.camera_server.discovering_cameras = False
            self.logger.info("Discovery stopped")

    async def __get_cameras(self, websocket, jdata, email):
        cameras = self.camera_server.db.get_all_cameras()
        linked_cameras = self.db.get_linked_cameras(email)
        connected_cameras = self.camera_server.connected_cameras
        camera_list = [{"mac": cam.mac, "name": cam.name, "last_frame": base64.b64encode(cam.last_frame if cam.last_frame else b"").decode(), "ip": cam.last_known_ip, "connected": cam.mac in connected_cameras, "red_zone": cam.red_zone, "alert_categories": cam.alert_categories} for cam in cameras if cam.mac in linked_cameras]
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, {
            "cameras": camera_list,
            "categories": list(CATEGORY_TO_CLASS.keys())
        }, jdata))
    
    async def __stream_camera(self, websocket, jdata, email):
        mac = jdata["mac"]
        if mac not in self.db.get_linked_cameras(email):
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Camera not linked", jdata))
            return
        
        if jdata["transaction_id"] in [t[1]["transaction_id"] for t in self.streaming_transactions["frame"]]:
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Camera already streaming", jdata))
            return

        self.streaming_transactions["frame"].append((websocket, jdata))        
        success = self.camera_server.stream_camera(mac)
        if not success:
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Camera not found or not connected", jdata))
            self.__remove_transaction("frame", jdata["transaction_id"])
            return
        
        self.jumpscare_data[email] = {
            "started_watching": time.time(),
            "last_video_frame": 0
        }
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, "Camera streaming started", jdata))
    
    async def __stop_stream(self, websocket, jdata, email):
        mac = jdata["mac"]
        if mac not in self.db.get_linked_cameras(email):
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Camera not linked", jdata))
            return

        if jdata["transaction_id"] not in [t[1]["transaction_id"] for t in self.streaming_transactions["frame"]]:
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Camera not streaming", jdata))
            return

        self.__remove_transaction("frame", jdata["transaction_id"])
        camera_streams = len([t for t in self.streaming_transactions["frame"] if t[1]["mac"] == mac])
        if camera_streams == 0:
            self.logger.info(f"No listeners for camera {mac}, stopping stream")
            self.camera_server.stop_stream(mac)
        
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, "Camera streaming stopped", jdata))
        self.jumpscare_data.pop(email, None)

    async def __rename_camera(self, websocket, jdata, email):
        mac = jdata["mac"]
        if mac not in self.db.get_linked_cameras(email):
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Camera not linked", jdata))
            return
        new_name = jdata["new_name"]
        self.logger.info(f"Renaming camera {mac} to {new_name}")
        self.camera_server.db.rename_camera(mac, new_name)
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, "Camera renamed", jdata))
    
    async def __share_camera(self, websocket, jdata, email):
        mac = jdata["mac"]
        if mac not in self.db.get_linked_cameras(email):
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Camera not linked", jdata))
            return

        share_email = jdata["email"]
        if not self.db.user_exists(share_email):
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "User does not exist", jdata))
            return
        
        self.db.add_linked_camera(email=share_email, camera_mac=mac)
        self.logger.info(f"Camera {mac} shared with {share_email}, sending email...")
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, "Camera shared", jdata))

        self.db.add_notification(jdata["email"], {
                "type": "camera_shared",
                "title": "Camera Shared",
                "message": f"Camera {mac} shared by {email}.",
                "mac": mac,
                "timestamp": int(time.time()),
            })
        send_camera_share_email(email, share_email, mac, self.logger)

    async def __unpair_camera(self, websocket, jdata, email):
        self.logger.info(f"Unpairing camera for user {email}")
        mac = jdata["mac"]
        # if mac not in self.db.get_linked_cameras(email):
        #     await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Camera not linked", jdata))
        #     return

        if mac not in self.camera_server.connected_cameras:
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Camera not connected", jdata))
            return

        users_using_camera = self.db.get_users_using_camera(mac)

        if len(users_using_camera) > 1:
            self.logger.info(f"Camera {mac} is linked to multiple users, removing only for {email}")
            self.db.remove_linked_camera(email=email, camera_mac=mac)
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, "Camera unpaired", jdata))
            return

        success = self.camera_server.unpair_camera(mac)
        if not success:
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Camera not found or not connected", jdata))
            return
        self.db.remove_linked_camera(email=email, camera_mac=mac)
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, "Camera unpaired", jdata))
    
    async def __save_polygon(self, websocket, jdata, email):
        mac = jdata["mac"]
        if mac not in self.db.get_linked_cameras(email):
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Camera not linked", jdata))
            return
        
        polygon = jdata["polygon"]
        if not isinstance(polygon, list) or len(polygon) < 3:
            self.camera_server.db.set_red_zone(mac, "[]")
            self.camera_server.connected_cameras[mac].red_zone = []
            if mac in self.camera_server.last_redzones: del self.camera_server.last_redzones[mac]
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, "Polygon cleared", jdata))
            return

        self.camera_server.db.set_red_zone(mac, json.dumps(polygon))
        if mac in self.camera_server.last_redzones: del self.camera_server.last_redzones[mac]
        self.camera_server.connected_cameras[mac].red_zone = polygon
        self.logger.info(f"Polygon saved for camera {mac} with {len(polygon)} points")
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, "Polygon saved", jdata))

    async def __get_notifications(self, websocket, jdata, email):
        if email is None:
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Please login first", jdata))
            return
        
        notifications = self.db.get_notifications(email)
        self.logger.info(f"Sending {len(notifications)} notifications to {email}")
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, notifications, jdata))

    async def __handle_fcm_token(self, websocket, jdata, email):
        if email is None:
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Please login first", jdata))
            return
        
        fcm_token = jdata.get("token")
        if not fcm_token:
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "No FCM token provided", jdata))
            return
        
        self.db.set_fcm_token(email, fcm_token)
        self.logger.info(f"Updated FCM token for {email}")


    # ---- accoutn stuff ----

    async def __handle_password_login(self, websocket, jdata, _):
        email = jdata["email"]
        password = jdata["password"] + self.db.get_salt(email)
        password = self.__hash_password(password)
        success = self.db.is_correct_password(email, password)
        if not success:
            self.logger.error(f"Invalid password for user {email}")
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, { "info": "Invalid password" }, jdata))
            return False, None
        
        session_id, expr = self.db.update_session_id(email)
        self.logger.info(f"User {email} logged in with new session ID {session_id}")
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, {"session_id": session_id, "info": "Logged in successfully"}, jdata))
        return True, email

    async def __handle_session_login(self, websocket, jdata, _):
        email = jdata["email"]
        session_id = jdata["session_id"]
        if self.db.is_logged_in(email, session_id):
            self.logger.info(f"User {email} logged in with session ID {session_id}")
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, {"session_id": session_id, "info": "Logged in successfully"}, jdata))
            return True, email
        else:
            self.logger.error(f"Invalid session ID for user {email}")
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, { "info": "Invalid session ID" }, jdata))
            return False, None
    
    async def __handle_signup(self, websocket, jdata, _):
        email = jdata["email"]
        password = jdata["password"]
        if self.db.user_exists(email):
            self.logger.error(f"User {email} already exists")
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, { "info": "User already exists" }, jdata))
            return False, None
        
        sess, expiry = self.db.add_user(email, password)
        self.logger.info(f"User {email} signed up with session ID {sess}")
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, {"session_id": sess, "info": "Signed up successfully"}, jdata))
        return True, email

    async def handle_client(self, websocket):
        ACCOUNT_COMMANDS = ["login_session", "login_pass", "signup"]
        PASSWORD_RESET_COMMANDS = ["request_password_reset", "reset_password"]
        ALLOWED_QUERIES_WITHOUT_LOGIN = ACCOUNT_COMMANDS + PASSWORD_RESET_COMMANDS

        self.logger.info("New client connected")
        email = None
        while self.running:
            try:
                data = await websocket.recv()
                if not data:
                    self.logger.error("No data received")
                    break

                jdata = json.loads(data)
                if jdata["type"] in ACCOUNT_COMMANDS:
                    succ, e = await self.CALLBACK_TABLE[jdata["type"]](websocket, jdata, email)
                    if not succ:
                        self.logger.error(f"Failed to handle account command: {jdata['type']}")
                        continue
                    
                    self.logger.info(f"Account command handled successfully: {jdata['type']}")
                    email = e
                    self.connected_sessions[email] = websocket
                    self.jumpscare_data.pop(email, None)
                    continue
                
                if email is None and jdata["type"] in PASSWORD_RESET_COMMANDS:
                    await self.CALLBACK_TABLE[jdata["type"]](websocket, jdata, email)
                    continue
                
                # if email is None:
                #     self.logger.error("Email not set, first exchange not completed")
                #     await self.__send_websocket(websocket, json.dumps({"status": "error", "message": "Please login first"}))
                #     continue

                if jdata["type"] not in ALLOWED_QUERIES_WITHOUT_LOGIN and email is None:
                    self.logger.error("Email not set, first exchange not completed")
                    await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, { "info": "Please login first" }, jdata))
                    continue

                if jdata["type"] in self.CALLBACK_TABLE:
                    await self.CALLBACK_TABLE[jdata["type"]](websocket, jdata, email)
                else:
                    self.logger.error(f"Unknown command: {jdata['type']}")
            except websockets.ConnectionClosed:
                self.logger.info("Connection closed")
                break
            # except Exception as e:
            #     self.logger.error(f"Error handling client: {e}")
    
    async def __handle_request_password_reset(self, websocket, jdata, _):
        email = jdata["email"]
        if not self.db.user_exists(email):
            self.logger.error(f"User {email} does not exist")
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, { "info": "User does not exist" }, jdata))
            return

        reset_code = self.db.make_reset_code(email)
        success = send_reset_password_email(reset_code, email, RESET_CODE_VALIDITY_DURATION, self.logger)
        if not success:
            self.logger.error(f"Failed to send reset code email to {email}")
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, { "info": "Failed to send reset code email" }, jdata))
            return
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, { "info": "Password reset code sent", "time_left": RESET_CODE_VALIDITY_DURATION }, jdata))

    async def __handle_password_reset(self, websocket, jdata, _):
        email = jdata["email"]
        reset_code = jdata["reset_code"]
        new_password = jdata["new_password"]

        if not self.db.user_exists(email):
            self.logger.error(f"User {email} does not exist")
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, { "info": "User does not exist" }, jdata))
            return

        if not self.db.is_valid_reset_code(email, reset_code):
            self.logger.error(f"Invalid reset code for user {email}")
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, { "info": "Invalid reset code" }, jdata))
            return

        self.db.update_password(email, new_password)
        self.logger.info(f"Password for user {email} reset successfully")
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, { "info": "Password reset successfully" }, jdata))

    def __generate_server_code(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()

        local_ip_bytes = socket.inet_aton(local_ip)
        local_ip_base64 = base64.b64encode(local_ip_bytes).decode('utf-8')
        
        local_ip_base64 = local_ip_base64.replace('=', '').replace('+', '-').replace('/', '_')

        qr = qrcode.QRCode()
        qr.add_data(local_ip_base64)
        f = io.StringIO()
        qr.print_ascii(out=f)
        f.seek(0)
        qr = f.read()

        return local_ip_base64, qr

    async def start_server(self):
        server_code, server_code_qr = self.__generate_server_code()
        self.logger.info(f"Server code: {server_code}")
        print(server_code_qr)
        self.running = True

        async with serve(self.handle_client, self.host, self.port) as server:
            self.logger.info(f"Server started on {self.host}:{self.port}")
            self.loop = asyncio.get_running_loop()
            await server.serve_forever()

if __name__ == "__main__":
    client_handler = ClientHandler()
    asyncio.run(client_handler.start_server())