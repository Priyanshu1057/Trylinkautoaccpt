from pyrogram import Client
from pyrogram.types import ChatJoinRequest
from config import API_ID, API_HASH, BOT_TOKEN_2

# List of all running secondary bot clients.
# Index 0 = first fallback, index 1 = second fallback, etc.
secondary_bots: list[Client] = []


def _make_client(token: str, name: str) -> Client:
    bot = Client(
        name,
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=token,
        workers=100,
        sleep_threshold=15,
    )

    @bot.on_chat_join_request()
    async def cache_peer(client: Client, m: ChatJoinRequest) -> None:
        # Receiving this event caches the user's peer (access_hash) in this
        # bot's session so it can DM them later.
        # Bot MUST be added as admin (Invite Users) to the same channels/groups.
        pass

    return bot


async def start_extra_bot(token: str) -> Client | None:
    """Start a single extra bot and append it to secondary_bots. Returns the client."""
    try:
        bot = _make_client(token, f":memory:_{len(secondary_bots)}")
        await bot.start()
        me = await bot.get_me()
        secondary_bots.append(bot)
        print(f"Extra bot started: @{me.username}")
        return bot
    except Exception as e:
        print(f"Failed to start extra bot: {e}")
        return None


async def stop_extra_bot(token: str) -> bool:
    """Stop and remove a secondary bot by its token."""
    global secondary_bots
    for i, bot in enumerate(secondary_bots):
        # Each bot stores its token so we can match it
        if getattr(bot, "_token", None) == token:
            try:
                await bot.stop()
            except Exception:
                pass
            secondary_bots.pop(i)
            return True
    return False


async def init_secondary_bots() -> None:
    """Called at startup — loads all saved tokens from DB and starts them."""
    from .db import tb

    # BOT_TOKEN_2 env var (legacy support)
    if BOT_TOKEN_2:
        await start_extra_bot(BOT_TOKEN_2)

    # Tokens stored via /addbot command
    saved = await tb.get_all_extra_bots()
    for entry in saved:
        token = entry.get("token", "")
        if token and token != BOT_TOKEN_2:
            await start_extra_bot(token)
