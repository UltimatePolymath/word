from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

from shivu import shivuu
from shivu.archive.coin import get_user_coin_balance, create_user_coin_doc

# Helper to format bold italic
def bold_italic(text: str) -> str:
    return f"**`{text}`**"

@shivuu.on_message(filters.command("nectrozz"))
async def show_nectrozz_balance(_, message: Message):
    user_id = message.from_user.id

    # Ensure user document exists
    await create_user_coin_doc(user_id)

    # Get balance using unified coin handler
    balance = await get_user_coin_balance(user_id)
    amount = balance.get("Nectrozz", 0)
    text = bold_italic(f"Current Balance: ₦{amount:,}")
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
