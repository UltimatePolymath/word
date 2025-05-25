import logging
import urllib.request
from pymongo import ReturnDocument
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, collection, db, CHARA_CHANNEL_ID, SUPPORT_CHAT, LOGGER, sudo

# Rarity map with updated rarities
rarity_map = {
    1: "⚪ Common",
    2: "🟢 Medium",
    3: "🟣 Rare",
    4: "🟡 High"
}

WRONG_FORMAT_TEXT = """Wrong ❌️ format...  eg. /upload Img_url muzan-kibutsuji Demon-slayer 3

img_url character-name anime-name rarity-number

use rarity number accordingly rarity Map

rarity_map = 1 (⚪ Common), 2 (🟢 Medium), 3 (🟣 Rare), 4 (🟡 High)"""

async def get_next_sequence_number(sequence_name):
    """Get the next sequence number for a given sequence name."""
    sequence_collection = db.sequences
    try:
        sequence_document = await sequence_collection.find_one_and_update(
            {'_id': sequence_name}, 
            {'$inc': {'sequence_value': 1}}, 
            return_document=ReturnDocument.AFTER
        )
        if not sequence_document:
            await sequence_collection.insert_one({'_id': sequence_name, 'sequence_value': 0})
            LOGGER.debug(f"Initialized sequence {sequence_name} with value 0")
            return 0
        LOGGER.debug(f"Sequence {sequence_name} incremented to {sequence_document['sequence_value']}")
        return sequence_document['sequence_value']
    except Exception as e:
        LOGGER.error(f"Failed to get next sequence number for {sequence_name}: {e}")
        raise

async def check_user_permission(user_id: int) -> bool:
    """Check if the user has a role in the sudo collection."""
    try:
        user = await sudo.find_one({"user_id": user_id})
        has_permission = user is not None and user.get("role") in ["superuser", "owner", "sudo", "uploader"]
        LOGGER.debug(f"Permission check for user {user_id}: {'Allowed' if has_permission else 'Denied'}")
        return has_permission
    except Exception as e:
        LOGGER.error(f"Failed to check permission for user {user_id}: {e}")
        return False

async def upload(update: Update, context: CallbackContext) -> None:
    """Upload a new character to the database and channel."""
    user_id = update.effective_user.id
    if not await check_user_permission(user_id):
        LOGGER.warning(f"User {user_id} denied access to /upload (not in sudo collection)")
        await update.message.reply_text("You don't have permission to use this command. Contact the bot owner.")
        return

    try:
        args = context.args
        if len(args) != 4:
            await update.message.reply_text(WRONG_FORMAT_TEXT)
            return

        character_name = args[1].replace('-', ' ').title()
        anime = args[2].replace('-', ' ').title()

        try:
            urllib.request.urlopen(args[0])
        except Exception:
            LOGGER.warning(f"Invalid URL provided by user {user_id}: {args[0]}")
            await update.message.reply_text('Invalid URL.')
            return

        try:
            rarity = rarity_map[int(args[3])]
        except (KeyError, ValueError):
            LOGGER.warning(f"Invalid rarity provided by user {user_id}: {args[3]}")
            await update.message.reply_text('Invalid rarity. Please use 1, 2, 3, or 4.')
            return

        id = str(await get_next_sequence_number('character_id')).zfill(2)

        character = {
            'img_url': args[0],
            'name': character_name,
            'anime': anime,
            'rarity': rarity,
            'id': id
        }

        try:
            message = await context.bot.send_photo(
                chat_id=CHARA_CHANNEL_ID,
                photo=args[0],
                caption=f'<b>Character Name:</b> {character_name}\n<b>Anime Name:</b> {anime}\n<b>Rarity:</b> {rarity}\n<b>ID:</b> {id}\nAdded by <a href="tg://user?id={user_id}">{update.effective_user.first_name}</a>',
                parse_mode='HTML'
            )
            character['message_id'] = message.message_id
            await collection.insert_one(character)
            LOGGER.info(f"User {user_id} uploaded character ID {id} to channel and database")
            await update.message.reply_text('CHARACTER ADDED....')
        except Exception as e:
            await collection.insert_one(character)
            LOGGER.warning(f"User {user_id} uploaded character ID {id} to database but failed to send to channel: {e}")
            await update.message.reply_text("Character Added but no Database Channel Found, Consider adding one.")
        
    except Exception as e:
        LOGGER.error(f"Character upload failed for user {user_id}: {e}")
        await update.message.reply_text(f'Character Upload Unsuccessful. Error: {str(e)}\nIf you think this is a source error, forward to: {SUPPORT_CHAT}')

async def delete(update: Update, context: CallbackContext) -> None:
    """Delete a character from the database and channel."""
    user_id = update.effective_user.id
    if not await check_user_permission(user_id):
        LOGGER.warning(f"User {user_id} denied access to /delete (not in sudo collection)")
        await update.message.reply_text("You don't have permission to use this command. Contact the bot owner.")
        return

    try:
        args = context.args
        if len(args) != 1:
            LOGGER.warning(f"User {user_id} provided incorrect format for /delete: {args}")
            await update.message.reply_text('Incorrect format... Please use: /delete ID')
            return

        character = await collection.find_one_and_delete({'id': args[0]})
        if character:
            try:
                await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character['message_id'])
                LOGGER.info(f"User {user_id} deleted character ID {args[0]} from channel and database")
                await update.message.reply_text('DONE')
            except Exception as e:
                LOGGER.warning(f"User {user_id} deleted character ID {args[0]} from database but failed to delete from channel: {e}")
                await update.message.reply_text('Deleted Successfully from db, but character not found In Channel')
        else:
            LOGGER.warning(f"User {user_id} attempted to delete non-existent character ID {args[0]}")
            await update.message.reply_text('Character not found.')
    except Exception as e:
        LOGGER.error(f"Character deletion failed for user {user_id}: {e}")
        await update.message.reply_text(f'Error: {str(e)}')

async def update(update: Update, context: CallbackContext) -> None:
    """Update a character's details in the database and channel."""
    user_id = update.effective_user.id
    if not await check_user_permission(user_id):
        LOGGER.warning(f"User {user_id} denied access to /update (not in sudo collection)")
        await update.message.reply_text("You don't have permission to use this command. Contact the bot owner.")
        return

    try:
        args = context.args
        if len(args) != 3:
            LOGGER.warning(f"User {user_id} provided incorrect format for /update: {args}")
            await update.message.reply_text('Incorrect format. Please use: /update id field new_value')
            return

        # Get character by ID
        character = await collection.find_one({'id': args[0]})
        if not character:
            LOGGER.warning(f"User {user_id} attempted to update non-existent character ID {args[0]}")
            await update.message.reply_text('Character not found.')
            return

        # Check if field is valid
        valid_fields = ['img_url', 'name', 'anime', 'rarity']
        if args[1] not in valid_fields:
            LOGGER.warning(f"User {user_id} provided invalid field for /update: {args[1]}")
            await update.message.reply_text(f'Invalid field. Please use one of the following: {", ".join(valid_fields)}')
            return

        # Update field
        if args[1] in ['name', 'anime']:
            new_value = args[2].replace('-', ' ').title()
        elif args[1] == 'rarity':
            try:
                new_value = rarity_map[int(args[2])]
            except (KeyError, ValueError):
                LOGGER.warning(f"User {user_id} provided invalid rarity for /update: {args[2]}")
                await update.message.reply_text('Invalid rarity. Please use 1, 2, 3, or 4.')
                return
        else:
            new_value = args[2]

        await collection.find_one_and_update({'id': args[0]}, {'$set': {args[1]: new_value}})
        updated_character = await collection.find_one({'id': args[0]})

        try:
            if args[1] == 'img_url':
                await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character['message_id'])
                message = await context.bot.send_photo(
                    chat_id=CHARA_CHANNEL_ID,
                    photo=new_value,
                    caption=f'<b>Character Name:</b> {updated_character["name"]}\n<b>Anime Name:</b> {updated_character["anime"]}\n<b>Rarity:</b> {updated_character["rarity"]}\n<b>ID:</b> {updated_character["id"]}\nUpdated by <a href="tg://user?id={user_id}">{update.effective_user.first_name}</a>',
                    parse_mode='HTML'
                )
                await collection.find_one_and_update({'id': args[0]}, {'$set': {'message_id': message.message_id}})
            else:
                await context.bot.edit_message_caption(
                    chat_id=CHARA_CHANNEL_ID,
                    message_id=character['message_id'],
                    caption=f'<b>Character Name:</b> {updated_character["name"]}\n<b>Anime Name:</b> {updated_character["anime"]}\n<b>Rarity:</b> {updated_character["rarity"]}\n<b>ID:</b> {updated_character["id"]}\nUpdated by <a href="tg://user?id={user_id}">{update.effective_user.first_name}</a>',
                    parse_mode='HTML'
                )
            LOGGER.info(f"User {user_id} updated character ID {args[0]} field {args[1]} to {new_value}")
            await update.message.reply_text('Updated Done in Database.... But sometimes it Takes Time to edit Caption in Your Channel..So wait..')
        except Exception as e:
            LOGGER.error(f"User {user_id} updated character ID {args[0]} in database but failed to update channel: {e}")
            await update.message.reply_text('Updated in database, but failed to update in channel. Ensure the bot is in the channel and the character exists.')
    except Exception as e:
        LOGGER.error(f"Character update failed for user {user_id}: {e}")
        await update.message.reply_text(f'Error: {str(e)}. Possible issues: Bot not in channel, character not found, or invalid ID.')

# Register handlers
UPLOAD_HANDLER = CommandHandler('upload', upload, block=False)
application.add_handler(UPLOAD_HANDLER)
DELETE_HANDLER = CommandHandler('delete', delete, block=False)
application.add_handler(DELETE_HANDLER)
UPDATE_HANDLER = CommandHandler('update', update, block=False)
application.add_handler(UPDATE_HANDLER)
