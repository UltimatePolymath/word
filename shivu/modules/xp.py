"""Module for XP-related Telegram commands in the Shivu bot."""

from pyrogram import filters
from pyrogram.types import Message
from shivu import shivuu, LOGGER
from shivu.archive.xp import get_user_xp, set_user_xp, get_top_xp_users, XPError

@shivuu.on_message(filters.command("xp"))
async def check_xp(_: shivuu, message: Message) -> None:
    """
    Display a user's XP, level, and rank.

    Args:
        _ (shivuu): Pyrogram client instance (unused, for decorator).
        message (Message): The incoming message with the command.
    """
    user_id = message.from_user.id
    try:
        data = await get_user_xp(user_id)
        await message.reply_text(
            f"🧑‍🚀 Your Stats:\n"
            f"Rank: {data['rank']}\n"
            f"Level: {data['level']}\n"
            f"XP: {data['xp']}\n"
            f"XP to Next Level: {data['next_level_xp']}"
        )
    except XPError as e:
        await message.reply_text("😓 Error fetching your stats. Try again later.")
        LOGGER.error(f"XP error for user {user_id}: {e}")

@shivuu.on_message(filters.command("leaderboard"))
async def show_leaderboard(_: shivuu, message: Message) -> None:
    """
    Display the top 10 users by XP with their ranks.

    Args:
        _ (shivuu): Pyrogram client instance (unused, for decorator).
        message (Message): The incoming message with the command.
    """
    try:
        top_users = await get_top_xp_users(10)
        if not top_users:
            await message.reply_text("🏆 No users with XP yet!")
            return
        text = "🏆 Leaderboard:\n"
        for i, user in enumerate(top_users, 1):
            text += f"{i}. User {user['user_id']}: {user['rank']} (Level {user['level']}, {user['xp']} XP)\n"
        await message.reply_text(text)
    except XPError as e:
        await message.reply_text("😓 Error fetching leaderboard. Try again later.")
        LOGGER.error(f"Leaderboard error: {e}")

@shivuu.on_message(filters.command("setxp"))
async def set_xp_command(_: shivuu, message: Message) -> None:
    """
    Set a user's XP (sudo only).

    Usage: /setxp <user_id> <xp>

    Args:
        _ (shivuu): Pyrogram client instance (unused, for decorator).
        message (Message): The incoming message with the command.
    """
    user_id = message.from_user.id
    try:
        if len(message.command) != 3:
            await message.reply_text("Usage: /setxp <user_id> <xp>")
            return

        target_user_id = int(message.command[1])
        xp = int(message.command[2])

        data = await set_user_xp(user_id, xp)  # Checks sudo permissions
        await message.reply_text(
            f"✅ Set XP for user {target_user_id}:\n"
            f"Rank: {data['rank']}\n"
            f"Level: {data['level']}\n"
            f"XP: {data['xp']}"
        )
    except ValueError as e:
        await message.reply_text(f"Invalid input: {e}")
    except XPError as e:
        await message.reply_text("😓 Error setting XP. Try again later.")
        LOGGER.error(f"Set XP error for user {user_id}: {e}")
