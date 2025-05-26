import random
from html import escape
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from shivu import application, SUPPORT_CHAT, UPDATE_CHAT, BOT_USERNAME, db, GROUP_ID
from shivu import pm_users as collection
from shivu.archive.coin import create_user_coin_doc
from shivu.archive.xp import create_user_xp

# Small caps converter
def to_small_caps(text: str) -> str:
    normal = "abcdefghijklmnopqrstuvwxyz"
    smallcaps = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    return ''.join(smallcaps[normal.index(c)] if c in normal else c for c in text.lower())

caption_main = """🍂 ɢʀᴇᴇᴛɪɴɢs, ɪ'ᴍ ⟦ 𝕾𝖎𝖓 ☒ 𝕮𝖆𝖙𝖈𝖍𝖊𝖗 ⟧, ɴɪᴄᴇ ᴛᴏ ᴍᴇᴇᴛ ʏᴏᴜ!
━━━━━━━▧▣▧━━━━━━━
⦾ ᴡʜᴀᴛ ɪ ᴅᴏ: ɪ sᴘᴀᴡɴ   
     ωαιƒυ ɪɴ ʏᴏᴜʀ ᴄʜᴀᴛ ғᴏʀ
     ᴜsᴇʀs ᴛᴏ ɢʀᴀʙ.
⦾ ᴛᴏ ᴜsᴇ ᴍᴇ: ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ
     ɢʀᴏᴜᴘ ᴀɴᴅ ᴛᴀᴘ ᴛʜᴇ ʜᴇʟᴘ
     ʙᴜᴛᴛᴏɴ ғᴏʀ ᴅᴇᴛᴀɪʟs.
━━━━━━━▧▣▧━━━━━━━"""

buttons_main = InlineKeyboardMarkup([
    [InlineKeyboardButton("☊ " + to_small_caps("Add Me"), url=f"http://t.me/{BOT_USERNAME}?startgroup=new"),
     InlineKeyboardButton("⚙ " + to_small_caps("Help"), callback_data='help')],
    [InlineKeyboardButton("✦ " + to_small_caps("Support"), url=f"https://t.me/{SUPPORT_CHAT}"),
     InlineKeyboardButton("☍ " + to_small_caps("Updates"), url=f"https://t.me/{UPDATE_CHAT}")],
    [InlineKeyboardButton("⌬ " + to_small_caps("Source"), url="https://youtu.be/dQw4w9WgXcQ?si=NvUDu8RN78zX_VEJ")]
])

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    user_data = await collection.find_one({"_id": user_id})
    if user_data is None:
        await collection.insert_one({"_id": user_id, "first_name": first_name, "username": username})
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"New user Started The Bot..\nUser: <a href='tg://user?id={user_id}'>{escape(first_name)}</a>",
            parse_mode='HTML'
        )
    elif user_data['first_name'] != first_name or user_data['username'] != username:
        await collection.update_one({"_id": user_id}, {"$set": {"first_name": first_name, "username": username}})

    # Initialize sin's make
    await create_user_coin_doc(user_id)
    await create_user_xp(user_id)

    # Send photo with inline buttons
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo="https://i.ibb.co/k61RdYyz/tmporofsr6m.jpg",
        caption=caption_main,
        reply_markup=buttons_main
    )


async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'help':
        help_text = to_small_caps("""
HELP MENU:

• /guess – guess character (group only)  
• /fav – add to favorites  
• /trade – trade characters  
• /gift – gift characters to users  
• /collection – view your collection  
• /topgroups – most active groups  
• /top – top users  
• /ctop – your chat top  
• /changetime – set spawn time (group only)
        """)

        back_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("↶ " + to_small_caps("Back"), callback_data='back')]
        ])

        await query.edit_message_caption(
            caption=help_text,
            reply_markup=back_button
        )

    elif query.data == 'back':
        await query.edit_message_caption(
            caption=caption_main,
            reply_markup=buttons_main
        )

# Handlers
application.add_handler(CommandHandler('start', start))
application.add_handler(CallbackQueryHandler(button))
