import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
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

@Client.on_message(filters.chat(config.SOURCE_CHANNEL) & (filters.document | filters.audio))
async def source_channel_handler(bot: Client, message: Message):
    try:
        caption = message.caption or message.document.file_name or message.audio.title or ""
        story = await find_story_by_caption(caption)
        
        if not story:
            await send_log(bot, f"⚠️ **Unmapped File Received:** Caption: `{caption[:80]}`")
            return

        story_key = story['story_key']
        target_channel_id = story['target_chat_id']
        threshold = story['threshold']

        start_ep, end_ep = parse_episodes(caption)
        saved_msg = await message.copy(config.DB_CHANNEL)

        is_multi_ep = (start_ep is not None and end_ep is not None and end_ep > start_ep)

        # 1. Combined Audio File Case (e.g., 1-10 episodes in single file)
        if is_multi_ep:
            batch_link = f"https://t.me/{config.BOT_USERNAME}?start=file_{saved_msg.id}"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🎧 Listen Eps {start_ep}-{end_ep} ↗️", url=batch_link)],
                [InlineKeyboardButton("TUTORIAL ↗️", url="https://t.me/your_tutorial"), InlineKeyboardButton("HELP ↗️", url="https://t.me/your_help")]
            ])
            await bot.send_message(
                chat_id=target_channel_id,
                text=f"<b>{story_key.title()}</b>\n\n<b>MMH EPS {start_ep} - {end_ep}</b>",
                reply_markup=keyboard
            )
            await send_log(bot, f"🚀 **Combined File Posted:** `{story_key}` (Eps {start_ep}-{end_ep}) in `{target_channel_id}`")
            return

        # 2. Single Episode Case: Add to Buffer
        await add_to_buffer(story_key, saved_msg.id, start_ep)
        msg_ids, ep_nums = await get_buffer(story_key)

        # 3. Post when Buffer Threshold is Reached
        if len(msg_ids) >= threshold:
            first_ep = ep_nums[0] if ep_nums and ep_nums[0] else "Start"
            last_ep = ep_nums[-1] if ep_nums and ep_nums[-1] else "End"
            batch_link = f"https://t.me/{config.BOT_USERNAME}?start=batch_{msg_ids[0]}_{msg_ids[-1]}"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"Eps {first_ep}-{last_ep} ({len(msg_ids)} Files) ↗️", url=batch_link)],
                [InlineKeyboardButton("TUTORIAL ↗️", url="https://t.me/your_tutorial"), InlineKeyboardButton("HELP ↗️", url="https://t.me/your_help")]
            ])

            await bot.send_message(
                chat_id=target_channel_id,
                text=f"<b>{story_key.title()}</b>\n\n<b>EPISODES {first_ep} - {last_ep}</b>",
                reply_markup=keyboard
            )
            await send_log(bot, f"📦 **Batch Posted:** `{story_key}` ({len(msg_ids)} Files) in `{target_channel_id}`")
            await clear_buffer(story_key)

    except Exception as e:
        await send_error_log(bot, e, "Source Channel Handler Error")
