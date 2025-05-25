from shivu import sudo

# Structure in DB: { "_id": user_id, "role": "superuser"/"owner"/"sudo"/"uploader" }

async def add_user(user_id: int, role: str):
    await sudo.update_one({"_id": user_id}, {"$set": {"role": role}}, upsert=True)

async def remove_user(user_id: int):
    await sudo.delete_one({"_id": user_id})

async def get_user_role(user_id: int) -> str:
    user = await sudo.find_one({"_id": user_id})
    return user.get("role") if user else None

async def get_all_users_by_role(role: str):
    cursor = sudo.find({"role": role})
    return [doc["_id"] async for doc in cursor]

async def get_all_sudo_users():
    cursor = sudo.find({})
    return [{ "id": doc["_id"], "role": doc["role"] } async for doc in cursor]
