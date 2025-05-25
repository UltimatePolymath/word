from shivu import sudo as sudo_db
from shivu.config import OWNER_ID
from .constants import SUPERUSER_ID, OWNER, SUDO, UPLOADER, ROLES
from pyrogram.types import User
from functools import wraps
from pyrogram.errors import UserNotParticipant
from pyrogram import Client, filters
from pyrogram.types import Message

# --------------------------------
# Role Fetching and Validation
# --------------------------------

async def get_role(user_id: int) -> str | None:
    entry = await sudo_db.find_one({"user_id": user_id})
    return entry["role"] if entry else None

async def get_appointer(user_id: int) -> int | None:
    entry = await sudo_db.find_one({"user_id": user_id})
    return entry["appointed_by"] if entry else None

async def is_role(user_id: int, role: str) -> bool:
    return await get_role(user_id) == role

# --------------------------------
# Hierarchy Logic
# --------------------------------

def role_priority(role: str) -> int:
    """Defines role hierarchy levels. Higher is stronger."""
    return {
        SUPERUSER_ID: 999,
        OWNER: 3,
        SUDO: 2,
        UPLOADER: 1,
    }.get(role, 0)

async def has_clearance(actor_id: int, target_role: str) -> bool:
    """Checks if actor has permission to appoint/remove target_role"""
    if actor_id == SUPERUSER_ID:
        return True
    actor_role = await get_role(actor_id)

    if actor_role == OWNER:
        return target_role in [SUDO, UPLOADER]
    elif actor_role == SUDO:
        return target_role == UPLOADER
    return False

async def can_remove(actor_id: int, target_id: int) -> bool:
    """Checks if actor is allowed to remove the target_id"""
    if actor_id == SUPERUSER_ID:
        return True

    target_role = await get_role(target_id)
    actor_role = await get_role(actor_id)

    if not target_role:
        return False

    if actor_role == OWNER:
        return target_role in [SUDO, UPLOADER]
    elif actor_role == SUDO:
        if target_role == UPLOADER:
            appointed_by = await get_appointer(target_id)
            return appointed_by == actor_id
    return False

# --------------------------------
# DB Management
# --------------------------------

async def assign_role(user_id: int, role: str, appointed_by: int):
    await sudo_db.update_one(
        {"user_id": user_id},
        {"$set": {"role": role, "appointed_by": appointed_by}},
        upsert=True
    )

async def remove_role(user_id: int):
    await sudo_db.delete_one({"user_id": user_id})

# --------------------------------
# Decorators for Command Access
# --------------------------------

def sudo_only():
    def decorator(func):
        @wraps(func)
        async def wrapper(client: Client, message: Message):
            user_id = message.from_user.id
            if user_id in [SUPERUSER_ID, OWNER_ID]:
                return await func(client, message)

            user_role = await get_role(user_id)
            if user_role in [OWNER, SUDO]:
                return await func(client, message)

            await message.reply_text(
                "`access denied` ⟶ you lack clearance to enter this command panel."
            )
        return wrapper
    return decorator
