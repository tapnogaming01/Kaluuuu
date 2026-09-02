import asyncio
import time
from datetime import datetime
from aiohttp import web
from pyrogram import Client, idle
import config

# 🚀 Build Version
BUILD_VERSION = "v2.0"

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({
        "status": "running", 
        "bot": config.BOT_USERNAME,
        "version": BUILD_VERSION
    })

async def start_web_server():
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.PORT)
    await site.start()
    print(f"🌐 Web Server listening on port {config.PORT}")

# 🔄 Session Name updated to "MultiStoryBot_v2" to fix USER_MIGRATE_303 error
bot = Client(
    "MultiStoryBot_v2",
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

# 🔔 Startup Log Sender
async def send_restart_log():
    try:
        me = await bot.get_me()
        bot_name = me.first_name
        bot_username = me.username
        current_time = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

        restart_text = (
            "🚀 **ʙᴏᴛ ʀᴇꜱᴛᴀʀᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!**\n\n"
            f"🤖 **ʙᴏᴛ ɴᴀᴍᴇ:** [{bot_name}](https://t.me/{bot_username})\n"
            f"⏰ **ʀᴇꜱᴛᴀʀᴛ ᴛɪᴍᴇ:** `{current_time}`\n"
            f"🏷️ **ʙᴜɪʟᴅ ᴠᴇʀꜱɪᴏɴ:** `{BUILD_VERSION}`\n"
            f"🟢 **ꜱᴛᴀᴛᴜꜱ:** `ᴏɴʟɪɴᴇ & ʀᴇᴀᴅʏ`"
        )

        log_channel = getattr(config, "LOG_CHANNEL", None)
        if log_channel:
            await bot.send_message(
                chat_id=int(log_channel),
                text=restart_text,
                disable_web_page_preview=True
            )
            print("📢 Restart log sent to LOG_CHANNEL successfully!")
    except Exception as e:
        print(f"⚠️ Failed to send restart log: {e}")

async def main():
    await start_web_server()
    print("🤖 Starting Telegram Bot...")
    await bot.start()
    print("✅ Bot is active and running!")

    # 🔑 Bot Safe Peer Cache
    print("🔄 Caching channels...")
    await cache_peer_safe(config.DB_CHANNEL)
    await cache_peer_safe(config.LOG_CHANNEL)
    if hasattr(config, "SOURCE_CHANNEL"):
        await cache_peer_safe(config.SOURCE_CHANNEL)

    # 📢 Send Restart Log Alert
    await send_restart_log()

    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
