from shivu import coin

async def create_user_coin_doc(user_id: int):
    existing = await coin.find_one({"_id": user_id})
    if not existing:
        await coin.insert_one({
            "_id": user_id,
            "Nectrozz": 0,
            "Kairoz": 0
        })
