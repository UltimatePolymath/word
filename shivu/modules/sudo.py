from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from shivu import shivuu, sudo, OWNER_ID
from pymongo import UpdateOne

PREVIEW_IMG = "https://i.ibb.co/M5ShPN50/tmpgr3gsx2o.jpg"

SYMBOLS = {
    "appoint": "⟜",
    "discard": "⊘",
    "owner": "≡",
    "sudo": "⊠",
    "uploader": "⊡",
    "view": "⋗",
    "back": "↻"
}


def smallcaps(text: str) -> str:
    table = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ")
    return text.lower().translate(table)


async def get_roles(user_id: int) -> list:
    doc = await sudo.find_one({"user_id": user_id})
    return doc.get("roles", []) if doc else []


async def add_role(user_id: int, role: str, appointed_by: int):
    await sudo.update_one(
        {"user_id": user_id},
        {"$addToSet": {"roles": role}, "$setOnInsert": {"appointed_by": appointed_by}},
        upsert=True
    )


async def remove_user(user_id: int):
    await sudo.delete_one({"user_id": user_id})


async def validate(actor_id: int, target_role: str) -> bool:
    if actor_id == OWNER_ID:
        return True
    actor_roles = await get_roles(actor_id)
    if target_role == "owner":
        return False
    if target_role == "sudo":
        return "owner" in actor_roles
    if target_role == "uploader":
        return "sudo" in actor_roles
    return False


def appoint_panel():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{SYMBOLS['owner']} {smallcaps('owner')}", callback_data="appoint:owner"),
            InlineKeyboardButton(f"{SYMBOLS['sudo']} {smallcaps('sudo')}", callback_data="appoint:sudo")
        ],
        [
            InlineKeyboardButton(f"{SYMBOLS['uploader']} {smallcaps('uploader')}", callback_data="appoint:uploader"),
            InlineKeyboardButton(f"{SYMBOLS['discard']} {smallcaps('discard')}", callback_data="discard")
        ],
        [
            InlineKeyboardButton(f"{SYMBOLS['back']} {smallcaps('back')}", callback_data="cancel")
        ]
    ])


def main_panel():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{SYMBOLS['view']} {smallcaps('owners')}", callback_data="view:owner"),
            InlineKeyboardButton(f"{SYMBOLS['view']} {smallcaps('sudos')}", callback_data="view:sudo")
        ],
        [
            InlineKeyboardButton(f"{SYMBOLS['view']} {smallcaps('uploaders')}", callback_data="view:uploader")
        ]
    ])


@shivuu.on_message(filters.command("sudo") & filters.private)
async def sudo_entry(client: Client, message: Message):
    user_id = message.from_user.id
    if not (user_id == OWNER_ID or "owner" in await get_roles(user_id) or "sudo" in await get_roles(user_id)):
        return await message.reply_text("you lack proper clearance to access role management.")
    
    if message.reply_to_message:
        replied = message.reply_to_message.from_user
        await message.reply_photo(
            PREVIEW_IMG,
            caption=f"{smallcaps('target:')} <b>{replied.first_name}</b>\n{smallcaps('id:')} <code>{replied.id}</code>\n\n{smallcaps('choose an action below:')}",
            reply_markup=appoint_panel()
        )
        return
    
    await message.reply_photo(
        PREVIEW_IMG,
        caption=f"{smallcaps('role access panel:')}",
        reply_markup=main_panel()
    )


@shivuu.on_callback_query(filters.regex("appoint:(.*)"))
async def appoint_handler(client: Client, callback: CallbackQuery):
    role = callback.data.split(":")[1]
    actor = callback.from_user.id
    message = callback.message

    if not message.reply_to_message:
        return await callback.answer("no user to appoint.", show_alert=True)

    target = message.reply_to_message.from_user.id
    if not await validate(actor, role):
        return await callback.answer("you can't appoint this role.", show_alert=True)

    await add_role(target, role, actor)
    await callback.answer(f"{role} role appointed.")


@shivuu.on_callback_query(filters.regex("discard"))
async def discard_handler(client: Client, callback: CallbackQuery):
    actor = callback.from_user.id
    message = callback.message

    if not message.reply_to_message:
        return await callback.answer("no user to discard.", show_alert=True)

    target = message.reply_to_message.from_user.id
    if actor != OWNER_ID:
        doc = await sudo.find_one({"user_id": target})
        if not doc or doc.get("appointed_by") != actor:
            return await callback.answer("you can only discard users you appointed.", show_alert=True)

    await remove_user(target)
    await callback.answer("user removed.")


@shivuu.on_callback_query(filters.regex("view:(.*)"))
async def view_roles_handler(client: Client, callback: CallbackQuery):
    role = callback.data.split(":")[1]
    docs = sudo.find({"roles": role})
    users = [f"{doc['user_id']}" async for doc in docs]

    text = f"{smallcaps('current')} {role}s:\n" + '\n'.join([f"• <code>{uid}</code>" for uid in users]) if users else "no users with this role."
    await callback.message.edit_text(text, reply_markup=main_panel())


@shivuu.on_callback_query(filters.regex("cancel"))
async def cancel_cb(client: Client, callback: CallbackQuery):
    await callback.message.delete()
