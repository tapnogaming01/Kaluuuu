import time
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import config

client = AsyncIOMotorClient(config.MONGO_URL)
db = client['MultiStoryBatchBot']

stories_col = db['stories']
buffer_col = db['buffers']
users_col = db['users']
settings_col = db['bot_settings']
used_tokens_col = db['used_tokens']  # Used/Burned Tokens for Anti-Bypass
pending_req_col = db['pending_requests']  # 📩 Pending Join Requests Tracking

# -------------------------------------------------------------
# 1. Dynamic Time Parser Helper (e.g., '15m', '1h', '12h', '1d')
# -------------------------------------------------------------
def parse_time_to_seconds(time_str: str) -> int:
    """समय स्ट्रिंग (जैसे: 15m, 1h, 12h, 1d) को सेकंड्स में कन्वर्ट करता है"""
    time_str = str(time_str).lower().strip()
    try:
        if time_str.endswith("m"):
            return int(time_str[:-1]) * 60
        elif time_str.endswith("h"):
            return int(time_str[:-1]) * 3600
        elif time_str.endswith("d"):
            return int(time_str[:-1]) * 86400
        else:
            return int(time_str) * 3600  # डिफ़ॉल्ट घंटे
    except Exception:
        return 12 * 3600  # फॉलबैक 12 घंटे


# -------------------------------------------------------------
# 2. Global Settings Control (Updated with 3 Verification Slots)
# -------------------------------------------------------------
async def get_settings():
    settings = await settings_col.find_one({"id": "global_settings"})
    if not settings:
        default_data = {
            "id": "global_settings",
            "protect_content": getattr(config, "PROTECT_CONTENT", True),
            "auto_delete_enabled": getattr(config, "AUTO_DELETE_ENABLED", True),
            "auto_delete_minutes": getattr(config, "AUTO_DELETE_MINUTES", 5),
            
            # Dynamic 3 Verification Slots Settings
            "v1_url": getattr(config, "SHORTENER_URL", "gplinks.in"),
            "v1_api": getattr(config, "SHORTENER_API", ""),
            "v1_time": "12h",
            "v1_tutorial": "https://t.me/your_channel",
            "v1_enabled": getattr(config, "SHORTENER_VERIFY_ENABLED", True),

            "v2_url": "", "v2_api": "", "v2_time": "12h", "v2_tutorial": "", "v2_enabled": False,
            "v3_url": "", "v3_api": "", "v3_time": "12h", "v3_tutorial": "", "v3_enabled": False,

            # Force Subscribe Channels
            "fsub_1": getattr(config, "FSUB_CHANNEL_1", "https://t.me/your_channel"),
            "fsub_2": getattr(config, "FSUB_CHANNEL_2", "https://t.me/your_channel"),
            "fsub_3": getattr(config, "FSUB_CHANNEL_3", "https://t.me/your_channel"),
            "fsub_4": getattr(config, "FSUB_CHANNEL_4", "https://t.me/your_channel")
        }
        await settings_col.insert_one(default_data)
        return default_data
    return settings


async def update_settings(data, value=None):
    """
    1. update_settings({"fsub_1": "link"}) -> Dict फ़ॉर्मैट सपोर्ट करता है।
    2. update_settings("fsub_1", "link") -> Single Key-Value फ़ॉर्मैट सपोर्ट करता है।
    """
    if isinstance(data, dict):
        update_dict = data
    else:
        update_dict = {data: value}

    await settings_col.update_one(
        {"id": "global_settings"},
        {"$set": update_dict},
        upsert=True
    )


# -------------------------------------------------------------
# 3. User & Multi-Step Verification System
# -------------------------------------------------------------
async def add_user(user_id: int, name: str) -> bool:
    """
    यूज़र को ऐड करता है।
    अगर नया यूज़र है तो True, पुराना यूज़र है तो False रिटर्न करेगा।
    """
    user = await users_col.find_one({"user_id": user_id})
    if not user:
        await users_col.insert_one({
            "user_id": user_id,
            "name": name,
            "is_banned": False,
            "bypass_attempts": 0,
            "verifications": {
                "v1_until": 0,
                "v2_until": 0,
                "v3_until": 0
            },
            "joined_at": datetime.now(timezone.utc)
        })
        return True
    return False


async def get_user_verification_status(user_id: int) -> dict:
    """यूज़र का Dynamic Slot Verification Status रिटर्न करता है"""
    user = await users_col.find_one({"user_id": user_id}) or {}
    verifications = user.get("verifications", {})
    now = int(time.time())

    settings = await get_settings()

    v1_ok = (now < verifications.get("v1_until", 0)) if settings.get("v1_enabled") else True
    v2_ok = (now < verifications.get("v2_until", 0)) if settings.get("v2_enabled") else True
    v3_ok = (now < verifications.get("v3_until", 0)) if settings.get("v3_enabled") else True

    # अगला कौन सा Slot वेरीफाई करना बाकी है
    next_slot = None
    if settings.get("v1_enabled") and not v1_ok:
        next_slot = 1
    elif settings.get("v2_enabled") and not v2_ok:
        next_slot = 2
    elif settings.get("v3_enabled") and not v3_ok:
        next_slot = 3

    return {
        "v1": v1_ok,
        "v2": v2_ok,
        "v3": v3_ok,
        "is_fully_verified": v1_ok and v2_ok and v3_ok,
        "next_slot": next_slot
    }


async def set_user_slot_verified(user_id: int, slot_num: int):
    """किसी खास स्लॉट के टाइम के अनुसार यूज़र को वेरीफाई मार्क करता है"""
    settings = await get_settings()
    time_str = settings.get(f"v{slot_num}_time", "12h")
    seconds = parse_time_to_seconds(time_str)
    expire_time = int(time.time()) + seconds

    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {f"verifications.v{slot_num}_until": expire_time}},
        upsert=True
    )


# -------------------------------------------------------------
# 4. Story Mapping System
# -------------------------------------------------------------
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


# -------------------------------------------------------------
# 5. Buffer System
# -------------------------------------------------------------
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


# -------------------------------------------------------------
# 6. Ban & Anti-Bypass Database Logic
# -------------------------------------------------------------
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


# -------------------------------------------------------------
# 7. Token Burning Logic
# -------------------------------------------------------------
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


# -------------------------------------------------------------
# 8. Pending Join Request Tracking (Approval Link Feature)
# -------------------------------------------------------------
async def add_pending_request(user_id: int, chat_id: int):
    """जब कोई यूज़र प्राइवेट चैनल में Approval Request भेजेगा तो DB में रिकॉर्ड सेव होगा"""
    await pending_req_col.update_one(
        {"user_id": user_id},
        {"$addToSet": {"chat_ids": chat_id}},
        upsert=True
    )


async def is_request_pending(user_id: int, chat_id: int) -> bool:
    """चेक करता है कि क्या यूज़र ने संबंधित चैनल के लिए Request भेज रखी है"""
    req = await pending_req_col.find_one({"user_id": user_id, "chat_ids": chat_id})
    return bool(req)
