import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
)
from shivu import application, LOGGER, collection, user_collection

# States for ConversationHandler
NAME_SEARCH, ID_SEARCH = range(2)

# Cache for inline queries
cached_searches = {}  # {user_id: [character_ids]}

async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /find command to open the initial panel."""
    user_id = update.effective_user.id
    LOGGER.info(f"User {user_id} invoked /find")

    caption = (
        "🔍 **Character Finder** 🔍\n\n"
        "Explore the vibrant world of characters in our bot! "
        "Whether you're searching for a favorite character by name or tracking down a specific ID, "
        "this tool helps you uncover details and ownership info."
    )
    keyboard = [[InlineKeyboardButton("Find a Character", callback_data="find_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_photo(
        photo="https://i.ibb.co/whQn3yWs/tmp6lapxvnc.jpg",
        caption=caption,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def find_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the main panel with Find IDs and Search ID options."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    LOGGER.info(f"User {user_id} opened find panel")

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
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def find_ids_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user for a character name to search."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    LOGGER.info(f"User {user_id} selected Find IDs")

    await query.message.edit_caption(
        caption="🔍 Please enter a character name (e.g., 'Siesta') or part of it:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="find_panel")]])
    )
    return NAME_SEARCH

async def search_id_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user for a character ID to search."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    LOGGER.info(f"User {user_id} selected Search ID")

    await query.message.edit_caption(
        caption="🔍 Please enter a character ID (e.g., '01'):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="find_panel")]])
    )
    return ID_SEARCH

async def name_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle character name search and display results."""
    user_id = update.effective_user.id
    name = update.message.text.strip()
    LOGGER.info(f"User {user_id} searched for character name: {name}")

    # Search characters by name (case-insensitive, partial match)
    characters = await collection.find(
        {"name": {"$regex": name, "$options": "i"}}
    ).to_list(length=None)

    if not characters:
        await update.message.reply_text(
            f"No characters found matching '{name}'. Try another name."
        )
        return ConversationHandler.END

    # Group by name and anime for unique entries
    found = {}
    for char in characters:
        key = f"{char['name']} [{char['anime']}]"
        if key not in found:
            found[key] = []
        found[key].append(char['id'])

    # Format response
    response = f"**Found {len(found)} character(s) matching '{name}':**\n\n"
    character_ids = []
    for key, ids in found.items():
        response += f"{key}: {', '.join(sorted(ids))}\n"
        character_ids.extend(ids)

    # Cache IDs for inline query
    cached_searches[user_id] = sorted(character_ids)

    keyboard = [
        [InlineKeyboardButton("Go Inline", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("Back", callback_data="find_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text=response,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def id_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle character ID search and list users who own it."""
    user_id = update.effective_user.id
    char_id = update.message.text.strip()
    LOGGER.info(f"User {user_id} searched for character ID: {char_id}")

    # Validate character ID
    character = await collection.find_one({"id": char_id})
    if not character:
        await update.message.reply_text(
            f"No character found with ID '{char_id}'. Try another ID."
        )
        return ConversationHandler.END

    # Find users with this character ID
    users = await user_collection.find(
        {"characters.id": char_id}
    ).to_list(length=None)

    if not users:
        await update.message.reply_text(
            f"No users own character ID '{char_id}' ({character['name']} [{character['anime']}])."
        )
        return ConversationHandler.END

    # Count occurrences per user
    user_counts = []
    for user in users:
        count = sum(1 for char in user['characters'] if char['id'] == char_id)
        user_counts.append({
            'user_id': user['id'],
            'first_name': user['first_name'],
            'count': count
        })

    # Sort by count (descending)
    user_counts.sort(key=lambda x: x['count'], reverse=True)

    # Format response
    response = (
        f"**Users owning {character['name']} [{character['anime']}] (ID: {char_id})**:\n\n"
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
        parse_mode="HTML"
    )
    return ConversationHandler.END

async def back_to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to the initial panel."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    LOGGER.info(f"User {user_id} returned to initial panel")

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
            parse_mode="Markdown"
        ),
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    user_id = update.effective_user.id
    LOGGER.info(f"User {user_id} cancelled find conversation")
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
