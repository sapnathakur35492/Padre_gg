import asyncio
import websockets
import msgpack
import json
import time
import random
import string
import random
import string
import config
import aiohttp # Added for Token Refresh
from colorama import Fore, Style, init

from dataclasses import dataclass

init(autoreset=True)

@dataclass
class ConnectionState:
    auth_confirmed: bool = False
    req_id_counter: int = 1
    subscriptions: dict = None

    def __post_init__(self):
        self.subscriptions = {}

def get_session_id():
    """Generate a random session ID similar to the browser client."""
    # Format: d-XXXXXXXXXXX (11 random chars)
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=11))
    return f"d-{random_str}"

def get_current_ts_ms():
    """Return current Unix timestamp in milliseconds."""
    return int(time.time() * 1000)

async def refresh_session():
    """
    Uses the Refresh Token to get a new Access Token from Google Identity Toolkit.
    Returns: new_access_token (str) or None if failed.
    """
    if not config.PADRE_REFRESH_TOKEN or not config.PADRE_API_KEY:
        print(f"{Fore.YELLOW}[AutoRefresh] Missing Refresh Token or API Key. Manual update required.{Style.RESET_ALL}")
        return None

    url = f"https://securetoken.googleapis.com/v1/token?key={config.PADRE_API_KEY}"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": config.PADRE_REFRESH_TOKEN
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    new_token = data.get("access_token")
                    print(f"{Fore.GREEN}[AutoRefresh] Successfully Refreshed Session Token! 🔄{Style.RESET_ALL}")
                    return new_token
                else:
                    text = await resp.text()
                    print(f"{Fore.RED}[AutoRefresh] Failed to refresh token. Status: {resp.status} Response: {text}{Style.RESET_ALL}")
                    return None
    except Exception as e:
        print(f"{Fore.RED}[AutoRefresh] Exception during refresh: {e}{Style.RESET_ALL}")
        return None

async def padre_tracker():
    """Main client loop."""
    # Append ?desc=%2Ftrenches to match client behavior
    uri = f"{config.PADRE_WS_URL}?desc=%2Ftrenches"
    relay_uri = config.RELAY_URL
    
    # Session setup
    token = config.PADRE_TOKEN
    uid = config.PADRE_UID
    session_id = get_session_id()

    # 24/7 Automation: Initial Token Check/Refresh
    if not token and config.PADRE_REFRESH_TOKEN:
        print(f"{logger_prefix} No initial token found. Attempting to generate one via Refresh Token...")
        token = await refresh_session()
        if not token:
            print(f"{logger_prefix} {Fore.RED}Critical: Could not generate initial token. Exiting.{Style.RESET_ALL}")
            return

    state = ConnectionState()
    
    logger_prefix = f"{Fore.MAGENTA}[PadreTracker]{Style.RESET_ALL}"
    
    print(f"{logger_prefix} Connecting to {uri}...")
    
    headers = {
        "Origin": "https://trade.padre.gg",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with websockets.connect(uri, extra_headers=headers) as ws:
        # 1. Send Handshake
        # Protocol: [1, token, sessionId]
        print(f"{logger_prefix} Authenticating...")
        auth_payload = [1, token, session_id]
        # JSON encode (Protocol Discovery: Server expects JSON uplink, MsgPack downlink)
        await ws.send(json.dumps(auth_payload))
        
        # Connect to Relay Server
        relay_ws = None
        try:
            relay_ws = await websockets.connect(relay_uri)
            print(f"{logger_prefix} {Fore.GREEN}Connected to Relay Server at {relay_uri}{Style.RESET_ALL}")
        except Exception as e:
            print(f"\n{logger_prefix} {Fore.RED}Connection Error: {e}{Style.RESET_ALL}")
            print(f"{logger_prefix} Reconnecting in 5 seconds...")
            
            # 24/7 Logic: Before reconnecting, try to refresh the token 
            # because the likely cause of a drop (after 1 hour) is expiration.
            if config.PADRE_REFRESH_TOKEN:
                 print(f"{logger_prefix} Attempting token refresh before reconnect...")
                 new_t = await refresh_session()
                 if new_t:
                     token = new_t # Update the token for the next loop iteration
            
            await asyncio.sleep(5)

        async def send_heartbeat():
            """Send periodic heartbeat/checks if needed."""
            # Browser sends nothing? JS code shows server ping processing.
            # If server sends PING (Opcode 9), websockets lib handles it usually.
            # But MultiplexManager has a keepalive mechanism.
            while True:
                await asyncio.sleep(30)
                # Implement app-level ping if connection drops?
                pass

        # Start heartbeat loop if necessary
        # asyncio.create_task(send_heartbeat())

        # Main Receive Loop
        async for raw_msg in ws:
            try:
                # Decode MessagePack
                decoded = msgpack.unpackb(raw_msg)
                
                # Check message type
                # Structure is typically [type, id, payload] or similar
                if not isinstance(decoded, list):
                    # DEBUG: Print non-list messages
                    # print(f"{logger_prefix} {Fore.YELLOW}Received non-list message: {decoded}{Style.RESET_ALL}")
                    continue
                    
                msg_type = decoded[0]
                
                # --- DEBUGGING LINE (Temporary) ---
                print(f"{logger_prefix} [RAW DEBUG] Type: {msg_type} | Payload: {str(decoded)[:200]}...")
                # ----------------------------------
                
                # DEBUG: Print ANY message type for diagnosis
                # print(f"{logger_prefix} [DEBUG] Received Type: {msg_type} | Data: {str(decoded)[:100]}")
                
                # Type 4: Auth Response / System Message?
                # Based on JS: if (4 !== e[0] && 1 !== e[0])... if (4) this.onAuth()
                # Type 4 or 1 or 3: Auth Response / System Message
                # Observed: Server sends [3] after JSON auth indicating success
                if msg_type == 4 or msg_type == 1 or msg_type == 3:
                    if not state.auth_confirmed:
                        print(f"{logger_prefix} {Fore.GREEN}Authentication Confirmed!{Style.RESET_ALL}")
                        state.auth_confirmed = True
                        
                        # SUBSCRIBE once authed
                        # Subscribe to Tweet Feed
                        # Path: ws /tweet/subscribe-feed/v2/:uid
                        # Request ID can be 1
                        sub_id = state.req_id_counter
                        state.req_id_counter += 1
                        
                        target_path = f"ws /tweet/subscribe-feed/v2/{uid}"
                        print(f"{logger_prefix} Subscribing to Personal Feed: {target_path}")
                        
                        sub_payload = [4, sub_id, target_path]
                        await ws.send(json.dumps(sub_payload))
                        state.subscriptions[sub_id] = "tweet_feed"

                        # --- TRENCHES FEED SUBSCRIPTION (Added for Client Fix) ---
                        sub_id_trenches = state.req_id_counter
                        state.req_id_counter += 1
                        trenches_path = "ws /tweet/trenches/v1" 
                        print(f"{logger_prefix} Subscribing to Trenches Feed: {trenches_path}")
                        
                        sub_payload_trenches = [4, sub_id_trenches, trenches_path]
                        await ws.send(json.dumps(sub_payload_trenches))
                        state.subscriptions[sub_id_trenches] = "trenches_feed"
                        # ---------------------------------------------------------

                elif msg_type == 5:
                    # Data Message: [5, conn_id, payload]
                    conn_id = decoded[1]
                    payload = decoded[2]
                    
                    # --- FILTERING LOGIC ---
                    # Inspect payload for username matches (heuristic based on common structures)
                    # We convert payload to string to search indiscriminately if exact field is unknown
                    payload_str = str(payload).lower()
                    
                    is_target_match = False
                    if config.TARGET_USERNAMES:
                        for user in config.TARGET_USERNAMES:
                            if user.lower() in payload_str:
                                is_target_match = True
                                break
                    
                    # If FILTER_ONLY_TARGETS is ON, and No Match -> SKIP
                    if config.FILTER_ONLY_TARGETS and not is_target_match:
                         print(f"{Fore.CYAN}[FILTER] {ts_human} | Ignored event (Not target user){Style.RESET_ALL}")
                         continue
                    # -----------------------

                    # Add Timestamp
                    ts = get_current_ts_ms()
                    import datetime
                    ts_human = datetime.datetime.fromtimestamp(ts/1000).strftime('%H:%M:%S.%f')[:-3]
                    
                    event_data = {
                        "timestamp": ts,
                        "timestamp_human": ts_human,
                        "source": "padre",
                        "is_target_match": is_target_match,
                        "event": payload
                    }
                    
                    # Serialize to JSON
                    json_data = json.dumps(event_data)
                    
                    # Relay
                    if relay_ws:
                        await relay_ws.send(json_data)
                        match_tag = " [TARGET MATCH!]" if is_target_match else ""
                        print(f"{Fore.CYAN}[RELAY] {ts_human} | Forwarded event from conn {conn_id}{match_tag}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.CYAN}[ECHO] {ts_human} | {json_data[:100]}...{Style.RESET_ALL}")

                elif msg_type == 6:
                    print(f"{logger_prefix} {Fore.YELLOW}Server sent CLOSE for conn {decoded[1]}{Style.RESET_ALL}")
                
                elif msg_type == 7:
                    print(f"{logger_prefix} {Fore.RED}Server sent ERROR for conn {decoded[1]}: {decoded[2]}{Style.RESET_ALL}")
                
                # Heartbeat/Ping handling (Type 2?)
                elif msg_type == 2:
                    # Ping?
                    pass

            except Exception as e:
                print(f"{logger_prefix} Error processing message: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    while True:
        try:
            asyncio.run(padre_tracker())
        except Exception as e:
            print(f"{Fore.RED}Connection lost: {e}. Reconnecting in 5s...{Style.RESET_ALL}")
            time.sleep(5)
