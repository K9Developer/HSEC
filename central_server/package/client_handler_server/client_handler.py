import asyncio
import socket
import websockets
from websockets.asyncio.server import serve
from package.client_handler_server.email_manager import send_reset_password_email, send_camera_share_email
from package.camera_server.camera_server import CameraServer
from package.client_handler_server.constants import RESET_CODE_VALIDITY_DURATION, ResponseStatus
from package.client_handler_server.database_manager import UserDatabase
from package.socket_server_lib.socket_server import DefaultLogger
import json
import base64
import hashlib

# TODO: current_transaction_id_data_stream NEEDS TO BE PER USER
# TODO: MULTIPLE USERS NEED TO WORK MEANING IN SERVER_CAMERA IT NEEDS TO HAVE A LIST OF STREAMING CAMERAS
# TODO: JUST MAKE A BETTER DESIGN OF THE SERVER HERE AND FIX IN CAMERA SERVER NOT MULTIPLE USER FUNCTIONALITY



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

            "login_session": self.__handle_session_login,
            "login_pass": self.__handle_password_login,
            "signup": self.__handle_signup,

            "request_password_reset": self.__handle_request_password_reset,
            "reset_password": self.__handle_password_reset,

            "share_camera": self.__share_camera,
        }

        self.streaming_transactions = {
            "discover_cameras": [],
            "frame": [],
            "paired_cameras": [],
        }

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

    async def __on_camera_frame(self, mac, frame):
        for websocket, jdata in self.streaming_transactions["frame"]:
            if jdata["mac"] == mac:
                await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, {"mac": mac, "frame": base64.b64encode(frame).decode(), "type": "frame"}, jdata))

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
            print(jdata, mac, jdata["mac"] == mac)
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
        camera_list = [{"mac": cam.mac, "name": cam.name, "last_frame": base64.b64encode(cam.last_frame if cam.last_frame else b"").decode(), "ip": cam.last_known_ip, "connected": cam.mac in connected_cameras} for cam in cameras if cam.mac in linked_cameras]
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, camera_list, jdata))
    
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

    async def __rename_camera(self, websocket, jdata, email):
        mac = jdata["mac"]
        if mac not in self.db.get_linked_cameras(email):
            print("Camera not linked:", mac, self.db.get_linked_cameras(email))
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
        send_camera_share_email(email, share_email, mac, self.logger)
        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, "Camera shared", jdata))


    async def __unpair_camera(self, websocket, jdata, email):
        mac = jdata["mac"]
        if mac not in self.db.get_linked_cameras(email):
            await self.__send_websocket(websocket, self.__get_response(ResponseStatus.ERROR, "Camera not linked", jdata))
            return

        # self.camera_server.db.remove_camera(mac)
        users_using_camera = self.db.get_users_using_camera(mac)
        if users_using_camera == 0:
            camera = self.camera_server.connected_cameras[mac]
            if camera and camera.client:
                self.camera_server.camera_server.disconnect_client(camera.client)
                self.camera_server.connected_cameras.pop(mac, None)
        
        self.db.remove_linked_camera(email=jdata["email"], camera_mac=mac)

        await self.__send_websocket(websocket, self.__get_response(ResponseStatus.SUCCESS, "Camera unpaired", jdata))
    
    # ---- accoutn stuff ----

    async def __handle_password_login(self, websocket, jdata, _):
        email = jdata["email"]
        password = jdata["password"] + self.db.get_salt(email)
        password = self.__hash_password(password)
        print(f"Password for {email}: {jdata["password"]} + {self.db.get_salt(email)}")
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
        return local_ip_base64

    async def start_server(self):
        server_code = self.__generate_server_code()
        self.logger.info(f"Server code: {server_code}")
        self.running = True

        # ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        # ssl_ctx.load_cert_chain(certfile="./package/client_handler_server/certs/cert.pem", keyfile="./package/client_handler_server/certs/privkey.pem")
        # self.logger.info("SSL context created")

        async with serve(self.handle_client, self.host, self.port) as server:
            self.logger.info(f"Server started on {self.host}:{self.port}")
            self.loop = asyncio.get_running_loop()
            await server.serve_forever()

if __name__ == "__main__":
    client_handler = ClientHandler()
    asyncio.run(client_handler.start_server())