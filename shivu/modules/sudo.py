from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from shivu import shivuu
from shivu.sudo.constants import SUPERUSER_ID, ROLE_DISPLAY, PREVIEW_IMAGE, PREVIEW_CAPTION
from shivu.sudo.utils import get_role, has_clearance, can_remove, assign_role, remove_role

# Entry point command
@shivuu.on_message(filters.command("sudo") & filters.group)
async def sudo_entry(_, message: Message):
    if not message.reply_to_message:
        # No reply -> show general panel (view roles only)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("View Roles", callback_data="sudo_view_roles")]
        ])
        await message.reply_photo(PREVIEW_IMAGE, caption=PREVIEW_CAPTION, reply_markup=keyboard)
        return

    if not message.reply_to_message.from_user:
        return

    target = message.reply_to_message.from_user
    actor = message.from_user

    if target.id == actor.id:
        return await message.reply("You can't sudo yourself.")

    # Check if actor has clearance
    clearance = await has_clearance(actor.id, await get_role(target.id))
    if not clearance:
        return await message.reply("`access denied` ⟶ you lack clearance to manage this user.")

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Admin", callback_data=f"sudo_admin:{target.id}"),
            InlineKeyboardButton("View Roles", callback_data="sudo_view_roles")
        ]
    ])
    await message.reply_photo(PREVIEW_IMAGE, caption=PREVIEW_CAPTION, reply_markup=keyboard)

# View Roles Panel
@shivuu.on_callback_query(filters.regex("^sudo_view_roles$"))
async def view_roles_panel(_, query: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⟪ Owner ⟫", callback_data="view_role:owner")],
        [
            InlineKeyboardButton("⊘ Sudo", callback_data="view_role:sudo"),
            InlineKeyboardButton("≡ Uploader", callback_data="view_role:uploader")
        ],
        [InlineKeyboardButton("‹ Back", callback_data="sudo_back")]
    ])
    await query.message.edit_caption(PREVIEW_CAPTION, reply_markup=keyboard)

# Admin Panel
@shivuu.on_callback_query(filters.regex("^sudo_admin:(\\d+)$"))
async def sudo_admin_panel(_, query: CallbackQuery):
    target_id = int(query.data.split(":")[1])
    actor_id = query.from_user.id

    # Permission Check
    clearance = await has_clearance(actor_id, await get_role(target_id))
    if not clearance:
        return await query.answer("Access denied.", show_alert=True)

    assignable = []
    actor_role = await get_role(actor_id)

    if actor_id == SUPERUSER_ID:
        assignable = ["owner", "sudo", "uploader"]
    elif actor_role == "owner":
        assignable = ["sudo", "uploader"]
    elif actor_role == "sudo":
        assignable = ["uploader"]

    assign_buttons = [
        InlineKeyboardButton(ROLE_DISPLAY[r], callback_data=f"assign:{target_id}:{r}")
        for r in assignable
    ]

    keyboard = InlineKeyboardMarkup([
        assign_buttons,
        [InlineKeyboardButton("Discard", callback_data=f"discard:{target_id}"),
         InlineKeyboardButton("‹ Back", callback_data="sudo_back")]
    ])
    await query.message.edit_caption(f"Manage roles for `{target_id}`:", reply_markup=keyboard)

# Assign Role
@shivuu.on_callback_query(filters.regex("^assign:(\\d+):(\\w+)$"))
async def assign_role_handler(_, query: CallbackQuery):
    _, target_id, role = query.data.split(":")
    target_id = int(target_id)
