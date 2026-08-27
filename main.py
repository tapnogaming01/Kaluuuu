import asyncio
from aiohttp import web
from pyrogram import Client, idle
import config

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({"status": "running", "bot": config.BOT_USERNAME})

async def start_web_server():
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.PORT)
    await site.start()
    print(f"🌐 Web Server listening on port {config.PORT}")

bot = Client(
    "MultiStoryBot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    plugins=dict(root="plugins")
)

async def cache_peer_safe(chat_id):
    try:
        await bot.get_chat(int(chat_id))
        print(f"✅ Cached peer: {chat_id}")
    except Exception as e:
        print(f"⚠️ Failed to cache {chat_id}: {e}")

async def main():
    await start_web_server()
    print("🤖 Starting Telegram Bot...")
    await bot.start()
    print("✅ Bot is active and running!")

    # 🔑 Bot Safe Peer Cache: get_chat use karein
    print("🔄 Caching channels...")
    await cache_peer_safe(config.DB_CHANNEL)
    await cache_peer_safe(config.LOG_CHANNEL)
    if hasattr(config, "SOURCE_CHANNEL"):
        await cache_peer_safe(config.SOURCE_CHANNEL)

    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
