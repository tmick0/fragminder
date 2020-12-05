import asyncio
import requests
import steam.steamid

__all__ = ['get_item_count', 'get_user_id']


page_limit = 100
gameid = 730


def build_url(user_id, last_assetid=""):
    return 'https://steamcommunity.com/inventory/{:d}/{:d}/2?l=english&count={:d}&start_assetid={}'.format(user_id, gameid, page_limit, last_assetid)


async def get_item_count(user_id, asset_id):
    loop = asyncio.get_event_loop()
    last_asset_id = ""

    while True:
        url = build_url(user_id, last_asset_id)
        r = await loop.run_in_executor(None, requests.get, url)
        if not r.status_code == 200: # error
            break
        data = r.json()
        if not 'assets' in data: # reached end
            break
        last_asset_id = data["assets"][-1]["assetid"]

        for item in data['descriptions']:
            if not 'actions' in item:
                continue

            for action in item['actions']:
                if action['name'].startswith("Inspect"):
                    inspect_url = action["link"]
                    break
            else: # this item doesn't have an inspect url
                continue

            if not inspect_url.endswith("%{}".format(asset_id)): # this is not the item
                continue

            for desc in item['descriptions']:
                if desc['value'].startswith('StatTrak'):
                    return int(desc['value'].split(' ')[-1])
            else: # the item is not stattrak
                return None


async def get_user_id(steam_profile_url):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, steam.steamid.steam64_from_url, steam_profile_url)
