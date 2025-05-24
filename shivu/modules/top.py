import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes
from pyromod import listen

from shivu import user_collection, application 

IMAGE_URL = "https://i.ibb.co/Zpcqv2p3/tmpepyoc31z.jpg"
PAGE_SIZE = 10
MODE = "users"

# Unicode small caps approximation for header:
HEADER_SMALL_CAPS = (
    "ᴛᴏᴘ ᴜꜱᴇʀꜱ ᴡɪᴛʜ ᴍᴏꜱᴛ ᴄʜᴀʀᴀᴄᴛᴇʀꜱ\n\n"
)


async def build_leaderboard_text(offset: int = 0) -> str:
    cursor = user_collection.aggregate([
        {"$project": {"username": 1, "first_name": 1, "character_count": {"$size": "$characters"}}},
        {"$sort": {"character_count": -1}},
        {"$skip": offset},
        {"$limit": PAGE_SIZE}
    ])
    leaderboard_data = await cursor.to_list(length=PAGE_SIZE)
    if not leaderboard_data:
        return "<b>No more users to show.</b>"

    lines = []
    for i, user in enumerate(leaderboard_data, start=offset + 1):
        username = user.get('username', 'Unknown')
        first_name = html.escape(user.get('first_name', 'Unknown'))
        if len(first_name) > 15:
            first_name = first_name[:15] + '...'
        character_count = user['character_count']
        lines.append(f'{i}. <a href="https://t.me/{username}"><b>{first_name}</b></a> ➾ <b>{character_count}</b>')

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

    # Arrange as 2 buttons per row except last row with one button only
    # The above layout fits that

    return InlineKeyboardMarkup(buttons)


async def leaderboard_command(update, context: ContextTypes.DEFAULT_TYPE):
    offset = 0
    text = await build_leaderboard_text(offset)
    buttons = build_buttons(offset)

    await update.message.reply_photo(
        photo=IMAGE_URL,
        caption=text,
        parse_mode="HTML",
        reply_markup=buttons
    )


async def find_rank_handler(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text("Please enter the rank number you want to find (e.g. 15):")
    try:
        # Wait for user reply (timeout after 30 seconds)
        response = await context.bot.listen(update.effective_chat.id, timeout=30)
        rank_text = response.text.strip()

        if not rank_text.isdigit():
            await query.message.reply_text("Invalid rank number. Please enter a valid number.")
            return

        rank = int(rank_text)
        if rank < 1:
            await query.message.reply_text("Rank number must be greater than 0.")
            return

        # Calculate offset based on rank
        offset = ((rank - 1) // PAGE_SIZE) * PAGE_SIZE
        text = await build_leaderboard_text(offset)
        buttons = build_buttons(offset)

        # Edit original message with the requested page
        await query.message.edit_media(
            media=InputMediaPhoto(media=IMAGE_URL, caption=text, parse_mode="HTML"),
            reply_markup=buttons
        )
    except Exception as e:
        await query.message.reply_text("Timeout or error occurred. Please try again.")


async def clear_handler(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Clear leaderboard message or send a simple message
    await query.message.edit_caption(caption="Leaderboard cleared.")


async def leaderboard_callback(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "leaderboard_users_find":
        return await find_rank_handler(update, context)

    if data == "leaderboard_users_clear":
        return await clear_handler(update, context)

    # Data format: leaderboard_users_OFFSET
    parts = data.split("_")
    offset = int(parts[-1]) if parts[-1].isdigit() else 0

    text = await build_leaderboard_text(offset)
    buttons = build_buttons(offset)

    await query.message.edit_media(
        media=InputMediaPhoto(media=IMAGE_URL, caption=text, parse_mode="HTML"),
        reply_markup=buttons
    )


application.add_handler(CommandHandler("top", leaderboard_command))
application.add_handler(CallbackQueryHandler(leaderboard_callback, pattern=r"^leaderboard_users(_find|_clear|_\d+)$"))
