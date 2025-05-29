import logging
import os
from pyrogram import Client

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)

LOGGER = logging.getLogger(__name__)

# Load environment variables for Pyrogram
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

# Initialize Pyrogram client for the word game bot
hax = Client(
    name="word_game_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)
