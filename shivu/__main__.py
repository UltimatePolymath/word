import importlib
import time
import random
import re
import asyncio
from html import escape 
from threading import Thread
from flask import Flask
import pyrogram
from pyrogram import Client, filters
from pyrogram.enums import ChatAction
import wordfreq
import nltk
from nltk.corpus import words
import json
import os
import aiofiles
from typing import Dict, Set, Optional
from datetime import datetime
from dotenv import load_dotenv
from pyrogram.errors import FloodWait

import nest_asyncio
nest_asyncio.apply()
flask_app = Flask(__name__)

# Download NLTK words corpus if not already present
try:
    nltk.data.find('corpora/words')
except LookupError:
    try:
        nltk.download('words')
    except Exception as e:
        print(f"Failed to download NLTK words corpus: {e}")

# Load environment variables
load_dotenv()
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
LOG_CHAT_ID = int(os.getenv("LOG_CHAT_ID", "0"))

# Authorized user IDs
ADMIN_IDS = {678309690, 7360592638}
GAME_BOT_ID = 840338206  # User ID for game bot responses

# Initialize Pyrogram client
app = Client(
    "word_game_group",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# Data structures
enabled_chats: Dict[int, Dict[str, any]] = {}  # chat_id -> {alias, name, case}
used_words: Dict[int, Set[str]] = {}  # chat_id -> set of used words
last_prompt: Dict[int, Dict[str, any]] = {}  # chat_id -> {start_letter, min_length}
CONFIG_FILE = "chat_config.json"
last_bot_message_id: Dict[int, int] = {}  # Track last bot message ID per chat
INITIALIZED = False  # Flag to ensure load_config runs only once

@flask_app.route("/")
def index():
    return "Shivu Daemon Running on 7860"

def run_flask():
    flask_app.run(host="0.0.0.0", port=7860, debug=False, use_reloader=False)

# Function to load chat config
async def load_config():
    global enabled_chats, used_words
    if os.path.exists(CONFIG_FILE):
        try:
            async with aiofiles.open(CONFIG_FILE, 'r') as f:
                data = json.loads(await f.read())
                enabled_chats = {int(k): v for k, v in data.get('enabled_chats', {}).items()}
                used_words = {int(k): set(v) for k, v in data.get('used_words', {}).items()}
        except Exception as e:
            await safe_send_message(LOG_CHAT_ID, f"Failed to load config: {e}")
            enabled_chats = {}
            used_words = {}
    else:
        enabled_chats = {}
        used_words = {}

# Function to save chat config
async def save_config():
    try:
        async with aiofiles.open(CONFIG_FILE, 'w') as f:
            await f.write(json.dumps({
                'enabled_chats': enabled_chats,
                'used_words': {k: list(v) for k, v in used_words.items()}
            }))
    except Exception as e:
        await safe_send_message(LOG_CHAT_ID, f"Failed to save config: {e}")

# Function to generate 4-digit alias
def generate_alias() -> str:
    return str(random.randint(1000, 9999))

# Function for safe message sending with flood control
async def safe_send_message(chat_id, text, **kwargs):
    try:
        message = await app.send_message(chat_id, text, **kwargs)
        if chat_id in enabled_chats and 'disable_notification' in kwargs and kwargs['disable_notification']:
            last_bot_message_id[chat_id] = message.id
        return message
    except FloodWait as e:
        await asyncio.sleep(e.x)
        message = await app.send_message(chat_id, text, **kwargs)
        if chat_id in enabled_chats and 'disable_notification' in kwargs and kwargs['disable_notification']:
            last_bot_message_id[chat_id] = message.id
        return message
    except Exception as e:
        print(f"Error sending message to {chat_id}: {e}")
        if chat_id != LOG_CHAT_ID:
            await safe_send_message(LOG_CHAT_ID, f"Error sending message to {chat_id}: {e}")
        return None

# Function to log rejected words to rejections.txt
async def log_rejected_word(chat_id: int, word: str, reason: str):
    """
    Append a rejected word to rejections.txt with timestamp, chat ID, and reason.
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] Chat ID: {chat_id}, Word: {word}, Reason: {reason}\n"
        async with aiofiles.open("rejections.txt", "a") as f:
            await f.write(log_entry)
    except Exception as e:
        await safe_send_message(LOG_CHAT_ID, f"Failed to log rejected word '{word}' to rejections.txt: {e}")

# Function to retrieve game word
async def get_game_word(start_letter: str, min_length: int, chat_id: int, case: str) -> Optional[str]:
    """
    Get a word starting with start_letter, at least min_length, for the given chat.
    Case 1: Use wordfreq (highest frequency).
    Case 4: Try words ending with x, then z, then y with freq >= 0.000001, else any word ending with x,y,z, else any word.
    Avoid chat-specific duplicates. Capitalize first letter for output.
    """
    if chat_id not in used_words:
        used_words[chat_id] = set()
    
    # Get wordfreq words
    wordfreq_words = wordfreq.top_n_list('en', 321180)
    matching_words = [
        word for word in wordfreq_words
        if len(word) >= min_length
        and word.lower().startswith(start_letter.lower())
        and re.match(r'^[a-zA-Z]+$', word)
        and word.lower() not in used_words[chat_id]
    ]
    
    if matching_words:
        if case == '1':
            # Case 1: Pick highest frequency word
            word_freq = [(word, wordfreq.word_frequency(word.lower(), 'en')) for word in matching_words]
            if not word_freq:
                await safe_send_message(LOG_CHAT_ID, f"No wordfreq words meet min_length {min_length} for '{start_letter}' in chat {chat_id}")
                return None
            word_freq.sort(key=lambda x: x[1], reverse=True)
            selected_word = word_freq[0][0]
            frequency = word_freq[0][1]
            used_words[chat_id].add(selected_word.lower())
            await save_config()
            await safe_send_message(LOG_CHAT_ID, f"Sent word (Case 1): {selected_word} (length={len(selected_word)}, freq={frequency:.6f}) to chat {chat_id} ({enabled_chats[chat_id]['name']})")
            return selected_word[0].upper() + selected_word[1:].lower()
        elif case == '4':
            target_end_letters = ['x', 'z', 'y']
            # Phase 1: Try words with freq >= 0.000001 ending with 'x', 'z', 'y'
            for end_letter in target_end_letters:
                valid_words = [
                    (word, wordfreq.word_frequency(word.lower(), 'en'))
                    for word in matching_words
                    if word.lower().endswith(end_letter)
                    and wordfreq.word_frequency(word.lower(), 'en') >= 0.000001
                ]
                if valid_words:
                    valid_words.sort(key=lambda x: x[1], reverse=True)  # Highest frequency first
                    selected_word = valid_words[0][0]
                    frequency = valid_words[0][1]
                    used_words[chat_id].add(selected_word.lower())
                    await save_config()
                    await safe_send_message(LOG_CHAT_ID, f"Sent word (Case 4, ends with {end_letter}, freq >= 0.000001): {selected_word} (length={len(selected_word)}, freq={frequency:.6f}) to chat {chat_id} ({enabled_chats[chat_id]['name']})")
                    return selected_word[0].upper() + selected_word[1:].lower()
            
            # Phase 2: No high-freq words found, try any word ending with 'x', 'y', 'z'
            for end_letter in ['x', 'y', 'z']:  # Different order for fallback
                valid_words = [
                    (word, wordfreq.word_frequency(word.lower(), 'en'))
                    for word in matching_words
                    if word.lower().endswith(end_letter)
                ]
                if valid_words:
                    valid_words.sort(key=lambda x: x[1], reverse=True)
                    selected_word = valid_words[0][0]
                    frequency = valid_words[0][1]
                    used_words[chat_id].add(selected_word.lower())
                    await save_config()
                    await safe_send_message(LOG_CHAT_ID, f"Sent word (Case 4, ends with {end_letter}, any freq): {selected_word} (length={len(selected_word)}, freq={frequency:.6f}) to chat {chat_id} ({enabled_chats[chat_id]['name']})")
                    return selected_word[0].upper() + selected_word[1:].lower()
            
            # Fallback: Any word matching start_letter and min_length
            word_freq = [(word, wordfreq.word_frequency(word.lower(), 'en')) for word in matching_words]
            if word_freq:
                word_freq.sort(key=lambda x: x[1], reverse=True)
                selected_word = word_freq[0][0]
                frequency = word_freq[0][1]
                used_words[chat_id].add(selected_word.lower())
                await save_config()
                await safe_send_message(LOG_CHAT_ID, f"Sent word (Case 4, fallback): {selected_word} (length={len(selected_word)}, freq={frequency:.6f}) to chat {chat_id} ({enabled_chats[chat_id]['name']})")
                return selected_word[0].upper() + selected_word[1:].lower()
    
    await safe_send_message(LOG_CHAT_ID, f"No valid wordfreq word found for '{start_letter}' with min length {min_length} in chat {chat_id} ({enabled_chats[chat_id]['name']})")
    return None

# Command handler: Enable chat
@app.on_message(filters.command("on"))
async def enable_chat(client, message):
    if message.from_user.id not in ADMIN_IDS:
        print(f"Unauthorized /on attempt by user {message.from_user.id}")
        return
    if len(message.command) != 3:
        await safe_send_message(LOG_CHAT_ID, "Usage: /on {chat_id} {case}")
        return
    try:
        chat_id = int(message.command[1])
        case = message.command[2]
        if case not in ['1', '4']:
            await safe_send_message(LOG_CHAT_ID, f"Failed to enable chat {chat_id}: Invalid case {case}")
            return
        if chat_id not in enabled_chats:
            chat = await client.get_chat(chat_id)
            chat_name = chat.title if chat.type in ["group", "supergroup"] else chat.username or f"{chat.first_name or ''} {chat.last_name or ''}".strip()
            alias = generate_alias()
            enabled_chats[chat_id] = {"alias": alias, "name": chat_name, "case": case}
            used_words[chat_id] = set()
            await save_config()
            log_message = f"Enabled chat {chat_id} ({chat_name}) with alias {alias}, case {case}"
            if case == '4':
                log_message += " (XYZ Priority Mode)"
            await safe_send_message(LOG_CHAT_ID, log_message)
        else:
            await safe_send_message(LOG_CHAT_ID, f"Chat {chat_id} ({enabled_chats[chat_id]['name']}) is already enabled with alias {enabled_chats[chat_id]['alias']}, case {enabled_chats[chat_id]['case']}")
    except (ValueError, pyrogram.errors.exceptions.bad_request_400.PeerIdInvalid):
        await safe_send_message(LOG_CHAT_ID, f"Failed to enable chat: Invalid chat ID {message.command[1]}")

# Command handler: Disable chat
@app.on_message(filters.command("off"))
async def disable_chat(client, message):
    if message.from_user.id not in ADMIN_IDS:
        print(f"Unauthorized /off attempt by user {message.from_user.id}")
        return
    if len(message.command) != 2:
        await safe_send_message(LOG_CHAT_ID, "Usage: /off {chat_id}")
        return
    try:
        chat_id = int(message.command[1])
        if chat_id in enabled_chats:
            alias = enabled_chats[chat_id]["alias"]
            name = enabled_chats[chat_id]["name"]
            case = enabled_chats[chat_id]["case"]
            enabled_chats.pop(chat_id)
            used_words.pop(chat_id, None)
            last_prompt.pop(chat_id, None)
            await save_config()
            await safe_send_message(LOG_CHAT_ID, f"Disabled chat {chat_id} ({name}) with alias {alias}, case {case}")
        else:
            await safe_send_message(LOG_CHAT_ID, f"Failed to disable chat {chat_id}: Not enabled")
    except ValueError:
        await safe_send_message(LOG_CHAT_ID, f"Failed to disable chat: Invalid chat ID {message.command[1]}")

# Command handler: Clear used words
@app.on_message(filters.command("clear"))
async def clear_words(client, message):
    if message.from_user.id not in ADMIN_IDS:
        print(f"Unauthorized /clear attempt by user {message.from_user.id}")
        return
    if len(message.command) != 2:
        await safe_send_message(LOG_CHAT_ID, "Usage: /clear {chat_id}")
        return
    try:
        chat_id = int(message.command[1])
        if chat_id in enabled_chats:
            used_words[chat_id] = set()
            await save_config()
            await safe_send_message(LOG_CHAT_ID, f"Cleared used words for chat {chat_id} ({enabled_chats[chat_id]['name']}) with alias {enabled_chats[chat_id]['alias']}, case {enabled_chats[chat_id]['case']}")
        else:
            await safe_send_message(LOG_CHAT_ID, f"Failed to clear words for chat {chat_id}: Not enabled")
    except ValueError:
        await safe_send_message(LOG_CHAT_ID, f"Failed to clear words: Invalid chat ID {message.command[1]}")

# Command handler: Show enabled chats
@app.on_message(filters.command("runs"))
async def show_enabled_chats(client, message):
    if message.from_user.id not in ADMIN_IDS:
        print(f"Unauthorized /runs attempt by user {message.from_user.id}")
        return
    if enabled_chats:
        response = "Enabled chats:\n"
        for chat_id, info in enabled_chats.items():
            response += f"Chat ID: {chat_id}, Name: {info['name']}, Alias: {info['alias']}, Case: {info['case']}\n"
        await safe_send_message(LOG_CHAT_ID, f"Listed enabled chats:\n{response}")
    else:
        await safe_send_message(LOG_CHAT_ID, "No chats are enabled")

# Command handler: Show used words
@app.on_message(filters.command("usedwords"))
async def show_used_words(client, message):
    if message.from_user.id not in ADMIN_IDS:
        print(f"Unauthorized /usedwords attempt by user {message.from_user.id}")
        return
    if len(message.command) != 2:
        await safe_send_message(LOG_CHAT_ID, "Usage: /usedwords {chat_id}")
        return
    try:
        chat_id = int(message.command[1])
        if chat_id in enabled_chats:
            if chat_id in used_words and used_words[chat_id]:
                words_list = sorted(list(used_words[chat_id]))
                response = f"Used words for chat {chat_id} ({enabled_chats[chat_id]['name']}, case {enabled_chats[chat_id]['case']}):\n" + ", ".join(words_list)
            else:
                response = f"No used words for chat {chat_id} ({enabled_chats[chat_id]['name']}, case {enabled_chats[chat_id]['case']})"
            await safe_send_message(LOG_CHAT_ID, response)
        else:
            await safe_send_message(LOG_CHAT_ID, f"Failed to show used words: Chat {chat_id} is not enabled")
    except ValueError:
        await safe_send_message(LOG_CHAT_ID, f"Failed to show used words: Invalid chat ID {message.command[1]}")

# Game message handler
@app.on_message(filters.text & filters.group)
async def handle_game_message(client, message):
    chat_id = message.chat.id
    if chat_id not in enabled_chats:
        return
    
    # Pattern for game prompt
    prompt_pattern = r"Turn: X @ja \(Next: .+?\)\nYour word must start with (\w) and include at least (\d+) letters\."
    # Pattern for invalid word reply
    invalid_pattern = r"^(\w+) is not in my list of words$"
    # Pattern for accepted word reply
    accepted_pattern = r"^(\w+) is accepted$"
    # Pattern for word already used
    used_pattern = r"^(\w+) has been used$"
    
    # Clean message text and add words to used_words
    if message.text:
        cleaned_text = re.sub(r'[^a-zA-Z\s]', '', message.text).strip()
        word_list = cleaned_text.split()  # Fix naming conflict
        for word in word_list:
            if word and word.lower() not in used_words.get(chat_id, set()):
                used_words[chat_id].add(word.lower())
                await save_config()
                await safe_send_message(LOG_CHAT_ID, f"Added word '{word}' to used_words in chat {chat_id} ({enabled_chats[chat_id]['name']})")
    
    if message.text and re.match(prompt_pattern, message.text, re.MULTILINE):
        match = re.match(prompt_pattern, message.text, re.MULTILINE)
        start_letter = match.group(1)
        min_length = int(match.group(2))
        case = enabled_chats[chat_id]['case']
        
        last_prompt[chat_id] = {'start_letter': start_letter, 'min_length': min_length}
        
        try:
            await client.send_chat_action(chat_id, ChatAction.TYPING)
            await asyncio.sleep(1.5)
        except Exception as e:
            await safe_send_message(LOG_CHAT_ID, f"Error sending typing action to {chat_id}: {e}")
        
        word = await get_game_word(start_letter, min_length, chat_id, case)
        if word:
            await safe_send_message(chat_id, word, disable_notification=True)
        else:
            await safe_send_message(LOG_CHAT_ID, f"No valid word found for prompt in chat {chat_id}. Consider clearing used words with /clear.")
    
    elif message.reply_to_message and message.reply_to_message.id == last_bot_message_id.get(chat_id) and message.from_user.id == GAME_BOT_ID:
        cleaned_text = re.sub(r'[^a-zA-Z\s]', '', message.text).strip()
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        invalid_match = re.match(invalid_pattern, cleaned_text)
        accepted_match = re.match(accepted_pattern, cleaned_text)
        used_match = re.match(used_pattern, cleaned_text)
        
        if accepted_match:
            accepted_word = accepted_match.group(1)
            if accepted_word.lower() not in used_words.get(chat_id, set()):
                used_words[chat_id].add(accepted_word.lower())
                await save_config()
                await safe_send_message(LOG_CHAT_ID, f"Word '{accepted_word}' accepted in chat {chat_id} ({enabled_chats[chat_id]['name']})")
            else:
                await safe_send_message(LOG_CHAT_ID, f"Warning: Accepted word '{accepted_word}' was already in used_words for chat {chat_id} ({enabled_chats[chat_id]['name']})")
        
        elif invalid_match or used_match:
            invalid_word = invalid_match.group(1) if invalid_match else used_match.group(1)
            rejection_reason = "not in list" if invalid_match else "already used"
            await log_rejected_word(chat_id, invalid_word, rejection_reason)  # Log to rejections.txt
            await safe_send_message(LOG_CHAT_ID, f"Word '{invalid_word}' rejected ({rejection_reason}) in chat {chat_id} ({enabled_chats[chat_id]['name']}). Retrying with NLTK...")
            
            if chat_id not in last_prompt:
                await safe_send_message(LOG_CHAT_ID, f"No prompt data available for retry in chat {chat_id}. Scanning chat history...")
                try:
                    async for msg in app.get_chat_history(chat_id, limit=20):
                        if msg.text and re.match(prompt_pattern, msg.text, re.MULTILINE):
                            match = re.match(prompt_pattern, msg.text, re.MULTILINE)
                            start_letter = match.group(1)
                            min_length = int(match.group(2))
                            last_prompt[chat_id] = {'start_letter': start_letter, 'min_length': min_length}
                            break
                    else:
                        await safe_send_message(LOG_CHAT_ID, f"Could not find recent prompt for retry in chat {chat_id}")
                        return
                except Exception as e:
                    await safe_send_message(LOG_CHAT_ID, f"Error fetching prompt for retry in chat {chat_id}: {e}")
                    return
            
            start_letter = last_prompt[chat_id]['start_letter']
            min_length = last_prompt[chat_id]['min_length']
            
            try:
                await client.send_chat_action(chat_id, ChatAction.TYPING)
                await asyncio.sleep(1.5)
            except Exception as e:
                await safe_send_message(LOG_CHAT_ID, f"Error sending retry typing action to {chat_id}: {e}")
            
            nltk_word_set = set(words.words())
            nltk_matching_words = [
                word for word in nltk_word_set
                if len(word) >= min_length
                and word.lower().startswith(start_letter.lower())
                and re.match(r'^[a-zA-Z]+$', word)
                and word.lower() not in used_words[chat_id]
            ]
            
            if nltk_matching_words:
                nltk_matching_words.sort()
                selected_word = nltk_matching_words[0]
                if len(selected_word) >= min_length:
                    used_words[chat_id].add(selected_word.lower())
                    await save_config()
                    log_message = f"Sent retry word (NLTK, after '{invalid_word}' rejected as {rejection_reason}): {selected_word} (length={len(selected_word)}) to chat {chat_id} ({enabled_chats[chat_id]['name']})"
                    await safe_send_message(LOG_CHAT_ID, log_message)
                    await safe_send_message(chat_id, selected_word[0].upper() + selected_word[1:].lower(), disable_notification=True)
                else:
                    await safe_send_message(LOG_CHAT_ID, f"Selected NLTK word {selected_word} (length={len(selected_word)}) does not meet min_length {min_length} for retry in chat {chat_id}")
            else:
                await safe_send_message(LOG_CHAT_ID, f"No valid NLTK word found for '{start_letter}' with min length {min_length} in chat {chat_id} ({enabled_chats[chat_id]['name']})")

# Startup handler using raw update
@app.on_raw_update()
async def on_startup(client, update, users, chats):
    global INITIALIZED
    if not INITIALIZED:
        try:
            await load_config()
            await safe_send_message(LOG_CHAT_ID, "Bot started successfully")
            INITIALIZED = True
        except Exception as e:
            print(f"Failed to initialize bot: {e}")
            await safe_send_message(LOG_CHAT_ID, f"Failed to initialize bot: {e}")

def main() -> None:
    """Run bot."""
    print("hello")

if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    print("Bot is running...")
    app.run()  # Replaced hax.start() with app.run()
    print("Bot started")  # Replaced LOGGER.info("Bot started") with print
    main()
