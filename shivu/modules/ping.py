import time
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, LOGGER
from shivu.archive.sudo import check_user_permission

async def ping(update: Update, context: CallbackContext) -> None:
    """Handle the /ping command, restricted to users with any role in sudo collection."""
    user_id = update.effective_user.id
    
    # Check if user has any role
    user_role = await check_user_permission(user_id)
    if not user_role:
        LOGGER.warning(f"User {user_id} denied access to /ping (no role)")
        await update.message.reply_text("Nouu.. its a command for users with roles..")
        return
    
    start_time = time.time()
    message = await update.message.reply_text('Pong!')
    end_time = time.time()
    elapsed_time = round((end_time - start_time) * 1000, 3)
    
    LOGGER.info(f"User {user_id} (role: {user_role}) executed /ping, response time: {elapsed_time}ms")
    await message.edit_text(f'Pong! {elapsed_time}ms')

# Register handler
application.add_handler(CommandHandler("ping", ping, block=False))
