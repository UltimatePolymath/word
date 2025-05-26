"""Module for managing user coin balances (Nectrozz and Kairoz) in the Shivu bot."""

from typing import Dict, Optional
from shivu import coin as coin_collection
from shivu import LOGGER

class CoinError(Exception):
    """Custom exception for coin-related errors."""
    pass

async def create_user_coin_doc(user_id: int) -> None:
    """
    Create a new coin document for a user if it doesn't exist.

    Args:
        user_id (int): The Telegram user ID.

    Raises:
        CoinError: If the database operation fails.
    """
    try:
        existing = await coin_collection.find_one({"_id": user_id})
        if not existing:
            await coin_collection.insert_one({
                "_id": user_id,
                "Nectrozz": 0,
                "Kairoz": 0
            })
            LOGGER.debug(f"Created coin document for user {user_id}")
    except Exception as e:
        LOGGER.error(f"Failed to create coin document for user {user_id}: {e}")
        raise CoinError(f"Failed to create coin document: {e}")

async def get_user_coin_balance(user_id: int) -> Dict[str, int]:
    """
    Retrieve a user's Nectrozz and Kairoz balances.

    Args:
        user_id (int): The Telegram user ID.

    Returns:
        Dict[str, int]: A dictionary with 'Nectrozz' and 'Kairoz' balances.

    Raises:
        CoinError: If the database operation fails.
    """
    try:
        user = await coin_collection.find_one({"_id": user_id})
        if not user:
            await create_user_coin_doc(user_id)
            return {"Nectrozz": 0, "Kairoz": 0}
        return {
            "Nectrozz": user.get("Nectrozz", 0),
            "Kairoz": user.get("Kairoz", 0)
        }
    except Exception as e:
        LOGGER.error(f"Failed to retrieve coin balance for user {user_id}: {e}")
        raise CoinError(f"Failed to retrieve coin balance: {e}")

async def update_user_coins(
    user_id: int,
    nectrozz: Optional[int] = None,
    kairoz: Optional[int] = None,
    operation: str = "set"
) -> None:
    """
    Update a user's coin balances by setting, adding, or subtracting values.

    Args:
        user_id (int): The Telegram user ID.
        nectrozz (Optional[int]): Amount of Nectrozz to set/add/subtract.
        kairoz (Optional[int]): Amount of Kairoz to set/add/subtract.
        operation (str): Operation type ('set', 'add', 'subtract').

    Raises:
        ValueError: If amounts are negative or operation is invalid.
        CoinError: If the database operation fails.
    """
    if operation not in ["set", "add", "subtract"]:
        raise ValueError(f"Invalid operation: {operation}. Must be 'set', 'add', or 'subtract'.")

    if nectrozz is not None and nectrozz < 0:
        raise ValueError("Nectrozz amount cannot be negative.")
    if kairoz is not None and kairoz < 0:
        raise ValueError("Kairoz amount cannot be negative.")

    try:
        update_fields = {}
        if nectrozz is not None:
            update_fields["Nectrozz"] = nectrozz if operation != "subtract" else -nectrozz
        if kairoz is not None:
            update_fields["Kairoz"] = kairoz if operation != "subtract" else -kairoz

        if update_fields:
            mongo_op = "$set" if operation == "set" else "$inc"
            await coin_collection.update_one(
                {"_id": user_id},
                {mongo_op: update_fields},
                upsert=True
            )
            LOGGER.debug(f"Updated coins for user {user_id}: {operation} {update_fields}")
        else:
            LOGGER.debug(f"No coin updates for user {user_id}: No valid amounts provided")
    except Exception as e:
        LOGGER.error(f"Failed to update coins for user {user_id}: {e}")
        raise CoinError(f"Failed to update coins: {e}")

async def ensure_positive_balance(user_id: int, nectrozz: int = 0, kairoz: int = 0) -> bool:
    """
    Check if a user has sufficient coin balances for a subtraction operation.

    Args:
        user_id (int): The Telegram user ID.
        nectrozz (int): Amount of Nectrozz to check.
        kairoz (int): Amount of Kairoz to check.

    Returns:
        bool: True if the user has sufficient balance, False otherwise.

    Raises:
        CoinError: If the database operation fails.
    """
    try:
        balance = await get_user_coin_balance(user_id)
        sufficient = (
            balance["Nectrozz"] >= nectrozz and
            balance["Kairoz"] >= kairoz
        )
        LOGGER.debug(f"Balance check for user {user_id}: Sufficient={sufficient}, Required: Nectrozz={nectrozz}, Kairoz={kairoz}")
        return sufficient
    except Exception as e:
        LOGGER.error(f"Failed to check balance for user {user_id}: {e}")
        raise CoinError(f"Failed to check balance: {e}")

async def delete_user_coin_doc(user_id: int) -> bool:
    """
    Delete a user's coin document.

    Args:
        user_id (int): The Telegram user ID.

    Returns:
        bool: True if the document was deleted, False if it didn't exist.

    Raises:
        CoinError: If the database operation fails.
    """
    try:
        result = await coin_collection.delete_one({"_id": user_id})
        success = result.deleted_count > 0
        LOGGER.debug(f"Deleted coin document for user {user_id}: {'Success' if success else 'Not found'}")
        return success
    except Exception as e:
        LOGGER.error(f"Failed to delete coin document for user {user_id}: {e}")
        raise CoinError(f"Failed to delete coin document: {e}")
