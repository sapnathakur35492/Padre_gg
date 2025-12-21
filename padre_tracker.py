import asyncio
import websockets
import msgpack
import json
import os
import time
import datetime
import config
from colorama import Fore, Style, init

# Initialize Colorama
init(autoreset=True)

class ConnectionState:
    def __init__(self):
        self.auth_confirmed = False
        self.req_id_counter = 1
        self.subscriptions = {}

def get_session_id():
    import random
    import string
    chars = string.ascii_lowercase + string.digits
    return "d-" + ''.join(random.choice(chars) for _ in range(11))

def get_current_ts_ms():
    return int(time.time() * 1000)

async def refresh_session():
    """Refresh the Firebase token using the Refresh Token."""
    import aiohttp
    print(f"{Fore.YELLOW}[AutoRefresh] Refreshing Token...{Style.RESET_ALL}")
    url = f"https://securetoken.googleapis.com/v1/token?key={config.PADRE_API_KEY}"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": config.PADRE_REFRESH_TOKEN
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload) as resp:
                data = await resp.json()
                if "access_token" in data:
                    new_token = data["access_token"]
                    # Update config for current process
                    config.PADRE_TOKEN = new_token
                    print(f"{Fore.GREEN}[AutoRefresh] Successfully Refreshed Session{Style.RESET_ALL}")
                    return new_token
                else:
                    print(f"{Fore.RED}[AutoRefresh] Failed: {data}{Style.RESET_ALL}")
                    return None
    except Exception as e:
        print(f"{Fore.RED}[AutoRefresh] Exception: {e}{Style.RESET_ALL}")
        return None

# Override URL for backend1
config.PADRE_WS_URL = "wss://backend1.padre.gg/_multiplex"

async def padre_tracker():
    """Main client loop."""
    uri = f"{config.PADRE_WS_URL}?desc=%2Ftracker"
    token = config.PADRE_TOKEN
    uid = config.PADRE_UID
    session_id = get_session_id()
    state = ConnectionState()
    logger_prefix = f"{Fore.MAGENTA}[PadreTracker]{Style.RESET_ALL}"
    
    # Automation: Token Refresh (Force Refresh to ensure validity)
    if config.PADRE_REFRESH_TOKEN:
        token = await refresh_session()

    print(f"{logger_prefix} Connecting (BINARY) to {uri}...")
    headers = {
        "Origin": "https://trade.padre.gg",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with websockets.connect(uri, extra_headers=headers) as ws:
        # 1. Auth Handshake (Binary)
        print(f"{logger_prefix} Authenticating...")
        await ws.send(msgpack.packb([1, token, session_id]))

        # Delay to ensure server processes Auth
        await asyncio.sleep(0.5)

        # 2. Subscribe Immediately (Optimistic)
        print(f"{logger_prefix} Subscribing immediately...")
        # X Feed V3
        x_feed_topic = f"/twitter/tweet/subscribe-feed/v3/{config.PADRE_UID}?encodedCategoryFilters=&onlySubscribedAccounts=1"
        await ws.send(msgpack.packb([4, state.req_id_counter, x_feed_topic]))
        state.req_id_counter += 1
        # Trenches
        trenches_topic = "/frontend/trenches/v2"
        await ws.send(msgpack.packb([4, state.req_id_counter, trenches_topic]))
        state.req_id_counter += 1
        
        # 2. Relay Connection
        relay_ws = None
        target_relay = f"ws://127.0.0.1:{config.RELAY_PORT}" if config.RELAY_HOST == "0.0.0.0" else config.RELAY_URL
        try:
            relay_ws = await websockets.connect(target_relay)
            print(f"{logger_prefix} {Fore.GREEN}Connected to Relay at {target_relay}{Style.RESET_ALL}")
        except:
            print(f"{logger_prefix} {Fore.YELLOW}Relay Server offline (Listening only locally){Style.RESET_ALL}")

        async def send_heartbeat():
            while True:
                try:
                    await asyncio.sleep(15)
                    await ws.send(msgpack.packb([3]))
                except: break

        asyncio.create_task(send_heartbeat())

        # Broadcast System Ready
        if relay_ws:
            try:
                await relay_ws.send(json.dumps({
                    "message": "SYSTEM ONLINE: Padre Tracker Connected to Relay",
                    "timestamp": get_current_ts_ms()
                }))
                print(f"{logger_prefix} {Fore.CYAN}Sent System Ready signal to Relay{Style.RESET_ALL}")
            except: pass

        # Main Loop
        async for raw_msg in ws:
            try:
                decoded = msgpack.unpackb(raw_msg)
                if not isinstance(decoded, list): continue
                msg_type = decoded[0]
                
                # Debug every single incoming message
                print(f"{logger_prefix} [RECV] Type: {msg_type} | Count: {len(decoded)}")
                if msg_type != 3: # Hide heartbeats to see others
                    print(f"{logger_prefix} [RECV-DEBUG] {decoded}")

                # Auth confirmed logic is now handled optimistically.
                if msg_type in [1, 3, 4] and not state.auth_confirmed:
                    state.auth_confirmed = True
                    print(f"{logger_prefix} {Fore.GREEN}Server Acknowledged (Type {msg_type}){Style.RESET_ALL}")

                elif msg_type == 5:
                    payload = decoded[2]
                    payload_str = str(payload).lower()
                    
                    # Target Matching
                    is_match = False
                    if config.TARGET_USERNAMES:
                        for user in config.TARGET_USERNAMES:
                            if user.lower() in payload_str:
                                is_match = True
                                break
                    
                    if config.FILTER_ONLY_TARGETS and not is_match:
                        continue

                    ts_human = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    event_data = {
                        "timestamp": get_current_ts_ms(),
                        "timestamp_human": ts_human,
                        "source": "padre",
                        "is_target_match": is_match,
                        "event": payload
                    }

                    if relay_ws:
                        await relay_ws.send(json.dumps(event_data))
                        match_flag = " [TARGET MATCH!]" if is_match else ""
                        print(f"{Fore.CYAN}[RELAY] {ts_human} | Forwarded Data{match_flag}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.CYAN}[ECHO] {ts_human} | Match: {is_match}{Style.RESET_ALL}")

            except Exception as e:
                # print(f"Processing Error: {e}")
                pass

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    while True:
        try:
            asyncio.run(padre_tracker())
        except Exception as e:
            print(f"Loop error: {e}. Restarting...")
            time.sleep(5)
