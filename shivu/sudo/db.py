from shivu import db

sudo_collection = db['sudo']

async def get_user_role(user_id: int) -> str | None:
    """Fetch a user's role from the sudo collection."""
    user = await sudo_collection.find_one({"user_id": user_id})
    return user.get("role") if user else None

async def set_user_role(user_id: int, role: str) -> bool:
    """Assign or update a user's role in the sudo collection."""
    result = await sudo_collection.update_one(
        {"user_id": user_id},
        {"$set": {"role": role}},
        upsert=True
    )
    return result.modified_count > 0 or result.upserted_id is not None

async def remove_user_role(user_id: int) -> bool:
    """Remove a user's role from the sudo collection."""
    result = await sudo_collection.delete_one({"user_id": user_id})
    return result.deleted_count > 0

async def get_all_sudo_users() -> list[dict]:
    """Fetch all users with roles from the sudo collection."""
    return await sudo_collection.find().to_list(length=None)
