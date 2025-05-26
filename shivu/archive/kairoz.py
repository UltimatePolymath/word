from shivu import coin as coin_collection

# Initialize user with default Kairoz value
async def create_kairoz_user(user_id: int):
    existing = await coin_collection.find_one({"_id": user_id})
    if not existing:
        await coin_collection.insert_one({"_id": user_id, "Nectrozz": 0, "Kairoz": 0})

# Get current Kairoz balance
async def get_user_kairoz_balance(user_id: int) -> int:
    user = await coin_collection.find_one({"_id": user_id})
    return user.get("Kairoz", 0) if user else 0

# Add Kairoz to user
async def add_kairoz(user_id: int, amount: int):
    await coin_collection.update_one(
        {"_id": user_id},
        {"$inc": {"Kairoz": amount}},
        upsert=True
    )

# Subtract Kairoz from user
async def remove_kairoz(user_id: int, amount: int):
    await coin_collection.update_one(
        {"_id": user_id},
        {"$inc": {"Kairoz": -amount}},
        upsert=True
    )

# Set Kairoz balance directly
async def set_kairoz(user_id: int, amount: int):
    await coin_collection.update_one(
        {"_id": user_id},
        {"$set": {"Kairoz": amount}},
        upsert=True
    )
