import asyncio
import websockets
import json
import logging
from colorama import Fore, Style, init

# Initialize colors
init(autoreset=True)

# Configuration
HOST = "localhost"
PORT = 8765

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("RelayServer")

# Connected clients
connected_clients = set()

async def register(websocket):
    """Register a new client connection."""
    connected_clients.add(websocket)
    logger.info(f"{Fore.GREEN}[+] New client connected. Total: {len(connected_clients)}{Style.RESET_ALL}")

async def unregister(websocket):
    """Unregister a client connection."""
    connected_clients.remove(websocket)
    logger.info(f"{Fore.RED}[-] Client disconnected. Total: {len(connected_clients)}{Style.RESET_ALL}")

async def relay_handler(websocket):
    """Handle incoming connections and relay messages."""
    await register(websocket)
    try:
        async for message in websocket:
            # We assume the message is already JSON formatted by the tracker
            # If it comes from the tracker, we broadcast it to ALL other clients
            # Ideally, we distinguish between 'tracker' source and 'bot' listener, 
            # but for simplicity, we broadcast to all *others* or just all.
            # Let's broadcast to all connected clients (including sender, useful for verify).
            
            # Use asyncio.gather to broadcast concurrently
            if connected_clients:
                # logger.info(f"{Fore.CYAN}[>] Relaying message: {len(message)} bytes{Style.RESET_ALL}")
                await asyncio.gather(
                    *[client.send(message) for client in connected_clients],
                    return_exceptions=True
                )
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        await unregister(websocket)

async def main():
    """Start the WebSocket relay server."""
    logger.info(f"{Fore.YELLOW}[*] Starting Relay Server on ws://{HOST}:{PORT}{Style.RESET_ALL}")
    async with websockets.serve(relay_handler, HOST, PORT):
        await asyncio.get_running_loop().create_future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped.")
