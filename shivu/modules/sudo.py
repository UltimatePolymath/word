import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from shivu import shivuu, sudo as sudo_collection, LOGGER

# Role hierarchy
ROLE_HIERARCHY = {
    "superuser": 3,
    "owner": 2,
    "sudo": 1,
    "uploader": 0
}

SUPERUSER_ID = 6783092268  # Hardcoded superuser ID
PANEL_IMAGE = "https://i.ibb.co/M5ShPN50/tmpgr3gsx2o.jpg"

# Database operations
async def get_user_role(user_id: int) -> str | None:
    """Fetch a user's role from the sudo collection."""
    try:
        user = await sudo_collection.find_one({"user_id": user_id})
        return user.get("role") if user else None
    except Exception as e:
        LOGGER.error(f"Failed to get user role for {user_id}: {e}")
        return None

async def set_user_role(user_id: int, role: str) -> bool:
    """Assign or update a user's role in the sudo collection."""
    try:
        result = await sudo_collection.update_one(
            {"user_id": user_id},
            {"$set": {"role": role}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception as e:
        LOGGER.error(f"Failed to set role {role} for {user_id}: {e}")
        return False

async def remove_user_role(user_id: int) -> bool:
    """Remove a user's role from the sudo collection."""
    try:
        result = await sudo_collection.delete_one({"user_id": user_id})
        return result.deleted_count > 0
    except Exception as e:
        LOGGER.error(f"Failed to remove role for {user_id}: {e}")
        return False

async def get_all_sudo_users() -> list[dict]:
    """Fetch all users with roles from the sudo collection."""
    try:
        return await sudo_collection.find().to_list(length=None)
    except Exception as e:
        LOGGER.error(f"Failed to fetch all sudo users: {e}")
        return []

# Role logic and permissions
def can_manage_role(caller_role: str | None, target_role: str) -> bool:
    """Check if the caller can manage the target role based on hierarchy."""
    if caller_role is None:
        return False
    if caller_role == "superuser":
        return True
    caller_level = ROLE_HIERARCHY.get(caller_role, -1)
    target_level = ROLE_HIERARCHY.get(target_role, -1)
    return caller_level > target_level

def get_allowed_actions(caller_role: str | None) -> list[str]:
    """Return the roles a caller can assign/revoke based on their role."""
    if caller_role is None:
        return []
    if caller_role == "superuser":
        return ["owner", "sudo", "uploader"]
    if caller_role == "owner":
        return ["sudo", "uploader"]
    if caller_role == "sudo":
        return ["uploader"]
    return []

# Command handlers
@shivuu.on_message(filters.command("initsuperuser") & filters.user(SUPERUSER_ID))
async def init_superuser(client: Client, message: Message):
    """Initialize the superuser role for ID 6783092268."""
    success = await set_user_role(SUPERUSER_ID, "superuser")
    if success:
        LOGGER.info(f"Superuser role initialized for {SUPERUSER_ID}")
        await message.reply_text("✅ Superuser role initialized for ID 6783092268.")
    else:
        LOGGER.error(f"Failed to initialize superuser role for {SUPERUSER_ID}")
        await message.reply_text("❌ Failed to initialize superuser role.")

@shivuu.on_message(filters.command("sudo") & filters.reply)
async def sudo_command(client: Client, message: Message):
    """Handle the /sudo command to open the role management panel."""
    caller_id = message.from_user.id
    caller_role = await get_user_role(caller_id)
    
    # Log caller details
    LOGGER.info(f"Sudo command invoked by user {caller_id}, role: {caller_role}")
    
    # Check if caller has permission
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        LOGGER.warning(f"User {caller_id} denied access to /sudo (no role or not superuser)")
        await message.reply_text("⛔ You don't have permission to use this command!")
        return
    
    # Check if replied message has a valid user
    reply_message = message.reply_to_message
    if not reply_message.from_user:
        LOGGER.error(f"No valid user in replied message: chat_id={reply_message.chat.id}, message_id={reply_message.id}, from_user={reply_message.from_user}")
        await message.reply_text("⛔ Please reply to a message from a valid user!")
        return
    
    target_user = reply_message.from_user
    target_id = target_user.id
    target_role = await get_user_role(target_id)
    
    # Log target user details
    LOGGER.info(f"Target user: {target_id}, role: {target_role}")
    
    # Create inline panel
    buttons = [[InlineKeyboardButton("⟪ Open the Panel ⟫", callback_data=f"sudo_panel:{target_id}")]]
    await message.reply_photo(
        photo=PANEL_IMAGE,
        caption=f"🔧 Sudo Panel for {target_user.mention}\nCurrent Role: {target_role or 'None'}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Callback handlers
@shivuu.on_callback_query(filters.regex(r"^sudo_panel:(\d+)$"))
async def sudo_panel(client: Client, callback: CallbackQuery):
    """Handle the sudo panel interactions."""
    caller_id = callback.from_user.id
    caller_role = await get_user_role(caller_id)
    
    # Check permission
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        LOGGER.warning(f"User {caller_id} denied access to sudo panel")
        await callback.answer("⛔ You don't have permission!", show_alert=True)
        return
    
    target_id = int(callback.data.split(":")[1])
    target_role = await get_user_role(target_id)
    allowed_actions = get_allowed_actions(caller_role)
    
    # Log panel access
    LOGGER.info(f"User {caller_id} opened sudo panel for {target_id}, allowed actions: {allowed_actions}")
    
    # Build dynamic buttons based on caller's permissions
    buttons = []
    if target_role:
        if can_manage_role(caller_role, target_role):
            buttons.append([InlineKeyboardButton(
                f"⟪ Revoke {target_role.capitalize()} ⟫",
                callback_data=f"sudo_revoke:{target_id}:{target_role}"
            )])
    
    for role in allowed_actions:
        if target_role != role:  # Prevent assigning the same role
            buttons.append([InlineKeyboardButton(
                f"⟪ Assign {role.capitalize()} ⟫",
                callback_data=f"sudo_assign:{target_id}:{role}"
            )])
    
    buttons.append([InlineKeyboardButton("⟪ Close Panel ⟫", callback_data="sudo_close")])
    
    await callback.message.edit_caption(
        caption=f"🔧 Sudo Panel for User ID: {target_id}\nCurrent Role: {target_role or 'None'}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await callback.answer()

@shivuu.on_callback_query(filters.regex(r"^sudo_(assign|revoke):(\d+):(.+)$"))
async def sudo_action(client: Client, callback: CallbackQuery):
    """Handle assign/revoke actions."""
    caller_id = callback.from_user.id
    caller_role = await get_user_role(caller_id)
    
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        LOGGER.warning(f"User {caller_id} denied access to sudo action")
        await callback.answer("⛔ You don't have permission!", show_alert=True)
        return
    
    action, target_id, role = callback.data.split(":")
    target_id = int(target_id)
    
    if not can_manage_role(caller_role, role):
        LOGGER.warning(f"User {caller_id} attempted to manage {role} for {target_id} (not allowed)")
        await callback.answer(f"⛔ You can't manage the {role} role!", show_alert=True)
        return
    
    if action == "sudo_assign":
        success = await set_user_role(target_id, role)
        if success:
            LOGGER.info(f"User {caller_id} assigned {role} to {target_id}")
            await callback.message.edit_caption(
                caption=f"✅ Assigned {role.capitalize()} to User ID: {target_id}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⟪ Close Panel ⟫", callback_data="sudo_close")]])
            )
        else:
            LOGGER.error(f"Failed to assign {role} to {target_id}")
            await callback.answer("❌ Failed to assign role!", show_alert=True)
    elif action == "sudo_revoke":
        success = await remove_user_role(target_id)
        if success:
            LOGGER.info(f"User {caller_id} revoked role from {target_id}")
            await callback.message.edit_caption(
                caption=f"✅ Revoked role from User ID: {target_id}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⟪ Close Panel ⟫", callback_data="sudo_close")]])
            )
        else:
            LOGGER.error(f"Failed to revoke role from {target_id}")
            await callback.answer("❌ Failed to revoke role!", show_alert=True)
    
    await callback.answer()

@shivuu.on_callback_query(filters.regex(r"^sudo_close$"))
async def close_panel(client: Client, callback: CallbackQuery):
    """Close the sudo panel."""
    LOGGER.info(f"User {callback.from_user.id} closed sudo panel")
    await callback.message.delete()
    await callback.answer()
