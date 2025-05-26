from shivu import db
import logging

logger = logging.getLogger(__name__)
rarity_collection = db.rarity  # This uses the 'rarity' collection in your DB

async def set_rarity(no: int, emoji: str, rarity: str) -> None:
    """Insert or update a rarity entry by number."""
    try:
        await rarity_collection.update_one(
            {"no": no},
            {"$set": {"emoji": emoji, "rarity": rarity}},
            upsert=True
        )
        logger.info(f"Set rarity: no={no}, emoji={emoji}, rarity={rarity}")
    except Exception as e:
        logger.error(f"Error setting rarity for no={no}: {e}")

async def delete_rarity(no: int) -> bool:
    """Delete a rarity entry by number."""
    try:
        result = await rarity_collection.delete_one({"no": no})
        logger.info(f"Deleted rarity no={no}: {result.deleted_count > 0}")
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting rarity for no={no}: {e}")
        return False

async def get_all_rarities() -> list[dict]:
    """Get all rarities."""
    try:
        return await rarity_collection.find().sort("no").to_list(length=None)
    except Exception as e:
        logger.error(f"Error fetching rarities: {e}")
        return []
