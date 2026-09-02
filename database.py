from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta, timezone
import config

client = AsyncIOMotorClient(config.MONGO_URL)
db = client['MultiStoryBatchBot']

stories_col = db['stories']
buffer_col = db['buffers']
users_col = db['users']
settings_col = db['bot_settings']
used_tokens_col = db['used_tokens']  # Used/Burned Tokens for Anti-Bypass

# 1. Global Settings Control
async def get_settings():
    settings = await settings_col.find_one({"id": "global_settings"})
    if not settings:
        default_data = {
            "id": "global_settings",
            "protect_content": getattr(config, "PROTECT_CONTENT", True),
            "auto_delete_enabled": getattr(config, "AUTO_DELETE_ENABLED", True),
            "auto_delete_minutes": getattr(config, "AUTO_DELETE_MINUTES", 5),
            "shortener_verify_enabled": getattr(config, "SHORTENER_VERIFY_ENABLED", True),
            "verify_expire_hours": getattr(config, "VERIFY_EXPIRE_HOURS", 12),
            "shortener_url": getattr(config, "SHORTENER_URL", ""),
            "shortener_api": getattr(config, "SHORTENER_API", "")
        }
        await settings_col.insert_one(default_data)
        return default_data
    return settings

async def update_settings(key: str, value):
    await settings_col.update_one(
        {"id": "global_settings"},
        {"$set": {key: value}},
        upsert=True
    )

# 2. Story Mapping System
async def add_story_mapping(story_key: str, target_chat_id: int, threshold: int = 5):
    story_key = story_key.lower().strip()
    await stories_col.update_one(
        {"story_key": story_key},
        {"$set": {
            "story_key": story_key,
            "target_chat_id": target_chat_id,
            "threshold": threshold
        }},
        upsert=True
    )

async def delete_story_mapping(story_key: str):
    story_key = story_key.lower().strip()
    res = await stories_col.delete_one({"story_key": story_key})
    return res.deleted_count > 0

async def get_all_stories():
    return await stories_col.find({}).to_list(length=200)

async def find_story_by_caption(caption: str):
    if not caption:
        return None
    caption_lower = caption.lower()
    for story in await get_all_stories():
        if story['story_key'] in caption_lower:
            return story
    return None

# 3. Buffer System
async def add_to_buffer(story_key: str, file_msg_id: int, ep_num: int = None):
    await buffer_col.update_one(
        {"story_key": story_key},
        {"$push": {"msg_ids": file_msg_id, "ep_nums": ep_num}},
        upsert=True
    )

async def get_buffer(story_key: str):
    data = await buffer_col.find_one({"story_key": story_key})
    return (data.get("msg_ids", []), data.get("ep_nums", [])) if data else ([], [])

async def clear_buffer(story_key: str):
    await buffer_col.delete_one({"story_key": story_key})

# 4. Ban & Anti-Bypass Database Logic
async def is_user_banned(user_id: int) -> tuple[bool, str]:
    """चेक करता है कि यूजर बैन है या नहीं"""
    user = await users_col.find_one({"user_id": user_id})
    if user and user.get("is_banned", False):
        return True, user.get("ban_reason", "No reason provided")
    return False, ""

async def increment_bypass_count(user_id: int) -> int:
    """बायपास अटेम्प्ट काउंटर +1 बढ़ाता है"""
    res = await users_col.find_one_and_update(
        {"user_id": user_id},
        {"$inc": {"bypass_attempts": 1}},
        upsert=True,
        return_document=True
    )
    return res.get("bypass_attempts", 1)

async def ban_user(user_id: int, reason: str = "Bypass Abuse"):
    """यूजर को परमानेंट बैन करता है"""
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"is_banned": True, "ban_reason": reason}},
        upsert=True
    )

async def unban_user(user_id: int):
    """यूजर को अनबैन करता है और स्ट्राइक काउंट 0 कर देता है"""
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"is_banned": False, "bypass_attempts": 0}, "$unset": {"ban_reason": ""}},
        upsert=True
    )

# 5. Token Burning Logic
async def is_token_burned(encoded_payload: str) -> bool:
    """चेक करता है कि टोकन पहले यूज़ हो चुका है या नहीं"""
    burned = await used_tokens_col.find_one({"token": encoded_payload})
    return bool(burned)

async def burn_token(encoded_payload: str):
    """टोकन को डेटाबेस में बर्न दर्ज करता है"""
    await used_tokens_col.insert_one({
        "token": encoded_payload,
        "burned_at": datetime.now(timezone.utc)
    })
