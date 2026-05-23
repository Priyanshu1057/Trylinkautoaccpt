from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN, API_ID, API_HASH
from .db import tb
from .second import secondary_bots, start_extra_bot, stop_extra_bot


@Client.on_message(filters.command("addbot") & filters.private & filters.user(ADMIN))
async def add_bot_cmd(client: Client, message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply(
            "**Usage:** `/addbot <BOT_TOKEN>`\n\n"
            "The new bot must also be added as admin (Invite Users) "
            "to all your channels/groups."
        )

    token = args[1].strip()
    msg = await message.reply("⏳ **Verifying and starting the bot...**")

    # Validate token by connecting
    try:
        test = Client(":memory:", api_id=API_ID, api_hash=API_HASH, bot_token=token)
        await test.start()
        me = await test.get_me()
        await test.stop()
    except Exception as e:
        return await msg.edit(f"❌ **Invalid token or failed to connect.**\n\n`{e}`")

    # Check not already added
    existing = await tb.get_all_extra_bots()
    if any(b["token"] == token for b in existing):
        return await msg.edit(f"⚠️ **@{me.username} is already added as a secondary bot.**")

    # Save to DB
    saved = await tb.add_extra_bot(token, me.username)
    if not saved:
        return await msg.edit("❌ **Failed to save bot to database.**")

    # Start it live (no restart needed)
    bot = await start_extra_bot(token)
    if bot:
        await msg.edit(
            f"✅ **Secondary bot added and started!**\n\n"
            f"🤖 Bot: @{me.username}\n"
            f"🔢 Total secondary bots: `{len(secondary_bots)}`\n\n"
            f"⚠️ **Important:** Add @{me.username} as admin with **Invite Users** "
            f"permission to all your channels/groups so it can DM new members."
        )
    else:
        await msg.edit(
            f"⚠️ **Saved to DB but failed to start live.**\n"
            f"It will start automatically on next restart."
        )


@Client.on_message(filters.command("removebot") & filters.private & filters.user(ADMIN))
async def remove_bot_cmd(client: Client, message: Message) -> None:
    saved = await tb.get_all_extra_bots()
    if not saved:
        return await message.reply("ℹ️ **No secondary bots are configured.**")

    args = message.text.split(maxsplit=1)

    # If no argument, show numbered list and ask which to remove
    if len(args) < 2:
        lines = []
        for i, b in enumerate(saved, 1):
            lines.append(f"{i}. @{b.get('username', 'unknown')}")
        return await message.reply(
            "**Reply with the number of the bot to remove:**\n\n" +
            "\n".join(lines) +
            "\n\n**Usage:** `/removebot <number>`"
        )

    # Accept number (1-based index)
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
            f"✅ **Secondary bot removed.**\n\n"
            f"🤖 Bot: @{username}\n"
            f"🔢 Remaining secondary bots: `{len(secondary_bots)}`"
        )
    else:
        await msg.edit("❌ **Failed to remove from database.**")


@Client.on_message(filters.command("listbots") & filters.private & filters.user(ADMIN))
async def list_bots_cmd(client: Client, message: Message) -> None:
    primary = await client.get_me()
    saved = await tb.get_all_extra_bots()

    lines = [f"🔵 **Primary Bot:** @{primary.username} _(this bot)_\n"]

    if not saved:
        lines.append("➕ No secondary bots added yet.\nUse /addbot to add one.")
    else:
        lines.append(f"**Secondary Bots ({len(saved)}):**")
        for i, b in enumerate(saved, 1):
            username = b.get("username", "unknown")
            # Check if currently running
            running = any(
                True for bot in secondary_bots
                if bot.is_connected
            )
            status = "🟢 running" if running else "🔴 stopped"
            lines.append(f"{i}. @{username} — {status}")

    lines.append(
        "\n📌 Use `/addbot <token>` to add · `/removebot <number>` to remove"
    )

    await message.reply("\n".join(lines))
