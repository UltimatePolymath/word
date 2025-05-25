# shivu/modules/sudo_panel.py

from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from shivu import shivuu  # Correct import
from shivu.sudo.db import add_user, remove_user, get_user_role
from shivu.sudo.utils import can_assign, can_revoke, get_effective_role

IMAGE_URL = "https://i.ibb.co/M5ShPN50/tmpgr3gsx2o.jpg"

# This is the main callback to open the sudo panel
@shivuu.on_callback_query(filters.regex(r"open_sudo_panel_(\d+)"))
async def handle_open_panel(client, callback_query: CallbackQuery):
    target_user_id = int(callback_query.matches[0].group(1))  # Target user
    opener_id = callback_query.from_user.id  # The one opening the panel

    opener_role = await get_effective_role(opener_id)
    if opener_role not in ["superuser", "owner", "sudo"]:
        return await callback_query.answer("⨂ Access Denied", show_alert=True)

    target_role = await get_user_role(target_user_id)
    if target_role == "superuser":
        return await callback_query.answer("⨂ Cannot modify Superuser", show_alert=True)

    buttons = []
    for role in ["owner", "sudo", "uploader"]:
        if await can_assign(opener_id, role):
            if target_role == role:
                buttons.append([
                    InlineKeyboardButton(f"⨂ Revoke {role.capitalize()}", callback_data=f"revoke_{role}_{target_user_id}")
                ])
            else:
                buttons.append([
                    InlineKeyboardButton(f"⨁ Assign {role.capitalize()}", callback_data=f"assign_{role}_{target_user_id}")
                ])

    buttons.append([InlineKeyboardButton("⤿ Close Panel", callback_data="close_sudo_panel")])

    caption = f"""⌬ **Role Management Panel** ⌬

⌁ Target ID: `{target_user_id}`
⌁ Current Role: **{target_role or 'None'}**
⌁ Managed by: `{opener_role.capitalize()}`

Choose a function below:"""

    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=IMAGE_URL, caption=caption),
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# This is the callback handler for the 'Assign' button
@shivuu.on_callback_query(filters.regex(r"assign_(\w+)_(\d+)"))
async def handle_assign_role(client, callback_query: CallbackQuery):
    role = callback_query.matches[0].group(1)  # Role to assign (owner, sudo, uploader)
    target_user_id = int(callback_query.matches[0].group(2))

    opener_id = callback_query.from_user.id
    opener_role = await get_effective_role(opener_id)
    
    # Check if the opener can assign the requested role
    if not await can_assign(opener_id, role):
        return await callback_query.answer("⨂ You don't have permission to assign this role", show_alert=True)

    # Assign role to the user
    await add_user(target_user_id, role)

    caption = f"""⌬ **Role Management Panel** ⌬

⌁ Target ID: `{target_user_id}`
⌁ Current Role: **{role.capitalize()}**
⌁ Managed by: `{opener_role.capitalize()}`

Role `{role.capitalize()}` has been successfully assigned."""

    buttons = [
        [InlineKeyboardButton("⨂ Revoke " + role.capitalize(), callback_data=f"revoke_{role}_{target_user_id}")],
        [InlineKeyboardButton("⤿ Close Panel", callback_data="close_sudo_panel")]
    ]

    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=IMAGE_URL, caption=caption),
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# This is the callback handler for the 'Revoke' button
@shivuu.on_callback_query(filters.regex(r"revoke_(\w+)_(\d+)"))
async def handle_revoke_role(client, callback_query: CallbackQuery):
    role = callback_query.matches[0].group(1)  # Role to revoke
    target_user_id = int(callback_query.matches[0].group(2))

    opener_id = callback_query.from_user.id
    opener_role = await get_effective_role(opener_id)
    
    # Check if the opener can revoke the requested role
    if not await can_revoke(opener_id, role):
        return await callback_query.answer("⨂ You don't have permission to revoke this role", show_alert=True)

    # Revoke role from the user
    await remove_user(target_user_id)

    caption = f"""⌬ **Role Management Panel** ⌬

⌁ Target ID: `{target_user_id}`
⌁ Current Role: **None**
⌁ Managed by: `{opener_role.capitalize()}`

Role `{role.capitalize()}` has been successfully revoked."""

    buttons = [
        [InlineKeyboardButton("⨁ Assign " + role.capitalize(), callback_data=f"assign_{role}_{target_user_id}")],
        [InlineKeyboardButton("⤿ Close Panel", callback_data="close_sudo_panel")]
    ]

    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=IMAGE_URL, caption=caption),
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Close the panel (reset to initial state)
@shivuu.on_callback_query(filters.regex("close_sudo_panel"))
async def handle_close_panel(client, callback_query: CallbackQuery):
    await callback_query.message.delete()
