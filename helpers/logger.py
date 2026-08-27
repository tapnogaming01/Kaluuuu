import traceback
from pyrogram import Client
from pyrogram.enums import ParseMode
import config

async def send_log(bot: Client, text: str):
    try:
        log_channel = int(config.LOG_CHANNEL)
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
    # Traceback ke backticks ko clean karein taaki Markdown crash na ho
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
        await bot.send_message(
            chat_id=log_channel, 
            text=error_text,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        # Agar Telegram Log Channel fail ho toh Render Console me print karein
        print(f"❌ [Console Log Error] Failed to send error log to Telegram: {e}")
        print(f"Original Error in '{context}': {error}\nTraceback:\n{tb}")
