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

PADRE_TOKEN = get_env("PADRE_TOKEN")
PADRE_UID = get_env("PADRE_UID")
RELAY_URL = os.getenv("RELAY_URL", "ws://localhost:8765")
TARGET_USERNAMES = [u.strip() for u in os.getenv("TARGET_USERNAMES", "").split(",") if u.strip()]
FILTER_ONLY_TARGETS = os.getenv("FILTER_ONLY_TARGETS", "false").lower() == "true"
PADRE_WS_URL = "wss://backend.padre.gg/_multiplex"
