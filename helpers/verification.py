import aiohttp
import config
from database import get_settings

async def get_short_url(long_url: str) -> str:
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

    # Domain Formatting: https:// या http:// और Extra Slashes हटाकर Clean Domain बनाना
    shortener_site = shortener_site.replace("https://", "").replace("http://", "").strip("/")
    api_url = f"https://{shortener_site}/api?api={shortener_api}&url={long_url}"
    
    try:
        # Timeout 10s रखा गया है ताकि API स्लो होने पर बोट अटके नहीं
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    # content_type=None से text/plain या text/html रिस्पॉन्स भी JSON में हैंडल होता है
                    data = await resp.json(content_type=None)
                    
                    # अलग-अलग Shorteners API के keys चेक करना
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
        
    # किसी भी असफलता पर हमेशा safe fallback long_url रिटर्न होगा
    return long_url
