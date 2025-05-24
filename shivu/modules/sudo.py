from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from shivu import sudo, OWNER_ID, shivuu, PHOTO_URL
from typing import Optional, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
PREVIEW_IMAGE = "https://i.ibb.co/M5ShPN50/tmpgr3gsx2o.jpg"
ROLES = ["owner", "sudo", "uploader"]
ACTION_TIMEOUT = 30  # seconds

# Error Messages
INSUFFICIENT_PRIV = "⩥ ɪɴꜱᴜꜰꜰɪᴄɪᴇɴᴛ ᴘʀɪᴠɪʟᴇɢᴇꜱ"
INVALID_TARGET = "⩥ ɪɴᴠᴀʟɪᴅ ᴜꜱᴇʀ ꜱᴇʟᴇᴄᴛɪᴏɴ"
DB_ERROR = "⩥ ᴅᴀᴛᴀʙᴀꜱᴇ ᴏᴘᴇʀᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ"

async def get_roles(user_id: int) -> List[str]:
    """Fetch roles with caching and error handling"""
    if user_id == OWNER_ID:
        return ROLES
    try:
        doc = await sudo.find_one({"user_id": user_id})
        return doc.get("roles", []) if doc else []
    except Exception as e:
        logger.error(f"DB Error in get_roles: {e}")
        return []

async def modify_roles(
    user_id: int,
    role: str,
    actor_id: int,
    action: str
) -> bool:
    """Atomic role modification with validation"""
    if user_id == OWNER_ID and action == "remove":
        return False  # Prevent modifying superuser

    try:
        if action == "add":
            update = {
                "$addToSet": {"roles": role},
                "$set": {"appointed_by": actor_id}
            }
        else:
            update = {
                "$pull": {"roles": role},
                "$unset": {"appointed_by": ""}
            }

        result = await sudo.update_one(
            {"user_id": user_id},
            update,
            upsert=(action == "add")
        )
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception as e:
        logger.error(f"DB Error in modify_roles: {e}")
        return False

async def has_clearance(
    actor_id: int,
    target_id: Optional[int] = None,
    required_role: Optional[str] = None
) -> bool:
    """Enhanced permission system with role hierarchy"""
    if actor_id == OWNER_ID:
        return True

    try:
        actor_roles = await get_roles(actor_id)
        if not actor_roles:
            return False

        # Role-based hierarchy check
        role_hierarchy = {role: idx for idx, role in enumerate(ROLES)}
        if required_role:
            return any(
                role_hierarchy.get(r, -1) > role_hierarchy.get(required_role, 99)
                for r in actor_roles
            )

        # Target-specific checks
        if target_id:
            target_roles = await get_roles(target_id)
            return any(
                role_hierarchy.get(a_role, -1) > role_hierarchy.get(t_role, 99)
                for a_role in actor_roles
                for t_role in target_roles
            )

        return bool(actor_roles)
    except Exception as e:
        logger.error(f"Error in has_clearance: {e}")
        return False

@shivuu.on_message(filters.command("sudo"))
async def sudo_panel(client: Client, message: Message):
    """Main control panel with error handling"""
    try:
        uid = message.from_user.id
        if not await has_clearance(uid):
            return await message.reply("⩥ ɪɴꜱᴜꜰꜰɪᴄɪᴇɴᴛ ᴘʀɪᴠɪʟᴇɢᴇꜱ")

        if message.reply_to_message:
            target = message.reply_to_message.from_user
            if target.is_self or target.is_bot:
                return await message.reply(INVALID_TARGET)

            buttons = [
                [
                    InlineKeyboardButton("⟜ ᴀᴘᴘᴏɪɴᴛ", 
                        callback_data=f"role:appoint:{target.id}"),
                    InlineKeyboardButton("⊠ ʀᴇᴠᴏᴋᴇ", 
                        callback_data=f"role:revoke:{target.id}")
                ],
                [InlineKeyboardButton("⇲ ᴄᴀɴᴄᴇʟ", 
                    callback_data="role:cancel")]
            ]
            
            return await message.reply_photo(
                photo=PHOTO_URL,
                caption=(
                    f"⩥ ʀᴏʟᴇ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ\n\n"
                    f"⟐ ᴛᴀʀɢᴇᴛ: {target.mention}\n"
                    f"⊛ ɪᴅ: `{target.id}`"
                ),
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        # Fetch current hierarchy
        hierarchy = {}
        for role in ROLES:
            users = await sudo.find({"roles": role}).to_list(100)
            hierarchy[role] = [u["user_id"] for u in users]

        caption = "⩥ ꜱʏꜱᴛᴇᴍ ʜɪᴇʀᴀʀᴄʜʏ\n\n"
        for role in ROLES:
            caption += f"⟜ {role.capitalize()}ꜱ:\n"
            caption += "\n".join([f"• `{uid}`" for uid in hierarchy[role]]) or "∅ ɴᴏɴᴇ\n"
            caption += "\n\n"

        await message.reply_photo(
            PHOTO_URL,
            caption=caption[:4000],  # Telegram caption limit
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⛨ ᴜᴘᴅᴀᴛᴇ", callback_data="role:refresh")
            ]])
        )

    except Exception as e:
        logger.error(f"Panel Error: {e}")
        await message.reply("⩥ ꜱʏꜱᴛᴇᴍ ᴇʀʀᴏʀ")

@shivuu.on_callback_query(filters.regex(r"^role:(appoint|revoke):(\d+)$"))
async def role_management(client: Client, query: CallbackQuery):
    """Handle role modifications with atomic operations"""
    try:
        action, target_id = query.matches[0].group(1), int(query.matches[0].group(2))
        actor_id = query.from_user.id

        # Validation checks
        if target_id == query.from_user.id:
            return await query.answer("⩥ ꜱᴇʟꜰ-ᴍᴏᴅɪꜰɪᴄᴀᴛɪᴏɴ ʙʟᴏᴄᴋᴇᴅ", show_alert=True)

        if not await has_clearance(actor_id, target_id):
            return await query.answer(INSUFFICIENT_PRIV, show_alert=True)

        if action == "appoint":
            buttons = [
                [InlineKeyboardButton(role.capitalize(), 
                    callback_data=f"confirm:add:{role}:{target_id}")]
                for role in ROLES
                if await has_clearance(actor_id, required_role=role)
            ]
            await query.message.edit_reply_markup(
                InlineKeyboardMarkup(buttons + [[
                    InlineKeyboardButton("⇲ ʙᴀᴄᴋ", callback_data="role:cancel")
                ]])
            )
        else:
            target_roles = await get_roles(target_id)
            buttons = [
                [InlineKeyboardButton(f"ʀᴇᴍᴏᴠᴇ {role}", 
                    callback_data=f"confirm:remove:{role}:{target_id}")]
                for role in target_roles
                if await has_clearance(actor_id, required_role=role)
            ]
            await query.message.edit_reply_markup(
                InlineKeyboardMarkup(buttons + [[
                    InlineKeyboardButton("⇲ ʙᴀᴄᴋ", callback_data="role:cancel")
                ]])
            )

        await query.answer()

    except Exception as e:
        logger.error(f"Management Error: {e}")
        await query.answer(DB_ERROR, show_alert=True)

@shivuu.on_callback_query(filters.regex(r"^confirm:(add|remove):(\w+):(\d+)$"))
async def confirm_action(client: Client, query: CallbackQuery):
    """Final confirmation for role changes"""
    try:
        action, role, target_id = (
            query.matches[0].group(1),
            query.matches[0].group(2),
            int(query.matches[0].group(3)))
        
        if not await has_clearance(query.from_user.id, required_role=role):
            return await query.answer(INSUFFICIENT_PRIV, show_alert=True)

        success = await modify_roles(target_id, role, query.from_user.id, action)
        if success:
            msg = f"⩥ ꜱᴜᴄᴄᴇꜱꜱ: {role} {'ᴀᴅᴅᴇᴅ' if action == 'add' else 'ʀᴇᴍᴏᴠᴇᴅ'}"
            await query.answer(msg, show_alert=True)
            await query.message.delete()
            await sudo_panel(client, query.message)
        else:
            await query.answer("⩥ ɴᴏ ᴄʜᴀɴɢᴇꜱ ᴍᴀᴅᴇ", show_alert=True)

    except Exception as e:
        logger.error(f"Confirmation Error: {e}")
        await query.answer(DB_ERROR, show_alert=True)

@shivuu.on_callback_query(filters.regex("role:(cancel|refresh)$"))
async def refresh_or_cancel(client: Client, query: CallbackQuery):
    """Handle refresh and cancel actions"""
    try:
        if query.data == "role:refresh":
            await sudo_panel(client, query.message)
        else:
            await query.message.delete()
        await query.answer()
    except Exception as e:
        logger.error(f"Refresh Error: {e}")
        await query.answer("⩥ ᴏᴘᴇʀᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ", show_alert=True)
