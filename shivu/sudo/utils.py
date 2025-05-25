from functools import wraps
from pyrogram import Client
from pyrogram.types import Message
from shivu import sudo as sudo_collection  # MongoDB collection from __init__
from shivu.sudo.constants import SUPERUSER_ID, OWNER, SUDO, UPLOADER, ROLES


# --------------------------------
# Role Utilities
# --------------------------------

async def get_role(user_id: int) -> str | None:
    data = await sudo_collection.find_one({"_id": user_id})
    return data["role"] if data else None

async def get_appointer(user_id: int) -> int | None:
    data = await sudo_collection.find_one({"_id": user_id})
    return data["appointed_by"] if data else None

async def is_role(user_id: int, role: str) -> bool:
    return await get_role(user_id) == role


# --------------------------------
# Role Hierarchy Logic
# --------------------------------

def role_priority(role: str | None) -> int:
    return {
        OWNER: 3,
        SUDO: 2,
        UPLOADER: 1
    }.get(role, 0)

async def user_is_above(actor_id: int, target_id: int) -> bool:
    """Returns True if actor holds a higher role than target."""
    if actor_id == target_id:
        return False
    actor_role = await get_role(actor_id)
    target_role = await get_role(target_id)
    return role_priority(actor_role) > role_priority(target_role)

async def has_clearance(actor_id: int, target_role: str) -> bool:
    """Check if actor can appoint/remove the given role."""
    if actor_id == SUPERUSER_ID:
        return True

    actor_role = await get_role(actor_id)
    if actor_role == OWNER:
        return target_role in [SUDO, UPLOADER]
    if actor_role == SUDO:
        return target_role == UPLOADER
    return False

async def can_remove(actor_id: int, target_id: int) -> bool:
    """Validates whether actor can remove the target user."""
    if actor_id == SUPERUSER_ID:
        return True

    actor_role = await get_role(actor_id)
    target_role = await get_role(target_id)
    if not target_role:
        return False

    if actor_role == OWNER:
        return target_role in [SUDO, UPLOADER]
    if actor_role == SUDO:
        if target_role == UPLOADER:
            appointed_by = await get_appointer(target_id)
            return appointed_by == actor_id
    return False


# --------------------------------
# Decorators
# --------------------------------

def sudo_only():
    """Allows access only to sudo, owner, and superuser."""
    def decorator(func):
        @wraps(func)
        async def wrapper(client: Client, message: Message):
            user_id = message.from_user.id
            if user_id == SUPERUSER_ID:
                return await func(client, message)

            user_role = await get_role(user_id)
            if user_role in [OWNER, SUDO]:
                return await func(client, message)

            await message.reply_text(
                "`Access Denied` – You lack clearance to access this command panel."
            )
        return wrapper
    return decorator
