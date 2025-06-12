from package.client_handler_server.client_handler import ClientHandler
import asyncio

client_handler = ClientHandler()
asyncio.run(client_handler.start_server())