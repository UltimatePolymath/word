from shivu import coin

# Create a new document if it doesn't exist
async def create_user_coin_doc(user_id: int):
    existing = await coin.find_one({"_id": user_id})
    if not existing:
        await coin.insert_one({
            "_id": user_id,
            "Nectrozz": 0,
            "Kairoz": 0
        })

# Get a user's coin data
async def get_user_coins(user_id: int) -> dict:
    user = await coin.find_one({"_id": user_id})
    if not user:
        await create_user_coin_doc(user_id)
        return {"Nectrozz": 0, "Kairoz": 0}
    return {"Nectrozz": user.get("Nectrozz", 0), "Kairoz": user.get("Kairoz", 0)}

# Update a user's coin balances (set specific values)
async def set_user_coins(user_id: int, nectrozz: int = None, kairoz: int = None):
    update_fields = {}
    if nectrozz is not None:
        update_fields["Nectrozz"] = nectrozz
    if kairoz is not None:
        update_fields["Kairoz"] = kairoz
    if update_fields:
        await coin.update_one({"_id": user_id}, {"$set": update_fields}, upsert=True)

# Increment coin values
async def increment_user_coins(user_id: int, nectrozz_delta: int = 0, kairoz_delta: int = 0):
    await coin.update_one(
        {"_id": user_id},
        {"$inc": {"Nectrozz": nectrozz_delta, "Kairoz": kairoz_delta}},
        upsert=True
    )

# Delete a user's coin data
async def delete_user_coin_doc(user_id: int):
    await coin.delete_one({"_id": user_id})
