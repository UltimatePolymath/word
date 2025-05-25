import logging
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler
from shivu import application, top_global_groups_collection, pm_users, LOGGER
from shivu.archive.sudo import check_user_permission

async def broadcast(update: Update, context: CallbackContext) -> None:
    """Broadcast a replied message to all chats and users, restricted to owner and superuser."""
    user_id = update.effective_user.id
    
    # Check if user has owner or superuser role
    user_role = await check_user_permission(user_id)
    if not user_role or user_role not in ["owner", "superuser"]:
        LOGGER.warning(f"User {user_id} denied access to /broadcast (role: {user_role or 'None'})")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    message_to_broadcast = update.message.reply_to_message
    if message_to_broadcast is None:
        LOGGER.warning(f"User {user_id} attempted /broadcast without replying to a message")
        await update.message.reply_text("Please reply to a message to broadcast.")
        return

    all_chats = await top_global_groups_collection.distinct("group_id")
    all_users = await pm_users.distinct("_id")
    shuyaa = list(set(all_chats + all_users))

    failed_sends = 0
    LOGGER.info(f"User {user_id} (role: {user_role}) initiated broadcast to {len(shuyaa)} chats/users")

    for chat_id in shuyaa:
        try:
            await context.bot.forward_message(
                chat_id=chat_id,
                from_chat_id=message_to_broadcast.chat_id,
                message_id=message_to_broadcast.message_id
            )
        except Exception as e:
            LOGGER.error(f"Failed to send broadcast to {chat_id}: {e}")
            failed_sends += 1

    LOGGER.info(f"Broadcast by user {user_id} completed. Failed sends: {failed_sends}")
    await update.message.reply_text(f"Broadcast complete. Failed to send to {failed_sends} chats/users.")

# Register handler
application.add_handler(CommandHandler("broadcast", broadcast, block=False))
