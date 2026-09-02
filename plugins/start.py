import time
import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, PeerIdInvalid
import config
from database import (
    add_user,  # ✅ DB check & add user function
    get_settings, 
    is_user_banned, 
    increment_bypass_count, 
    ban_user,
    is_user_verified,
    set_user_verified,
    is_token_burned,
    burn_token
)
from helpers.logger import send_log, send_error_log
from helpers.verification import (
    get_shortlink as get_short_url, 
    create_secure_payload, 
    decode_and_verify_payload
)

FUNNY_HACKER_MESSAGES = [
    "🚨 **WHOA BRO! SLOW DOWN!** 🏎️💨\n\nआप इतनी जल्दी तो Flash भी नहीं आ सकता! 🧙‍♂️\nबॉट बाईपास करने की कोशिश? पकड़े गए! 🤖💥\n*(Warning {strike}/3 - 3 स्ट्राइक पर ऑटोमैटिक बैन कर दिया जाएगा!)*",
    "🕵️‍♂️ **Hey Anonymous Hacker!**\n\nscript चला के सोचे थे 2 सेकंड में फाइल मिल जाएगी? 😎\nस्मार्ट आप हो, तो अति-स्मार्ट हम हैं! 🗿\n*(Warning {strike}/3: 3 बार बाईपास करने पर हमेशा के लिए बैन हो जाओगे!)*",
    "🤖 **SYSTEM ALERT: Bypasser Spotted!** 🎯\n\n2 मिनट का रास्ता 5 सेकंड में? उड़ के गए थे क्या? ✈️\nना ना ना! चीटिंग नहीं चलेगी। टोकन Expire कर दिया गया है! 🚫\n*(Strike {strike}/3: सावधान रहें!)*"
]

# 🔄 Helper Function: Force Subscribe Checker
async def check_fsub_channels(bot: Client, user_id: int, settings: dict):
    unjoined_buttons = []
    
    # 4 potential channel keys saved in DB/Settings
    for i in range(1, 5):
        channel_url = settings.get(f"fsub_{i}") or getattr(config, f"FSUB_CHANNEL_{i}", None)
        if not channel_url or "your_channel" in channel_url:
            continue
        
        # Extract channel username or ID
        chat_identifier = channel_url.split("/")[-1].replace("@", "").strip()
        if not chat_identifier:
            continue

        try:
            member = await bot.get_chat_member(chat_identifier, user_id)
            if member.status in ["kicked", "left"]:
                unjoined_buttons.append([InlineKeyboardButton(f"📢 Join Channel {i}", url=channel_url)])
        except (UserNotParticipant, ChatAdminRequired, PeerIdInvalid, Exception):
            unjoined_buttons.append([InlineKeyboardButton(f"📢 Join Channel {i}", url=channel_url)])

    return unjoined_buttons


# 🔄 Auto Delete Handler Task
async def auto_delete_messages(bot: Client, chat_id: int, message_ids: list, delay: int, param: str):
    await asyncio.sleep(delay)
    try:
        # Files aur Notice message ko delete karna
        await bot.delete_messages(chat_id=chat_id, message_ids=message_ids)
        
        bot_username = getattr(config, "BOT_USERNAME", "vj_post_search_bot")
        get_again_url = f"https://t.me/{bot_username}?start={param}"

        # Permanent Message - Sirf 'Get File Again' Button ke sath
        await bot.send_message(
            chat_id=chat_id,
            text="🗑️ **Your files have been auto-deleted to protect content rights.**\n\nIf you want the files again, click the button below!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Get File Again", url=get_again_url)]
            ])
        )

    except Exception as e:
        await send_error_log(bot, e, "Auto Delete Task Failed")


@Client.on_message(filters.command("start") & filters.private)
async def start_handler(bot: Client, message: Message):
    try:
        user_id = message.from_user.id
        s = await get_settings()

        # ✅ Check & Register User in DB
        is_new = await add_user(user_id, message.from_user.first_name)

        if is_new:
            await send_log(
                bot, 
                f"🆕 **New User Registered!**\n"
                f"👤 **Name:** {message.from_user.mention}\n"
                f"🆔 **ID:** `{user_id}`"
            )

        # 0. Global Ban Check
        banned, reason = await is_user_banned(user_id)
        if banned:
            return await message.reply_text(
                f"🚫 **You are BANNED from using this bot!**\n\n"
                f"📝 **Reason:** `{reason}`\n"
                f"💬 Contact support if you think this is a mistake."
            )

        # 1. FORCE SUBSCRIBE CHECK
        unjoined_buttons = await check_fsub_channels(bot, user_id, s)
        if unjoined_buttons:
            param_str = message.command[1] if len(message.command) > 1 else ""
            bot_username = getattr(config, "BOT_USERNAME", message.message_thread_id)
            try_again_url = f"https://t.me/{bot.me.username}?start={param_str}" if param_str else f"https://t.me/{bot.me.username}?start"
            
            unjoined_buttons.append([InlineKeyboardButton("🔄 Try Again", url=try_again_url)])
            
            return await message.reply_text(
                "⚠️ **Force Subscribe Notice!**\n\n"
                "फाइल्स एक्सेस करने के लिए आपको हमारे स्पॉन्सर चैनल्स को जॉइन करना अनिवार्य है।\n"
                "नीचे दिए गए चैनल्स जॉइन करें और फिर **Try Again** पर क्लिक करें।",
                reply_markup=InlineKeyboardMarkup(unjoined_buttons)
            )

        # 2. Normal /start Command (Without parameters)
        if len(message.command) < 2:
            return await message.reply_text(
                f"👋 **Hello {message.from_user.first_name}!**\n\n"
                "Welcome to the **Audio Story File Store Bot**.\n"
                "Click episode buttons in the channel to get your audio files.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Updates Channel", url=getattr(config, "UPDATES_CHANNEL", "https://t.me/your_channel"))],
                    [InlineKeyboardButton("❓ Support", url="https://t.me/your_support")]
                ])
            )

        raw_param = message.command[1]

        # 3. ANTI-BYPASS & TOKEN VERIFICATION HANDLER
        if raw_param.startswith("verify_"):
            token_payload = raw_param.replace("verify_", "")

            if await is_token_burned(token_payload):
                return await message.reply_text(
                    "❌ **Token Expired or Already Used!**\n\nयह टोकन पहले ही यूज़ या एक्सपायर किया जा चुका है। कृपया नया लिंक जनरेट करें।"
                )

            token_user_id, target_param, created_at, is_valid = decode_and_verify_payload(token_payload)

            if not is_valid:
                return await message.reply_text("⛔ **Invalid / Tampered Verification Token!**")

            if token_user_id != user_id:
                return await message.reply_text(
                    "⚠️ **Access Denied!**\n\nयह वेरिफिकेशन टोकन किसी और यूज़र का है। आप इसका उपयोग नहीं कर सकते।"
                )

            time_taken = int(time.time()) - created_at
            if time_taken < 120:
                await burn_token(token_payload)
                attempts = await increment_bypass_count(user_id)

                if attempts >= 3:
                    await ban_user(user_id, reason="Auto-Banned: Exceeded 3 Bypass Attempts")
                    await send_log(
                        bot, 
                        f"🚨 **USER AUTO-BANNED!**\nUser: {message.from_user.mention} (`{user_id}`)\n"
                        f"Reason: Completed shortener in `{time_taken}s` (3 Strikes Exceeded)."
                    )
                    return await message.reply_text(
                        "⛔ **YOU HAVE BEEN BANNED!**\n\n"
                        "आप 3 बार बाईपास करते हुए पकड़े गए हैं। आपको बोट से permanently बैन कर दिया गया है।"
                    )
                else:
                    await send_log(
                        bot, 
                        f"⚠️ **Bypass Attempt Blocked:** {message.from_user.mention} (`{user_id}`) in `{time_taken}s` | Strike `{attempts}/3`"
                    )
                    msg_text = random.choice(FUNNY_HACKER_MESSAGES).format(strike=attempts)
                    return await message.reply_text(msg_text)

            verify_hours = s.get("verify_expire_hours", 12)
            await set_user_verified(user_id, hours=verify_hours)
            await burn_token(token_payload)
            await send_log(bot, f"✅ **User Verified:** {message.from_user.mention} (`{user_id}`) in `{time_taken}s`.")
            
            param = target_param
            await message.reply_text(
                f"🎉 **Verification Successful!**\n\n"
                f"Your file access is active for **{verify_hours} Hours**. Sending your files now..."
            )
        else:
            param = raw_param

        # 4. Shortener Verification Status Check
        ADMINS = getattr(config, "ADMINS", [])
        is_admin = user_id in ADMINS
        is_verify_enabled = s.get("shortener_verify_enabled", True)

        if not is_admin and is_verify_enabled and s.get("shortener_api"):
            is_verified = await is_user_verified(user_id)
            if not is_verified:
                secure_payload = create_secure_payload(user_id, param)
                raw_verify_link = f"https://t.me/{config.BOT_USERNAME}?start=verify_{secure_payload}"
                
                short_url = await get_short_url(raw_verify_link)

                btn = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔓 Verify Access (Click Here)", url=str(short_url))],
                    [InlineKeyboardButton("❓ How to Verify", url="https://t.me/your_tutorial")]
                ])
                return await message.reply_text(
                    "🔒 **Access Verification Required!**\n\n"
                    f"Please verify access to gain file availability for **{s.get('verify_expire_hours', 12)} Hours**.\n\n"
                    "⏱️ *Note: Complete verification properly without bypass scripts.*",
                    reply_markup=btn
                )

        # 5. Deliver Requested Files Logic
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
                await asyncio.sleep(1)

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

        # 6. Handle Auto-Deletion Task
        is_auto_del = s.get("auto_delete_enabled", True)
        del_min = s.get("auto_delete_minutes", 30)
        channel_url = getattr(config, "UPDATES_CHANNEL", "https://t.me/your_channel")

        if sent_messages and is_auto_del:
            del_msg = await message.reply_text(
                f"⚠️ **Important:**\n\n"
                f"All Messages will be deleted after **{del_min} minutes**. "
                f"Please save or forward these messages to your personal saved messages to avoid losing them!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Updates Channel", url=channel_url)]
                ])
            )
            sent_messages.append(del_msg.id)
            
            asyncio.create_task(auto_delete_messages(bot, user_id, sent_messages, del_min * 60, param))

        await send_log(
            bot,
            f"📥 **Files Delivered:** {len(sent_messages)-1 if is_auto_del and sent_messages else len(sent_messages)} files sent to {message.from_user.mention} (`{user_id}`).\n"
            f"🔒 Content Protection: `{is_protect}` | ⏳ Auto-Delete: `{del_min} min`"
        )

    except Exception as e:
        await send_error_log(bot, e, f"Start Handler Error: {message.text}")
        await message.reply_text("❌ An error occurred while fetching your files.")
