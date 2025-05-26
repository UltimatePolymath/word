from shivu.sin import currency_db

# Collection
bal = currency_db["bal"]

# Check if a user document already exists
async def is_user_initialized(user_id: int) -> bool:
    return await bal.find_one({"user_id": user_id}) is not None

# Ensure a document exists for a user
async def ensure_user(user_id: int):
    await bal.update_one(
        {"user_id": user_id},
        {"$setOnInsert": {"Nectrozz": 0}},
        upsert=True
    )

# Get user's Nectrozz balance
async def get_balance(user_id: int) -> int:
    user = await bal.find_one({"user_id": user_id})
    return user["Nectrozz"] if user else 0

# Update (increment) user's Nectrozz
async def add_nectrozz(user_id: int, amount: int):
    await ensure_user(user_id)
    await bal.update_one(
        {"user_id": user_id},
        {"$inc": {"Nectrozz": amount}}
    )

# Set Nectrozz to exact value
async def set_nectrozz(user_id: int, value: int):
    await ensure_user(user_id)
    await bal.update_one(
        {"user_id": user_id},
        {"$set": {"Nectrozz": value}}
    )
