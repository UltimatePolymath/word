# Credit: @Ishikki_Akabane

import io
import os
import textwrap
import traceback
from contextlib import redirect_stdout

from shivu import application, LOGGER
from shivu.archive.sudo import check_user_permission
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler

namespaces = {}

def namespace_of(chat, update, bot):
    """Create or retrieve a namespace for the chat."""
    if chat not in namespaces:
        namespaces[chat] = {
            "__builtins__": globals()["__builtins__"],
            "bot": bot,
            "effective_message": update.effective_message,
            "effective_user": update.effective_user,
            "effective_chat": update.effective_chat,
            "update": update,
        }
    return namespaces[chat]

def log_input(update):
    """Log the input command for debugging."""
    user = update.effective_user.id
    chat = update.effective_chat.id
    LOGGER.info(f"IN: {update.effective_message.text} (user={user}, chat={chat})")

async def send(msg, bot, update):
    """Send a message or file to the chat."""
    if len(str(msg)) > 2000:
        with io.BytesIO(str.encode(msg)) as out_file:
            out_file.name = "output.txt"
            await bot.send_document(
                chat_id=update.effective_chat.id,
                document=out_file,
                message_thread_id=update.effective_message.message_thread_id if update.effective_chat.is_forum else None
            )
    else:
        LOGGER.info(f"OUT: '{msg}'")
        await bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"`{msg}`",
            parse_mode=ParseMode.MARKDOWN,
            message_thread_id=update.effective_message.message_thread_id if update.effective_chat.is_forum else None
        )

def cleanup_code(code):
    """Clean up code by removing markdown formatting."""
    if code.startswith("```") and code.endswith("```"):
        return "\n".join(code.split("\n")[1:-1])
    return code.strip("` \n")

async def do(func, bot, update):
    """Execute or evaluate the provided code."""
    log_input(update)
    content = update.message.text.split(" ", 1)[-1]
    body = cleanup_code(content)
    env = namespace_of(update.message.chat_id, update, bot)

    os.chdir(os.getcwd())
    with open("temp.txt", "w") as temp:
        temp.write(body)

    stdout = io.StringIO()
    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

    try:
        exec(to_compile, env)
    except Exception as e:
        return f"{e.__class__.__name__}: {e}"

    func = env["func"]

    try:
        with redirect_stdout(stdout):
            func_return = await func()
    except Exception as e:
        value = stdout.getvalue()
        return f"{value}{traceback.format_exc()}"
    else:
        value = stdout.getvalue()
        result = None
        if func_return is None:
            if value:
                result = f"{value}"
            else:
                try:
                    result = f"{repr(eval(body, env))}"
                except:
                    pass
        else:
            result = f"{value}{func_return}"
        if result:
            return result

async def evaluate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Evaluate a Python expression, restricted to superuser."""
    user_id = update.effective_user.id
    user_role = await check_user_permission(user_id)
    if user_role != "superuser":
        LOGGER.warning(f"User {user_id} denied access to /eval (role: {user_role or 'None'})")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    bot = context.bot
    LOGGER.info(f"User {user_id} (role: superuser) executed /eval: {update.effective_message.text}")
    await send(await do(eval, bot, update), bot, update)

async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute Python code, restricted to superuser."""
    user_id = update.effective_user.id
    user_role = await check_user_permission(user_id)
    if user_role != "superuser":
        LOGGER.warning(f"User {user_id} denied access to /exec (role: {user_role or 'None'})")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    bot = context.bot
    LOGGER.info(f"User {user_id} (role: superuser) executed /exec: {update.effective_message.text}")
    await send(await do(exec, bot, update), bot, update)

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear the local namespace, restricted to superuser."""
    user_id = update.effective_user.id
    user_role = await check_user_permission(user_id)
    if user_role != "superuser":
        LOGGER.warning(f"User {user_id} denied access to /clearlocals (role: {user_role or 'None'})")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    bot = context.bot
    log_input(update)
    global namespaces
    if update.message.chat_id in namespaces:
        del namespaces[update.message.chat_id]
    LOGGER.info(f"User {user_id} (role: superuser) cleared locals in chat {update.message.chat_id}")
    await send("Cleared locals.", bot, update)

# Register handlers
EVAL_HANDLER = CommandHandler(("e", "ev", "eva", "eval"), evaluate, block=False)
EXEC_HANDLER = CommandHandler(("x", "ex", "exe", "exec", "py"), execute, block=False)
CLEAR_HANDLER = CommandHandler("clearlocals", clear, block=False)

application.add_handler(EVAL_HANDLER)
application.add_handler(EXEC_HANDLER)
application.add_handler(CLEAR_HANDLER)
