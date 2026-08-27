from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta, timezone
import config

client = AsyncIOMotorClient(config.MONGO_URL)
db = client['MultiStoryBatchBot']

stories_col = db['stories']
buffer_col = db['buffers']
users_col = db['users']
settings_col = db['bot_settings']

# 1. Global Settings Control
async def get_settings():
    settings = await settings_col.find_one({"id": "global_settings"})
    if not settings:
        default_data = {
            "id": "global_settings",
            "protect_content": config.PROTECT_CONTENT,
            "auto_delete_enabled": config.AUTO_DELETE_ENABLED,
            "auto_delete_minutes": config.AUTO_DELETE_MINUTES,
            "shortener_verify_enabled": config.SHORTENER_VERIFY_ENABLED,
            "verify_expire_hours": config.VERIFY_EXPIRE_HOURS,
            "shortener_url": config.SHORTENER_URL,
            "shortener_api": config.SHORTENER_API
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
    return await stories_col.find({}).to_list(length=100)

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

# 4. User Verification System
async def is_user_verified(user_id: int) -> bool:
    user = await users_col.find_one({"user_id": user_id})
    if not user or "verified_until" not in user:
        return False
    
    verified_until = user["verified_until"]
    if verified_until.tzinfo is None:
        verified_until = verified_until.replace(tzinfo=timezone.utc)
        
    return datetime.now(timezone.utc) < verified_until

async def set_user_verified(user_id: int, hours: int = 12):
    expire_time = datetime.now(timezone.utc) + timedelta(hours=hours)
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"verified_until": expire_time}},
        upsert=True
    )
