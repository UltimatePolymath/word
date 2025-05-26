import logging
import sys
import re
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, filters
from shivu import application as app, sudo as sudo_collection

# Configure logging (file-based for persistence)
logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global exception handler
def exception_handler(exc_type, exc_value, exc_traceback):
    logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = exception_handler

# Role hierarchy
ROLE_HIERARCHY = {
    "superuser": 3,
    "owner": 2,
    "sudo": 1,
    "uploader": 0
}

SUPERUSER_ID = 6783092268
PANEL_IMAGE = "https://i.ibb.co/M5ShPN50/tmpgr3gsx2o.jpg"

# Database Operations
async def db_fetch_user_role(user_id: int) -> str | None:
    try:
        user = await sudo_collection.find_one({"user_id": user_id})
        role = user.get("role") if user else None
        logger.debug(f"Fetched role for user {user_id}: {role}")
        return role
    except Exception as e:
        logger.error(f"Error fetching role for user {user_id}: {e}")
        return None

async def db_update_user_role(user_id: int, role: str) -> bool:
    try:
        result = await sudo_collection.update_one(
            {"user_id": user_id},
            {"$set": {"role": role}},
            upsert=True
        )
        success = result.modified_count > 0 or result.upserted_id is not None
        logger.debug(f"Set role {role} for user {user_id}: {'Success' if success else 'Failed'}")
        return success
    except Exception as e:
        logger.error(f"Error setting role {role} for user {user_id}: {e}")
        return False

async def db_delete_user_role(user_id: int) -> bool:
    try:
        result = await sudo_collection.delete_one({"user_id": user_id})
        success = result.deleted_count > 0
        logger.debug(f"Removed role for user {user_id}: {'Success' if success else 'Failed'}")
        return success
    except Exception as e:
        logger.error(f"Error removing role for user {user_id}: {e}")
        return False

async def db_list_sudo_users() -> list[dict]:
    try:
        users = await sudo_collection.find().to_list(length=None)
        logger.debug(f"Fetched {len(users)} sudo users")
        return users
    except Exception as e:
        logger.error(f"Error fetching sudo users: {e}")
        return []

# Role Logic and Permissions
def perm_can_manage_role(caller_role: str | None, target_role: str) -> bool:
    if caller_role is None:
        logger.debug(f"No caller role, cannot manage {target_role}")
        return False
    if caller_role == "superuser":
        logger.debug(f"Superuser can manage {target_role}")
        return True
    caller_level = ROLE_HIERARCHY.get(caller_role, -1)
    target_level = ROLE_HIERARCHY.get(target_role, -1)
    can_manage = caller_level > target_level
    logger.debug(f"Can {caller_role} (level {caller_level}) manage {target_role} (level {target_level})? {can_manage}")
    return can_manage

def perm_can_manage_user(caller_role: str | None, target_role: str | None) -> bool:
    if caller_role is None:
        logger.debug("No caller role, cannot manage any user")
        return False
    if caller_role == "superuser":
        logger.debug("Superuser can manage any user")
        return True
    caller_level = ROLE_HIERARCHY.get(caller_role, -1)
    target_level = ROLE_HIERARCHY.get(target_role, -1) if target_role else -1
    can_manage = caller_level > target_level
    logger.debug(f"Can {caller_role} (level {caller_level}) manage user with role {target_role} (level {target_level})? {can_manage}")
    return can_manage

def perm_get_allowed_roles(caller_role: str | None) -> list[str]:
    if caller_role is None:
        logger.debug("No role, no allowed actions")
        return []
    if caller_role == "superuser":
        actions = ["owner", "sudo", "uploader"]
    elif caller_role == "owner":
        actions = ["sudo", "uploader"]
    elif caller_role == "sudo":
        actions = ["uploader"]
    else:
        actions = []
    logger.debug(f"Allowed actions for {caller_role}: {actions}")
    return actions

# Command Handlers
async def handle_init_superuser(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    caller_id = update.effective_user.id
    if caller_id != SUPERUSER_ID:
        logger.warning(f"User {caller_id} denied access to /initsuperuser")
        await update.message.reply_text("⛔ You don't have permission to use this command!")
        return
    success = await db_update_user_role(SUPERUSER_ID, "superuser")
    response = "✅ Superuser role initialized for ID 6783092268." if success else "❌ Failed to initialize superuser role."
    logger.info(f"Superuser initialization for {SUPERUSER_ID}: {'Success' if success else 'Failed'}")
    await update.message.reply_text(response)

async def handle_list_sudo_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    caller_id = update.effective_user.id
    if caller_id != SUPERUSER_ID:
        logger.warning(f"User {caller_id} denied access to /sudo_list")
        await update.message.reply_text("⛔ You don't have permission to use this command!")
        return
    users = await db_list_sudo_users()
    if not users:
        await update.message.reply_text("No users with sudo roles found.")
        return
    response = "Sudo Users:\n" + "\n".join(f"User ID: {user['user_id']}, Role: {user['role']}" for user in users)
    await update.message.reply_text(response)

async def handle_sudo_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    caller_id = update.effective_user.id
    caller_role = await db_fetch_user_role(caller_id)
    logger.info(f"Sudo command by user {caller_id}, role: {caller_role}")
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        logger.warning(f"User {caller_id} denied access to /sudo")
        await update.message.reply_text("⛔ You don't have permission to use this command!")
        return
    if not update.message.reply_to_message or not update.message.reply_to_message.from_user:
        logger.error(f"No valid user in replied message: chat_id={update.message.chat.id}, message_id={update.message.id}")
        await update.message.reply_text("⛔ Please reply to a message from a valid user!")
        return
    target_user = update.message.reply_to_message.from_user
    target_id = target_user.id
    target_role = await db_fetch_user_role(target_id)
    if not perm_can_manage_user(caller_role, target_role):
        logger.warning(f"User {caller_id} (role: {caller_role}) cannot manage user {target_id} (role: {target_role})")
        await update.message.reply_text(f"⛔ You cannot manage a user with role {target_role or 'None'}!")
        return
    logger.info(f"Target user: {target_id}, role: {target_role}")
    buttons = [[InlineKeyboardButton("⟪ Open the Panel ⟫", callback_data=f"sudo_panel:{target_id}:{caller_id}")]]
    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=PANEL_IMAGE,
            caption=f"🔧 Sudo Panel for @{target_user.username or target_user.first_name}\nCurrent Role: {target_role or 'None'}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        logger.error(f"Failed to send sudo panel photo: {e}")
        await update.message.reply_text("❌ Failed to open sudo panel due to an error!")

# Callback Handlers
async def handle_sudo_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle sudo panel interactions."""
    callback = update.callback_query
    logger.info(f"Received callback: user_id={callback.from_user.id}, chat_id={callback.message.chat.id if callback.message else 'N/A'}, data={callback.data}")
    try:
        target_id, panel_owner_id = map(int, callback.data.split(":")[1:3])
    except (ValueError, IndexError) as e:
        logger.error(f"Invalid sudo_panel callback data: {callback.data}, error: {e}")
        await callback.answer(text="❌ Invalid callback data!", show_alert=True)
        return
    caller_id = callback.from_user.id
    logger.info(f"Processing sudo_panel: caller_id={caller_id}, target_id={target_id}, panel_owner_id={panel_owner_id}")
    if caller_id != panel_owner_id:
        logger.warning(f"User {caller_id} attempted to access panel owned by {panel_owner_id}")
        await callback.answer(text="⛔ This panel is only accessible by its creator!", show_alert=True)
        return
    caller_role = await db_fetch_user_role(caller_id)
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        logger.warning(f"User {caller_id} denied access to sudo panel")
        await callback.answer(text="⛔ You don't have permission to open this panel!", show_alert=True)
        return
    target_role = await db_fetch_user_role(target_id)
    if not perm_can_manage_user(caller_role, target_role):
        logger.warning(f"User {caller_id} (role: {caller_role}) cannot manage user {target_id} (role: {target_role})")
        await callback.answer(text=f"⛔ You cannot manage a user with role {target_role or 'None'}!", show_alert=True)
        return
    allowed_actions = perm_get_allowed_roles(caller_role)
    logger.info(f"Opened sudo panel for {target_id}, allowed actions: {allowed_actions}")
    buttons = []
    if target_role and perm_can_manage_role(caller_role, target_role):
        buttons.append([InlineKeyboardButton(
            f"⟪ Revoke {target_role.capitalize()} ⟫",
            callback_data=f"sudo_revoke:{target_id}:{target_role}:{caller_id}"
        )])
    for role in allowed_actions:
        if target_role != role:
            buttons.append([InlineKeyboardButton(
                f"⟪ Assign {role.capitalize()} ⟫",
                callback_data=f"sudo_assign:{target_id}:{role}:{caller_id}"
            )])
    buttons.append([InlineKeyboardButton("⟪ Close Panel ⟫", callback_data=f"sudo_close:{caller_id}")])
    try:
        await callback.message.edit_caption(
            caption=f"🔧 Sudo Panel for User ID: {target_id}\nCurrent Role: {target_role or 'None'}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Failed to edit sudo panel caption: {e}")
        await callback.answer(text="❌ Failed to update panel!", show_alert=True)

async def handle_sudo_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle assign/revoke role actions."""
    callback = update.callback_query
    logger.info(f"Received callback: user_id={callback.from_user.id}, chat_id={callback.message.chat.id if callback.message else 'N/A'}, data={callback.data}")
    try:
        action, target_id, role, panel_owner_id = callback.data.split(":")
        target_id, panel_owner_id = int(target_id), int(panel_owner_id)
    except (ValueError, IndexError) as e:
        logger.error(f"Invalid sudo_action callback data: {callback.data}, error: {e}")
        await callback.answer(text="❌ Invalid callback data!", show_alert=True)
        return
    caller_id = callback.from_user.id
    logger.info(f"Processing sudo_action: action={action}, target_id={target_id}, role={role}, panel_owner_id={panel_owner_id}")
    if caller_id != panel_owner_id:
        logger.warning(f"User {caller_id} attempted to perform {action} on panel owned by {panel_owner_id}")
        await callback.answer(text="⛔ This panel is only accessible by its creator!", show_alert=True)
        return
    caller_role = await db_fetch_user_role(caller_id)
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        logger.warning(f"User {caller_id} denied access to sudo action")
        await callback.answer(text="⛔ You don't have permission to perform this action!", show_alert=True)
        return
    target_role = await db_fetch_user_role(target_id)
    if not perm_can_manage_user(caller_role, target_role):
        logger.warning(f"User {caller_id} (role: {caller_role}) cannot manage user {target_id} (role: {target_role})")
        await callback.answer(text=f"⛔ You cannot manage a user with role {target_role or 'None'}!", show_alert=True)
        return
    if action == "sudo_assign" and not perm_can_manage_role(caller_role, role):
        logger.warning(f"User {caller_id} (role: {caller_role}) attempted to assign {role} to {target_id}")
        await callback.answer(text=f"⛔ You can't assign the {role} role!", show_alert=True)
        return
    elif action == "sudo_revoke" and not perm_can_manage_role(caller_role, target_role):
        logger.warning(f"User {caller_id} (role: {caller_role}) attempted to revoke {target_role} from {target_id}")
        await callback.answer(text=f"⛔ You can't revoke the {target_role} role!", show_alert=True)
        return
    try:
        if action == "sudo_assign":
            success = await db_update_user_role(target_id, role)
            if success:
                logger.info(f"User {caller_id} (role: {caller_role}) assigned {role} to {target_id}")
                await callback.message.edit_caption(
                    caption=f"✅ Assigned {role.capitalize()} to User ID: {target_id}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⟪ Close Panel ⟫", callback_data=f"sudo_close:{caller_id}")]])
                )
            else:
                logger.error(f"User {caller_id} failed to assign {role} to {target_id}")
                await callback.answer(text="❌ Failed to assign role!", show_alert=True)
        elif action == "sudo_revoke":
            success = await db_delete_user_role(target_id)
            if success:
                logger.info(f"User {caller_id} (role: {caller_role}) revoked role from {target_id}")
                await callback.message.edit_caption(
                    caption=f"✅ Revoked role from User ID: {target_id}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⟪ Close Panel ⟫", callback_data=f"sudo_close:{caller_id}")]])
                )
            else:
                logger.error(f"User {caller_id} failed to revoke role from {target_id}")
                await callback.answer(text="❌ Failed to revoke role!", show_alert=True)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error processing sudo_action: {e}")
        await callback.answer(text="❌ An error occurred while processing the action!", show_alert=True)

async def handle_close_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Close the sudo panel."""
    callback = update.callback_query
    logger.info(f"Received callback: user_id={callback.from_user.id}, chat_id={callback.message.chat.id if callback.message else 'N/A'}, data={callback.data}")
    try:
        panel_owner_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError) as e:
        logger.error(f"Invalid sudo_close callback data: {callback.data}, error: {e}")
        await callback.answer(text="❌ Invalid callback data!", show_alert=True)
        return
    caller_id = callback.from_user.id
    logger.info(f"Processing sudo_close: caller_id={caller_id}, panel_owner_id={panel_owner_id}")
    if caller_id != panel_owner_id:
        logger.warning(f"User {caller_id} attempted to close panel owned by {panel_owner_id}")
        await callback.answer(text="⛔ This panel can only be closed by its creator!", show_alert=True)
        return
    try:
        await callback.message.delete()
        logger.info(f"User {caller_id} closed sudo panel")
        await callback.answer()
    except Exception as e:
        logger.error(f"Failed to close sudo panel: {e}")
        await callback.answer(text="❌ Failed to close panel!", show_alert=True)

# Catch-All Callback Handler
async def handle_unhandled_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any unhandled callback queries."""
    callback = update.callback_query
    logger.warning(f"Unhandled callback query: user_id={callback.from_user.id}, chat_id={callback.message.chat.id if callback.message else 'N/A'}, data={callback.data}")
    await callback.answer(text="❌ This action is not supported or the callback data is invalid!", show_alert=True)

# Register Handlers
app.add_handler(CommandHandler("initsuperuser", handle_init_superuser, filters=filters.User(user_id=SUPERUSER_ID)))
app.add_handler(CommandHandler("sudo_list", handle_list_sudo_users, filters=filters.User(user_id=SUPERUSER_ID)))
app.add_handler(CommandHandler("sudo", handle_sudo_panel))
app.add_handler(CallbackQueryHandler(handle_sudo_panel_callback, pattern=r"^sudo_panel:(\d+):(\d+)$"))
app.add_handler(CallbackQueryHandler(handle_sudo_action_callback, pattern=r"^sudo_(assign|revoke):(\d+):(.+):(\d+)$"))
app.add_handler(CallbackQueryHandler(handle_close_panel_callback, pattern=r"^sudo_close:(\d+)$"))
app.add_handler(CallbackQueryHandler(handle_unhandled_callback))  # Catch-all last
