import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler

from shivu import (
    application,
    OWNER_ID,
    user_collection,
    top_global_groups_collection,
    group_user_totals_collection,
    sudo_users as SUDO_USERS
)

IMAGE_URL = "https://i.ibb.co/Zpcqv2p3/tmpepyoc31z.jpg"

BTN_USERS = "ᘔ ᴜꜱᴇʀꜱ 〤"
BTN_GROUPS = "ᘔ ɢʀᴏᴜᴘꜱ 〤"
BTN_CTOP = "ᘔ ᴄᴛᴏᴘ 〤"


async def build_leaderboard_text(mode: str, chat_id=None):
    if mode == "users":
        cursor = user_collection.aggregate([
            {"$project": {"username": 1, "first_name": 1, "character_count": {"$size": "$characters"}}},
            {"$sort": {"character_count": -1}},
            {"$limit": 10}
        ])
        leaderboard_data = await cursor.to_list(length=10)
        header = "<b>TOP 10 USERS WITH MOST CHARACTERS</b>\n\n"

        lines = []
        for i, user in enumerate(leaderboard_data, start=1):
            username = user.get('username', 'Unknown')
            first_name = html.escape(user.get('first_name', 'Unknown'))
            if len(first_name) > 15:
                first_name = first_name[:15] + '...'
            character_count = user['character_count']
            lines.append(f'{i}. <a href="https://t.me/{username}"><b>{first_name}</b></a> ➾ <b>{character_count}</b>')

        return header + "\n".join(lines)

    elif mode == "groups":
        cursor = top_global_groups_collection.aggregate([
            {"$project": {"group_name": 1, "count": 1}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ])
        leaderboard_data = await cursor.to_list(length=10)
        header = "<b>TOP 10 GROUPS WHO GUESSED MOST CHARACTERS</b>\n\n"

        lines = []
        for i, group in enumerate(leaderboard_data, start=1):
            group_name = html.escape(group.get('group_name', 'Unknown'))
            if len(group_name) > 15:
                group_name = group_name[:15] + '...'
            count = group['count']
            lines.append(f'{i}. <b>{group_name}</b> ➾ <b>{count}</b>')

        return header + "\n".join(lines)

    elif mode == "ctop":
        if chat_id is None:
            return "<b>CTOP leaderboard must be used in a group chat.</b>"
        cursor = group_user_totals_collection.aggregate([
            {"$match": {"group_id": chat_id}},
            {"$project": {"username": 1, "first_name": 1, "character_count": "$count"}},
            {"$sort": {"character_count": -1}},
            {"$limit": 10}
        ])
        leaderboard_data = await cursor.to_list(length=10)
        header = "<b>TOP 10 USERS WHO GUESSED CHARACTERS MOST TIME IN THIS GROUP</b>\n\n"

        lines = []
        for i, user in enumerate(leaderboard_data, start=1):
            username = user.get('username', 'Unknown')
            first_name = html.escape(user.get('first_name', 'Unknown'))
            if len(first_name) > 15:
                first_name = first_name[:15] + '...'
            character_count = user['character_count']
            lines.append(f'{i}. <a href="https://t.me/{username}"><b>{first_name}</b></a> ➾ <b>{character_count}</b>')

        return header + "\n".join(lines)


def build_buttons(current_mode: str):
    buttons = [
        [InlineKeyboardButton(BTN_USERS, callback_data="leaderboard_users"),
         InlineKeyboardButton(BTN_GROUPS, callback_data="leaderboard_groups")],
        [InlineKeyboardButton(BTN_CTOP, callback_data="leaderboard_ctop")]
    ]
    # Mark active button with diamond
    for row in buttons:
        for button in row:
            if button.callback_data == f"leaderboard_{current_mode}":
                button.text = f"◆ {button.text}"
    return InlineKeyboardMarkup(buttons)


async def leaderboard_command(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    mode = "users"  # default leaderboard

    text = await build_leaderboard_text(mode, chat_id)
    buttons = build_buttons(mode)

    await update.message.reply_photo(
        photo=IMAGE_URL,
        caption=text,
        parse_mode="HTML",
        reply_markup=buttons
    )


async def leaderboard_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    data = query.data

    mode = data.split("_")[1]

    text = await build_leaderboard_text(mode, chat_id)
    buttons = build_buttons(mode)

    await query.message.edit_media(
        media=InputMediaPhoto(media=IMAGE_URL, caption=text, parse_mode="HTML"),
        reply_markup=buttons
    )


application.add_handler(CommandHandler("leaderboard", leaderboard_command, block=False))
application.add_handler(CallbackQueryHandler(leaderboard_callback, pattern=r"leaderboard_"))
