import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode
from shivu import application, sudo as sudo_collection, LOGGER

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
    try:
        result = await sudo_collection.delete_one({"user_id": user_id})
        success = result.deleted_count > 0
        LOGGER.debug(f"Removed role for user {user_id}: {'Success' if success else 'Failed'}")
        return success
    except Exception as e:
        LOGGER.error(f"Failed to remove role for {user_id}: {e}", exc_info=True)
        return False

async def get_all_sudo_users() -> list[dict]:
    """Fetch all users with roles from the sudo collection."""
    try:
        users = await sudo_collection.find().to_list(length=None)
        LOGGER.debug(f"Fetched all sudo users: {len(users)} found")
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

def can_manage_user(caller_role: str | None, target_role: str | None) -> bool:
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

def get_allowed_actions(caller_role: str | None) -> list[str]:
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
async def init_superuser(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initialize the superuser role for ID 6783092268."""
    caller_id = update.effective_user.id
    if caller_id != SUPERUSER_ID:
        LOGGER.warning(f"User {caller_id} denied access to /initsuperuser")
        await update.message.reply_text("⛔ Only the superuser can use this command!")
        return

    success = await set_user_role(SUPERUSER_ID, "superuser")
    if success:
        LOGGER.info(f"Superuser role initialized for {SUPERUSER_ID}")
        await update.message.reply_text("✅ Superuser role initialized for ID 6783092268.")
    else:
        LOGGER.error(f"Failed to initialize superuser role for {SUPERUSER_ID}")
        await update.message.reply_text("❌ Failed to initialize superuser role. Check logs for details.")

async def sudo_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all users with sudo roles."""
    caller_id = update.effective_user.id
    if caller_id != SUPERUSER_ID:
        LOGGER.warning(f"User {caller_id} denied access to /sudo_list")
        await update.message.reply_text("⛔ Only the superuser can use this command!")
        return

    users = await get_all_sudo_users()
    if not users:
        await update.message.reply_text("No users with sudo roles found.")
        return
    response = "Sudo Users:\n"
    for user in users:
        response += f"User ID: {user['user_id']}, Role: {user['role']}\n"
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN_V2)

async def sudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /sudo command to open the role management panel."""
    caller_id = update.effective_user.id
    caller_role = await get_user_role(caller_id)

    # Log caller details
    LOGGER.info(f"Sudo command invoked by user {caller_id}, role: {caller_role}")

    # Check if caller has permission
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        LOGGER.warning(f"User {caller_id} denied access to /sudo (no role or not superuser)")
        await update.message.reply_text("⛔ You don't have permission to use this command!")
        return

    # Check if replied message has a valid user
    if not update.message.reply_to_message or not update.message.reply_to_message.from_user:
        LOGGER.error(f"No valid user in replied message: chat_id={update.effective_chat.id}, message_id={update.message.id}")
        await update.message.reply_text("⛔ Please reply to a message from a valid user!")
        return

    target_user = update.message.reply_to_message.from_user
    target_id = target_user.id
    target_role = await get_user_role(target_id)

    # Check if caller can manage the target user
    if not can_manage_user(caller_role, target_role):
        LOGGER.warning(f"User {caller_id} (role: {caller_role}) cannot manage user {target_id} (role: {target_role})")
        await update.message.reply_text(f"⛔ You cannot manage a user with role {target_role or 'None'}!")
        return

    # Log target user details
    LOGGER.info(f"Target user: {target_id}, role: {target_role}")

    # Create manual mention
    target_name = escape_markdown_v2(target_user.first_name)
    target_mention = f"[{target_name}](tg://user?id={target_id})"

    # Create inline panel with caller_id in callback data
    buttons = [[InlineKeyboardButton("⟪ Open the Panel ⟫", callback_data=f"sudo_panel:{target_id}:{caller_id}")]]
    await update.message.reply_photo(
        photo=PANEL_IMAGE,
        caption=f"🔧 Sudo Panel for {target_mention}\nCurrent Role: {target_role or 'None'}",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN_V2
    )

# Callback handlers
async def sudo_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the sudo panel interactions."""
    query = update.callback_query
    caller_id = query.from_user.id
    target_id, panel_owner_id = map(int, query.data.split(":")[1:3])

    # Check if the user is the panel owner
    if caller_id != panel_owner_id:
        LOGGER.warning(f"User {caller_id} attempted to open panel owned by {panel_owner_id}")
        await query.answer("⛔ This panel can only be accessed by the user who opened it!", show_alert=True)
        return

    caller_role = await get_user_role(caller_id)

    # Check permission
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        LOGGER.warning(f"User {caller_id} denied access to sudo panel (no role or not superuser)")
        await query.answer("⛔ You don't have permission to open this panel!", show_alert=True)
        return

    target_role = await get_user_role(target_id)

    # Check if caller can manage the target user
    if not can_manage_user(caller_role, target_role):
        LOGGER.warning(f"User {caller_id} (role: {caller_role}) cannot manage user {target_id} (role: {target_role})")
        await query.answer(f"⛔ You cannot manage a user with role {target_role or 'None'}!", show_alert=True)
        return

    allowed_actions = get_allowed_actions(caller_role)

    # Log panel access
    LOGGER.info(f"User {caller_id} (role: {caller_role}) opened sudo panel for {target_id}, allowed actions: {allowed_actions}")

    # Build dynamic buttons based on caller's permissions
    buttons = []
    if target_role and can_manage_role(caller_role, target_role):
        buttons.append([InlineKeyboardButton(
            f"⟪ Revoke {target_role.capitalize()} ⟫",
            callback_data=f"sudo_revoke:{target_id}:{target_role}:{caller_id}"
        )])

    for role in allowed_actions:
        if target_role != role:  # Prevent assigning the same role
            buttons.append([InlineKeyboardButton(
                f"⟪ Assign {role.capitalize()} ⟫",
                callback_data=f"sudo_assign:{target_id}:{role}:{caller_id}"
            )])

    buttons.append([InlineKeyboardButton("⟪ Close Panel ⟫", callback_data=f"sudo_close:{caller_id}")])

    await query.message.edit_caption(
        caption=f"🔧 Sudo Panel for User ID: {target_id}\nCurrent Role: {target_role or 'None'}",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    await query.answer()

async def sudo_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle assign/revoke actions."""
    query = update.callback_query
    caller_id = query.from_user.id
    action, target_id, role, panel_owner_id = query.data.split(":")
    target_id, panel_owner_id = int(target_id), int(panel_owner_id)

    # Check if the user is the panel owner
    if caller_id != panel_owner_id:
        LOGGER.warning(f"User {caller_id} attempted to perform {action} on panel owned by {panel_owner_id}")
        await query.answer("⛔ This panel can only be accessed by the user who opened it!", show_alert=True)
        return

    caller_role = await get_user_role(caller_id)

    # Check permission
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        LOGGER.warning(f"User {caller_id} denied access to sudo action (no role or not superuser)")
        await query.answer("⛔ You don't have permission to perform this action!", show_alert=True)
        return

    target_role = await get_user_role(target_id)

    # Check if caller can manage the target user
    if not can_manage_user(caller_role, target_role):
        LOGGER.warning(f"User {caller_id} (role: {caller_role}) cannot manage user {target_id} (role: {target_role})")
        await query.answer(f"⛔ You cannot manage a user with role {target_role or 'None'}!", show_alert=True)
        return

    # Verify hierarchy for the specific role being assigned/revoked
    if action == "sudo_assign" and not can_manage_role(caller_role, role):
        LOGGER.warning(f"User {caller_id} (role: {caller_role}) attempted to assign {role} to {target_id} (not allowed)")
        await query.answer(f"⛔ You can't assign the {role} role!", show_alert=True)
        return
    elif action == "sudo_revoke" and not can_manage_role(caller_role, target_role):
        LOGGER.warning(f"User {caller_id} (role: {caller_role}) attempted to revoke {target_role} from {target_id} (not allowed)")
        await query.answer(f"⛔ You can't revoke the {target_role} role!", show_alert=True)
        return

    if action == "sudo_assign":
        success = await set_user_role(target_id, role)
        if success:
            LOGGER.info(f"User {caller_id} (role: {caller_role}) assigned {role} to {target_id}")
            await query.message.edit_caption(
                caption=f"✅ Assigned {role.capitalize()} to User ID: {target_id}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⟪ Close Panel ⟫", callback_data=f"sudo_close:{caller_id}")]]),
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            LOGGER.error(f"User {caller_id} failed to assign {role} to {target_id}")
            await query.answer("❌ Failed to assign role! Check logs for details.", show_alert=True)
    elif action == "sudo_revoke":
        success = await remove_user_role(target_id)
        if success:
            LOGGER.info(f"User {caller_id} (role: {caller_role}) revoked role from {target_id}")
            await query.message.edit_caption(
                caption=f"✅ Revoked role from User ID: {target_id}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⟪ Close Panel ⟫", callback_data=f"sudo_close:{caller_id}")]]),
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            LOGGER.error(f"User {caller_id} failed to revoke role from {target_id}")
            await query.answer("❌ Failed to revoke role! Check logs for details.", show_alert=True)

    await query.answer()

async def close_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Close the sudo panel."""
    query = update.callback_query
    caller_id = query.from_user.id
    panel_owner_id = int(query.data.split(":")[1])

    # Check if the user is the panel owner
    if caller_id != panel_owner_id:
        LOGGER.warning(f"User {caller_id} attempted to close panel owned by {panel_owner_id}")
        await query.answer("⛔ This panel can only be closed by the user who opened it!", show_alert=True)
        return

    LOGGER.info(f"User {caller_id} closed sudo panel")
    await query.message.delete()
    await query.answer()

# Register handlers
application.add_handler(CommandHandler("initsuperuser", init_superuser, filters=filters.User(user_id=SUPERUSER_ID)))
application.add_handler(CommandHandler("sudo_list", sudo_list, filters=filters.User(user_id=SUPERUSER_ID)))
application.add_handler(CommandHandler("sudo", sudo_command, filters=filters.REPLY))
application.add_handler(CallbackQueryHandler(sudo_panel, pattern=r"^sudo_panel:\d+:\d+$"))
application.add_handler(CallbackQueryHandler(sudo_action, pattern=r"^sudo_(assign|revoke):\d+:.+:\d+$"))
application.add_handler(CallbackQueryHandler(close_panel, pattern=r"^sudo_close:\d+$"))

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    LOGGER.error(f"Update {update} caused error: {context.error}", exc_info=context.error)

application.add_error_handler(error_handler)
