import asyncio
import websockets
import json
import logging
from colorama import Fore, Style, init
import config

# Configuration
HOST = config.RELAY_HOST
PORT = config.RELAY_PORT

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
            # Filter logic
            if config.FILTER_ONLY_TARGETS:
                try:
                    data = json.loads(message)
                    # Expecting [5, sub_id, payload] or similar structure
                    # Payload usually contains 'data' -> 'user' -> 'screen_name' or just 'user' -> 'screen_name'
                    
                    if isinstance(data, list) and len(data) >= 3 and data[0] == 5:
                        payload = data[2]
                        screen_name = None
                        
                        # Attempt to find screen_name in various common paths
                        if isinstance(payload, dict):
                            # Path 1: payload['user']['screen_name']
                            if 'user' in payload and 'screen_name' in payload['user']:
                                screen_name = payload['user']['screen_name']
                            # Path 2: payload['data']['user']['screen_name']
                            elif 'data' in payload and 'user' in payload['data'] and 'screen_name' in payload['data']['user']:
                                screen_name = payload['data']['user']['screen_name']
                        
                        if screen_name:
                            # Check against target list (case-insensitive)
                            targets = [t.lower() for t in config.TARGET_USERNAMES]
                            if screen_name.lower() not in targets:
                                # logger.info(f"{Fore.LIGHTBLACK_EX}Filtered out message from @{screen_name}{Style.RESET_ALL}")
                                continue # Skip broadcasting
                            else:
                                logger.info(f"{Fore.CYAN}[Filter] MATCH: Relaying tweet from @{screen_name}{Style.RESET_ALL}")
                
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    logger.error(f"Error filtering message: {e}")

            # Broadcast logic
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
