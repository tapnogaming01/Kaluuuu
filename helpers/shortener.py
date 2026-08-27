import aiohttp
from database import get_settings

async def get_short_url(long_url: str) -> str:
    s = await get_settings()
    shortener_site = s.get("shortener_url", "gplinks.in")
    shortener_api = s.get("shortener_api", "")

    if not shortener_api:
        return long_url

    api_url = f"https://{shortener_site}/api?api={shortener_api}&url={long_url}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                data = await resp.json()
                if data.get("status") == "success":
                    return data.get("shortlink") or data.get("url")
                elif "shortenedUrl" in data:
                    return data.get("shortenedUrl")
    except Exception:
        pass
        
    return long_url
