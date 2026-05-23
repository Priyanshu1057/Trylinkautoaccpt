from pyrogram import Client
from pyrogram.types import ChatJoinRequest
from config import API_ID, API_HASH, BOT_TOKEN_2

second_bot: Client | None = None

async def init_second_bot() -> None:
    global second_bot
    if not BOT_TOKEN_2:
        return

    second_bot = Client(
        "techifybots_second",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN_2,
        workers=100,
        sleep_threshold=15,
    )

    # Registering this handler causes Pyrogram to cache every requesting
    # user's peer (user_id + access_hash) inside second_bot's session storage.
    # Once cached, second_bot can DM that user at any time — even if they
    # never pressed /start on Bot 2.
    # IMPORTANT: Bot 2 must be added as admin (Invite Users) to the same
    # channels/groups as Bot 1 so it receives these events too.
    @second_bot.on_chat_join_request()
    async def cache_peer(client: Client, m: ChatJoinRequest) -> None:
        pass  # Receiving the event is all that's needed — Pyrogram caches the peer

    await second_bot.start()
    me = await second_bot.get_me()
    print(f"Secondary bot started as {me.first_name} (@{me.username})")
