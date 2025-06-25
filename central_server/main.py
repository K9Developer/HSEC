from package.client_handler_server.client_handler import ClientHandler
import asyncio
import os

if not os.path.exists("databases"):
    os.makedirs("databases")
if not os.path.exists("certs"):
    os.makedirs("certs")
if not os.path.exists("recordings"):
    os.makedirs("recordings")


client_handler = ClientHandler()
asyncio.run(client_handler.start_server())