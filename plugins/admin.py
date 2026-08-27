from pyrogram import Client, filters
from pyrogram.types import Message
import config
from database import (
    get_settings, update_settings,
    add_story_mapping, delete_story_mapping, get_all_stories
)

admin_filter = filters.user(config.ADMINS)

# 1. Dashboard Settings Panel
@Client.on_message(filters.command("settings") & admin_filter)
async def settings_cmd(bot: Client, message: Message):
    s = await get_settings()
    
    protect_status = "✅ ON" if s.get("protect_content") else "❌ OFF"
    autodel_status = "✅ ON" if s.get("auto_delete_enabled") else "❌ OFF"
    verify_status = "✅ ON" if s.get("shortener_verify_enabled") else "❌ OFF"
    
    short_url = s.get("shortener_url", "Not Set")
    short_api = s.get("shortener_api", "")
    api_display = f"`{short_api[:6]}...{short_api[-4:]}`" if len(short_api) > 10 else "`Not Set`"

    msg = (
        "⚙️ **Bot Control Settings Panel**\n\n"
        f"🔗 **Shortener Verification:** {verify_status}\n"
        f"🌐 **Current Shortener Site:** `{short_url}`\n"
        f"🔑 **Shortener API Key:** {api_display}\n"
        f"⏱️ **Verify Expire Time:** `{s.get('verify_expire_hours')} Hours`\n\n"
        f"🔒 **Content Protection:** {protect_status}\n"
        f"🗑️ **Auto-Delete Mode:** {autodel_status}\n"
        f"⏳ **Auto-Delete Time:** `{s.get('auto_delete_minutes')} Minutes`\n\n"
        "🛠️ **Commands List:**\n"
        "• `/setshortener <domain> <api>` - Set Shortener Site & API Key\n"
        "• `/seturl <domain>` | `/setapi <api>` - Set individual parameters\n"
        "• `/toggleverify` - Turn Shortener Verification ON/OFF\n"
        "• `/setverifytime <hours>` - Set Verification Expire Time\n"
        "• `/toggleprotect` - Turn Content Protection ON/OFF\n"
        "• `/toggleautodelete` - Turn Auto-Delete ON/OFF\n"
        "• `/setautodelete <minutes>` - Set Auto-Delete Timer\n"
        "• `/addstory` | `/delstory` | `/liststories` - Manage Story Mappings"
    )
    await message.reply_text(msg)

# 2. Story Mapping Commands
@Client.on_message(filters.command("addstory") & admin_filter)
async def add_story_cmd(bot: Client, message: Message):
    try:
        args = message.text.split(" ", 1)[1].split("|")
        story_name = args[0].strip()
        target_id = int(args[1].strip())
        threshold = int(args[2].strip()) if len(args) > 2 else config.DEFAULT_THRESHOLD

        await add_story_mapping(story_name, target_id, threshold)
        await message.reply_text(
            f"✅ **Story Mapped Successfully!**\n\n"
            f"📌 **Story Keyword:** `{story_name}`\n"
            f"🎯 **Target Channel:** `{target_id}`\n"
            f"📊 **Threshold:** `{threshold} files`"
        )
    except Exception:
        await message.reply_text("❌ **Usage:** `/addstory Story Keyword | -100xxxxxxxxx | [threshold]`")

@Client.on_message(filters.command("delstory") & admin_filter)
async def del_story_cmd(bot: Client, message: Message):
    try:
        story_name = message.text.split(" ", 1)[1].strip()
        if await delete_story_mapping(story_name):
            await message.reply_text(f"🗑️ Story `{story_name}` removed successfully!")
        else:
            await message.reply_text("⚠️ Story not found in database.")
    except IndexError:
        await message.reply_text("❌ Usage: `/delstory story_keyword`")

@Client.on_message(filters.command("liststories") & admin_filter)
async def list_stories_cmd(bot: Client, message: Message):
    stories = await get_all_stories()
    if not stories:
        return await message.reply_text("ℹ️ No mapped stories found.")
    
    msg = "📚 **Mapped Stories & Target Channels:**\n\n"
    for s in stories:
        msg += f"• **Keyword:** `{s['story_key']}` | **Channel:** `{s['target_chat_id']}` | **Threshold:** `{s['threshold']}`\n"
    await message.reply_text(msg)

# 3. Dynamic Shortener Commands
@Client.on_message(filters.command("setshortener") & admin_filter)
async def set_shortener_cmd(bot: Client, message: Message):
    try:
        args = message.text.split(maxsplit=2)
        site = args[1].strip().replace("https://", "").replace("http://", "").strip("/")
        api = args[2].strip()

        await update_settings("shortener_url", site)
        await update_settings("shortener_api", api)
        await message.reply_text(f"✅ **Shortener Settings Saved:** `{site}`")
    except Exception:
        await message.reply_text("❌ **Usage:** `/setshortener gplinks.in <api_key>`")

@Client.on_message(filters.command("seturl") & admin_filter)
async def set_url_cmd(bot: Client, message: Message):
    try:
        url = message.text.split(" ", 1)[1].strip().replace("https://", "").replace("http://", "").strip("/")
        await update_settings("shortener_url", url)
        await message.reply_text(f"🌐 **Shortener Site Domain set to:** `{url}`")
    except IndexError:
        await message.reply_text("❌ **Usage:** `/seturl droplink.co`")

@Client.on_message(filters.command("setapi") & admin_filter)
async def set_api_cmd(bot: Client, message: Message):
    try:
        api = message.text.split(" ", 1)[1].strip()
        await update_settings("shortener_api", api)
        await message.reply_text(f"🔑 **API Key updated successfully!**")
    except IndexError:
        await message.reply_text("❌ **Usage:** `/setapi <api_key>`")

@Client.on_message(filters.command("toggleverify") & admin_filter)
async def toggle_verify_cmd(bot: Client, message: Message):
    s = await get_settings()
    new_state = not s.get("shortener_verify_enabled", True)
    await update_settings("shortener_verify_enabled", new_state)
    await message.reply_text(f"🔗 **Shortener Verification is now {'ENABLED ✅' if new_state else 'DISABLED ❌'}**")

@Client.on_message(filters.command("setverifytime") & admin_filter)
async def set_verify_time_cmd(bot: Client, message: Message):
    try:
        hours = int(message.text.split(" ", 1)[1].strip())
        await update_settings("verify_expire_hours", hours)
        await message.reply_text(f"⏱️ **Verification Validity set to `{hours} Hours`!**")
    except Exception:
        await message.reply_text("❌ **Usage:** `/setverifytime <hours>`")

# 4. Protection & Auto-Delete Toggle Commands
@Client.on_message(filters.command("toggleprotect") & admin_filter)
async def toggle_protect_cmd(bot: Client, message: Message):
    s = await get_settings()
    new_state = not s.get("protect_content", True)
    await update_settings("protect_content", new_state)
    await message.reply_text(f"🔒 **Content Protection is now {'ENABLED ✅' if new_state else 'DISABLED ❌'}**")

@Client.on_message(filters.command("toggleautodelete") & admin_filter)
async def toggle_autodelete_cmd(bot: Client, message: Message):
    s = await get_settings()
    new_state = not s.get("auto_delete_enabled", True)
    await update_settings("auto_delete_enabled", new_state)
    await message.reply_text(f"🗑️ **Auto-Delete Mode is now {'ENABLED ✅' if new_state else 'DISABLED ❌'}**")

@Client.on_message(filters.command("setautodelete") & admin_filter)
async def set_autodelete_time_cmd(bot: Client, message: Message):
    try:
        minutes = int(message.text.split(" ", 1)[1].strip())
        await update_settings("auto_delete_minutes", minutes)
        await message.reply_text(f"⏱️ **Auto-Delete Timer set to `{minutes} Minutes`!**")
    except Exception:
        await message.reply_text("❌ **Usage:** `/setautodelete <minutes>`")
