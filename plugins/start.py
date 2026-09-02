import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import config
from database import get_settings, is_user_verified, set_user_verified
from helpers.logger import send_log, send_error_log
from helpers.shortener import get_short_url

async def auto_delete_messages(bot: Client, chat_id: int, message_ids: list, delay: int):
    await asyncio.sleep(delay)
    try:
        await bot.delete_messages(chat_id=chat_id, message_ids=message_ids)
        warning = await bot.send_message(
            chat_id=chat_id,
            text="🗑️ **Your files have been auto-deleted to protect content rights.**\nClick the link again if you need them!"
        )
        await asyncio.sleep(10)
        await warning.delete()
    except Exception as e:
        await send_error_log(bot, e, "Auto Delete Task Failed")

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(bot: Client, message: Message):
    try:
        user_id = message.from_user.id
        s = await get_settings()

        # 1. Normal /start Command
        if len(message.command) < 2:
            await send_log(bot, f"👤 **New User Started Bot:** {message.from_user.mention} (`{user_id}`)")
            return await message.reply_text(
                f"👋 **Hello {message.from_user.first_name}!**\n\n"
                "Welcome to the **Audio Story File Store Bot**.\n"
                "Click episode buttons in the channel to get your audio files.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Updates Channel", url="https://t.me/your_channel")],
                    [InlineKeyboardButton("❓ Support", url="https://t.me/your_support")]
                ])
            )

        param = message.command[1]

        # 2. Verification Token Pass Handler
        # अगर पैरामीटर 'verify_' से शुरू होता है तो ओरिजिनल फाइल ID निकालें
        if param.startswith("verify_"):
            verify_hours = s.get("verify_expire_hours", 12)
            await set_user_verified(user_id, hours=verify_hours)
            await send_log(bot, f"✅ **User Verified:** {message.from_user.mention} (`{user_id}`)")
            
            # verify_USERID_file_1234 से असली फाइल पैरामीटर निकालें
            parts = param.split("_", 2)
            if len(parts) > 2:
                param = parts[2]  # अब param बन जाएगा 'file_1234' या 'batch_10_20'
                await message.reply_text(
                    f"🎉 **Verification Successful!**\n\n"
                    f"Your file access is active for **{verify_hours} Hours**. Sending your files now..."
                )
            else:
                return await message.reply_text(
                    f"🎉 **Verification Successful!**\n\n"
                    f"Your file access is active for the next **{verify_hours} Hours**. Click your episode link again to receive files!"
                )

        # 3. Shortener Verification Status Check
        is_verify_enabled = s.get("shortener_verify_enabled", True)
        if is_verify_enabled and s.get("shortener_api"):
            is_verified = await is_user_verified(user_id)
            if not is_verified:
                # ओरिजिनल param (file_xx या batch_xx) को वेरिफिकेशन लिंक में अटैच करें
                raw_verify_link = f"https://t.me/{config.BOT_USERNAME}?start=verify_{user_id}_{param}"
                short_url = await get_short_url(raw_verify_link)

                btn = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔓 Verify Access (Click Here)", url=short_url)],
                    [InlineKeyboardButton("❓ How to Verify", url="https://t.me/your_tutorial")]
                ])
                return await message.reply_text(
                    "🔒 **Access Verification Required!**\n\n"
                    f"Please verify access to gain file availability for **{s.get('verify_expire_hours')} Hours**.",
                    reply_markup=btn
                )

        # 4. Deliver Requested Files (Protected & Auto-Deleted)
        sent_messages = []
        is_protect = s.get("protect_content", True)
        status_msg = await message.reply_text("🔄 **Fetching files...**")

        if param.startswith("batch_"):
            parts = param.split("_")
            start_id, end_id = int(parts[1]), int(parts[2])
            for m_id in range(start_id, end_id + 1):
                copied = await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=config.DB_CHANNEL,
                    message_id=m_id,
                    protect_content=is_protect
                )
                sent_messages.append(copied.id)

        elif param.startswith("file_"):
            msg_id = int(param.split("_")[1])
            copied = await bot.copy_message(
                chat_id=user_id,
                from_chat_id=config.DB_CHANNEL,
                message_id=msg_id,
                protect_content=is_protect
            )
            sent_messages.append(copied.id)

        await status_msg.delete()

        # 5. Handle Auto-Deletion Task
        is_auto_del = s.get("auto_delete_enabled", True)
        del_min = s.get("auto_delete_minutes", 5)

        if sent_messages and is_auto_del:
            del_msg = await message.reply_text(
                f"⚠️ **Notice:** These files will automatically be deleted in **{del_min} Minutes** to protect content rights."
            )
            sent_messages.append(del_msg.id)
            asyncio.create_task(auto_delete_messages(bot, user_id, sent_messages, del_min * 60))

        await send_log(
            bot,
            f"📥 **Files Delivered:** {len(sent_messages)-1 if is_auto_del and sent_messages else len(sent_messages)} files sent to {message.from_user.mention} (`{user_id}`).\n"
            f"🔒 Content Protection: `{is_protect}` | ⏳ Auto-Delete: `{del_min} min`"
        )

    except Exception as e:
        await send_error_log(bot, e, f"Start Handler Error: {message.text}")
        await message.reply_text("❌ An error occurred while fetching your files.")
