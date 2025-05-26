from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from shivu import shivuu
from shivu.archive.coin import get_user_coin_balance, create_user_coin_doc

KAIROZ_SYMBOL = "₭"

@shivuu.on_message(filters.command("kairoz"))
async def kairoz_cmd(_, message: Message):
    user_id = message.from_user.id

    # Ensure user document exists
    await create_user_coin_doc(user_id)

    # Get coin balances
    balance = await get_user_coin_balance(user_id)
    kairoz = balance.get("Kairoz", 0)

    await message.reply_text(
        f"**Current Kairoz Balance:** `{KAIROZ_SYMBOL}{kairoz:,}[.](https://i.ibb.co/ymvNjsTs/tmpyx38ufcs.jpg)`",
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=False
    )
