# shivu/modules/sudo_panel.py

from pyrogram import filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from shivu import shivuu
from shivu.sudo.db import add_user, remove_user, get_user_role
from shivu.sudo.utils import (
    can_assign,
    can_revoke,
    get_effective_role,
)

IMAGE_URL = "https://i.ibb.co/M5ShPN50/tmpgr3gsx2o.jpg"

# COMMAND: /sudo
@shivuu.on_message(filters.command("sudo") & filters.reply)
async def open_sudo_panel_command(_, message: Message):
    opener_id = message.from_user.id
    target_user = message.reply_to_message.from_user

    # Permission check
    opener_role = await get_effective_role(opener_id)
    if opener_role not in ["superuser", "owner", "sudo"]:
        return await message.reply("⨂ You are not allowed to access the sudo panel.")

    # Panel opener button
    panel_button = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "☰ Open the Panel",
                    callback_data=f"open_sudo_panel_{target_user.id}",
                )
            ]
        ]
    )

    await message.reply_photo(
        photo=IMAGE_URL,
        caption=(
            f"⌬ **Sudo Role Control**\n\n"
            f"↳ Reply target: `{target_user.id}`\n"
            f"↳ Use the panel to manage roles."
        ),
        reply_markup=panel_button,
    )


# CALLBACK: Open Panel
@shivuu.on_callback_query(filters.regex(r"open_sudo_panel_(\d+)"))
async def open_sudo_panel(_, callback_query: CallbackQuery):
    target_id = int(callback_query.matches[0].group(1))
    opener_id = callback_query.from_user.id

    opener_role = await get_effective_role(opener_id)
    if opener_role not in ["superuser", "owner", "sudo"]:
        return await callback_query.answer("⨂ Access Denied", show_alert=True)

    target_role = await get_user_role(target_id)
    if target_role == "superuser":
        return await callback_query.answer("⨂ Cannot modify Superuser", show_alert=True)

    buttons = []
    for role in ["owner", "sudo", "uploader"]:
        if await can_assign(opener_id, role):
            if target_role == role:
                buttons.append([
                    InlineKeyboardButton(f"⨂ Revoke {role.capitalize()}", callback_data=f"revoke_{role}_{target_id}")
                ])
            else:
                buttons.append([
                    InlineKeyboardButton(f"⨁ Assign {role.capitalize()}", callback_data=f"assign_{role}_{target_id}")
                ])

    buttons.append([InlineKeyboardButton("⤿ Close Panel", callback_data="close_sudo_panel")])

    caption = (
        f"⌬ **Role Management Panel** ⌬\n\n"
        f"⌁ Target ID: `{target_id}`\n"
        f"⌁ Current Role: **{target_role or 'None'}**\n"
        f"⌁ Managed by: `{opener_role.capitalize()}`\n\n"
        f"Choose an action:"
    )

    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=IMAGE_URL, caption=caption),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# CALLBACK: Assign Role
@shivuu.on_callback_query(filters.regex(r"assign_(\w+)_(\d+)"))
async def assign_role(_, callback_query: CallbackQuery):
    role, target_id = callback_query.matches[0].group(1), int(callback_query.matches[0].group(2))
    opener_id = callback_query.from_user.id
    opener_role = await get_effective_role(opener_id)

    if not await can_assign(opener_id, role):
        return await callback_query.answer("⨂ You lack permission to assign this role.", show_alert=True)

    await add_user(target_id, role)

    await open_sudo_panel(_, callback_query)  # Refresh the panel


# CALLBACK: Revoke Role
@shivuu.on_callback_query(filters.regex(r"revoke_(\w+)_(\d+)"))
async def revoke_role(_, callback_query: CallbackQuery):
    role, target_id = callback_query.matches[0].group(1), int(callback_query.matches[0].group(2))
    opener_id = callback_query.from_user.id
    opener_role = await get_effective_role(opener_id)

    if not await can_revoke(opener_id, role):
        return await callback_query.answer("⨂ You lack permission to revoke this role.", show_alert=True)

    await remove_user(target_id)

    await open_sudo_panel(_, callback_query)  # Refresh the panel


# CALLBACK: Close Panel
@shivuu.on_callback_query(filters.regex("close_sudo_panel"))
async def close_panel(_, callback_query: CallbackQuery):
    await callback_query.message.delete()
