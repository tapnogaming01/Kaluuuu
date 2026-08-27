import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
import config
from database import find_story_by_caption, add_to_buffer, get_buffer, clear_buffer
from helpers.logger import send_log, send_error_log

EPISODE_REGEX = r'(?:ep|eps|episode)?\s*(\d+)\s*(?:-|to|से|\s)*(\d+)?'

def parse_episodes(text: str):
    if not text:
        return None, None
    match = re.search(EPISODE_REGEX, text, re.IGNORECASE)
    if match:
        start_ep = int(match.group(1))
        end_ep = int(match.group(2)) if match.group(2) else start_ep
        return start_ep, end_ep
    return None, None

# SOURCE_CHANNEL ID ko safe Integer me convert karein
try:
    SOURCE_CHAT_ID = int(config.SOURCE_CHANNEL)
except Exception:
    SOURCE_CHAT_ID = config.SOURCE_CHANNEL

# Dynamic Filter: Document, Audio, Video, Voice sabhi cover karein
@Client.on_message(filters.chat(SOURCE_CHAT_ID) & (filters.document | filters.audio | filters.video | filters.voice))
async def source_channel_handler(bot: Client, message: Message):
    print(f"📥 [Source Channel] New File Received! Message ID: {message.id}")
    try:
        db_channel_id = int(config.DB_CHANNEL)
        
        # Peer cache Warm-up for DB Channel
        try:
            await bot.get_chat(db_channel_id)
        except Exception:
            pass

        # 1. Sabse pehle DB Channel me file COPY karein (Bina kisi condition ke)
        saved_msg = await message.copy(db_channel_id)
        print(f"✅ [DB Channel] File copied successfully! New DB Msg ID: {saved_msg.id}")

        # Caption safe extraction
        caption = message.caption or ""
        if not caption and message.document:
            caption = message.document.file_name or ""
        elif not caption and message.audio:
            caption = message.audio.title or message.audio.file_name or ""
        elif not caption and message.video:
            caption = message.video.file_name or ""

        story = await find_story_by_caption(caption)
        
        if not story:
            print(f"⚠️ Story mapping not found for caption: '{caption}'")
            await send_log(bot, f"⚠️ **Unmapped File Received & Saved to DB:** Caption: `{caption[:80]}`")
            return

        story_key = story['story_key']
        target_channel_id = int(story['target_chat_id'])
        threshold = int(story['threshold'])

        start_ep, end_ep = parse_episodes(caption)
        is_multi_ep = (start_ep is not None and end_ep is not None and end_ep > start_ep)

        # Target Channel Peer Cache Resolution
        try:
            await bot.get_chat(target_channel_id)
        except Exception as target_peer_err:
            await send_error_log(bot, target_peer_err, f"Target Channel `{target_channel_id}` Access Failed")

        # 2. Combined Audio File Case
        if is_multi_ep:
            batch_link = f"https://t.me/{config.BOT_USERNAME}?start=file_{saved_msg.id}"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🎧 Listen Eps {start_ep}-{end_ep} ↗️", url=batch_link)],
                [InlineKeyboardButton("TUTORIAL ↗️", url="https://t.me/your_tutorial"), InlineKeyboardButton("HELP ↗️", url="https://t.me/your_help")]
            ])
            try:
                await bot.send_message(
                    chat_id=target_channel_id,
                    text=f"<b>{story_key.title()}</b>\n\n<b>MMH EPS {start_ep} - {end_ep}</b>",
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                await send_log(bot, f"🚀 **Combined File Posted:** `{story_key}` (Eps {start_ep}-{end_ep}) in `{target_channel_id}`")
            except Exception as post_err:
                await send_error_log(bot, post_err, f"Target Channel `{target_channel_id}` Post Error")
            return

        # 3. Single Episode Case: Add to Buffer
        await add_to_buffer(story_key, saved_msg.id, start_ep)
        msg_ids, ep_nums = await get_buffer(story_key)

        # 4. Post when Buffer Threshold is Reached
        if len(msg_ids) >= threshold:
            first_ep = ep_nums[0] if ep_nums and ep_nums[0] else "Start"
            last_ep = ep_nums[-1] if ep_nums and ep_nums[-1] else "End"
            batch_link = f"https://t.me/{config.BOT_USERNAME}?start=batch_{msg_ids[0]}_{msg_ids[-1]}"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"Eps {first_ep}-{last_ep} ({len(msg_ids)} Files) ↗️", url=batch_link)],
                [InlineKeyboardButton("TUTORIAL ↗️", url="https://t.me/your_tutorial"), InlineKeyboardButton("HELP ↗️", url="https://t.me/your_help")]
            ])

            try:
                await bot.send_message(
                    chat_id=target_channel_id,
                    text=f"<b>{story_key.title()}</b>\n\n<b>EPISODES {first_ep} - {last_ep}</b>",
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                await send_log(bot, f"📦 **Batch Posted:** `{story_key}` ({len(msg_ids)} Files) in `{target_channel_id}`")
                await clear_buffer(story_key)
            except Exception as post_err:
                await send_error_log(bot, post_err, f"Target Channel `{target_channel_id}` Batch Post Error")

    except Exception as e:
        print(f"❌ Source Channel Handler Exception: {e}")
        await send_error_log(bot, e, "Source Channel Handler Error")
