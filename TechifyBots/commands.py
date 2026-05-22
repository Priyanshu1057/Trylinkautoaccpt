import random
from pyrogram import Client, filters, enums
from pyrogram.errors import UserIsBlocked, PeerIdInvalid, InputUserDeactivated
from pyrogram.errors import *
from pyrogram.raw.types import InputPeerUser
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from config import *
import asyncio
from Script import text
from .db import tb
from .fsub import get_fsub

# Secondary bot client — initialized once and reused.
# Used to DM users who have blocked the primary bot.
_second_bot: Client | None = None

async def get_second_bot() -> Client | None:
    global _second_bot
    if not BOT_TOKEN_2:
        return None
    if _second_bot is None or not _second_bot.is_connected:
        _second_bot = Client(
            ":memory:",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN_2
        )
        await _second_bot.start()
    return _second_bot


@Client.on_message(filters.command("start"))
async def start_cmd(client, message):
    if await tb.get_user(message.from_user.id) is None:
        await tb.add_user(message.from_user.id, message.from_user.first_name)
        bot = await client.get_me()
        await client.send_message(
            LOG_CHANNEL,
            text.LOG.format(
                message.from_user.id,
                getattr(message.from_user, "dc_id", "N/A"),
                message.from_user.first_name or "N/A",
                f"@{message.from_user.username}" if message.from_user.username else "N/A",
                bot.username
            )
        )
    if IS_FSUB and not await get_fsub(client, message): return
    await message.reply_photo(
        photo=random.choice(PICS),
        caption=text.START.format(message.from_user.mention),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('⇆ 𝖠𝖽𝖽 𝖬𝖾 𝖳𝗈 𝖸𝗈𝗎𝗋 𝖦𝗋𝗈𝗎𝗉 ⇆', url=f"https://telegram.me/QuickAcceptBot?startgroup=true&admin=invite_users")],
            [InlineKeyboardButton('ℹ️ 𝖠𝖻𝗈𝗎𝗍', callback_data='about'),
             InlineKeyboardButton('📚 𝖧𝖾𝗅𝗉', callback_data='help')],
            [InlineKeyboardButton('⇆ 𝖠𝖽𝖽 𝖬𝖾 𝖳𝗈 𝖸𝗈𝗎𝗋 𝖢𝗁𝖺𝗇𝗇𝖾𝗅 ⇆', url=f"https://telegram.me/QuickAcceptBot?startchannel=true&admin=invite_users")]
            ])
        )

@Client.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message):
    reply = await message.reply(
        text=("❓ <b>𝘏𝘢𝘷𝘪𝘯𝘨 𝘛𝘳𝘰𝘶𝘣𝘭𝘦?</b>\n\n𝘐𝘧 𝘺𝘰𝘶'𝘳𝘦 𝘧𝘢𝘤𝘪𝘯𝘨 𝘢𝘯𝘺 𝘱𝘳𝘰𝘣𝘭𝘦𝘮 𝘸𝘩𝘪𝘭𝘦 𝘶𝘴𝘪𝘯𝘨 𝘵𝘩𝘦 𝘣𝘰𝘵 𝘰𝘳 𝘪𝘵𝘴 𝘤𝘰𝘮𝘮𝘢𝘯𝘥𝘴, 𝘱𝘭𝘦𝘢𝘴𝘦 𝘸𝘢𝘵𝘤𝘩 𝘵𝘩𝘦 𝘵𝘶𝘵𝘰𝘳𝘪𝘢𝘭 𝘷𝘪𝘥𝘦𝘰 𝘣𝘦𝘭𝘰𝘸.\n\n🎥 𝘛𝘩𝘦 𝘷𝘪𝘥𝘦𝘰 𝘸𝘪𝘭𝘭 𝘤𝘭𝘦𝘢𝘳𝘭𝘺 𝘦𝘹𝘱𝘭𝘢𝘪𝘯 𝘩𝘰𝘸 𝘵𝘰 𝘶𝘴𝘦 𝘦𝘢𝘤𝘩 𝘧𝘦𝘢𝘵𝘶𝘳𝘦 𝘸𝘪𝘵𝘩 𝘦𝘢𝘴𝘦.\n\n💖 𝘍𝘰𝘳 𝘮𝘰𝘳𝘦 𝘶𝘱𝘥𝘢𝘵𝘦𝘴 — <b><a href='https://techifybots.github.io/PayWeb/'>𝘚𝘶𝘱𝘱𝘰𝘳𝘵 𝘜𝘴.</a></b>"
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 𝘞𝘢𝘵𝘤𝘩 𝘛𝘶𝘵𝘰𝘳𝘪𝘢𝘭", url="https://youtu.be/_n3V0gFZMh8")]
        ])
    )
    await asyncio.sleep(300)
    await reply.delete()
    try:
        await message.delete()
    except:
        pass

@Client.on_message(filters.command('accept') & filters.private)
async def accept(client, message):
    show = await message.reply("**Please Wait.....**")
    user_data = await tb.get_session(message.from_user.id)
    if user_data is None:
        return await show.edit("**To accept join requests, please /login first.**")
    try:
        acc = Client("joinrequest", session_string=user_data, api_id=API_ID, api_hash=API_HASH)
        await acc.connect()
    except:
        return await show.edit("**Your login session has expired. Use /logout first, then /login again.**")
    await show.edit("**Forward a message from your Channel or Group (with forward tag).\n\nMake sure your logged-in account is an admin there with full rights.**")
    fwd_msg = await client.listen(message.chat.id)
    if fwd_msg.forward_from_chat and fwd_msg.forward_from_chat.type not in [enums.ChatType.PRIVATE, enums.ChatType.BOT]:
        chat_id = fwd_msg.forward_from_chat.id
        try:
            info = await acc.get_chat(chat_id)
        except:
            return await show.edit("**Error: Ensure your account is admin in this Channel/Group with required rights.**")
    else:
        return await message.reply("**Message not forwarded from a valid Channel/Group.**")
    await fwd_msg.delete()
    msg = await show.edit("**Accepting all join requests... Please wait.**")
    try:
        while True:
            await acc.approve_all_chat_join_requests(chat_id)
            await asyncio.sleep(1)
            join_requests = [req async for req in acc.get_chat_join_requests(chat_id)]
            if not join_requests:
                break
        await msg.edit("**✅ Successfully accepted all join requests.**")
    except Exception as e:
        await msg.edit(f"**An error occurred:** `{str(e)}`")

@Client.on_chat_join_request()
async def approve_new(client, m):
    if not NEW_REQ_MODE:
        return
    try:
        await client.approve_chat_join_request(m.chat.id, m.from_user.id)
    except Exception as e:
        print(f"Failed to approve join request: {e}")
        return

    bot_me = await client.get_me()
    bot_username = bot_me.username

    # The join request event provides the user's access_hash.
    # We store it here so the secondary bot can also use it directly
    # without needing the user to have ever started Bot 2.
    user_id = m.from_user.id
    access_hash = m.from_user.access_hash

    try:
        # Pyrogram MTProto has the access_hash from the event — DM works
        # even if the user never pressed /start on the bot.
        await client.send_message(
            user_id,
            text.ACCEPTED.format(m.from_user.mention, m.chat.title)
        )
    except UserIsBlocked:
        # Primary bot is blocked. Try the secondary bot using the
        # access_hash from the join request so it can reach the user
        # without them having started Bot 2.
        second_bot = await get_second_bot()
        if second_bot:
            try:
                # Build the peer directly with the access_hash we already have
                peer = InputPeerUser(user_id=user_id, access_hash=access_hash)
                second_me = await second_bot.get_me()
                await second_bot.send_message(
                    peer,
                    text.ACCEPTED_BLOCKED.format(
                        m.from_user.mention,
                        m.chat.title,
                        bot_username,
                        second_me.username
                    )
                )
                try:
                    await client.send_message(
                        LOG_CHANNEL,
                        f"🚫 <b>Primary Bot Blocked — Secondary Bot Sent DM Successfully</b>\n\n"
                        f"👤 User: {m.from_user.mention} (<code>{user_id}</code>)\n"
                        f"🔗 Username: @{m.from_user.username or 'N/A'}\n"
                        f"📢 Chat: <b>{m.chat.title}</b> (<code>{m.chat.id}</code>)"
                    )
                except Exception:
                    pass
            except Exception as e:
                print(f"Secondary bot also failed: {e}")
                try:
                    await client.send_message(
                        LOG_CHANNEL,
                        f"🚫 <b>Both Bots Failed to DM User</b>\n\n"
                        f"👤 User: {m.from_user.mention} (<code>{user_id}</code>)\n"
                        f"🔗 Username: @{m.from_user.username or 'N/A'}\n"
                        f"📢 Chat: <b>{m.chat.title}</b> (<code>{m.chat.id}</code>)\n\n"
                        f"❌ Error: {e}"
                    )
                except Exception:
                    pass
        else:
            try:
                await client.send_message(
                    LOG_CHANNEL,
                    f"🚫 <b>User Blocked the Bot — No Secondary Bot Configured</b>\n\n"
                    f"👤 User: {m.from_user.mention} (<code>{user_id}</code>)\n"
                    f"🔗 Username: @{m.from_user.username or 'N/A'}\n"
                    f"📢 Chat: <b>{m.chat.title}</b> (<code>{m.chat.id}</code>)\n\n"
                    f"ℹ️ Set BOT_TOKEN_2 env variable to enable secondary bot fallback."
                )
            except Exception:
                pass
    except Exception as e:
        print(f"Failed to send welcome message: {e}")
