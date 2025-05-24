import random
from html import escape
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from shivu import application, SUPPORT_CHAT, UPDATE_CHAT, BOT_USERNAME, db, GROUP_ID
from shivu import pm_users as collection

# Small caps converter
def to_small_caps(text: str) -> str:
    normal = "abcdefghijklmnopqrstuvwxyz"
    smallcaps = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    return ''.join(smallcaps[normal.index(c)] if c in normal else c for c in text.lower())

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
    else:
        if user_data['first_name'] != first_name or user_data['username'] != username:
            await collection.update_one({"_id": user_id}, {"$set": {"first_name": first_name, "username": username}})

    caption = """🍂 ɢʀᴇᴇᴛɪɴɢs, ɪ'ᴍ ⟦ 𝕾𝖎𝖓 ☒ 𝕮𝖆𝖙𝖈𝖍𝖊𝖗 ⟧, ɴɪᴄᴇ ᴛᴏ ᴍᴇᴇᴛ ʏᴏᴜ!
━━━━━━━▧▣▧━━━━━━━
⦾ ᴡʜᴀᴛ ɪ ᴅᴏ: ɪ sᴘᴀᴡɴ   
     ωαιƒυ ɪɴ ʏᴏᴜʀ ᴄʜᴀᴛ ғᴏʀ
     ᴜsᴇʀs ᴛᴏ ɢʀᴀʙ.
⦾ ᴛᴏ ᴜsᴇ ᴍᴇ: ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ
     ɢʀᴏᴜᴘ ᴀɴᴅ ᴛᴀᴘ ᴛʜᴇ ʜᴇʟᴘ
     ʙᴜᴛᴛᴏɴ ғᴏʀ ᴅᴇᴛᴀɪʟs.
━━━━━━━▧▣▧━━━━━━━"""

    buttons = [
        [InlineKeyboardButton("☊ " + to_small_caps("Add Me"), url=f'http://t.me/{BOT_USERNAME}?startgroup=new'),
         InlineKeyboardButton("⚙ " + to_small_caps("Help"), callback_data='help')],
        [InlineKeyboardButton("✦ " + to_small_caps("Support"), url=f'https://t.me/{SUPPORT_CHAT}'),
         InlineKeyboardButton("☍ " + to_small_caps("Updates"), url=f'https://t.me/{UPDATE_CHAT}')],
        [InlineKeyboardButton("⌬ " + to_small_caps("Source"), url='https://youtu.be/dQw4w9WgXcQ?si=NvUDu8RN78zX_VEJ')]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo="https://i.ibb.co/k61RdYyz/tmporofsr6m.jpg",
        caption=caption,
        reply_markup=reply_markup
    )

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'help':
        help_text = """
***Help Section:***

› /guess – Guess character (only in groups)  
› /fav – Add to favorites  
› /trade – Trade characters  
› /gift – Gift characters to another user  
› /collection – See your collection  
› /topgroups – Groups with most activity  
› /top – Top users  
› /ctop – Your chat top  
› /changetime – Change spawn time (group only)
"""
        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("↶ " + to_small_caps("Back"), callback_data='back')]])
        await context.bot.edit_message_caption(
            chat_id=update.effective_chat.id,
            message_id=query.message.message_id,
            caption=help_text,
            reply_markup=back_markup
        )

    elif query.data == 'back':
        await start(update, context)

# Add handlers to application
application.add_handler(CommandHandler('start', start))
application.add_handler(CallbackQueryHandler(button))
