from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

from shivu import shivuu
from shivu.archive.coin import get_user_nectrozz_balance

# Helper to format bold italic
def bold_italic(text: str) -> str:
    return f"*_{text}_*"

@shivuu.on_message(filters.command("nectrozz"))
async def show_nectrozz_balance(_, message: Message):
    user_id = message.from_user.id
    balance = await get_user_nectrozz_balance(user_id)
    text = bold_italic(f"Current Balance: ₦{balance:,}")
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
