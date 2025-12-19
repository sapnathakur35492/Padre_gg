import asyncio
import websockets
import json
import config
from colorama import Fore, Style, init

init(autoreset=True)

async def test_bot():
    uri = config.RELAY_URL
    print(f"{Fore.YELLOW}[BOT] Connecting to Relay Server at {uri}...{Style.RESET_ALL}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"{Fore.GREEN}[BOT] Connected! Waiting for events...{Style.RESET_ALL}")
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    ts = data.get("timestamp")
                    ts_human = data.get("timestamp_human")
                    event = data.get("event")
                    
                    print(f"{Fore.CYAN}[BOT] ⚡ Received Event!{Style.RESET_ALL}")
                    print(f"      {Fore.YELLOW}Unix Timestamp (ms): {ts}{Style.RESET_ALL}  <-- Your Requirement")
                    print(f"      {Fore.YELLOW}Human Time         : {ts_human}{Style.RESET_ALL}")
                    print(f"      {Fore.WHITE}Data: {str(event)[:100]}...{Style.RESET_ALL}")
                    
                    # Latency check (if event has a timestamp, but usually it doesn't match local clock perfectly)
                    now = int(asyncio.get_running_loop().time() * 1000)
                    # Simple print
                except json.JSONDecodeError:
                    print(f"{Fore.RED}[BOT] Received non-JSON: {message}{Style.RESET_ALL}")
                    
    except ConnectionRefusedError:
        print(f"{Fore.RED}[BOT] Connection failed. Is relay_server.py running?{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        asyncio.run(test_bot())
    except KeyboardInterrupt:
        print("[BOT] Stopped.")
