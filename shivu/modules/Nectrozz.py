from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

from shivu import shivuu
from shivu.archive.coin import get_user_nectrozz_balance
from shivu import coin as coin_collection

# Helper to format bold italic
def bold_italic(text: str) -> str:
    return f"**`{text}`**"

@shivuu.on_message(filters.command("nectrozz"))
async def show_nectrozz_balance(_, message: Message):
    user_id = message.from_user.id

    # Check if user exists in the coin collection
    user_data = await coin_collection.find_one({"_id": user_id})
    if not user_data:
        return await message.reply_text("Please use /start first to initialize your profile.")

    balance = await get_user_nectrozz_balance(user_id)
    amount = balance.get("amount", 0) if isinstance(balance, dict) else balance
    text = bold_italic(f"Current Balance: ₦{amount:,}")
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
