import logging
from motor.motor_asyncio import AsyncIOMotorClient

# =========================
# Logging Setup
# =========================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.FileHandler("sin_log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)

LOGGER = logging.getLogger(__name__)

# =========================
# Currency MongoDB Setup
# =========================
CURRENCY_MONGO_URL = (
    "mongodb+srv://worker:TFqF209jhTbnWDAN@cluster0.if6ahq2.mongodb.net/"
    "?retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true"
)

currency_client = AsyncIOMotorClient(CURRENCY_MONGO_URL)
currency_db = currency_client["currency_database"]

# =========================
# (Future) Other Modules Setup
# =========================
# Example:
# GAME_MONGO_URL = "mongodb+srv://...<game_credentials>..."
# game_client = AsyncIOMotorClient(GAME_MONGO_URL)
# game_db = game_client["game_database"]
