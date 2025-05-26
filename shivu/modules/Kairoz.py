from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from shivu import shivuu
from shivu.archive.kairoz import get_user_kairoz_balance, create_kairoz_user

KAIROZ_SYMBOL = "₭"

@shivuu.on_message(filters.command("kairoz"))
async def kairoz_cmd(_, message: Message):
    user_id = message.from_user.id

    user_data = await get_user_kairoz_balance(user_id)
    if user_data is None:
        await create_kairoz_user(user_id)
        await message.reply_text(
            "***You're not initialized yet. Please use /start to begin.***",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    balance = await get_user_kairoz_balance(user_id)
    await message.reply_text(
        f"**Current [K](https://i.ibb.co/ymvNjsTs/tmpyx38ufcs.jpg)airoz Balance:** `{KAIROZ_SYMBOL}{balance:,}`",
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=False
    )
