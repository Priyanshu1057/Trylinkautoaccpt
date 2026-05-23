from pyrogram import Client, filters
from pyrogram.types import Message
from config import ADMIN, API_ID, API_HASH
from .db import tb
from .second import secondary_bots, start_extra_bot, stop_extra_bot


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

    # Validate token by connecting briefly
    try:
        test = Client(":memory:", api_id=API_ID, api_hash=API_HASH, bot_token=token)
        await test.start()
        me = await test.get_me()
        await test.stop()
    except Exception as e:
        return await msg.edit(f"❌ **Invalid token or failed to connect.**\n\n`{e}`")

    await msg.edit(f"✅ Token valid — @{me.username}\n⏳ **Saving and starting...**")

    # Upsert into DB (handles both new and retry-after-failure cases)
    db_error = await tb.upsert_extra_bot(token, me.username)
    if db_error is not None:
        return await msg.edit(
            f"❌ **Failed to save @{me.username} to database.**\n\n"
            f"**Error:** `{db_error}`\n\n"
            f"Check your `DB_URI` / MongoDB connection and try again."
        )

    # Check if already running (user may be retrying after a crash)
    already_running = any(
        getattr(b, "_extra_token", None) == token and b.is_connected
        for b in secondary_bots
    )

    if already_running:
        return await msg.edit(
            f"ℹ️ **@{me.username} is already running.**\n\n"
            f"🔢 Total secondary bots: `{len(secondary_bots)}`"
        )

    # Start it live — no restart needed
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
            f"⚠️ **@{me.username} saved to DB but failed to start live.**\n\n"
            f"Possible reasons:\n"
            f"• Bot token was recently revoked\n"
            f"• Pyrogram session conflict\n\n"
            f"It will retry automatically on next restart."
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
