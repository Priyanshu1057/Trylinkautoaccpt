import os
from datetime import datetime
from pytz import timezone
from pyrogram import Client
from aiohttp import web
from config import API_ID, API_HASH, BOT_TOKEN, ADMIN, LOG_CHANNEL
from TechifyBots.second import init_second_bot

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route(request):
    return web.Response(text="<h3 align='center'><b>I am Alive</b></h3>", content_type='text/html')

async def web_server():
    app = web.Application(client_max_size=30_000_000)
    app.add_routes(routes)
    return app

class Bot(Client):
    def __init__(self):
        super().__init__(
            "techifybots",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="TechifyBots"),
            workers=200,
            sleep_threshold=15
        )

    async def start(self):
        app = web.AppRunner(await web_server())
        await app.setup()
        try:
            await web.TCPSite(app, "0.0.0.0", int(os.getenv("PORT", 8080))).start()
            print("Web server started.")
        except Exception as e:
            print(f"Web server error: {e}")

        await super().start()
        me = await self.get_me()
        print(f"Primary bot started as {me.first_name}")

        # Start secondary bot (if BOT_TOKEN_2 is set)
        await init_second_bot()

        if isinstance(ADMIN, int):
            try:
                await self.send_message(ADMIN, f"**{me.first_name} is started...**")
            except Exception as e:
                print(f"Error sending message to admin: {e}")
        if LOG_CHANNEL:
            try:
                now = datetime.now(timezone("Asia/Kolkata"))
                msg = (
                    f"**{me.mention} is restarted!**\n\n"
                    f"📅 Date : `{now.strftime('%d %B, %Y')}`\n"
                    f"⏰ Time : `{now.strftime('%I:%M:%S %p')}`\n"
                    f"🌐 Timezone : `Asia/Kolkata`"
                )
                await self.send_message(LOG_CHANNEL, msg)
            except Exception as e:
                print(f"Error sending to LOG_CHANNEL: {e}")

    async def stop(self, *args):
        from TechifyBots.second import second_bot
        if second_bot and second_bot.is_connected:
            await second_bot.stop()
        await super().stop()
        print("Bot stopped.")

Bot().run()
