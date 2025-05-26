from pyrogram import filters
from pyrogram.types import Message
from shivu import shivuu
from shivu.archive.rarity import set_rarity, get_all_rarities, delete_rarity
from shivu.archive.sudo import check_user_permission

@shivuu.on_message(filters.command("setrarity"))
async def set_rarity_command(_, message: Message):
    user_id = message.from_user.id
    role = await check_user_permission(user_id)

    if role != "superuser":
        return await message.reply_text("Only the superuser can set rarities.")

    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        return await message.reply_text("Usage: /setrarity <number> <emoji> <rarity>")

    try:
        no = int(args[1])
        emoji = args[2]
        rarity = args[3]
        await set_rarity(no, emoji, rarity)
        await message.reply_text(f"Rarity set:\nNo: {no}\nEmoji: {emoji}\nRarity: {rarity}")
    except ValueError:
        await message.reply_text("Invalid number. Use: /setrarity <number> <emoji> <rarity>")

@shivuu.on_message(filters.command("delrarity"))
async def delete_rarity_command(_, message: Message):
    user_id = message.from_user.id
    role = await check_user_permission(user_id)

    if role != "superuser":
        return await message.reply_text("Only the superuser can delete rarities.")

    args = message.text.split()
    if len(args) != 2:
        return await message.reply_text("Usage: /delrarity <number>")

    try:
        no = int(args[1])
        deleted = await delete_rarity(no)
        if deleted:
            await message.reply_text(f"Rarity with No: {no} deleted.")
        else:
            await message.reply_text(f"No rarity found with No: {no}")
    except ValueError:
        await message.reply_text("Invalid number. Use: /delrarity <number>")

@shivuu.on_message(filters.command("rarities"))
async def list_rarities_command(_, message: Message):
    all_rarities = await get_all_rarities()

    if not all_rarities:
        return await message.reply_text("No rarities found.")

    text = "**Available Rarities:**\n\n"
    for rarity in all_rarities:
        text += f"**No:** {rarity['no']} | **Emoji:** {rarity['emoji']} | **Rarity:** {rarity['rarity']}\n"

    await message.reply_text(text)
