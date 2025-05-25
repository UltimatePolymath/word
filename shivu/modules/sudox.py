import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from shivu import shivuu, sudo as sudo_collection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    """Fetch a user's role from the sudo collection."""
    try:
        user = await sudo_collection.find_one({"user_id": user_id})
        role = user.get("role") if user else None
        logger.debug(f"Fetched role for user {user_id}: {role}")
        return role
    except Exception as e:
        logger.error(f"Error fetching role for user {user_id}: {e}")
        return None

async def db_update_user_role(user_id: int, role: str) -> bool:
    """Assign or update a user's role in the sudo collection."""
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
    """Remove a user's role from the sudo collection."""
    try:
        result = await sudo_collection.delete_one({"user_id": user_id})
        success = result.deleted_count > 0
        logger.debug(f"Removed role for user {user_id}: {'Success' if success else 'Failed'}")
        return success
    except Exception as e:
        logger.error(f"Error removing role for user {user_id}: {e}")
        return False

async def db_list_sudo_users() -> list[dict]:
    """Fetch all users with roles from the sudo collection."""
    try:
        users = await sudo_collection.find().to_list(length=None)
        logger.debug(f"Fetched {len(users)} sudo users")
        return users
    except Exception as e:
        logger.error(f"Error fetching sudo users: {e}")
        return []

# Role Logic and Permissions
def perm_can_manage_role(caller_role: str | None, target_role: str) -> bool:
    """Check if caller can manage the target role based on hierarchy."""
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
    """Check if caller can manage a user with the target role."""
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
    """Return roles a caller can assign/revoke based on their role."""
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
@shivuu.on_message(filters.command("initsuperuser") & filters.user(SUPERUSER_ID))
async def handle_init_superuser(client: Client, message: Message):
    """Initialize superuser role for ID 6783092268."""
    success = await db_update_user_role(SUPERUSER_ID, "superuser")
    response = "✅ Superuser role initialized for ID 6783092268." if success else "❌ Failed to initialize superuser role."
    logger.info(f"Superuser initialization for {SUPERUSER_ID}: {'Success' if success else 'Failed'}")
    await message.reply_text(response)

@shivuu.on_message(filters.command("sudo_list") & filters.user(SUPERUSER_ID))
async def handle_list_sudo_users(client: Client, message: Message):
    """List all users with sudo roles."""
    users = await db_list_sudo_users()
    if not users:
        await message.reply_text("No users with sudo roles found.")
        return
    response = "Sudo Users:\n" + "\n".join(f"User ID: {user['user_id']}, Role: {user['role']}" for user in users)
    await message.reply_text(response)

@shivuu.on_message(filters.command("sudo") & filters.reply)
async def handle_sudo_panel(client: Client, message: Message):
    """Open role management panel for a replied-to user."""
    caller_id = message.from_user.id
    caller_role = await db_fetch_user_role(caller_id)
    logger.info(f"Sudo command by user {caller_id}, role: {caller_role}")

    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        logger.warning(f"User {caller_id} denied access to /sudo")
        await message.reply_text("⛔ You don't have permission to use this command!")
        return

    reply_message = message.reply_to_message
    if not reply_message.from_user:
        logger.error(f"No valid user in replied message: chat_id={reply_message.chat.id}, message_id={reply_message.id}")
        await message.reply_text("⛔ Please reply to a message from a valid user!")
        return

    target_user = reply_message.from_user
    target_id = target_user.id
    target_role = await db_fetch_user_role(target_id)

    if not perm_can_manage_user(caller_role, target_role):
        logger.warning(f"User {caller_id} (role: {caller_role}) cannot manage user {target_id} (role: {target_role})")
        await message.reply_text(f"⛔ You cannot manage a user with role {target_role or 'None'}!")
        return

    logger.info(f"Target user: {target_id}, role: {target_role}")
    buttons = [[InlineKeyboardButton("⟪ Open the Panel ⟫", callback_data=f"sudo_panel:{target_id}:{caller_id}")]]
    await message.reply_photo(
        photo=PANEL_IMAGE,
        caption=f"🔧 Sudo Panel for {target_user.mention}\nCurrent Role: {target_role or 'None'}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Callback Handlers
@shivuu.on_callback_query(filters.regex(r"^sudo_panel:(\d+):(\d+)$"))
async def handle_sudo_panel_callback(client: Client, callback: CallbackQuery):
    """Handle sudo panel interactions."""
    caller_id = callback.from_user.id
    target_id, panel_owner_id = map(int, callback.data.split(":")[1:3])

    if caller_id != panel_owner_id:
        logger.warning(f"User {caller_id} attempted to access panel owned by {panel_owner_id}")
        await callback.answer("⛔ This panel is only accessible by its creator!", show_alert=True)
        return

    caller_role = await db_fetch_user_role(caller_id)
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        logger.warning(f"User {caller_id} denied access to sudo panel")
        await callback.answer("⛔ You don't have permission to open this panel!", show_alert=True)
        return

    target_role = await db_fetch_user_role(target_id)
    if not perm_can_manage_user(caller_role, target_role):
        logger.warning(f"User {caller_id} (role: {caller_role}) cannot manage user {target_id} (role: {target_role})")
        await callback.answer(f"⛔ You cannot manage a user with role {target_role or 'None'}!", show_alert=True)
        return

    allowed_actions = perm_get_allowed_roles(caller_role)
    logger.info(f"User {caller_id} (role: {caller_role}) opened sudo panel for {target_id}, allowed actions: {allowed_actions}")

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
    await callback.message.edit_caption(
        caption=f"🔧 Sudo Panel for User ID: {target_id}\nCurrent Role: {target_role or 'None'}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await callback.answer()

@shivuu.on_callback_query(filters.regex(r"^sudo_(assign|revoke):(\d+):(.+):(\d+)$"))
async def handle_sudo_action_callback(client: Client, callback: CallbackQuery):
    """Handle assign/revoke role actions."""
    caller_id = callback.from_user.id
    action, target_id, role, panel_owner_id = callback.data.split(":")
    target_id, panel_owner_id = int(target_id), int(panel_owner_id)

    if caller_id != panel_owner_id:
        logger.warning(f"User {caller_id} attempted to perform {action} on panel owned by {panel_owner_id}")
        await callback.answer("⛔ This panel is only accessible by its creator!", show_alert=True)
        return

    caller_role = await db_fetch_user_role(caller_id)
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        logger.warning(f"User {caller_id} denied access to sudo action")
        await callback.answer("⛔ You don't have permission to perform this action!", show_alert=True)
        return

    target_role = await db_fetch_user_role(target_id)
    if not perm_can_manage_user(caller_role, target_role):
        logger.warning(f"User {caller_id} (role: {caller_role}) cannot manage user {target_id} (role: {target_role})")
        await callback.answer(f"⛔ You cannot manage a user with role {target_role or 'None'}!", show_alert=True)
        return

    if action == "sudo_assign" and not perm_can_manage_role(caller_role, role):
        logger.warning(f"User {caller_id} (role: {caller_role}) attempted to assign {role} to {target_id}")
        await callback.answer(f"⛔ You can't assign the {role} role!", show_alert=True)
        return
    elif action == "sudo_revoke" and not perm_can_manage_role(caller_role, target_role):
        logger.warning(f"User {caller_id} (role: {caller_role}) attempted to revoke {target_role} from {target_id}")
        await callback.answer(f"⛔ You can't revoke the {target_role} role!", show_alert=True)
        return

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
            await callback.answer("❌ Failed to assign role!", show_alert=True)
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
            await callback.answer("❌ Failed to revoke role!", show_alert=True)
    
    await callback.answer()

@shivuu.on_callback_query(filters.regex(r"^sudo_close:(\d+)$"))
async def handle_close_panel_callback(client: Client, callback: CallbackQuery):
    """Close the sudo panel."""
    caller_id = callback.from_user.id
    panel_owner_id = int(callback.data.split(":")[1])

    if caller_id != panel_owner_id:
        logger.warning(f"User {caller_id} attempted to close panel owned by {panel_owner_id}")
        await callback.answer("⛔ This panel can only be closed by its creator!", show_alert=True)
        return

    logger.info(f"User {caller_id} closed sudo panel")
    await callback.message.delete()
    await callback.answer()
