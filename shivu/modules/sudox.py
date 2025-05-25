import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode
from shivu import application, sudo as sudo_collection, LOGGER

# Configure logging explicitly
logging.basicConfig(
    filename='log.txt',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logging.getLogger('telegram').setLevel(logging.DEBUG)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)

# Role hierarchy
ROLE_HIERARCHY = {
    "superuser": 3,
    "owner": 2,
    "sudo": 1,
    "uploader": 0
}

SUPERUSER_ID = 6783092268  # Hardcoded superuser ID
PANEL_IMAGE = "https://i.ibb.co/M5ShPN50/tmpgr3gsx2o.jpg"

# Utility to escape Markdown V2 special characters
def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Markdown V2."""
    special_chars = r'([_\*\[\]\(\)\~`>\#\+\-\=\|\{\}\.\!])'
    return re.sub(special_chars, r'\\\1', text)

# Database operations
async def get_user_role(user_id: int) -> str | None:
    """Fetch a user's role from the sudo collection."""
    LOGGER.debug(f"Attempting to fetch role for user {user_id}")
    try:
        user = await sudo_collection.find_one({"user_id": user_id})
        role = user.get("role") if user else None
        LOGGER.debug(f"Fetched role for user {user_id}: {role}")
        return role
    except Exception as e:
        LOGGER.error(f"Failed to get user role for {user_id}: {e}", exc_info=True)
        return None

async def set_user_role(user_id: int, role: str) -> bool:
    """Assign or update a user's role in the sudo collection."""
    LOGGER.debug(f"Attempting to set role {role} for user {user_id}")
    try:
        result = await sudo_collection.update_one(
            {"user_id": user_id},
            {"$set": {"role": role}},
            upsert=True
        )
        success = result.modified_count > 0 or result.upserted_id is not None
        LOGGER.debug(f"Set role {role} for user {user_id}: {'Success' if success else 'Failed'}")
        return success
    except Exception as e:
        LOGGER.error(f"Failed to set role {role} for {user_id}: {e}", exc_info=True)
        return False

async def remove_user_role(user_id: int) -> bool:
    """Remove a user's role from the sudo collection."""
    LOGGER.debug(f"Attempting to remove role for user {user_id}")
    try:
        result = await sudo_collection.delete_one({"user_id": user_id})
        success = result.deleted_count > 0
        LOGGER.debug(f"Removed role for user {user_id}: {'Success' if success else 'Failed'}")
        return success
    except Exception as e:
        LOGGER.error(f"Error removing role for {user_id}: {e}", exc_info=True)
        return False

async def get_all_sudo_users() -> list[dict]:
    """Return all users with roles from the sudo collection."""
    LOGGER.debug("Attempting to fetch all sudo users")
    try:
        users = await sudo_collection.find().to_list(length=None)
        LOGGER.debug(f"Fetched {len(users)} sudo users")
        return users
    except Exception as e:
        LOGGER.error(f"Failed to fetch all sudo users: {e}", exc_info=True)
        return []

# Role logic and permissions
def can_manage_role(caller_role: str | None, target_role: str) -> bool:
    """Check if the caller can manage the target role based on hierarchy."""
    if caller_role is None:
        LOGGER.debug(f"Caller has no role, cannot manage {target_role}")
        return False
    if caller_role == "superuser":
        LOGGER.debug(f"Superuser can manage {target_role}")
        return True
    caller_level = ROLE_HIERARCHY.get(caller_role, -1)
    target_level = ROLE_HIERARCHY.get(target_role, -1)
    can_manage = caller_level > target_level
    LOGGER.debug(f"Can {caller_role} (level {caller_level}) manage {target_role} (level {target_level})? {can_manage}")
    return can_manage

async def can_manage_user(caller_role: str, target_role: int | None) -> bool:
    """Check if the caller can manage a user with the target role."""
    if caller_role is None:
        LOGGER.debug("Caller has no role, cannot manage any user")
        return False
    if caller_role == "superuser":
        LOGGER.debug("Superuser can manage any user")
        return True
    caller_level = ROLE_HIERARCHY.get(caller_role, -1)
    target_level = ROLE_HIERARCHY.get(target_role, -1) if target_role else -1
    can_manage = caller_level > target_level
    LOGGER.debug(f"Can {caller_role} (level {caller_level}) manage user with role {target_role} (level {target_level})? {can_manage}")
    return can_manage

def get_allowed_roles(caller_role: str | None) -> list[str]:
    """Return the roles a caller can assign/revoke based on their role."""
    if caller_role is None:
        LOGGER.debug("No role, no allowed actions")
        return []
    if caller_role == "superuser":
        actions = ["owner", "sudo", "uploader"]
    elif caller_role == "owner":
        actions = ["sudo", "uploader"]
    elif caller_role == "sudo":
        actions = ["uploader"]
    else:
        actions = []
    LOGGER.debug(f"Allowed actions for {caller_role}: {actions}")
    return actions

# Command handlers
async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Debug command to test bot responsiveness."""
    caller_id = update.effective_user.id
    chat_id = update.effective_chat.id
    LOGGER.info(f"User {caller_id} invoked /debug in chat {chat_id}")
    await update.message.reply_text("✅ Debug: Bot is responsive! Check log.txt for details.")

async def init_superuser(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initialize the superuser role for ID 6783092268."""
    caller_id = update.effective_user.id
    LOGGER.debug(f"User {caller_id} invoked /initsuperuser")
    if caller_id != SUPERUSER_ID:
        LOGGER.warning(f"User {caller_id} denied access to /initsuperuser")
        await update.message.reply_text("❌ Only the superuser can use this command!")
        return

    success = await set_user_role(SUPERUSER_ID, "superuser")
    if success:
        LOGGER.info(f"Superuser role initialized for {SUPERUSER_ID}")
        await update.message.reply_text("✅ Superuser role initialized for ID 6783092268.")
    else:
        LOGGER.error(f"Failed to initialize superuser role for {SUPERUSER_ID}")
        await update.message.reply_text("❌ Failed to initialize superuser role. Check log.txt for details.")

async def sudo_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all users with sudo roles."""
    caller_id = update.effective_user.id
    LOGGER.debug(f"User {caller_id} invoked /sudo_list")
    if caller_id != SUPERUSER_ID:
        LOGGER.warning(f"User {caller_id} denied access to /sudo_list")
        await update.message.reply_text("❌ Only the superuser can use this command!")
        return

    users = await get_all_sudo_users()
    if not users:
        await update.message.reply_text("No users with roles found.")
        return
    text = "Sudo Roles:\n"
    for user in users:
        text += f"User ID: {user['user_id']}, Role: {user['role']}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

async def sudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /sudo command to open the role management panel."""
    caller_id = update.effective_user.id
    LOGGER.debug(f"User {caller_id} invoked /sudo")
    
    # Check if replied message exists and has a user
    if not update.message.reply_to_message or not update.message.reply_to_message.from_user:
        LOGGER.error(f"No valid user in replied message: chat_id={update.effective_chat.id}, message_id={update.message.id}")
        await update.message.reply_text("❌ Please reply to a user’s message!")
        return

    caller_role = await get_user_role(caller_id)
    LOGGER.info(f"Sudo command invoked by user {caller_id}, role: {caller_role}")

    # Check if caller has permission
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        LOGGER.warning(f"User {caller_id} access denied to /sudo (no role or not superuser)")
        await update.message.reply_text("❌ You don't have permission to use this command!")
        return

    target_user = update.message.reply_to_message.from_user
    target_id = target_user.id
    target_role = await get_user_role(target_id)

    # Check if caller can manage the target user
    if not await can_manage_user(caller_role, target_role):
        LOGGER.warning(f"User {caller_id} (role: {caller_role}) cannot manage {target_id} (role: {target_role})")
        await update.message.reply_text(f"❌ You cannot manage a user with role {target_role or 'None'}!")
        return

    # Log target user details
    LOGGER.info(f"Target user: {target_id}, role: {target_role}")

    # Create manual mention
    target_name = escape_markdown_v2(target_user.first_name or "Unknown")
    target_mention = f"[{target_name}](tg://user?id={target_id})"

    # Create inline panel
    try:
        buttons = [[InlineKeyboardButton("⟪ Open the Panel ⟰", callback_data=f"sudo_panel {target_id} {caller_id}")]]
        await update.message.reply_photo(
            photo=PANEL_IMAGE,
            caption=f"🔲 Sudo panel for {target_mention}\nCurrent role: {target_role or 'None'}",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        LOGGER.debug(f"Sent sudo panel for user {target_id} by {caller_id}")
    except Exception as e:
        LOGGER.error(f"Failed to send sudo panel for {target_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ Failed to open panel. Check logs for details.")

# Callback handlers
async def sudo_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle sudo panel interactions."""
    query = update.callback_query
    if not query:
        return
    caller_id = query.from_user.id
    LOGGER.debug(f"Callback query received: {query.data}")

    try:
        _, target_id, panel_owner_id = query.data.split()
        target_id, panel_owner_id = int(target_id), int(panel_owner_id)
    except ValueError:
        LOGGER.error(f"Invalid callback data: {query.data}")
        await query.answer("❌ Invalid panel data!", show_alert=True)
        return

    # Check if the caller is the panel owner
    if caller_id != panel_owner_id:
        LOGGER.warning(f"User {caller_id} tried to access panel owned by {panel_owner_id}")
        await query.answer("This panel can only be accessed by the user who opened it!", show_alert=True)
        return

    caller_role = await get_user_role(caller_id)
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        LOGGER.warning(f"User {caller_id} access denied to panel (no role)")
        await query.answer("❌ You don't have permission to open this panel!", show_alert=True)
        return

    target_role = await get_user_role(target_id)
    if not await can_manage_user(caller_role, target_role):
        LOGGER.warning(f"User {caller_id} (role: {caller_role}) cannot manage {target_id} (role: {target_role})")
        await query.answer(f"❌ You can't manage a user with role {target_role or 'None'}!", show_alert=True)
        return

    allowed_roles = get_allowed_roles(caller_role)
    LOGGER.info(f"User {caller_id} (role: {caller_role}) opened sudo panel for {target_id}, allowed roles: {allowed_roles}")

    # Build dynamic buttons
    buttons = []
    if target_role and can_manage_role(caller_role, target_role):
        buttons.append([InlineKeyboardButton(f"⟟ Revoke {target_role.capitalize()}",
callback_data=f"sudo_revoke {target_role} {target_id} {caller_id}")])
    for role in allowed_roles:
        if target_role != role:
            buttons.append([InlineKeyboardButton(f"⟟ Assign {role.capitalize()}",
callback_data=f"sudo_assign {role} {target_id} {caller_id}")])
    buttons.append([InlineKeyboardButton("⟟ Close panel", callback_data=f"close_panel {caller_id}")])

    try:
        await query.message.edit_caption(
            caption=f"🔲 Sudo panel for {target_id}",
            User ID: {target_id}\nCurrent role: {target_role or 'None'}",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        LOGGER.debug(f"Displayed sudo panel for {target_id} by {caller_id}")
        await query.answer()
    except Exception as e:
        LOGGER.error(f"Error updating sudo panel for {target_id}: {e}", exc_info=True)
        await query.answer("❌ Failed to update panel. Check logs!", show_alert=True)

async def sudo_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle role assign/revoke actions."""
    query = update.callback_query
    if not query:
        return
    caller_id = query.from_user.id
    LOGGER.debug(f"Callback action: {query.data}")

    try:
        action, role, target_id, panel_owner_id = query.data.split()
        target_id, panel_owner_id = int(target_id), int(panel_owner_id)
    except ValueError:
        LOGGER.error(f"Invalid action data: {query.data}")
        await query.answer("❌ Invalid action data!", show_alert=True)
        return

    # Check if caller is the panel owner
    if caller_id != panel_owner_id:
        LOGGER.warning(f"User {caller_id} attempted action {action} on panel owned by {panel_owner_id}")
        await query.answer("This panel can only be accessed by the user who opened it!", show_alert=True)
        return

    caller_role = await get_user_role(caller_id)
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        LOGGER.warning(f"User {caller_id} access denied to action {action} (no role)")
        await query.answer("❌ You don't have permission to perform this action!", show_alert=True)
        return

    target_role = await get_user_role(target_id)
    if not await can_manage_user(caller_role, target_role):
        LOGGER.warning(f"User {caller_id} (role: {caller_role}) cannot manage {target_id} (role: {target_role})")
        await query.answer(f"❌ You can't manage a user with role {target_role or 'None'}!", show_alert=True)
        return

    if action == "sudo_assign":
        if not can_manage_role(caller_role, role):
            LOGGER.warning(f"User {caller_id} (role: {caller_role}) cannot assign {role} to {target_id}")
            await query.answer(f"❌ You can't assign the {role} role!", show_alert=True)
            return
        success = await set_user_role(target_id, role)
        if success:
            LOGGER.info(f"User {caller_id} (role: {caller_role}) assigned {role} to {target_id}")
            await query.message.edit_caption(
                caption=f"✅ Assigned {role.capitalize()} to User ID: {target_id}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⟟ Close panel"", callback_data=f"close_panel {caller_id}")]]),
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            LOGGER.error(f"User {caller_id} failed to assign {role} to {target_id}")
            await query.answer("❌ Failed to assign role! Check logs for details.", show_alert=True)
    elif action == "sudo_revoke":
        if not callable(can_manage_role(caller_role, target_role)):
            LOGGER.warning(f"User {caller_id} (role: {caller_role}) cannot revoke {target_role} from {target_id}")
            await query.answer(f"❌ You can't revoke the {target_role} role!", show_alert=True)
            return
        success = await remove_user_role(target_id)
        if success:
            LOGGER.info(f"User {caller_id} (role: {caller_role}) revoked role from {target_id}")
            await query.message.edit_caption(
                caption=f"✅ Revoked role from User ID: {target_id}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⟟ Close panel"", callback_data=f"close_panel {caller_id}")]]),
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            LOGGER.error(f"User {caller_id} failed to revoke role from {target_id}")
            await query.answer("❌ Failed to revoke role! Check logs for details.", show_alert=True)

    await query.answer()

async def close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Close the sudo panel."""
    query = update.callback_query
    if not query:
        return
    caller_id = query.from_user.id
    try:
        _, panel_owner_id = query.data.split(" ")[1]
        panel_owner_id = int(panel_owner_id)
    except ValueError:
        LOGGER.error(f"Invalid close data: {query.data}")
        await query.answer()
        return

    if caller_id != panel_owner_id:
        LOGGER.warning(f"User {caller_id} tried to close panel owned by {panel_owner_id}")
        await query.answer("❌ This panel can only be closed by the user who opened it!", show_alert=True)
        return

    try:
        LOGGER.info(f"User {caller_id} closed sudo panel")
        await query.message.delete()
        await query.answer()
    except Exception as e:
        LOGGER.error(f"Error closing panel for {caller_id}: {e}", exc_info=True)
        await query.answer("❌ Failed to close panel!", show_alert=True)

# Register handlers
def register_handlers():
    """Register all command and callback handlers."""
    handlers = [
        CommandHandler("debug", debug_command),
        CommandHandler("initsuperuser", init_superuser, filters=filters.User(user_id=SUPERUSER_ID)),
        CommandHandler("sudo_list", sudo_list, filters=filters.User(user_id=SUPERUSER_ID))),
        CommandHandler("sudo"", sudo_callback, filters=filters.REPLY),
        CallbackQueryHandler(sudo_panel_callback, pattern=r"^sudo_panel\s\d+\s+\d+$"),
        CallbackQueryHandler(sudo_action_callback, pattern=r"^sudo_(assign|revoke)_.*\s+\d+\s+\d+$"),
        CallbackQueryHandler(close_callback, pattern=r"^close_panel\s+\d+$")
    ]

    for handler in handlers:
        application.add_handler(handler)
        LOGGER.info(f"Registered handler: {handler.command.__name__ if isinstance(handler, CommandHandler) else handler.callback.__name__}")

    application.add_error_handler(error_handler)

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    LOGGER.error(f"Update {update} caused error: {context.error}", exc_info=True)

# Register handlers
register_handlers()
