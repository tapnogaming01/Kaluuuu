from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, LinkPreviewOptions
import config
from database import (
    get_settings, update_settings,
    add_story_mapping, delete_story_mapping, get_all_stories
)

admin_filter = filters.user(config.ADMINS)


# -------------------------------------------------------------
# Helper Function: URL Sanitizer to Prevent 400 BUTTON_URL_INVALID Error
# -------------------------------------------------------------
def safe_url(url: str) -> str:
    """सुनिश्चित करता है कि बटन URL हमेशा 'https://' से शुरू हो और खाली न हो।"""
    if not url or not isinstance(url, str):
        return "https://t.me/"
    
    clean_url = url.strip()
    if not clean_url or "your_channel" in clean_url:
        return "https://t.me/"
    
    if clean_url.startswith("@"):
        return f"https://t.me/{clean_url.replace('@', '')}"
        
    if not clean_url.startswith(("http://", "https://")):
        return f"https://{clean_url}"
        
    return clean_url


# Helper function: Settings UI & Inline Buttons Generator
async def build_settings_panel():
    s = await get_settings()

    # Dynamic Buttons Status (🟢 ON / 🔴 OFF)
    verify_btn_status = "🟢 ON" if s.get("shortener_verify_enabled", True) else "🔴 OFF"
    autodel_btn_status = "🟢 ON" if s.get("auto_delete_enabled", True) else "🔴 OFF"
    protect_btn_status = "🟢 ON" if s.get("protect_content", True) else "🔴 OFF"

    # Dynamic Channels Link from DB (Validated with safe_url)
    fsub1 = safe_url(s.get("fsub_1") or getattr(config, "FSUB_CHANNEL_1", "https://t.me/"))
    fsub2 = safe_url(s.get("fsub_2") or getattr(config, "FSUB_CHANNEL_2", "https://t.me/"))
    fsub3 = safe_url(s.get("fsub_3") or getattr(config, "FSUB_CHANNEL_3", "https://t.me/"))
    fsub4 = safe_url(s.get("fsub_4") or getattr(config, "FSUB_CHANNEL_4", "https://t.me/"))

    # Clean UI Text
    text = (
        "⚡ **HERE IS THE SETTINGS MENU** ⚡\n"
        "_________________________________________\n\n"
        "CUSTOMIZE YOUR SETTINGS AS PER YOUR NEED."
    )

    # Clean Interactive Buttons Layout
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"🔐 VERIFICATION: {verify_btn_status}", callback_data="adm_toggle_verify")
        ],
        [
            InlineKeyboardButton(f"⏰ AUTO DELETE: {autodel_btn_status}", callback_data="adm_toggle_autodel")
        ],
        [
            InlineKeyboardButton(f"🛡️ PROTECT CONTENT: {protect_btn_status}", callback_data="adm_toggle_protect")
        ],
        # 📢 Dynamic 4 Force Subscribe Channel Buttons
        [
            InlineKeyboardButton("📢 Channel 1", url=fsub1),
            InlineKeyboardButton("📢 Channel 2", url=fsub2)
        ],
        [
            InlineKeyboardButton("📢 Channel 3", url=fsub3),
            InlineKeyboardButton("📢 Channel 4", url=fsub4)
        ],
        [
            InlineKeyboardButton("🏠 HOME", callback_data="adm_close")
        ]
    ])

    return text, buttons


# ==========================================
# 1. SETTINGS PANEL & CALLBACK HANDLERS
# ==========================================

@Client.on_message(filters.command("settings") & admin_filter)
async def settings_cmd(bot: Client, message: Message):
    text, markup = await build_settings_panel()
    await message.reply_text(
        text, 
        reply_markup=markup, 
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )


@Client.on_callback_query(filters.regex("^adm_"))
async def admin_settings_callback(bot: Client, query: CallbackQuery):
    if query.from_user.id not in config.ADMINS:
        return await query.answer("⛔ Admin access only!", show_alert=True)

    data = query.data
    s = await get_settings()

    if data == "adm_close":
        return await query.message.delete()

    elif data == "adm_toggle_verify":
        current = s.get("shortener_verify_enabled", True)
        await update_settings({"shortener_verify_enabled": not current})
        await query.answer(f"Verification: {'OFF 🔴' if current else 'ON 🟢'}")

    elif data == "adm_toggle_autodel":
        current = s.get("auto_delete_enabled", True)
        await update_settings({"auto_delete_enabled": not current})
        await query.answer(f"Auto Delete: {'OFF 🔴' if current else 'ON 🟢'}")

    elif data == "adm_toggle_protect":
        current = s.get("protect_content", True)
        await update_settings({"protect_content": not current})
        await query.answer(f"Protect Content: {'OFF 🔴' if current else 'ON 🟢'}")

    # Real-time Button Refresh
    text, markup = await build_settings_panel()
    await query.message.edit_text(
        text, 
        reply_markup=markup, 
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )


# ==========================================
# 2. STORY MAPPING COMMANDS
# ==========================================

@Client.on_message(filters.command("addstory") & admin_filter)
async def add_story_cmd(bot: Client, message: Message):
    try:
        args = message.text.split(" ", 1)[1].split("|")
        story_name = args[0].strip()
        target_id = int(args[1].strip())
        threshold = int(args[2].strip()) if len(args) > 2 else getattr(config, "DEFAULT_THRESHOLD", 5)

        await add_story_mapping(story_name, target_id, threshold)
        await message.reply_text(
            f"✅ **Story Mapped Successfully!**\n\n"
            f"📌 **Story Keyword:** `{story_name}`\n"
            f"🎯 **Target Channel:** `{target_id}`\n"
            f"📊 **Threshold:** `{threshold}` files"
        )
    except Exception:
        await message.reply_text("❌ गलत उपयोग। ऐसे लिखें:\n`/addstory Story Name | -100123456789 | 5`")


@Client.on_message(filters.command("delstory") & admin_filter)
async def del_story_cmd(bot: Client, message: Message):
    try:
        story_name = message.text.split(" ", 1)[1].strip()
        if await delete_story_mapping(story_name):
            await message.reply_text(f"🗑️ Story '`{story_name}`' removed successfully!")
        else:
            await message.reply_text("⚠️ Story database में नहीं मिली।")
    except IndexError:
        await message.reply_text("❌ गलत उपयोग। ऐसे लिखें:\n`/delstory Story Name`")


@Client.on_message(filters.command("liststories") & admin_filter)
async def list_stories_cmd(bot: Client, message: Message):
    stories = await get_all_stories()
    if not stories:
        return await message.reply_text("ℹ️ No mapped stories found.")
    
    msg = "📚 **Mapped Stories & Target Channels:**\n\n"
    for s in stories:
        msg += f"• **Keyword:** `{s['story_key']}` | **Channel:** `{s['target_chat_id']}` | **Threshold:** `{s['threshold']}`\n"
    await message.reply_text(msg)


# ==========================================
# 3. FORCE SUBSCRIBE CONTROL COMMANDS
# ==========================================

@Client.on_message(filters.command(["setfsub1", "setfsub2", "setfsub3", "setfsub4"]) & admin_filter)
async def set_fsub_channels_cmd(bot: Client, message: Message):
    try:
        cmd = message.command[0]
        raw_url = message.text.split(" ", 1)[1].strip()
        url = safe_url(raw_url)
        num = cmd.replace("setfsub", "")
        key = f"fsub_{num}"

        await update_settings({key: url})
        await message.reply_text(f"✅ **Channel {num} Link Updated!**\n\n🔗 {url}")
    except IndexError:
        await message.reply_text(f"❌ गलत उपयोग। ऐसे लिखें:\n`/{message.command[0]} https://t.me/your_channel_link`")


# ==========================================
# 4. SHORTENER & SYSTEM CONFIG COMMANDS
# ==========================================

@Client.on_message(filters.command("setshortener") & admin_filter)
async def set_shortener_cmd(bot: Client, message: Message):
    try:
        args = message.text.split(maxsplit=2)
        site = args[1].strip().replace("https://", "").replace("http://", "").strip("/")
        api = args[2].strip()

        await update_settings({"shortener_url": site, "shortener_api": api})
        await message.reply_text(f"✅ **Shortener Saved!**\n\n🌐 **Domain:** `{site}`\n🔑 **API Key:** `{api}`")
    except Exception:
        await message.reply_text("❌ गलत उपयोग। ऐसे लिखें:\n`/setshortener gplinks.in your_api_key`")


@Client.on_message(filters.command("seturl") & admin_filter)
async def set_url_cmd(bot: Client, message: Message):
    try:
        url = message.text.split(" ", 1)[1].strip().replace("https://", "").replace("http://", "").strip("/")
        await update_settings({"shortener_url": url})
        await message.reply_text(f"🌐 Shortener Domain set to: `{url}`")
    except IndexError:
        await message.reply_text("❌ गलत उपयोग। ऐसे लिखें:\n`/seturl droplink.co`")


@Client.on_message(filters.command("setapi") & admin_filter)
async def set_api_cmd(bot: Client, message: Message):
    try:
        api = message.text.split(" ", 1)[1].strip()
        await update_settings({"shortener_api": api})
        await message.reply_text("🔑 API Key updated successfully!")
    except IndexError:
        await message.reply_text("❌ गलत उपयोग। ऐसे लिखें:\n`/setapi your_api_key_here`")


@Client.on_message(filters.command("setverifytime") & admin_filter)
async def set_verify_time_cmd(bot: Client, message: Message):
    try:
        hours = int(message.text.split(" ", 1)[1].strip())
        await update_settings({"verify_expire_hours": hours})
        await message.reply_text(f"⏱️ Verification Validity set to **{hours} Hours**!")
    except Exception:
        await message.reply_text("❌ गलत उपयोग। ऐसे लिखें:\n`/setverifytime 24`")


@Client.on_message(filters.command("setautodelete") & admin_filter)
async def set_autodelete_time_cmd(bot: Client, message: Message):
    try:
        minutes = int(message.text.split(" ", 1)[1].strip())
        await update_settings({"auto_delete_minutes": minutes})
        await message.reply_text(f"⏱️ Auto-Delete Timer set to **{minutes} Minutes**!")
    except Exception:
        await message.reply_text("❌ गलत उपयोग। ऐसे लिखें:\n`/setautodelete 10`")
