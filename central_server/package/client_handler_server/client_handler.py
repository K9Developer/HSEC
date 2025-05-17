import asyncio
import websockets
from websockets.asyncio.server import serve
from central_server.package.client_handler_server.database_manager import UserDatabase
from central_server.package.socket_server_lib.socket_server import DefaultLogger
import json

class ClientHandler:
    def __init__(self, host='0.0.0.0', port=34531, logger=DefaultLogger()):
        self.host = host
        self.port = port
        self.logger = logger
        self.running = False
        self.db = UserDatabase()

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
        # session_id = await websocket.recv()
        success = await self.__handle_first_exchange(websocket)
        if not success:
            self.logger.error("Failed to handle first exchange")
            return


        while self.running:
            
            

    async def start_server(self):
        self.running = True
        async with serve(self.handle_client, self.host, self.port) as server:
            self.logger.info(f"Server started on {self.host}:{self.port}")
            await server.serve_forever()

if __name__ == "__main__":
    client_handler = ClientHandler()
    asyncio.run(client_handler.start_server())