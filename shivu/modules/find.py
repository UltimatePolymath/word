import logging
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from pyromod import listen
from shivu import shivuu, LOGGER, collection, user_collection

# Cache for inline queries
cached_searches = {}  # {user_id: [character_ids]}

@shivuu.on_message(filters.command("find") & (filters.private | filters.group))
async def find_command(client: Client, message):
    """Handle /find command to open the initial panel."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    LOGGER.info(f"User {user_id} invoked /find in chat {chat_id} at {message.date}")

    caption = (
        "🔍 **Character Finder** 🔍\n\n"
        "Explore the vibrant world of characters in our bot! "
        "Whether you're searching for a favorite character by name or tracking down a specific ID, "
        "this tool helps you uncover details and ownership info."
    )
    keyboard = [[InlineKeyboardButton("Find a Character", callback_data="find_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await message.reply_photo(
            photo="https://i.ibb.co/whQn3yWs/tmp6lapxvnc.jpg",
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        LOGGER.debug(f"Sent initial panel to user {user_id} in chat {chat_id}")
    except Exception as e:
        LOGGER.error(f"Failed to send initial panel to user {user_id}: {e}")
        await message.reply_text("Error opening panel. Please try again.")

@shivuu.on_callback_query(filters.regex(r"^find_panel$"))
async def find_panel_callback(client: Client, callback_query):
    """Handle the main panel with Find IDs and Search ID options."""
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    LOGGER.info(f"User {user_id} triggered find_panel callback in chat {chat_id}, query data: {callback_query.data}")

    try:
        await callback_query.answer()
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

        await callback_query.message.edit_caption(
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        LOGGER.debug(f"Displayed main panel for user {user_id} in chat {chat_id}")
    except Exception as e:
        LOGGER.error(f"Error in find_panel_callback for user {user_id}: {e}")
        await callback_query.message.reply_text("Error loading panel. Please try again.")

@shivuu.on_callback_query(filters.regex(r"^find_ids$"))
async def find_ids_callback(client: Client, callback_query):
    """Prompt user for a character name to search."""
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    LOGGER.info(f"User {user_id} triggered find_ids callback in chat {chat_id}, query data: {callback_query.data}")

    try:
        await callback_query.answer()
        await callback_query.message.edit_caption(
            caption="🔍 Please enter a character name (e.g., 'Siesta') or part of it:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="find_panel")]]),
            parse_mode=enums.ParseMode.MARKDOWN
        )
        LOGGER.debug(f"Prompted name search for user {user_id} in chat {chat_id}")

        # Wait for user input using pyromod.listen
        response = await client.listen(
            filters=filters.text & ~filters.command,
            user_id=user_id,
            chat_id=chat_id,
            timeout=60
        )
        name = response.text.strip()
        LOGGER.info(f"User {user_id} searched for character name: {name} in chat {chat_id}")

        # Search characters by name (case-insensitive, partial match)
        characters = await collection.find(
            {"name": {"$regex": name, "$options": "i"}}
        ).to_list(length=None)
        LOGGER.debug(f"Found {len(characters)} characters for name '{name}'")

        if not characters:
            await response.reply_text(
                f"No characters found matching '{name}'. Try another name.",
                parse_mode=enums.ParseMode.MARKDOWN
            )
            return

        found = {}
        for char in characters:
            key = f"{char['name']} [{char['anime']}]"
            if key not in found:
                found[key] = []
            found[key].append(char['id'])

        response_text = f"**Found {len(found)} character(s) matching '{name}'**:\n\n"
        character_ids = []
        for key, ids in found.items():
            response_text += f"{key}: {', '.join(sorted(ids))}\n"
            character_ids.extend(ids)

        cached_searches[user_id] = sorted(character_ids)
        keyboard = [
            [InlineKeyboardButton("Go Inline", switch_inline_query_current_chat="")],
            [InlineKeyboardButton("Back", callback_data="find_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await response.reply_text(
            text=response_text,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        LOGGER.debug(f"Displayed name search results for user {user_id}")
    except asyncio.TimeoutError:
        LOGGER.warning(f"User {user_id} timed out during name search in chat {chat_id}")
        await callback_query.message.reply_text("Search timed out. Please try again.")
    except Exception as e:
        LOGGER.error(f"Error in find_ids_callback for user {user_id}: {e}")
        await callback_query.message.reply_text("Error processing search. Please try again.")

@shivuu.on_callback_query(filters.regex(r"^search_id$"))
async def search_id_callback(client: Client, callback_query):
    """Prompt user for a character ID to search."""
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    LOGGER.info(f"User {user_id} triggered search_id callback in chat {chat_id}, query data: {callback_query.data}")

    try:
        await callback_query.answer()
        await callback_query.message.edit_caption(
            caption="🔍 Please enter a character ID (e.g., '01'):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="find_panel")]]),
            parse_mode=enums.ParseMode.MARKDOWN
        )
        LOGGER.debug(f"Prompted ID search for user {user_id} in chat {chat_id}")

        # Wait for user input using pyromod.listen
        response = await client.listen(
            filters=filters.text & ~filters.command,
            user_id=user_id,
            chat_id=chat_id,
            timeout=60
        )
        char_id = response.text.strip()
        LOGGER.info(f"User {user_id} searched for character ID: {char_id} in chat {chat_id}")

        # Validate character ID
        character = await collection.find_one({"id": char_id})
        if not character:
            await response.reply_text(
                f"No character found with ID '{char_id}'. Try another ID.",
                parse_mode=enums.ParseMode.MARKDOWN
            )
            return

        # Find users with this character ID
        users = await user_collection.find(
            {"characters.id": char_id}
        ).to_list(length=None)
        LOGGER.debug(f"Found {len(users)} users with character ID '{char_id}'")

        if not users:
            await response.reply_text(
                f"No users own character ID '{char_id}' ({character['name']} [{character['anime']}]).",
                parse_mode=enums.ParseMode.MARKDOWN
            )
            return

        user_counts = []
        for user in users:
            count = sum(1 for char in user['characters'] if char['id'] == char_id)
            user_counts.append({
                'user_id': user['id'],
                'first_name': user['first_name'],
                'count': count
            })

        user_counts.sort(key=lambda x: x['count'], reverse=True)
        response_text = (
            f"**Users owning {character['name']} [{character['anime']}] (ID: {char_id})**:\n\n"
        )
        for user in user_counts:
            response_text += (
                f"<a href=\"tg://user?id={user['user_id']}\">{user['first_name']}</a>: "
                f"{user['count']} {'copies' if user['count'] > 1 else 'copy'}\n"
            )

        keyboard = [[InlineKeyboardButton("Back", callback_data="find_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await response.reply_text(
            text=response_text,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        LOGGER.debug(f"Displayed ID search results for user {user_id}")
    except asyncio.TimeoutError:
        LOGGER.warning(f"User {user_id} timed out during ID search in chat {chat_id}")
        await callback_query.message.reply_text("Search timed out. Please try again.")
    except Exception as e:
        LOGGER.error(f"Error in search_id_callback for user {user_id}: {e}")
        await callback_query.message.reply_text("Error processing search. Please try again.")

@shivuu.on_callback_query(filters.regex(r"^back_to_start$"))
async def back_to_start_callback(client: Client, callback_query):
    """Return to the initial panel."""
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    LOGGER.info(f"User {user_id} triggered back_to_start callback in chat {chat_id}, query data: {callback_query.data}")

    try:
        await callback_query.answer()
        caption = (
            "🔍 **Character Finder** 🔍\n\n"
            "Explore the vibrant world of characters in our bot! "
            "Whether you're searching for a favorite character by name or tracking down a specific ID, "
            "this tool helps you uncover details and ownership info."
        )
        keyboard = [[InlineKeyboardButton("Find a Character", callback_data="find_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await callback_query.message.edit_media(
            media=InputMediaPhoto(
                media="https://i.ibb.co/whQn3yWs/tmp6lapxvnc.jpg",
                caption=caption,
                parse_mode=enums.ParseMode.MARKDOWN
            ),
            reply_markup=reply_markup
        )
        LOGGER.debug(f"Returned to initial panel for user {user_id} in chat {chat_id}")
    except Exception as e:
        LOGGER.error(f"Error in back_to_start_callback for user {user_id}: {e}")
        await callback_query.message.reply_text("Error returning to panel. Please try again.")

@shivuu.on_message(filters.command("debug"))
async def debug_command(client: Client, message):
    """Debug command to test logging and bot responsiveness."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    LOGGER.info(f"User {user_id} invoked /debug in chat {chat_id} at {message.date}")
    await message.reply_text("Debug: Bot is responsive. Check log.txt for details.")

@shivuu.on_raw_update()
async def raw_update(client: Client, update, users, chats):
    """Log raw updates for debugging."""
    LOGGER.debug(f"Received raw update: {update}")
