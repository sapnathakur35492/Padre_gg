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
                    # Expected format from tracker: {"event": payload, ...}
                    # Payload for Type 5 is often [5, sub_id, payload_body]
                    if isinstance(data, dict) and "event" in data:
                        payload = data["event"]
                        
                        if isinstance(payload, list) and len(payload) >= 3 and payload[0] == 5:
                            body = payload[2]
                            
                            # Handle batch tweets structure: {"tweets": [...]}
                            tweets_to_check = []
                            if isinstance(body, dict):
                                if "tweets" in body and isinstance(body["tweets"], list):
                                    tweets_to_check = body["tweets"]
                                else:
                                    tweets_to_check = [body]
                            
                            is_match = False
                            targets = [t.lower() for t in config.TARGET_USERNAMES]
                            
                            for tweet in tweets_to_check:
                                screen_name = None
                                if isinstance(tweet, dict):
                                    # Try various paths for the username
                                    user_obj = tweet.get("user") or tweet.get("data", {}).get("user")
                                    if user_obj and isinstance(user_obj, dict):
                                        screen_name = user_obj.get("screen_name") or user_obj.get("username")
                                    
                                    if not screen_name:
                                        screen_name = tweet.get("screen_name") or tweet.get("username")
                                
                                if screen_name and screen_name.lower() in targets:
                                    logger.info(f"{Fore.CYAN}[Filter] MATCH: Relaying tweet from @{screen_name}{Style.RESET_ALL}")
                                    is_match = True
                                    break
                            
                            if not is_match:
                                continue # Skip broadcasting if no tweet matches targets
                
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
