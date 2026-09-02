import time
import base64
import hmac
import hashlib
import aiohttp
import config
from database import get_settings, users_col, used_tokens_col

SECRET_KEY = getattr(config, "SECRET_KEY", "MySuperSecretKey123")

# 1. URL Shortener Helper Function
async def get_shortlink(long_url: str) -> str:
    """
    Long URL को Shortener API से शॉर्ट बनाता है।
    अगर API डाउन हो, एरर दे या डेटाबेस में डिटेल्स न हों तो ओरिजिनल long_url रिटर्न करता है।
    """
    s = await get_settings()
    
    # Database से वैल्यू लें, अगर खाली हो तो config.py से Fallback लें
    shortener_site = (s.get("shortener_url") or getattr(config, "SHORTENER_URL", "gplinks.in")).strip()
    shortener_api = (s.get("shortener_api") or getattr(config, "SHORTENER_API", "")).strip()

    if not shortener_api or not shortener_site:
        return long_url

    # Domain Formatting: https:// या http:// और Extra Slashes हटाना
    shortener_site = shortener_site.replace("https://", "").replace("http://", "").strip("/")
    api_url = f"https://{shortener_site}/api?api={shortener_api}&url={long_url}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    
                    short_link = (
                        data.get("shortenedUrl") 
                        or data.get("url") 
                        or data.get("shortlink") 
                        or data.get("link")
                        or data.get("short_url")
                    )
                    
                    if short_link and isinstance(short_link, str):
                        return short_link
                else:
                    print(f"❌ [Shortener HTTP Error]: Status {resp.status}")
                    
    except Exception as e:
        print(f"❌ [Shortener Exception Error]: {e}")
        
    return long_url


# 2. Payload Encryption & Verification Logic
def create_secure_payload(user_id: int, target_param: str) -> str:
    """Token me User ID, Target, Creation Time & Signature Embed karta h"""
    created_at = int(time.time())
    raw_str = f"{user_id}:{target_param}:{created_at}"
    
    # Generate HMAC Signature to prevent tampering
    signature = hmac.new(SECRET_KEY.encode(), raw_str.encode(), hashlib.sha256).hexdigest()[:10]
    payload = f"{raw_str}:{signature}"
    
    # Safe Base64 Encoding
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_and_verify_payload(encoded_payload: str):
    """Payload decode karke signature, tampering aur data validation check karta h"""
    try:
        padding = "=" * (-len(encoded_payload) % 4)
        decoded_str = base64.urlsafe_b64decode(encoded_payload + padding).decode()
        parts = decoded_str.split(":")
        
        if len(parts) != 4:
            return None, None, None, False

        user_id, target_param, created_at, signature = int(parts[0]), parts[1], int(parts[2]), parts[3]
        
        # Verify Signature
        expected_raw = f"{user_id}:{target_param}:{created_at}"
        expected_sig = hmac.new(SECRET_KEY.encode(), expected_raw.encode(), hashlib.sha256).hexdigest()[:10]
        
        if hmac.compare_digest(signature, expected_sig):
            return user_id, target_param, created_at, True
        return None, None, None, False
    except Exception:
        return None, None, None, False
