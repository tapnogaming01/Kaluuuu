import traceback
from pyrogram import Client
import config

async def send_log(bot: Client, text: str):
    try:
        await bot.send_message(chat_id=config.LOG_CHANNEL, text=text, disable_web_page_preview=True)
    except Exception as e:
        print(f"Failed to send log: {e}")

async def send_error_log(bot: Client, error: Exception, context: str = ""):
    tb = traceback.format_exc()
    error_text = (
        f"🚨 **BOT ERROR REPORT**\n\n"
        f"📍 **Context:** `{context}`\n"
        f"❌ **Error Type:** `{type(error).__name__}`\n"
        f"💬 **Message:** `{str(error)}`\n\n"
        f"🛠️ **Traceback:**\n`{tb[-1000:]}`"
    )
    try:
        await bot.send_message(chat_id=config.LOG_CHANNEL, text=error_text)
    except Exception as e:
        print(f"Failed to send error log: {e}")
