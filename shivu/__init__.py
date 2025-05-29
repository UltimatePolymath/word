import logging
import os
from pyrogram import Client

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)

logging.getLogger("apscheduler").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("pyrate_limiter").setLevel(logging.ERROR)
LOGGER = logging.getLogger(__name__)

# Fetch configuration from environment (Hugging Face Secrets)
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

# Create Pyrogram Client using session string
hax = Client(
    name="sex",  # This is just the name of the session, not the string
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)
