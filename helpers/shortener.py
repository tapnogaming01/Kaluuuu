import aiohttp
from database import get_settings

async def get_short_url(long_url: str) -> str:
    s = await get_settings()
    shortener_site = s.get("shortener_url", "gplinks.in").strip()
    shortener_api = s.get("shortener_api", "").strip()

    if not shortener_api or not shortener_site:
        return long_url

    # URL से https:// या http:// हटाकर क्लीन डोमेन बनाएँ
    shortener_site = shortener_site.replace("https://", "").replace("http://", "").strip("/")
    api_url = f"https://{shortener_site}/api?api={shortener_api}&url={long_url}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=10) as resp:
                # content_type=None ताकि अगर API text/plain भी भेजे तो json parse हो जाए
                data = await resp.json(content_type=None)
                
                # अलग-अलग Shorteners के Response Keys को सुरक्षित तरीके से चेक करें
                short_link = (
                    data.get("shortlink") 
                    or data.get("url") 
                    or data.get("shortenedUrl") 
                    or data.get("link")
                )
                
                # अगर valid string मिलती है तो ही रिटर्न करें
                if short_link and isinstance(short_link, str):
                    return short_link
                    
    except Exception as e:
        print(f"[Shortener Error]: {e}")
        
    # किसी भी असफलता या None मिलने पर हमेशा fallback long_url ही रिटर्न होगा
    return long_url
