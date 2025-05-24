import html
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, InputMediaPhoto
from pyromod import listen
from pyrogram import filters

from shivu import user_collection, shivuu  # your pyrogram.Client instance is shivuu

IMAGE_URL = "https://i.ibb.co/Zpcqv2p3/tmpepyoc31z.jpg"
PAGE_SIZE = 10

HEADER_SMALL_CAPS = "ᴛᴏᴘ ᴜꜱᴇʀꜱ ᴡɪᴛʜ ᴍᴏꜱᴛ ᴄʜᴀʀᴀᴄᴛᴇʀꜱ\n\n"


async def build_leaderboard_text(offset: int = 0) -> str:
    cursor = user_collection.aggregate([
        {"$project": {
            "username": 1,
            "first_name": 1,
            "character_count": {"$size": "$characters"}
        }},
        {"$sort": {"character_count": -1}},
        {"$skip": offset},
        {"$limit": PAGE_SIZE}
    ])
    leaderboard_data = await cursor.to_list(length=PAGE_SIZE)

    if not leaderboard_data:
        return "<b>No more users to show.</b>"

    lines = []
    for i, user in enumerate(leaderboard_data, start=offset + 1):
        username = user.get("username", "Unknown")
        first_name = html.escape(user.get("first_name", "Unknown"))
        if len(first_name) > 15:
            first_name = first_name[:15] + "..."
        character_count = user["character_count"]
        lines.append(
            f'{i}. <a href="https://t.me/{username}"><b>{first_name}</b></a> ➾ <b>{character_count}</b>'
        )

    return f"<b>{HEADER_SMALL_CAPS}</b>" + "\n".join(lines)


def build_buttons(offset: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("⟳ Refresh", callback_data=f"leaderboard_users_{offset}"),
            InlineKeyboardButton("⌕ Find", callback_data="leaderboard_users_find")
        ],
        [
            InlineKeyboardButton("⌫ Clear", callback_data="leaderboard_users_clear"),
            InlineKeyboardButton("⟶ Next", callback_data=f"leaderboard_users_{offset + PAGE_SIZE}")
        ],
        [
            InlineKeyboardButton("« Prev", callback_data=f"leaderboard_users_{max(0, offset - PAGE_SIZE)}")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


@shivuu.on_message(filters.command("top"))
async def leaderboard_command(client, message):
    offset = 0
    text = await build_leaderboard_text(offset)
    buttons = build_buttons(offset)

    await message.reply_photo(
        photo=IMAGE_URL,
        caption=text,
        parse_mode="html",
        reply_markup=buttons
    )


@shivuu.on_callback_query(filters.regex(r"^leaderboard_users(_find|_clear|_\d+)$"))
async def leaderboard_callback(client, callback_query: CallbackQuery):
    await callback_query.answer()
    data = callback_query.data

    if data == "leaderboard_users_find":
        await callback_query.message.reply_text("Please enter the rank number you want to find (e.g. 15):")

        try:
            response = await client.listen(callback_query.message.chat.id, timeout=30)
            rank_text = response.text.strip()

            if not rank_text.isdigit():
                await callback_query.message.reply_text("Invalid input. Please enter a valid number.")
                return

            rank = int(rank_text)
            if rank < 1:
                await callback_query.message.reply_text("Rank must be greater than 0.")
                return

            offset = ((rank - 1) // PAGE_SIZE) * PAGE_SIZE
            text = await build_leaderboard_text(offset)
            buttons = build_buttons(offset)

            await callback_query.message.edit_media(
                media=InputMediaPhoto(media=IMAGE_URL, caption=text, parse_mode="html"),
                reply_markup=buttons
            )
        except Exception:
            await callback_query.message.reply_text("Timeout or error occurred. Please try again.")

        return

    if data == "leaderboard_users_clear":
        # Delete entire message as requested
        await callback_query.message.delete()
        return

    # Pagination handler
    parts = data.split("_")
    offset = int(parts[-1]) if parts[-1].isdigit() else 0

    text = await build_leaderboard_text(offset)
    buttons = build_buttons(offset)

    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=IMAGE_URL, caption=text, parse_mode="html"),
        reply_markup=buttons
    )
