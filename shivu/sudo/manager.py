from shivu import sudo as sudo_collection
from .constants import ROLES, SUPERUSER_ID

async def get_role(user_id: int) -> str | None:
    doc = await sudo_collection.find_one({'user_id': user_id})
    return doc['role'] if doc else None

async def set_role(user_id: int, role: str) -> bool:
    if role not in ROLES:
        return False
    await sudo_collection.update_one(
        {'user_id': user_id},
        {'$set': {'role': role}},
        upsert=True
    )
    return True

async def remove_role(user_id: int) -> bool:
    result = await sudo_collection.delete_one({'user_id': user_id})
    return result.deleted_count > 0

async def is_superuser(user_id: int) -> bool:
    return user_id == SUPERUSER_ID

async def can_manage(executor_id: int, target_role: str) -> bool:
    if await is_superuser(executor_id):
        return True

    executor_role = await get_role(executor_id)

    if executor_role == "owner":
        return target_role in ["sudo", "uploader"]
    if executor_role == "sudo":
        return target_role == "uploader"
    
    return False
