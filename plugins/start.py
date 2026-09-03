import time
import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatJoinRequest
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, PeerIdInvalid
import config
from script import Script
from database import (
    add_user, 
    get_settings, 
    is_user_banned, 
    increment_bypass_count, 
    ban_user,
    get_user_verification_status,
    set_user_slot_verified,
    is_token_burned,
    burn_token,
    add_pending_request,
    is_request_pending
)
from helpers.logger import send_log, send_error_log
from helpers.verification import (
    get_shortlink as get_short_url, 
    create_secure_payload, 
    decode_and_verify_payload
)

# 🛑 Cancel Tracking Dictionary
CANCEL_TASKS = {}


# 📩 Event Handler: Catch Private Channel Join Requests and Save to DB
@Client.on_chat_join_request()
async def track_join_request(bot: Client, request: ChatJoinRequest):
    try:
        user_id = request.from_user.id
        chat_id = request.chat.id
        
        # Save request to MongoDB
        await add_pending_request(user_id, chat_id)
        print(f"📩 Join Request Saved in DB | User: {user_id} | Chat: {chat_id}")
    except Exception as e:
        print(f"⚠️ Error Saving Join Request to DB: {e}")


# 🔄 Helper Function: Force Subscribe Checker (Member or Pending Request Check)
async def check_fsub_channels(bot: Client, user_id: int, settings: dict):
    unjoined_buttons = []
    
    for i in range(1, 5):
        channel_val = settings.get(f"fsub_{i}") or getattr(config, f"FSUB_CHANNEL_{i}", None)
        if not channel_val or "your_channel" in str(channel_val):
            continue
        
        channel_val = str(channel_val).strip()

        # 1. Chat Identifier Extract Logic
        chat_identifier = None
        if channel_val.startswith("-100") or channel_val.lstrip("-").isdigit():
            chat_identifier = int(channel_val)
        elif "t.me/" in channel_val:
            clean_path = channel_val.split("t.me/")[-1].replace("@", "").strip()
            if not clean_path.startswith("+") and not clean_path.startswith("joinchat/"):
                chat_identifier = f"@{clean_path.split('/')[0]}"
            else:
                chat_identifier = channel_val
        elif channel_val.startswith("@"):
            chat_identifier = channel_val
        else:
            chat_identifier = f"@{channel_val}"

        if not chat_identifier:
            continue

        # 2. Join Link Generator (Approval / Join Request Link Support)
        join_url = None
        if isinstance(chat_identifier, int) or (isinstance(channel_val, str) and channel_val.startswith("-100")):
            try:
                # 🛑 Approval Invite Link (Join Request Enabled)
                invite_link_obj = await bot.create_chat_invite_link(
                    chat_id=chat_identifier,
                    creates_join_request=True
                )
                join_url = invite_link_obj.invite_link
            except Exception as e:
                print(f"⚠️ Approval Invite Link Error (Channel {i}): {e}")
                try:
                    chat_info = await bot.get_chat(chat_identifier)
                    join_url = chat_info.invite_link or await bot.export_chat_invite_link(chat_identifier)
                except Exception:
                    join_url = "https://t.me/"
        elif "http" in channel_val:
            join_url = channel_val
        else:
            clean_username = str(chat_identifier).replace("@", "")
            join_url = f"https://t.me/{clean_username}"

        # 3. MongoDB Pending Request Check (Bypass FSub if Request Sent)
        if isinstance(chat_identifier, int):
            if await is_request_pending(user_id, chat_identifier):
                continue

        # 4. Membership Check
        try:
            member = await bot.get_chat_member(chat_id=chat_identifier, user_id=user_id)
            if member.status in ["left", "kicked"]:
                unjoined_buttons.append([InlineKeyboardButton(f"📢 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ {i}", url=join_url)])
        except UserNotParticipant:
            unjoined_buttons.append([InlineKeyboardButton(f"📢 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ {i}", url=join_url)])
        except Exception as e:
            print(f"⚠️ FSUB Check Error (Channel {i}): {e}")
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
                [InlineKeyboardButton("🔄 ɢᴇᴛ ꜰɪʟᴇ ᴀɢᴀɪɴ", url=get_again_url)]
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
            unjoined_buttons.append([InlineKeyboardButton("🔄 ᴛʀʏ ᴀɢᴀɪɴ", callback_data=f"check_fsub#{param_str}")])
            return await message.reply_text(Script.FSUB_TXT, reply_markup=InlineKeyboardMarkup(unjoined_buttons))

        # 2. Normal /start Command
        if len(message.command) < 2:
            main_buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("❓ ʜᴇʟᴘ", callback_data="help_btn"),
                    InlineKeyboardButton("ℹ️ ᴀʙᴏᴜᴛ", callback_data="about_btn")
                ],
                [
                    InlineKeyboardButton("📢 ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ", url=getattr(config, "UPDATES_CHANNEL", "https://t.me/pratilipifm0900")),
                    InlineKeyboardButton("💬 ꜱᴜᴘᴘᴏʀᴛ", url="https://t.me/pratilipifm0900")
                ]
            ])
            return await message.reply_text(
                Script.START_TXT.format(first_name=message.from_user.first_name),
                reply_markup=main_buttons
            )

        raw_param = message.command[1]

        # 3. Dynamic 3-Slots Verification Handler
        if raw_param.startswith("verify_"):
            token_payload = raw_param.replace("verify_", "")

            if await is_token_burned(token_payload):
                return await message.reply_text(Script.TOKEN_EXPIRED_TXT)

            token_user_id, target_param, created_at, is_valid = decode_and_verify_payload(token_payload)

            if not is_valid:
                return await message.reply_text("⛔ **ɪɴᴠᴀʟɪᴅ / ᴛᴀᴍᴘᴇʀᴇᴅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛᴏᴋᴇɴ!**")

            if token_user_id != user_id:
                return await message.reply_text("⚠️ **ᴀᴄᴄᴇꜱꜱ ᴅᴇɴɪᴇᴅ!**\n\nᴛʜɪꜱ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛᴏᴋᴇɴ ʙᴇʟᴏɴɢꜱ ᴛᴏ ᴀɴᴏᴛʜᴇʀ ᴜꜱᴇʀ.")

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
                    return await message.reply_text("⛔ **ʏᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ʙᴀɴɴᴇᴅ!**\n\nʏᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ᴄᴀᴜɢʜᴛ ʙʏᴘᴀꜱꜱɪɴɢ 3 ᴛɪᴍᴇꜱ.")
                else:
                    await send_log(bot, f"⚠️ **Bypass Attempt Blocked:** {message.from_user.mention} (`{user_id}`) in `{time_taken}s` | Strike `{attempts}/3`")
                    msg_text = random.choice(Script.FUNNY_HACKER_MESSAGES).format(strike=attempts)
                    return await message.reply_text(msg_text)

            # Slot verification status fetch
            v_status = await get_user_verification_status(user_id)
            current_slot = v_status.get("next_slot", 1) or 1
            
            # Set time dynamically based on the verified slot
            await set_user_slot_verified(user_id, current_slot)
            await burn_token(token_payload)
            
            slot_time = s.get(f"v{current_slot}_time", "12h")
            await send_log(bot, f"✅ **User Verified Slot {current_slot}:** {message.from_user.mention} (`{user_id}`) in `{time_taken}s`.")
            
            param = target_param
            
            # Fetch message dynamically from script.py
            success_txt = getattr(Script, f"VERIFY_SUCCESS_TXT_{current_slot}", Script.VERIFY_SUCCESS_TXT_1)
            await message.reply_text(success_txt.format(hours=slot_time))
        else:
            param = raw_param

        # 4. Shortener Verification Check (3-Step Check)
        ADMINS = getattr(config, "ADMINS", [])
        is_admin = user_id in ADMINS

        if not is_admin:
            v_status = await get_user_verification_status(user_id)
            
            if not v_status.get("is_fully_verified", False):
                next_slot = v_status.get("next_slot", 1)
                
                shortener_url = s.get(f"v{next_slot}_url")
                shortener_api = s.get(f"v{next_slot}_api")
                tutorial_url = s.get(f"v{next_slot}_tutorial") or "https://t.me/your_tutorial"
                slot_time = s.get(f"v{next_slot}_time", "12h")

                if shortener_url and shortener_api:
                    secure_payload = create_secure_payload(user_id, param)
                    raw_verify_link = f"https://t.me/{config.BOT_USERNAME}?start=verify_{secure_payload}"
                    short_url = await get_short_url(raw_verify_link, shortener_url, shortener_api)

                    BUY_STORE_URL = "http://t.me/storysellerbyACbot/Store"

                    btn = InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"🔓 ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ {next_slot} (ᴄʟɪᴄᴋ ʜᴇʀᴇ)", url=str(short_url))],
                        [InlineKeyboardButton("🛒 ʙᴜʏ ꜱᴛᴏʀʏ (ᴊᴜꜱᴛ ₹1 - ₹5)", url=BUY_STORE_URL)],
                        [InlineKeyboardButton("❓ ʜᴏᴡ ᴛᴏ ᴠᴇʀɪꜰʏ", url=tutorial_url)]
                    ])
                    
                    req_txt = getattr(Script, f"VERIFY_REQ_TXT_{next_slot}", Script.VERIFY_REQ_TXT_1)
                    return await message.reply_text(
                        req_txt.format(expire_hours=slot_time),
                        reply_markup=btn
                    )

        # 5. Deliver Files
        await process_file_delivery(bot, message, param, s)

    except Exception as e:
        await send_error_log(bot, e, f"Start Handler Error: {message.text}")
        await message.reply_text("❌ ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ꜰᴇᴛᴄʜɪɴɢ ʏᴏᴜʀ ꜰɪʟᴇꜱ.")


# ❓ Command Handlers for /help & /about
@Client.on_message(filters.command("help") & filters.private)
async def help_handler(bot: Client, message: Message):
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="back_start")]])
    await message.reply_text(Script.HELP_TXT, reply_markup=btn)


@Client.on_message(filters.command("about") & filters.private)
async def about_handler(bot: Client, message: Message):
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 ᴅᴇᴠᴇʟᴏᴘᴇR", url="https://t.me/KCXRY")],
        [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="back_start")]
    ])
    await message.reply_text(Script.ABOUT_TXT, reply_markup=btn, disable_web_page_preview=True)


# 🔄 Updated File Delivery Helper
async def process_file_delivery(bot: Client, message: Message, param: str, settings: dict):
    user_id = message.from_user.id
    sent_messages = []
    is_protect = settings.get("protect_content", True)
    
    dev_url = "https://t.me/KCXRY"
    wait_buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 ᴅᴇᴠᴇʟᴏᴘᴇʀ", url=dev_url)],
        [InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data=f"cancel_dl#{user_id}")]
    ])

    status_msg = await message.reply_text(
        Script.PLEASE_WAIT_TXT,
        reply_markup=wait_buttons
    )

    CANCEL_TASKS[user_id] = False

    try:
        if param.startswith("batch_"):
            parts = param.split("_")
            start_id, end_id = int(parts[1]), int(parts[2])
            
            for m_id in range(start_id, end_id + 1):
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

    try:
        await status_msg.delete()
    except Exception:
        pass

    is_auto_del = settings.get("auto_delete_enabled", True)
    del_min = settings.get("auto_delete_minutes", 30)
    channel_url = getattr(config, "UPDATES_CHANNEL", "https://t.me/pratilipifm0900")

    if sent_messages and is_auto_del:
        del_msg = await message.reply_text(
            Script.AUTO_DEL_WARN_TXT.format(del_min=del_min),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ", url=channel_url)]
            ])
        )
        sent_messages.append(del_msg.id)
        asyncio.create_task(auto_delete_messages(bot, user_id, sent_messages, del_min * 60, param))

    await send_log(
        bot,
        f"📥 **Files Delivered:** {len(sent_messages)-1 if is_auto_del and sent_messages else len(sent_messages)} files sent to {message.from_user.mention} (`{user_id}`).\n"
        f"🔒 Content Protection: `{is_protect}` | ⏳ Auto-Delete: `{del_min} min`"
    )


# 🔄 Callback Navigation Handler (Help, About & Back)
@Client.on_callback_query(filters.regex(r"^(help_btn|about_btn|back_start)$"))
async def navigation_callbacks(bot: Client, query: CallbackQuery):
    data = query.data

    if data == "help_btn":
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="back_start")]])
        await query.message.edit_text(Script.HELP_TXT, reply_markup=btn)

    elif data == "about_btn":
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 ᴅᴇᴠᴇʟᴏᴘᴇʀ", url="https://t.me/KCXRY")],
            [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="back_start")]
        ])
        await query.message.edit_text(Script.ABOUT_TXT, reply_markup=btn, disable_web_page_preview=True)

    elif data == "back_start":
        main_buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❓ ʜᴇʟᴘ", callback_data="help_btn"),
                InlineKeyboardButton("ℹ️ ᴀʙᴏᴜᴛ", callback_data="about_btn")
            ],
            [
                InlineKeyboardButton("📢 ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ", url=getattr(config, "UPDATES_CHANNEL", "https://t.me/pratilipifm0900")),
                InlineKeyboardButton("💬 ꜱᴜᴘᴘᴏʀᴛ", url="https://t.me/pratilipifm0900")
            ]
        ])
        await query.message.edit_text(
            Script.START_TXT.format(first_name=query.from_user.first_name),
            reply_markup=main_buttons
        )


# 🔄 Callback Query Handler for Try Again Button
@Client.on_callback_query(filters.regex(r"^check_fsub#"))
async def check_fsub_callback(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    param = query.data.split("#")[1]
    s = await get_settings()

    unjoined_buttons = await check_fsub_channels(bot, user_id, s)
    
    if unjoined_buttons:
        await query.answer("❌ ʏᴏᴜ ʜᴀᴠᴇ ɴᴏᴛ ᴊᴏɪɴᴇᴅ ᴀʟʟ ᴄʜᴀɴɴᴇʟꜱ ʏᴇᴛ!", show_alert=True)
        unjoined_buttons.append([InlineKeyboardButton("🔄 ᴛʀʏ ᴀɢᴀɪɴ", callback_data=f"check_fsub#{param}")])
        try:
            await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(unjoined_buttons))
        except Exception:
            pass
    else:
        await query.answer("✅ ᴀʟʟ ᴄʜᴀɴɴᴇʟꜱ ᴊᴏɪɴ ʀᴇQᴜᴇꜱᴛ ꜱᴇɴᴛ / ᴊᴏɪɴᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!", show_alert=False)
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
        return await query.answer("⚠️ ᴛʜɪꜱ ʙᴜᴛᴛᴏɴ ɪꜱ ɴᴏᴛ ꜰᴏʀ ʏᴏᴜ!", show_alert=True)

    CANCEL_TASKS[target_user_id] = True
    await query.answer("🛑 ꜱᴛᴏᴘᴘɪɴɢ ꜰɪʟᴇ ᴅᴇʟɪᴠᴇʀʏ...", show_alert=False)
