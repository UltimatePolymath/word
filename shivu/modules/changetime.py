from pymongo import ReturnDocument
from pyrogram.enums import ChatMemberStatus, ChatType
from shivu import user_totals_collection, shivuu
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

ADMINS = [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

def to_small_caps(text: str) -> str:
    normal = "abcdefghijklmnopqrstuvwxyz"
    smallcaps = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    return ''.join(smallcaps[normal.index(c)] if c in normal else c for c in text.lower())

@shivuu.on_message(filters.command(["changetime", "ᴄʜᴀɴɢᴇᴛɪᴍᴇ"]))
async def spawn_panel(client: Client, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return await message.reply_text("Only in groups, dear.")

    member = await client.get_chat_member(chat_id, user_id)
    if member.status not in ADMINS:
        return await message.reply_text("Only admins can access the spawn panel.")

    panel_text = (
        "╭━〔 𝕾𝖎𝖓 🎃 𝕮𝖆𝖙𝖈𝖍𝖊𝖗 〕━╮\n"
        "  ✦ Welcome to the spawn panel ✦\n"
        "╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
        "⤷ ⦿ 𝟱𝟬 ━ Per 50 messages\n"
        "⤷ ⦿ 𝟭𝟬𝟬 ━ Per 100 messages\n"
        "⤷ ⦿ Custom ━ Set your own count (>50)\n"
        "⤷ ⦿ Showtime ━ View current count\n"
        "⤷ ⦿ Resettime ━ Reset to 100\n"
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("➴ 𝟱𝟬", callback_data="settime_50"),
         InlineKeyboardButton("➴ 𝟭𝟬𝟬", callback_data="settime_100")],
        [InlineKeyboardButton("✎ Custom", callback_data="settime_custom"),
         InlineKeyboardButton("✧ Showtime", callback_data="settime_show")],
        [InlineKeyboardButton("↻ Resettime", callback_data="settime_reset")]
    ])

    await message.reply_text(panel_text, reply_markup=buttons)


@shivuu.on_callback_query(filters.regex(r"settime_"))
async def handle_time_callbacks(client: Client, query):
    await query.answer()  # Acknowledge the callback to remove loading state
    data = query.data.split("_")[1]
    chat_id = query.message.chat.id

    if data in ["50", "100"]:
        new_value = int(data)
        await user_totals_collection.find_one_and_update(
            {"chat_id": str(chat_id)},
            {"$set": {"message_frequency": new_value}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        await query.message.edit_text(f"✅ Spawn time set to every {new_value} messages.")

    elif data == "reset":
        await user_totals_collection.find_one_and_update(
            {"chat_id": str(chat_id)},
            {"$set": {"message_frequency": 100}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        await query.message.edit_text("🔄 Reset to default (100 messages).")

    elif data == "show":
        chat_data = await user_totals_collection.find_one({"chat_id": str(chat_id)})
        count = chat_data.get("message_frequency", 100) if chat_data else 100
        await query.message.edit_text(f"⏱ Current spawn frequency: {count} messages.")

    elif data == "custom":
        await query.message.edit_text("✍ Please enter your custom message count (must be ≥ 50):")

        try:
            response: Message = await client.listen(chat_id)
            value = int(response.text)
            if value < 50:
                await client.send_message(chat_id, "❌ Must be at least 50.")
                return
            await user_totals_collection.find_one_and_update(
                {"chat_id": str(chat_id)},
                {"$set": {"message_frequency": value}},
                upsert=True,
                return_document=ReturnDocument.AFTER
            )
            await client.send_message(chat_id, f"✅ Custom spawn time set to {value} messages.")
        except ValueError:
            await client.send_message(chat_id, "❌ Invalid number.")
