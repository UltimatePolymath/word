from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from shivu import application  # Telegram Application from init
from shivu import shivuu  # Pyrogram client from init
from shivu.config import OWNER_ID
from shivu.sudo.constants import ROLES, ROLE_DISPLAY, SUPERUSER_ID, PREVIEW_IMAGE, PREVIEW_CAPTION
from shivu.sudo.utils import (
    get_role, is_role, assign_role, remove_role,
    has_clearance, can_remove, sudo_only, user_is_above
)
from shivu.sudo.db import get_all_by_role

# ------------------------
# /sudo command handler
# ------------------------

@application.on_message(filters.command("sudo") & filters.group)
@sudo_only()
async def sudo_panel(client, message: Message):
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        target_id = target.id
        actor_id = message.from_user.id

        target_role = await get_role(target_id)
        actor_clearances = []

        for role in ROLES:
            if not await is_role(target_id, role) and await has_clearance(actor_id, role):
                actor_clearances.append(role)

        remove_btn = None
        if await can_remove(actor_id, target_id):
            remove_btn = InlineKeyboardButton("⊖ ᴅɪꜱᴄᴀʀᴅ", callback_data=f"sudo_remove:{target_id}")

        promote_btns = [
            InlineKeyboardButton(f"⟜ ᴀᴘᴘᴏɪɴᴛ {ROLE_DISPLAY[r]}", callback_data=f"sudo_promote:{target_id}:{r}")
            for r in actor_clearances
        ]

        row_buttons = [promote_btns[i:i+2] for i in range(0, len(promote_btns), 2)]
        if remove_btn:
            row_buttons.append([remove_btn])

        await message.reply_photo(
            photo=PREVIEW_IMAGE,
            caption=f"{PREVIEW_CAPTION}\n• ᴛᴀʀɢᴇᴛ: `{target.first_name}` (`{target_id}`)\n• current ʀᴏʟᴇ: `{target_role or 'None'}`",
            reply_markup=InlineKeyboardMarkup(row_buttons)
        )

    else:
        # Show current list of all users by role
        lines = ["⤷ ᴄᴜʀʀᴇɴᴛ ʀᴏʟᴇ ᴍᴀᴘ:\n"]
        for role in ROLES:
            user_ids = await get_all_by_role(role)
            display = ROLE_DISPLAY[role]
            if not user_ids:
                lines.append(f"{display} → `none`")
                continue

            user_mentions = []
            for uid in user_ids:
                try:
                    user = await shivuu.get_users(uid)
                    user_mentions.append(f"[{user.first_name}](tg://user?id={uid})")
                except:
                    user_mentions.append(f"`{uid}`")

            lines.append(f"{display} → " + ", ".join(user_mentions))

        await message.reply_photo(
            photo=PREVIEW_IMAGE,
            caption=PREVIEW_CAPTION + "\n\n" + "\n".join(lines)
        )


# ------------------------
# CallbackQuery Handlers
# ------------------------

@application.on_callback_query(filters.regex(r"^sudo_promote:(\d+):(\w+)$"))
async def promote_callback(_, query: CallbackQuery):
    actor_id = query.from_user.id
    target_id = int(query.matches[0].group(1))
    target_role = query.matches[0].group(2)

    if not await has_clearance(actor_id, target_role):
        return await query.answer("Access denied", show_alert=True)

    await assign_role(target_id, target_role, actor_id)
    user = await shivuu.get_users(target_id)
    await query.message.edit_caption(
        f"⟪ {user.first_name} ⟫ has been appointed as {ROLE_DISPLAY[target_role]}"
    )


@application.on_callback_query(filters.regex(r"^sudo_remove:(\d+)$"))
async def remove_callback(_, query: CallbackQuery):
    actor_id = query.from_user.id
    target_id = int(query.matches[0].group(1))

    if not await can_remove(actor_id, target_id):
        return await query.answer("Access denied", show_alert=True)

    await remove_role(target_id)
    user = await shivuu.get_users(target_id)
    await query.message.edit_caption(
        f"⊖ {user.first_name} has been removed from the role panel."
    )
