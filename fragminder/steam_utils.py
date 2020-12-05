import asyncio
import steam.steamid

__all__ = ['get_user_id']


async def get_user_id(steam_profile_url):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, steam.steamid.steam64_from_url, steam_profile_url)
