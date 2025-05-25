import logging
from pymongo import ReturnDocument
from shivu import db, LOGGER

async def check_user_permission(user_id: int) -> str | None:
    """Check if the user has a role in the sudo collection and return the role."""
    try:
        user = await db.sudo.find_one({"user_id": user_id})
        role = user.get("role") if user and user.get("role") in ["superuser", "owner", "sudo", "uploader"] else None
        LOGGER.debug(f"Permission check for user {user_id}: Role {role or 'None'}")
        return role
    except Exception as e:
        LOGGER.error(f"Failed to check permission for user {user_id}: {e}")
        return None

# Other functions (get_user_role, set_user_role, remove_user_role, get_all_sudo_users) remain unchanged
async def get_user_role(user_id: int) -> str | None:
    """Fetch a user's role from the sudo collection."""
    try:
        user = await db.sudo.find_one({"user_id": user_id})
        role = user.get("role") if user else None
        LOGGER.debug(f"Fetched role for user {user_id}: {role}")
        return role
    except Exception as e:
        LOGGER.error(f"Failed to get user role for {user_id}: {e}")
        return None

async def set_user_role(user_id: int, role: str) -> bool:
    """Assign or update a user's role in the sudo collection."""
    try:
        result = await db.sudo.update_one(
            {"user_id": user_id},
            {"$set": {"role": role}},
            upsert=True
        )
        success = result.modified_count > 0 or result.upserted_id is not None
        LOGGER.debug(f"Set role {role} for user {user_id}: {'Success' if success else 'Failed'}")
        return success
    except Exception as e:
        LOGGER.error(f"Failed to set role {role} for {user_id}: {e}")
        return False

async def remove_user_role(user_id: int) -> bool:
    """Remove a user's role from the sudo collection."""
    try:
        result = await db.sudo.delete_one({"user_id": user_id})
        success = result.deleted_count > 0
        LOGGER.debug(f"Removed role for user {user_id}: {'Success' if success else 'Failed'}")
        return success
    except Exception as e:
        LOGGER.error(f"Failed to remove role for {user_id}: {e}")
        return False

async def get_all_sudo_users() -> list[dict]:
    """Fetch all users with roles from the sudo collection."""
    try:
        users = await db.sudo.find().to_list(length=None)
        LOGGER.debug(f"Fetched all sudo users: {len(users)} found")
        return users
    except Exception as e:
        LOGGER.error(f"Failed to fetch all sudo users: {e}")
        return []
