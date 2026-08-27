import traceback
from pyrogram import Client
from pyrogram.enums import ParseMode
import config

async def resolve_peer_safe(bot: Client, chat_id: int):
    """Pyrogram memory me channel details load karta hai taaki PeerIdInvalid na aaye"""
    try:
        await bot.get_chat(chat_id)
    except Exception:
        pass

async def send_log(bot: Client, text: str):
    try:
        log_channel = int(config.LOG_CHANNEL)
        await resolve_peer_safe(bot, log_channel)
        await bot.send_message(
            chat_id=log_channel, 
            text=text, 
            disable_web_page_preview=True,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"❌ [Console Log] Failed to send log to Telegram: {e} | Text: {text}")

async def send_error_log(bot: Client, error: Exception, context: str = ""):
    tb = traceback.format_exc()
    clean_tb = tb.replace("`", "'")[-1000:]
    
    error_text = (
        f"🚨 **BOT ERROR REPORT**\n\n"
        f"📍 **Context:** `{context}`\n"
        f"❌ **Error Type:** `{type(error).__name__}`\n"
        f"💬 **Message:** `{str(error)}`\n\n"
        f"🛠️ **Traceback:**\n```text\n{clean_tb}\n```"
    )
    try:
        log_channel = int(config.LOG_CHANNEL)
        await resolve_peer_safe(bot, log_channel)
        await bot.send_message(
            chat_id=log_channel, 
            text=error_text,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"❌ [Console Log Error] Telegram Log Failed: {e}\nContext: {context}\nError: {error}\nTraceback:\n{tb}")
