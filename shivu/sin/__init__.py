import logging
from motor.motor_asyncio import AsyncIOMotorClient
from shivu.sin.make import initialize_user as make  # Centralized user initializer

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
CURRENCY_MONGO_URL = "mongodb+srv://currency:yu7Qj5jegVqgSkhq@cluster0.fjwfvaj.mongodb.net/?retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true"

currency_client = AsyncIOMotorClient(CURRENCY_MONGO_URL)
currency_db = currency_client["currency_database"]

# =========================
# make function reference (central user initializer)
# =========================
make = make  # Expose initialize_user as `make`
