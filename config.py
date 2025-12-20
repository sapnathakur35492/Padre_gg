import os
import sys
from dotenv import load_dotenv
from colorama import Fore, Style

# Load environment variables from .env file
load_dotenv()

def get_env(key, required=True):
    val = os.getenv(key)
    if not val and required:
        print(f"{Fore.RED}Error: Missing required environment variable: {key}{Style.RESET_ALL}")
        print(f"Please set {key} in your .env file.")
        sys.exit(1)
    return val

PADRE_TOKEN = get_env("PADRE_TOKEN", required=False)
PADRE_UID = get_env("PADRE_UID")
PADRE_REFRESH_TOKEN = os.getenv("PADRE_REFRESH_TOKEN")
PADRE_API_KEY = os.getenv("PADRE_API_KEY")
RELAY_HOST = os.getenv("RELAY_HOST", "127.0.0.1")
RELAY_PORT = int(os.getenv("RELAY_PORT", "8765"))
RELAY_URL = f"ws://{RELAY_HOST}:{RELAY_PORT}"
TARGET_USERNAMES = [u.strip() for u in os.getenv("TARGET_USERNAMES", "").split(",") if u.strip()]
FILTER_ONLY_TARGETS = os.getenv("FILTER_ONLY_TARGETS", "false").lower() == "true"
PADRE_WS_URL = "wss://backend.padre.gg/_multiplex"
