"""Core module for managing user XP, levels, and ranks in the Shivu bot."""

from typing import Dict, List
from shivu import xp_collection, LOGGER
from shivu.archive.sudo import check_user_permission

class XPError(Exception):
    """Custom exception for XP-related errors."""
    pass

# Define 9 ranks with XP thresholds
RANKS = [
    {"name": "Novice", "min_xp": 0, "max_xp": 999},
    {"name": "Apprentice", "min_xp": 1000, "max_xp": 1999},
    {"name": "Adept", "min_xp": 2000, "max_xp": 3499},
    {"name": "Expert", "min_xp": 3500, "max_xp": 4999},
    {"name": "Master", "min_xp": 5000, "max_xp": 6999},
    {"name": "Grandmaster", "min_xp": 7000, "max_xp": 8999},
    {"name": "Champion", "min_xp": 9000, "max_xp": 11999},
    {"name": "Legend", "min_xp": 12000, "max_xp": 14999},
    {"name": "Mythic", "min_xp": 15000, "max_xp": float("inf")},
]

def calculate_level_and_rank(xp: int) -> tuple[int, int, str]:
    """
    Calculate the user's level, XP needed for next level, and current rank.

    Args:
        xp (int): Total XP of the user.

    Returns:
        tuple[int, int, str]: Current level, XP needed for next level, and rank name.
    """
    level = xp // 1000
    xp_for_next_level = 1000 * (level + 1) - xp
    for rank in RANKS:
        if rank["min_xp"] <= xp <= rank["max_xp"]:
            return level, xp_for_next_level, rank["name"]
    return level, xp_for_next_level, RANKS[-1]["name"]  # Fallback to Mythic

async def create_user_xp(user_id: int) -> None:
    """
    Create a user document in xp_collection if it doesn't exist.

    Args:
        user_id (int): The Telegram user ID.

    Raises:
        XPError: If the database operation fails.
    """
    try:
        existing_user = await xp_collection.find_one({"_id": user_id})
        if not existing_user:
            await xp_collection.insert_one({"_id": user_id, "xp": 0})
            LOGGER.debug(f"Created XP document for user {user_id}")
    except Exception as e:
        LOGGER.error(f"Failed to create XP document for user {user_id}: {e}")
        raise XPError(f"Failed to create XP document: {e}")

async def get_user_xp(user_id: int) -> Dict[str, any]:
    """
    Retrieve a user's XP, level, rank, and XP needed for the next level.

    Args:
        user_id (int): The Telegram user ID.

    Returns:
        Dict[str, any]: Dictionary with 'xp', 'level', 'rank', 'next_level_xp'.

    Raises:
        XPError: If the database operation fails.
    """
    try:
        await create_user_xp(user_id)  # Ensure user document exists
        user = await xp_collection.find_one({"_id": user_id})
        xp = user.get("xp", 0)
        level, next_level_xp, rank = calculate_level_and_rank(xp)
        result = {"xp": xp, "level": level, "rank": rank, "next_level_xp": next_level_xp}
        LOGGER.debug(f"Fetched XP for user {user_id}: {result}")
        return result
    except Exception as e:
        LOGGER.error(f"Failed to fetch XP for user {user_id}: {e}")
        raise XPError(f"Failed to fetch XP: {e}")

async def add_user_xp(user_id: int, xp: int) -> Dict[str, any]:
    """
    Add XP to a user and update their level and rank.

    Args:
        user_id (int): The Telegram user ID.
        xp (int): Amount of XP to add (must be positive).

    Returns:
        Dict[str, any]: Updated 'xp', 'level', 'rank', 'next_level_xp'.

    Raises:
        ValueError: If XP amount is negative.
        XPError: If the database operation fails.
    """
    if xp < 0:
        raise ValueError("XP amount cannot be negative.")

    try:
        await create_user_xp(user_id)  # Ensure user document exists
        result = await xp_collection.update_one(
            {"_id": user_id},
            {"$inc": {"xp": xp}},
            upsert=True
        )
        LOGGER.debug(f"Added {xp} XP for user {user_id}, modified: {result.modified_count}")
        return await get_user_xp(user_id)
    except Exception as e:
        LOGGER.error(f"Failed to add XP for user {user_id}: {e}")
        raise XPError(f"Failed to add XP: {e}")

async def set_user_xp(user_id: int, xp: int) -> Dict[str, any]:
    """
    Set a user's XP to a specific value (sudo only).

    Args:
        user_id (int): The Telegram user ID.
        xp (int): XP value to set (must be non-negative).

    Returns:
        Dict[str, any]: Updated 'xp', 'level', 'rank', 'next_level_xp'.

    Raises:
        ValueError: If XP is negative or user lacks sudo permissions.
        XPError: If the database operation fails.
    """
    if xp < 0:
        raise ValueError("XP value cannot be negative.")

    role = await check_user_permission(user_id)
    if not role in ["superuser", "owner", "sudo"]:
        raise ValueError("Only sudo users can set XP.")

    try:
        await create_user_xp(user_id)  # Ensure user document exists
        await xp_collection.update_one(
            {"_id": user_id},
            {"$set": {"xp": xp}},
            upsert=True
        )
        LOGGER.debug(f"Set XP to {xp} for user {user_id}")
        return await get_user_xp(user_id)
    except Exception as e:
        LOGGER.error(f"Failed to set XP for user {user_id}: {e}")
        raise XPError(f"Failed to set XP: {e}")

async def reset_user_xp(user_id: int) -> bool:
    """
    Reset a user's XP to 0 (sudo only).

    Args:
        user_id (int): The Telegram user ID.

    Returns:
        bool: True if reset was successful, False if no XP data existed.

    Raises:
        ValueError: If user lacks sudo permissions.
        XPError: If the database operation fails.
    """
    role = await check_user_permission(user_id)
    if not role in ["superuser", "owner", "sudo"]:
        raise ValueError("Only sudo users can reset XP.")

    try:
        result = await xp_collection.update_one(
            {"_id": user_id},
            {"$set": {"xp": 0}}
        )
        success = result.modified_count > 0
        LOGGER.debug(f"Reset XP for user {user_id}: {'Success' if success else 'No XP data'}")
        return success
    except Exception as e:
        LOGGER.error(f"Failed to reset XP for user {user_id}: {e}")
        raise XPError(f"Failed to reset XP: {e}")

async def get_top_xp_users(limit: int = 10) -> List[Dict[str, any]]:
    """
    Fetch the top users by XP.

    Args:
        limit (int): Number of users to return (default: 10).

    Returns:
        List[Dict[str, any]]: List of dictionaries with 'user_id', 'xp', 'level', 'rank'.

    Raises:
        XPError: If the database operation fails.
    """
    try:
        users = await xp_collection.find(
            {"xp": {"$gt": 0}}
        ).sort("xp", -1).limit(limit).to_list(length=limit)
        result = [
            {
                "user_id": user["_id"],
                "xp": user.get("xp", 0),
                "level": calculate_level_and_rank(user.get("xp", 0))[0],
                "rank": calculate_level_and_rank(user.get("xp", 0))[2]
            }
            for user in users
        ]
        LOGGER.debug(f"Fetched top {limit} XP users: {len(result)} found")
        return result
    except Exception as e:
        LOGGER.error(f"Failed to fetch top XP users: {e}")
        raise XPError(f"Failed to fetch top XP users: {e}")
