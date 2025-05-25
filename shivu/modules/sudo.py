from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from shivu import shivuu, sudo_collection
from shivu.sudo.db import get_user_role, set_user_role, remove_user_role, get_all_sudo_users
from shivu.sudo.utils import can_manage_role, get_allowed_actions, SUPERUSER_ID

PANEL_IMAGE = "https://i.ibb.co/M5ShPN50/tmpgr3gsx2o.jpg"

@shivuu.on_message(filters.command("sudo") & filters.reply)
async def sudo_command(client: Client, message: Message):
    """Handle the /sudo command to open the role management panel."""
    caller_id = message.from_user.id
    caller_role = await get_user_role(caller_id)
    
    # Check if caller has permission
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        await message.reply_text("⛔ You don't have permission to use this command!")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    target_role = await get_user_role(target_id)
    
    # Create inline panel
    buttons = [[InlineKeyboardButton("⟪ Open the Panel ⟫", callback_data=f"sudo_panel:{target_id}")]]
    await message.reply_photo(
        photo=PANEL_IMAGE,
        caption=f"🔧 Sudo Panel for {target_user.mention}\nCurrent Role: {target_role or 'None'}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@shivuu.on_callback_query(filters.regex(r"^sudo_panel:(\d+)$"))
async def sudo_panel(client: Client, callback: CallbackQuery):
    """Handle the sudo panel interactions."""
    caller_id = callback.from_user.id
    caller_role = await get_user_role(caller_id)
    
    # Check permission
    if caller_role not in ["superuser", "owner", "sudo"] and caller_id != SUPERUSER_ID:
        await callback.answer("⛔ You don't have permission!", show_alert=True)
        return
    
    target_id = int(callback.data.split(":")[1])
    target_role = await get_user_role(target_id)
    allowed_actions = get_allowed_actions(caller_role)
    
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
        await callback.answer("⛔ You don't have permission!", show_alert=True)
        return
    
    action, target_id, role = callback.data.split(":")
    target_id = int(target_id)
    
    if not can_manage_role(caller_role, role):
        await callback.answer(f"⛔ You can't manage the {role} role!", show_alert=True)
        return
    
    if action == "sudo_assign":
        await set_user_role(target_id, role)
        await callback.message.edit_caption(
            caption=f"✅ Assigned {role.capitalize()} to User ID: {target_id}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⟪ Close Panel ⟫", callback_data="sudo_close")]])
        )
    elif action == "sudo_revoke":
        await remove_user_role(target_id)
        await callback.message.edit_caption(
            caption=f"✅ Revoked role from User ID: {target_id}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⟪ Close Panel ⟫", callback_data="sudo_close")]])
        )
    
    await callback.answer()

@shivuu.on_callback_query(filters.regex(r"^sudo_close$"))
async def close_panel(client: Client, callback: CallbackQuery):
    """Close the sudo panel."""
    await callback.message.delete()
    await callback.answer()
