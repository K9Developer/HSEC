import asyncio
import websockets
from websockets.asyncio.server import serve
from package.camera_server.camera_server import CameraServer
from package.client_handler_server.constants import ResponseStatus
from package.client_handler_server.database_manager import UserDatabase
from package.socket_server_lib.socket_server import DefaultLogger
import json

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
            "on_camera_discovered": self.__on_camera_discovered,
            "on_camera_paired": self.__on_camera_paired,
            "on_camera_pairing_failed": self.__on_camera_pairing_failed,
            "on_camera_frame": self.__on_camera_frame,
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
        }

        self.streaming_camera_macs = set()
        self.streaming_transactions = {
            "discover_cameras": [],
            "frame": [],
            "paired_cameras": [],
        }

    def __remove_transaction(self, stream, transaction_id):
        for i in range(len(self.streaming_transactions[stream])):
            if self.streaming_transactions[stream][i][1]["transaction_id"] == transaction_id:
                self.streaming_transactions[stream].pop(i)
                break

    def __get_response(self, status: str, data, jdata):
        return {
            "status": status,
            "data": data,
            "transaction_id": jdata["transaction_id"]
        }

    def __on_camera_frame(self, camera, frame):
        self.logger.info(f"Camera frame received: {camera.mac}")
        for websocket, jdata in self.streaming_transactions["frame"]:
            if jdata["mac"] == camera.mac:
                websocket.send(json.dumps(self.__get_response(ResponseStatus.SUCCESS, {"mac": camera.mac, "frame": frame}, jdata)))
                break

    def __on_camera_discovered(self, camera):
        self.logger.info(f"Camera discovered: {camera.mac}")
        for websocket, jdata in self.streaming_transactions["discover_cameras"]:
            websocket.send(json.dumps(self.__get_response(ResponseStatus.SUCCESS, {"mac": camera.mac, "name": camera.name}, jdata)))

    def __on_camera_pairing_failed(self, camera):
        self.logger.error(f"Camera pairing failed: {camera.mac}")
        for websocket, jdata in self.streaming_transactions["paired_cameras"]:
            if jdata["mac"] == camera.mac:
                websocket.send(json.dumps(self.__get_response(ResponseStatus.ERROR, "Pairing failed", jdata)))
                self.streaming_transactions["paired_cameras"].remove((websocket, jdata))

    def __on_camera_paired(self, camera):
        self.logger.info(f"Camera paired: {camera.mac}")
        for websocket, jdata in self.streaming_transactions["paired_cameras"]:
            if jdata["mac"] == camera.mac:
                websocket.send(json.dumps(self.__get_response(ResponseStatus.SUCCESS, {"mac": camera.mac, "name": camera.name}, jdata)))
                self.streaming_transactions["paired_cameras"].remove((websocket, jdata))

    async def __pair_camera(self, websocket, jdata):
        mac = jdata["mac"]
        self.camera_server.pair_camera(mac, jdata["code"])
        self.streaming_transactions["paired_cameras"].append((websocket, jdata))

    async def __discover_cameras(self, websocket, jdata):
        if self.current_transaction_id_data_stream:
            await websocket.send(json.dumps(self.__get_response(ResponseStatus.ERROR, "Another stream is already in progress", jdata)))
            self.logger.error("Another stream is already in progress")
            return
        
        self.streaming_transactions["discover_cameras"].append((websocket, jdata))
        self.camera_server.discover_cameras()
        await websocket.send(json.dumps(self.__get_response(ResponseStatus.SUCCESS, "Discovery started", jdata)))

    async def __stop_discovery(self, websocket, jdata):
        self.camera_server.discovering_cameras = False
        self.current_transaction_id_data_stream = None
        await websocket.send(json.dumps(self.__get_response(ResponseStatus.SUCCESS, "Discovery stopped", jdata)))
        self.__remove_transaction("discover_cameras", jdata["transaction_id"])
            

    async def __get_cameras(self, websocket, jdata):
        cameras = self.camera_server.db.get_all_cameras()
        camera_list = [{"mac": cam.mac, "name": cam.name, "last_frame": cam.last_frame, "ip": cam.last_known_ip} for cam in cameras]
        await websocket.send(json.dumps(self.__get_response(ResponseStatus.SUCCESS, camera_list, jdata)))
    
    async def __stream_camera(self, websocket, jdata):
        mac = jdata["mac"]
        if mac in self.streaming_camera_macs:
            await websocket.send(json.dumps(self.__get_response(ResponseStatus.ERROR, "Camera already streaming", jdata)))
            return
        
        self.camera_server.stream_camera(mac)
        websocket.send(json.dumps(self.__get_response(ResponseStatus.SUCCESS, "Camera streaming started", jdata)))
    
    async def __stop_stream(self, websocket, jdata):
        mac = jdata["mac"]
        if mac not in self.streaming_camera_macs:
            await websocket.send(json.dumps(self.__get_response(ResponseStatus.ERROR, "Camera not streaming", jdata)))
            return
        
        self.camera_server.stop_stream(mac)
        websocket.send(json.dumps(self.__get_response(ResponseStatus.SUCCESS, "Camera streaming stopped", jdata)))
        self.streaming_camera_macs.remove(mac)
        self.__remove_transaction("frame", jdata["transaction_id"])

    async def __rename_camera(self, websocket, jdata):
        mac = jdata["mac"]
        new_name = jdata["new_name"]
        self.camera_server.db.rename_camera(mac, new_name)
        await websocket.send(json.dumps(self.__get_response(ResponseStatus.SUCCESS, "Camera renamed", jdata)))
    
    async def __unpair_camera(self, websocket, jdata):
        mac = jdata["mac"]

        self.camera_server.db.remove_camera(mac)
        camera = self.camera_server.connected_cameras[mac]
        if camera and camera.client:
            self.camera_server.camera_server.disconnect_client(camera.client)
            self.camera_server.connected_cameras.pop(mac, None)

        await websocket.send(json.dumps(self.__get_response(ResponseStatus.SUCCESS, "Camera unpaired", jdata)))
    
    async def __handle_first_exchange(self, websocket: websockets.ClientConnection):
        data = await websocket.recv()
        if not data:
            self.logger.error("No data received")
            return False

        jdata = json.loads(data)
        if jdata["type"] == "login_session":
            email = jdata["email"]
            session_id = jdata["session_id"]
            if self.db.is_logged_in(email, session_id):
                self.logger.info(f"User {email} logged in with session ID {session_id}")
                await websocket.send(json.dumps({"status": "success", "message": ""}))
                return True
            else:
                self.logger.error(f"Invalid session ID for user {email}")
                await websocket.send(json.dumps({"status": "error", "message": "Invalid session ID"}))
                return False
        elif jdata["type"] == "login_pass":
            email = jdata["email"]
            password = jdata["password"]
            success = self.db.is_correct_password(email, password)
            if not success:
                self.logger.error(f"Invalid password for user {email}")
                await websocket.send(json.dumps({"status": "error", "message": "Invalid password"}))
                return False
            
            session_id, expr = self.db.update_session_id(email)
            self.logger.info(f"User {email} logged in with new session ID {session_id}")
            await websocket.send(json.dumps({"status": "success", "session_id": session_id, "message": ""}))
            return True
        elif jdata["type"] == "signup":
            email = jdata["email"]
            password = jdata["password"]
            if self.db.user_exists(email):
                self.logger.error(f"User {email} already exists")
                await websocket.send(json.dumps({"status": "error", "message": "User already exists"}))
                return False
            
            sess, expiry = self.db.add_user(email, password)
            self.logger.info(f"User {email} signed up with session ID {sess}")
            await websocket.send(json.dumps({"status": "success", "session_id": sess, "message": ""}))
            return True

    async def handle_client(self, websocket):
        try:
            success = await self.__handle_first_exchange(websocket)
            if not success:
                self.logger.error("Failed to handle first exchange")
                return
        except Exception as e:
            self.logger.error(f"Error during first exchange: {e}")
            return

        while self.running:
            try:
                data = await websocket.recv()
                if not data:
                    self.logger.error("No data received")
                    break

                jdata = json.loads(data)
                if jdata["type"] in self.CALLBACK_TABLE:
                    await self.CALLBACK_TABLE[jdata["type"]](websocket, jdata)
                else:
                    self.logger.error(f"Unknown command: {jdata['type']}")
            except websockets.ConnectionClosed:
                self.logger.info("Connection closed")
                break
            except Exception as e:
                self.logger.error(f"Error handling client: {e}")
                break

    async def start_server(self):
        self.running = True
        async with serve(self.handle_client, self.host, self.port) as server:
            self.logger.info(f"Server started on {self.host}:{self.port}")
            await server.serve_forever()

if __name__ == "__main__":
    client_handler = ClientHandler()
    asyncio.run(client_handler.start_server())