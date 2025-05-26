from pyrogram import filters
from pyrogram.types import Message
from shivu import shivuu
from shivu.sin.currency import get_balance, is_user_initialized

@shivuu.on_message(filters.command("bal"))
async def balance_command(_, message: Message):
    user_id = message.from_user.id

    if not await is_user_initialized(user_id):
        await message.reply_text("You don't have an account yet. Use /start to begin!")
        return

    amount = await get_balance(user_id)
    await message.reply_text(f"Your Nectrozz balance: **{amount}**")
