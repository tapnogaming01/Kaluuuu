import time
import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, PeerIdInvalid
import config
from script import Script
from database import (
    add_user, 
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

# 🛑 Cancel Tracking Dictionary
CANCEL_TASKS = {}


# 🔄 Helper Function: Robust Force Subscribe Checker
async def check_fsub_channels(bot: Client, user_id: int, settings: dict):
    unjoined_buttons = []
    
    for i in range(1, 5):
        channel_val = settings.get(f"fsub_{i}") or getattr(config, f"FSUB_CHANNEL_{i}", None)
        if not channel_val or "your_channel" in str(channel_val):
            continue
        
        channel_val = str(channel_val).strip()

        chat_identifier = None
        if channel_val.startswith("-100") or channel_val.lstrip("-").isdigit():
            chat_identifier = int(channel_val)
        elif "t.me/" in channel_val:
            clean_path = channel_val.split("t.me/")[-1].replace("@", "").strip()
            if not clean_path.startswith("+") and not clean_path.startswith("joinchat/"):
                chat_identifier = f"@{clean_path.split('/')[0]}"
        elif channel_val.startswith("@"):
            chat_identifier = channel_val
        else:
            chat_identifier = f"@{channel_val}"

        if not chat_identifier:
            continue

        try:
            member = await bot.get_chat_member(chat_id=chat_identifier, user_id=user_id)
            if member.status in ["left", "kicked"]:
                unjoined_buttons.append([InlineKeyboardButton(f"📢 Join Channel {i}", url=channel_val if "http" in channel_val else f"https://t.me/{chat_identifier.replace('@','')}")])
        except UserNotParticipant:
            unjoined_buttons.append([InlineKeyboardButton(f"📢 Join Channel {i}", url=channel_val if "http" in channel_val else f"https://t.me/{chat_identifier.replace('@','')}")])
        except Exception:
            pass

    return unjoined_buttons


# 🔄 Auto Delete Handler Task
async def auto_delete_messages(bot: Client, chat_id: int, message_ids: list, delay: int, param: str):
    await asyncio.sleep(delay)
    try:
        await bot.delete_messages(chat_id=chat_id, message_ids=message_ids)
        bot_username = getattr(config, "BOT_USERNAME", "vj_post_search_bot")
        get_again_url = f"https://t.me/{bot_username}?start={param}"

        await bot.send_message(
            chat_id=chat_id,
            text=Script.AUTO_DEL_DONE_TXT,
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

        # Check & Register User
        is_new = await add_user(user_id, message.from_user.first_name)
        if is_new:
            await send_log(
                bot, 
                f"🆕 **New User Registered!**\n👤 **Name:** {message.from_user.mention}\n🆔 **ID:** `{user_id}`"
            )

        # 0. Global Ban Check
        banned, reason = await is_user_banned(user_id)
        if banned:
            return await message.reply_text(Script.BANNED_TXT.format(reason=reason))

        # 1. Force Subscribe Check
        unjoined_buttons = await check_fsub_channels(bot, user_id, s)
        if unjoined_buttons:
            param_str = message.command[1] if len(message.command) > 1 else "none"
            unjoined_buttons.append([InlineKeyboardButton("🔄 Try Again", callback_data=f"check_fsub#{param_str}")])
            return await message.reply_text(Script.FSUB_TXT, reply_markup=InlineKeyboardMarkup(unjoined_buttons))

        # 2. Normal /start Command
        if len(message.command) < 2:
            return await message.reply_text(
                Script.START_TXT.format(first_name=message.from_user.first_name),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Updates Channel", url=getattr(config, "UPDATES_CHANNEL", "https://t.me/your_channel"))],
                    [InlineKeyboardButton("❓ Support", url="https://t.me/your_support")]
                ])
            )

        raw_param = message.command[1]

        # 3. Verification Handler
        if raw_param.startswith("verify_"):
            token_payload = raw_param.replace("verify_", "")

            if await is_token_burned(token_payload):
                return await message.reply_text(Script.TOKEN_EXPIRED_TXT)

            token_user_id, target_param, created_at, is_valid = decode_and_verify_payload(token_payload)

            if not is_valid:
                return await message.reply_text("⛔ **Invalid / Tampered Verification Token!**")

            if token_user_id != user_id:
                return await message.reply_text("⚠️ **Access Denied!**\n\nयह वेरिफिकेशन टोकन किसी और यूज़र का है।")

            time_taken = int(time.time()) - created_at
            if time_taken < 120:
                await burn_token(token_payload)
                attempts = await increment_bypass_count(user_id)

                if attempts >= 3:
                    await ban_user(user_id, reason="Auto-Banned: Exceeded 3 Bypass Attempts")
                    await send_log(
                        bot, 
                        f"🚨 **USER AUTO-BANNED!**\nUser: {message.from_user.mention} (`{user_id}`)\nReason: Completed shortener in `{time_taken}s`."
                    )
                    return await message.reply_text("⛔ **YOU HAVE BEEN BANNED!**\n\nआप 3 बार बाईपास करते हुए पकड़े गए हैं।")
                else:
                    await send_log(bot, f"⚠️ **Bypass Attempt Blocked:** {message.from_user.mention} (`{user_id}`) in `{time_taken}s` | Strike `{attempts}/3`")
                    msg_text = random.choice(Script.FUNNY_HACKER_MESSAGES).format(strike=attempts)
                    return await message.reply_text(msg_text)

            verify_hours = s.get("verify_expire_hours", 12)
            await set_user_verified(user_id, hours=verify_hours)
            await burn_token(token_payload)
            await send_log(bot, f"✅ **User Verified:** {message.from_user.mention} (`{user_id}`) in `{time_taken}s`.")
            
            param = target_param
            await message.reply_text(Script.VERIFY_SUCCESS_TXT.format(hours=verify_hours))
        else:
            param = raw_param

        # 4. Shortener Verification Check
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
                    Script.VERIFY_REQ_TXT.format(expire_hours=s.get('verify_expire_hours', 12)),
                    reply_markup=btn
                )

        # 5. Deliver Files
        await process_file_delivery(bot, message, param, s)

    except Exception as e:
        await send_error_log(bot, e, f"Start Handler Error: {message.text}")
        await message.reply_text("❌ An error occurred while fetching your files.")


# 🔄 Updated File Delivery Helper with Developer & Cancel Support
async def process_file_delivery(bot: Client, message: Message, param: str, settings: dict):
    user_id = message.from_user.id
    sent_messages = []
    is_protect = settings.get("protect_content", True)
    
    # Buttons Structure
    dev_url = "https://t.me/Kaluu"
    wait_buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 DEVELOPER", url=dev_url)],
        [InlineKeyboardButton("❌ CANCEL", callback_data=f"cancel_dl#{user_id}")]
    ])

    status_msg = await message.reply_text(
        Script.PLEASE_WAIT_TXT,
        reply_markup=wait_buttons
    )

    # Reset Cancel State
    CANCEL_TASKS[user_id] = False

    try:
        if param.startswith("batch_"):
            parts = param.split("_")
            start_id, end_id = int(parts[1]), int(parts[2])
            
            for m_id in range(start_id, end_id + 1):
                # Check for Cancellation
                if CANCEL_TASKS.get(user_id, False):
                    await status_msg.edit_text(Script.CANCELLED_TXT)
                    await asyncio.sleep(2)
                    await status_msg.delete()
                    return

                copied = await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=config.DB_CHANNEL,
                    message_id=m_id,
                    protect_content=is_protect
                )
                sent_messages.append(copied.id)
                await asyncio.sleep(1)

        elif param.startswith("file_"):
            if not CANCEL_TASKS.get(user_id, False):
                msg_id = int(param.split("_")[1])
                copied = await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=config.DB_CHANNEL,
                    message_id=msg_id,
                    protect_content=is_protect
                )
                sent_messages.append(copied.id)

    finally:
        CANCEL_TASKS.pop(user_id, None)

    # Delete Wait Message after sending files
    try:
        await status_msg.delete()
    except Exception:
        pass

    # Auto Delete Handle
    is_auto_del = settings.get("auto_delete_enabled", True)
    del_min = settings.get("auto_delete_minutes", 30)
    channel_url = getattr(config, "UPDATES_CHANNEL", "https://t.me/your_channel")

    if sent_messages and is_auto_del:
        del_msg = await message.reply_text(
            Script.AUTO_DEL_WARN_TXT.format(del_min=del_min),
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


# 🔄 Callback Query Handler for Try Again Button
@Client.on_callback_query(filters.regex(r"^check_fsub#"))
async def check_fsub_callback(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    param = query.data.split("#")[1]
    s = await get_settings()

    unjoined_buttons = await check_fsub_channels(bot, user_id, s)
    
    if unjoined_buttons:
        await query.answer("❌ आपने अभी भी सभी चैनल्स जॉइन नहीं किए हैं!", show_alert=True)
        unjoined_buttons.append([InlineKeyboardButton("🔄 Try Again", callback_data=f"check_fsub#{param}")])
        try:
            await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(unjoined_buttons))
        except Exception:
            pass
    else:
        await query.answer("✅ सभी चैनल्स सफलतापूर्वक जॉइन हो चुके हैं!", show_alert=False)
        await query.message.delete()
        
        if param != "none":
            query.message.command = ["start", param]
        else:
            query.message.command = ["start"]
            
        await start_handler(bot, query.message)


# 🛑 Callback Query Handler for Cancel Delivery
@Client.on_callback_query(filters.regex(r"^cancel_dl#"))
async def cancel_delivery_callback(bot: Client, query: CallbackQuery):
    target_user_id = int(query.data.split("#")[1])

    if query.from_user.id != target_user_id:
        return await query.answer("⚠️ यह बटन आपके लिए नहीं है!", show_alert=True)

    CANCEL_TASKS[target_user_id] = True
    await query.answer("🛑 फाइल डिलीवरी रोकी जा रही है...", show_alert=False)
