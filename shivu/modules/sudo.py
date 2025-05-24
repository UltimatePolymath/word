from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from shivu import sudo, OWNER_ID, shivuu
from pymongo import ReturnDocument

PREVIEW_IMAGE = "https://i.ibb.co/M5ShPN50/tmpgr3gsx2o.jpg"

ROLES = ["owner", "sudo", "uploader"]
ROLE_SYMBOLS = {
    "owner": "◉",
    "sudo": "⟜",
    "uploader": "⋇"
}
BUTTON_LABELS = {
    "appoint": "⟴ appoint",
    "discard": "⊘ discard",
    "back": "← back",
}

def format_smallcaps(text: str) -> str:
    return ''.join(chr(0x1D5BA + ord(c.lower()) - ord('a')) if c.isalpha() else c for c in text)

def role_key(role): return f"{role}_by"

def get_role_doc(user_id):
    return sudo.find_one({"user_id": user_id})

async def is_allowed(issuer_id: int, target_role: str) -> bool:
    if issuer_id == OWNER_ID:
        return True
    issuer_data = await sudo.find_one({"user_id": issuer_id})
    if not issuer_data:
        return False
    if target_role == "owner":
        return False
    if target_role == "sudo" and "owner" in issuer_data.get("roles", []):
        return True
    if target_role == "uploader" and "sudo" in issuer_data.get("roles", []):
        return True
    return False

def build_roles_text(user_data):
    lines = []
    for role in ROLES:
        if role in user_data.get("roles", []):
            lines.append(f"{ROLE_SYMBOLS[role]} {format_smallcaps(role)}  — appointed by `{user_data.get(role_key(role), 'unknown')}`")
    return "\n".join(lines) or "no roles assigned."

def build_inline_buttons(user_id, appoint_mode=True):
    buttons = []
    temp_row = []
    for idx, role in enumerate(ROLES):
        action = "appoint" if appoint_mode else "discard"
        label = f"{ROLE_SYMBOLS[role]} {format_smallcaps(role)}"
        data = f"{action}:{role}:{user_id}"
        temp_row.append(InlineKeyboardButton(label, callback_data=data))
        if len(temp_row) == 2:
            buttons.append(temp_row)
            temp_row = []
    if temp_row:
        buttons.append(temp_row)
    buttons.append([InlineKeyboardButton(BUTTON_LABELS["back"], callback_data=f"back:{user_id}")])
    return buttons

def build_role_view_buttons():
    buttons = []
    temp_row = []
    for idx, role in enumerate(ROLES):
        label = f"{ROLE_SYMBOLS[role]} {format_smallcaps(role)}s"
        data = f"view:{role}"
        temp_row.append(InlineKeyboardButton(label, callback_data=data))
        if len(temp_row) == 2:
            buttons.append(temp_row)
            temp_row = []
    if temp_row:
        buttons.append(temp_row)
    return buttons

@shivuu.on_message(filters.command("sudo") & filters.private)
async def sudo_entry(c: Client, m: Message):
    if not (await sudo.find_one({"user_id": m.from_user.id})) and m.from_user.id != OWNER_ID:
        return await m.reply("you lack the clearance for this interface.")

    if m.reply_to_message:
        target = m.reply_to_message.from_user
        user_data = await sudo.find_one({"user_id": target.id}) or {"user_id": target.id, "roles": []}
        text = f"𓆩 {format_smallcaps('role profile')} 𓆪\n\n" \
               f"for: `{target.id}` — {target.first_name}\n\n" + build_roles_text(user_data)

        buttons = [
            [InlineKeyboardButton(BUTTON_LABELS["appoint"], callback_data=f"panel:appoint:{target.id}"),
             InlineKeyboardButton(BUTTON_LABELS["discard"], callback_data=f"panel:discard:{target.id}")]
        ]
        await m.reply_photo(PREVIEW_IMAGE, caption=text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await m.reply_photo(
            PREVIEW_IMAGE,
            caption="𓆩 " + format_smallcaps("view role-holders") + " 𓆪",
            reply_markup=InlineKeyboardMarkup(build_role_view_buttons())
        )

@shivuu.on_callback_query(filters.regex(r"^panel:(appoint|discard):(\d+)$"))
async def open_action_panel(c: Client, cq: CallbackQuery):
    action, uid = cq.data.split(":")[1:]
    uid = int(uid)
    appoint_mode = action == "appoint"
    await cq.edit_message_caption(
        f"𓆩 {format_smallcaps('select role')} to {action} 𓆪\n\nfor: `{uid}`",
        reply_markup=InlineKeyboardMarkup(build_inline_buttons(uid, appoint_mode))
    )

@shivuu.on_callback_query(filters.regex(r"^(appoint|discard):(\w+):(\d+)$"))
async def handle_role_action(c: Client, cq: CallbackQuery):
    action, role, uid = cq.data.split(":")
    issuer_id = cq.from_user.id
    uid = int(uid)

    if not await is_allowed(issuer_id, role):
        return await cq.answer("access denied for this action.", show_alert=True)

    existing = await sudo.find_one({"user_id": uid}) or {"user_id": uid, "roles": []}

    if action == "appoint":
        if role not in existing["roles"]:
            existing["roles"].append(role)
            existing[role_key(role)] = issuer_id
            await sudo.replace_one({"user_id": uid}, existing, upsert=True)
    else:
        if role in existing["roles"]:
            existing["roles"].remove(role)
            existing.pop(role_key(role), None)
            if existing["roles"]:
                await sudo.replace_one({"user_id": uid}, existing)
            else:
                await sudo.delete_one({"user_id": uid})

    text = f"𓆩 {format_smallcaps('updated role profile')} 𓆪\n\nfor: `{uid}`\n\n" + build_roles_text(existing)
    await cq.edit_message_caption(text, reply_markup=InlineKeyboardMarkup(build_inline_buttons(uid, appoint_mode=True)))

@shivuu.on_callback_query(filters.regex(r"^view:(\w+)$"))
async def handle_view_role(c: Client, cq: CallbackQuery):
    role = cq.data.split(":")[1]
    cursor = sudo.find({ "roles": role })
    users = await cursor.to_list(None)
    lines = [f"{ROLE_SYMBOLS[role]} `{u['user_id']}` — {u.get(role_key(role), 'unknown')}" for u in users]
    text = f"𓆩 {format_smallcaps(role)}s 𓆪\n\n" + ("\n".join(lines) if lines else "none found.")
    await cq.edit_message_caption(text, reply_markup=InlineKeyboardMarkup(build_role_view_buttons()))

@shivuu.on_callback_query(filters.regex(r"^back:(\d+)$"))
async def handle_back(c: Client, cq: CallbackQuery):
    uid = int(cq.data.split(":")[1])
    user_data = await sudo.find_one({"user_id": uid}) or {"user_id": uid, "roles": []}
    text = f"𓆩 {format_smallcaps('role profile')} 𓆪\n\nfor: `{uid}`\n\n" + build_roles_text(user_data)
    buttons = [
        [InlineKeyboardButton(BUTTON_LABELS["appoint"], callback_data=f"panel:appoint:{uid}"),
         InlineKeyboardButton(BUTTON_LABELS["discard"], callback_data=f"panel:discard:{uid}")]
    ]
    await cq.edit_message_caption(text, reply_markup=InlineKeyboardMarkup(buttons))
