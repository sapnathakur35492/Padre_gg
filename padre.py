import asyncio
import websockets
import json
from datetime import datetime

async def listen():
    url = "ws://127.0.0.1:8795"
    
    try:
        async with websockets.connect(url) as websocket:
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Connected to {url}")
            
            while True:
                # Wait for a message from the server
                message = await websocket.recv()
                
                print(f"\n--- Message Received at {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ---")
                
                try:
                    # Attempt to parse and pretty-print if it's JSON
                    data = json.loads(message)
                    print(json.dumps(data, indent=4))
                except json.JSONDecodeError:
                    # If it's not JSON, just print the raw string
                    print(message)
                    
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(listen())
    except KeyboardInterrupt:
        print("\nConnection closed by user.")