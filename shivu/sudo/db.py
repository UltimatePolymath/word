# shivu/sudo/db.py

from shivu import sudo as sudo_collection  # MongoDB collection from shivu.__init__

# --- CREATE / UPDATE ---

async def assign_role(user_id: int, role: str, appointed_by: int):
    await sudo_collection.update_one(
        {"_id": user_id},
        {"$set": {"role": role, "appointed_by": appointed_by}},
        upsert=True
    )


# --- READ ---

async def get_user_role(user_id: int) -> str | None:
    data = await sudo_collection.find_one({"_id": user_id})
    return data["role"] if data else None


async def get_appointed_by(user_id: int) -> int | None:
    data = await sudo_collection.find_one({"_id": user_id})
    return data["appointed_by"] if data else None


async def get_all_by_role(role: str) -> list[int]:
    cursor = sudo_collection.find({"role": role})
    return [doc["_id"] async for doc in cursor]


# --- DELETE ---

async def remove_role(user_id: int):
    await sudo_collection.delete_one({"_id": user_id})
