from pyrogram import Client, filters
from pyrogram.types import Message
import config
from database import ban_user, unban_user, users_col

ADMINS = getattr(config, "ADMINS", [])

# 1. Manual Ban Command
@Client.on_message(filters.command("ban") & filters.private)
async def ban_command_handler(bot: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return

    if len(message.command) < 2:
        return await message.reply_text(
            "<b>Usage:</b> <code>/ban <user_id> <reason></code>\n\n"
            "<b>Example:</b> <code>/ban 123456789 Script Abuse</code>"
        )

    try:
        user_id = int(message.command[1])
        reason = " ".join(message.command[2:]) if len(message.command) > 2 else "Banned by Admin"

        await ban_user(user_id, reason=reason)
        await message.reply_text(
            f"✅ <b>User Banned Successfully!</b>\n\n"
            f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
            f"📝 <b>Reason:</b> {reason}"
        )
    except ValueError:
        await message.reply_text("❌ <i>Invalid User ID! ID numeric honi chahiye.</i>")
    except Exception as e:
        await message.reply_text(f"❌ <b>Error:</b> `{e}`")


# 2. Manual Unban Command
@Client.on_message(filters.command("unban") & filters.private)
async def unban_command_handler(bot: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return

    if len(message.command) < 2:
        return await message.reply_text(
            "<b>Usage:</b> <code>/unban <user_id></code>\n\n"
            "<b>Example:</b> <code>/unban 123456789</code>"
        )

    try:
        user_id = int(message.command[1])

        await unban_user(user_id)
        await message.reply_text(
            f"🎉 <b>User Unbanned Successfully!</b>\n\n"
            f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
            f"🔄 <i>Bypass attempts reset to 0.</i>"
        )
    except ValueError:
        await message.reply_text("❌ <i>Invalid User ID!</i>")
    except Exception as e:
        await message.reply_text(f"❌ <b>Error:</b> `{e}`")


# 3. Banned Users Count & List Command
@Client.on_message(filters.command("banned") & filters.private)
async def banned_list_handler(bot: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return

    try:
        # DB se un sabhi users ko find karein jinka is_banned True hai
        banned_users = await users_col.find({"is_banned": True}).to_list(length=100)
        total_banned = len(banned_users)

        if total_banned == 0:
            return await message.reply_text("✅ <b>No users are currently banned!</b>")

        text = f"🚫 <b>Total Banned Users:</b> <code>{total_banned}</code>\n\n"
        for idx, user in enumerate(banned_users[:20], 1):  # Starting 20 users show honge
            u_id = user.get("user_id")
            reason = user.get("ban_reason", "No reason")
            text += f"{idx}. <code>{u_id}</code> — {reason}\n"

        if total_banned > 20:
            text += f"\n<i>...and {total_banned - 20} more users.</i>"

        await message.reply_text(text)
    except Exception as e:
        await message.reply_text(f"❌ <b>Error:</b> `{e}`")
