import html
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
    CallbackQuery,
)
from pyromod import listen
from shivu import shivuu, user_collection


IMAGE_URL = "https://i.ibb.co/Zpcqv2p3/tmpepyoc31z.jpg"
PAGE_SIZE = 10
HEADER_SMALL_CAPS = "ᴛᴏᴘ ᴜꜱᴇʀꜱ �ᴡɪᴛʜ ᴍᴏꜱᴛ ᴄʜᴀʀᴀᴄᴛᴇʀꜱ\n\n"


async def build_leaderboard_text(offset: int = 0) -> str:
    offset = max(0, offset)  # Ensure offset is not negative
    
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
        username = user.get("username")
        first_name = html.escape(user.get("first_name", "Unknown"))
        if len(first_name) > 15:
            first_name = first_name[:15] + "..."
        character_count = user["character_count"]
        
        line = (f'{i}. <a href="https://t.me/{username}"><b>{first_name}</b></a> ➾ <b>{character_count}</b>' 
                if username else 
                f'{i}. <b>{first_name}</b> ➾ <b>{character_count}</b>')
        lines.append(line)

    return f"<b>{HEADER_SMALL_CAPS}</b>" + "\n".join(lines)


def build_buttons(offset: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("⟳ Refresh", callback_data=f"leaderboard_users_{offset}"),
            InlineKeyboardButton("⌕ Find", callback_data="leaderboard_users_find")
        ],
        [
            InlineKeyboardButton("⌫ Clear", callback_data="leaderboard_users_clear")
        ]
    ]
    
    if offset > 0:
        buttons[1].insert(0, InlineKeyboardButton("« Prev", callback_data=f"leaderboard_users_{max(0, offset - PAGE_SIZE)}"))
    
    buttons[1].append(InlineKeyboardButton("⟶ Next", callback_data=f"leaderboard_users_{offset + PAGE_SIZE}"))
    
    return InlineKeyboardMarkup(buttons)


@shivuu.on_message(filters.command("top"))
async def leaderboard_command(_, message: Message):
    offset = 0
    text = await build_leaderboard_text(offset)
    buttons = build_buttons(offset)

    await message.reply_photo(
        photo=IMAGE_URL,
        caption=text,
        reply_markup=buttons,
        parse_mode=ParseMode.HTML
    )


@shivuu.on_callback_query(filters.regex(r"^leaderboard_users"))
async def leaderboard_callback(_, query: CallbackQuery):
    await query.answer()  # Answer callback to stop loading animation
    
    data = query.data

    if data == "leaderboard_users_find":
        await query.message.reply_text("Please enter the rank number you want to find (e.g. 15):")

        try:
            response = await shivuu.listen(query.message.chat.id, filters.text, timeout=30)
            rank_text = response.text.strip()

            if not rank_text.isdigit():
                await response.reply_text("Invalid input. Please enter a number.", quote=True)
                return

            rank = int(rank_text)
            if rank < 1:
                await response.reply_text("Rank must be at least 1.", quote=True)
                return

            offset = ((rank - 1) // PAGE_SIZE) * PAGE_SIZE
            text = await build_leaderboard_text(offset)
            buttons = build_buttons(offset)

            await query.message.edit_media(
                media=InputMediaPhoto(media=IMAGE_URL, caption=text, parse_mode=ParseMode.HTML),
                reply_markup=buttons
            )
        except TimeoutError:
            await query.message.reply_text("Timed out waiting for response. Please try again.")
        except Exception as e:
            await query.message.reply_text(f"An error occurred: {str(e)}")
        return

    if data == "leaderboard_users_clear":
        await query.message.edit_caption(
            caption="Leaderboard cleared.",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        offset = int(data.split("_")[-1])
        text = await build_leaderboard_text(offset)
        
        if "No more users to show" in text and offset > 0:
            offset = max(0, offset - PAGE_SIZE)
            text = await build_leaderboard_text(offset)
            
        buttons = build_buttons(offset)

        await query.message.edit_media(
            media=InputMediaPhoto(media=IMAGE_URL, caption=text, parse_mode=ParseMode.HTML),
            reply_markup=buttons
        )
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)
