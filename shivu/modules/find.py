import logging
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
)
from telegram.constants import ParseMode
from shivu import application, LOGGER, collection, user_collection

# States for ConversationHandler
NAME_SEARCH, ID_SEARCH = range(2)

# Cache for inline queries
cached_searches = {}  # {user_id: [character_ids]}

async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /find command to open the initial panel."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    LOGGER.info(f"User {user_id} invoked /find in chat {chat_id} at {update.message.date}")

    caption = (
        "🔍 **Character Finder** 🔍\n\n"
        "Explore the vibrant world of characters in our bot! "
        "Whether you're searching for a favorite character by name or tracking down a specific ID, "
        "this tool helps you uncover details and ownership info."
    )
    keyboard = [[InlineKeyboardButton("Find a Character", callback_data="find_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await update.message.reply_photo(
            photo="https://i.ibb.co/whQn3yWs/tmp6lapxvnc.jpg",
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        LOGGER.debug(f"Sent initial panel to user {user_id} in chat {chat_id}")
    except Exception as e:
        LOGGER.error(f"Failed to send initial panel to user {user_id}: {e}")
        await update.message.reply_text("Error opening panel. Please try again.")
        return

async def find_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the main panel with Find IDs and Search ID options."""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    LOGGER.info(f"User {user_id} triggered find_panel callback in chat {chat_id}, query data: {query.data}")

    try:
        await query.answer()
        caption = (
            "🔎 **Character Search Panel** 🔎\n\n"
            "Choose an option below:\n"
            "• **Find IDs**: Search for characters by their name (e.g., 'Siesta').\n"
            "• **Search ID**: Find out who owns a specific character ID (e.g., '01')."
        )
        keyboard = [
            [InlineKeyboardButton("Find IDs", callback_data="find_ids")],
            [InlineKeyboardButton("Search ID", callback_data="search_id")],
            [InlineKeyboardButton("Back", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_caption(
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        LOGGER.debug(f"Displayed main panel for user {user_id} in chat {chat_id}")
        return ConversationHandler.END
    except Exception as e:
        LOGGER.error(f"Error in find_panel_callback for user {user_id}: {e}")
        await query.message.reply_text("Error loading panel. Please try again.")
        return ConversationHandler.END

async def find_ids_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user for a character name to search."""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    LOGGER.info(f"User {user_id} triggered find_ids callback in chat {chat_id}, query data: {query.data}")

    try:
        await query.answer()
        await query.message.edit_caption(
            caption="🔍 Please enter a character name (e.g., 'Siesta') or part of it:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="find_panel")]]),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        LOGGER.debug(f"Prompted name search for user {user_id} in chat {chat_id}")
        return NAME_SEARCH
    except Exception as e:
        LOGGER.error(f"Error in find_ids_callback for user {user_id}: {e}")
        await query.message.reply_text("Error prompting search. Please try again.")
        return ConversationHandler.END

async def search_id_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user for a character ID to search."""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    LOGGER.info(f"User {user_id} triggered search_id callback in chat {chat_id}, query data: {query.data}")

    try:
        await query.answer()
        await query.message.edit_caption(
            caption="🔍 Please enter a character ID (e.g., '01'):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="find_panel")]]),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        LOGGER.debug(f"Prompted ID search for user {user_id} in chat {chat_id}")
        return ID_SEARCH
    except Exception as e:
        LOGGER.error(f"Error in search_id_callback for user {user_id}: {e}")
        await query.message.reply_text("Error prompting search. Please try again.")
        return ConversationHandler.END

async def name_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle character name search and display results."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    name = update.message.text.strip()
    LOGGER.info(f"User {user_id} searched for character name: {name} in chat {chat_id}")

    try:
        characters = await collection.find(
            {"name": {"$regex": name, "$options": "i"}}
        ).to_list(length=None)
        LOGGER.debug(f"Found {len(characters)} characters for name '{name}'")

        if not characters:
            await update.message.reply_text(
                f"No characters found matching '{name}'. Try another name.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return ConversationHandler.END

        found = {}
        for char in characters:
            key = f"{char['name']} [{char['anime']}]"
            if key not in found:
                found[key] = []
            found[key].append(char['id'])

        response = f"**Found {len(found)} character(s) matching '{name}'**:\n\n"
        character_ids = []
        for key, ids in found.items():
            response += f"{key}: {', '.join(sorted(ids))}\n"
            character_ids.extend(ids)

        cached_searches[user_id] = sorted(character_ids)
        keyboard = [
            [InlineKeyboardButton("Go Inline", switch_inline_query_current_chat="")],
            [InlineKeyboardButton("Back", callback_data="find_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            text=response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        LOGGER.debug(f"Displayed name search results for user {user_id}")
        return ConversationHandler.END
    except Exception as e:
        LOGGER.error(f"Error in name_search for user {user_id}: {e}")
        await update.message.reply_text("Error processing search. Please try again.")
        return ConversationHandler.END

async def id_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle character ID search and list users who own it."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    char_id = update.message.text.strip()
    LOGGER.info(f"User {user_id} searched for character ID: {char_id} in chat {chat_id}")

    try:
        character = await collection.find_one({"id": char_id})
        if not character:
            await update.message.reply_text(
                f"No character found with ID '{char_id}'. Try another ID.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return ConversationHandler.END

        users = await user_collection.find(
            {"characters.id": char_id}
        ).to_list(length=None)
        LOGGER.debug(f"Found {len(users)} users with character ID '{char_id}'")

        if not users:
            await update.message.reply_text(
                f"No users own character ID '{char_id}' ({character['name']} [{character['anime']}]).",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return ConversationHandler.END

        user_counts = []
        for user in users:
            count = sum(1 for char in user['characters'] if char['id'] == char_id)
            user_counts.append({
                'user_id': user['id'],
                'first_name': user['first_name'],
                'count': count
            })

        user_counts.sort(key=lambda x: x['count'], reverse=True)
        response = (
            f"<b>Users owning {character['name']} [{character['anime']}] (ID: {char_id})</b>:\n\n"
        )
        for user in user_counts:
            response += (
                f"<a href=\"tg://user?id={user['user_id']}\">{user['first_name']}</a>: "
                f"{user['count']} {'copies' if user['count'] > 1 else 'copy'}\n"
            )

        keyboard = [[InlineKeyboardButton("Back", callback_data="find_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            text=response,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        LOGGER.debug(f"Displayed ID search results for user {user_id}")
        return ConversationHandler.END
    except Exception as e:
        LOGGER.error(f"Error in id_search for user {user_id}: {e}")
        await update.message.reply_text("Error processing search. Please try again.")
        return ConversationHandler.END

async def back_to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to the initial panel."""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    LOGGER.info(f"User {user_id} triggered back_to_start callback in chat {chat_id}, query data: {query.data}")

    try:
        await query.answer()
        caption = (
            "🔍 **Character Finder** 🔍\n\n"
            "Explore the vibrant world of characters in our bot! "
            "Whether you're searching for a favorite character by name or tracking down a specific ID, "
            "this tool helps you uncover details and ownership info."
        )
        keyboard = [[InlineKeyboardButton("Find a Character", callback_data="find_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_media(
            media=telegram.InputMediaPhoto(
                media="https://i.ibb.co/whQn3yWs/tmp6lapxvnc.jpg",
                caption=caption,
                parse_mode=ParseMode.MARKDOWN_V2
            ),
            reply_markup=reply_markup
        )
        LOGGER.debug(f"Returned to initial panel for user {user_id} in chat {chat_id}")
        return ConversationHandler.END
    except Exception as e:
        LOGGER.error(f"Error in back_to_start_callback for user {user_id}: {e}")
        await query.message.reply_text("Error returning to panel. Please try again.")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    LOGGER.info(f"User {user_id} cancelled find conversation in chat {chat_id}")
    await update.message.reply_text("Search cancelled.")
    return ConversationHandler.END

# Define ConversationHandler
find_handler = ConversationHandler(
    entry_points=[CommandHandler("find", find_command, block=False)],
    states={
        NAME_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_search)],
        ID_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, id_search)],
    },
    fallbacks=[
        CallbackQueryHandler(find_panel_callback, pattern="^find_panel$"),
        CallbackQueryHandler(find_ids_callback, pattern="^find_ids$"),
        CallbackQueryHandler(search_id_callback, pattern="^search_id$"),
        CallbackQueryHandler(back_to_start_callback, pattern="^back_to_start$"),
        CommandHandler("cancel", cancel)
    ]
)

# Register handler
application.add_handler(find_handler)

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    LOGGER.error(f"Update {update} caused error: {context.error}", exc_info=context.error)

application.add_error_handler(error_handler)
