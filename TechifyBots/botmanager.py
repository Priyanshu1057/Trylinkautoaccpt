import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from config import ADMIN
from .db import tb
from .second import secondary_bots, start_extra_bot, stop_extra_bot


async def _validate_token(token: str) -> dict | None:
    """
    Validate a bot token via plain HTTP (no Pyrogram session).
    Returns the bot info dict on success, None on failure.
    Does NOT touch the asyncio event loop or MongoDB connection pool.
    """
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data["result"]
    except Exception as e:
        print(f"Token validation HTTP error: {e}")
    return None


@Client.on_message(filters.command("addbot") & filters.private & filters.user(ADMIN))
async def add_bot_cmd(client: Client, message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply(
            "**Usage:** `/addbot <BOT_TOKEN>`\n\n"
            "The new bot must also be added as admin (**Invite Users** permission) "
            "to all your channels/groups."
        )

    token = args[1].strip()
    msg = await message.reply("⏳ **Verifying token...**")

    # Validate via HTTP — no Pyrogram session start/stop, no event loop disruption
    bot_info = await _validate_token(token)
    if not bot_info:
        return await msg.edit(
            "❌ **Invalid token or Telegram API unreachable.**\n\n"
            "Double-check the token and try again."
        )

    username = bot_info.get("username", "unknown")
    await msg.edit(f"✅ Token valid — @{username}\n⏳ **Saving to database...**")

    # Save to DB (upsert — safe to retry)
    db_error = await tb.upsert_extra_bot(token, username)
    if db_error is not None:
        return await msg.edit(
            f"❌ **Failed to save @{username} to database.**\n\n"
            f"**Error:** `{db_error}`\n\n"
            f"Check your `DB_URI` / MongoDB connection and try again."
        )

    await msg.edit(f"✅ Saved — @{username}\n⏳ **Starting bot live...**")

    # Check if already running (user may be retrying after a crash)
    already_running = any(
        getattr(b, "_extra_token", None) == token and b.is_connected
        for b in secondary_bots
    )
    if already_running:
        return await msg.edit(
            f"ℹ️ **@{username} is already running.**\n\n"
            f"🔢 Total secondary bots: `{len(secondary_bots)}`"
        )

    # Start live — no restart needed
    bot = await start_extra_bot(token)
    if bot:
        await msg.edit(
            f"✅ **Secondary bot added and started!**\n\n"
            f"🤖 Bot: @{username}\n"
            f"🔢 Total secondary bots: `{len(secondary_bots)}`\n\n"
            f"⚠️ **Important:** Add @{username} as admin with **Invite Users** "
            f"permission to all your channels/groups so it can DM new members."
        )
    else:
        await msg.edit(
            f"⚠️ **@{username} saved to DB but failed to start live.**\n\n"
            f"It will start automatically on next bot restart.\n"
            f"Make sure the token is not revoked."
        )


@Client.on_message(filters.command("removebot") & filters.private & filters.user(ADMIN))
async def remove_bot_cmd(client: Client, message: Message) -> None:
    saved = await tb.get_all_extra_bots()
    if not saved:
        return await message.reply("ℹ️ **No secondary bots are configured.**")

    args = message.text.split(maxsplit=1)

    # No argument — show numbered list
    if len(args) < 2:
        lines = []
        for i, b in enumerate(saved, 1):
            username = b.get("username", "unknown")
            is_running = any(
                getattr(bot, "_extra_token", None) == b.get("token") and bot.is_connected
                for bot in secondary_bots
            )
            status = "🟢" if is_running else "🔴"
            lines.append(f"{i}. {status} @{username}")
        return await message.reply(
            "**Secondary bots:**\n\n" +
            "\n".join(lines) +
            f"\n\n**Usage:** `/removebot <number>` (1–{len(saved)})"
        )

    # Accept 1-based index
    try:
        index = int(args[1].strip()) - 1
        if index < 0 or index >= len(saved):
            raise ValueError
    except ValueError:
        return await message.reply(
            f"❌ **Invalid number.** Use `/removebot <number>` (1–{len(saved)})."
        )

    entry = saved[index]
    token = entry["token"]
    username = entry.get("username", "unknown")

    msg = await message.reply(f"⏳ **Removing @{username}...**")

    removed_db = await tb.remove_extra_bot(token)
    await stop_extra_bot(token)

    if removed_db:
        await msg.edit(
            f"✅ **@{username} removed.**\n\n"
            f"🔢 Remaining secondary bots: `{len(secondary_bots)}`"
        )
    else:
        await msg.edit(
            f"⚠️ **@{username} was not found in the database.**\n"
            f"It may have already been removed."
        )


@Client.on_message(filters.command("listbots") & filters.private & filters.user(ADMIN))
async def list_bots_cmd(client: Client, message: Message) -> None:
    primary = await client.get_me()
    saved = await tb.get_all_extra_bots()

    lines = [f"🔵 **Primary Bot:** @{primary.username} _(this bot)_\n"]

    if not saved:
        lines.append("➕ No secondary bots added yet.\nUse `/addbot <token>` to add one.")
    else:
        lines.append(f"**Secondary Bots ({len(saved)}):**")
        for i, b in enumerate(saved, 1):
            username = b.get("username", "unknown")
            token = b.get("token", "")
            is_running = any(
                getattr(bot, "_extra_token", None) == token and bot.is_connected
                for bot in secondary_bots
            )
            status = "🟢 running" if is_running else "🔴 stopped"
            lines.append(f"{i}. @{username} — {status}")

    lines.append(
        "\n📌 `/addbot <token>` to add  ·  `/removebot <number>` to remove"
    )

    await message.reply("\n".join(lines))
