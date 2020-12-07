import asyncio
import requests
import urllib.parse
import re
import logging
from .csgo_client import csgo_client

__all__ = ['steamapi']

class steamapi(object):

    _gameid = 730
    _inspect_url_regex = re.compile('^steam://rungame/730/.*S([0-9]+)A([0-9]+)D([0-9]+)$')

    def __init__(self, config):
        self._key = config['steam_api_key']
        self._config = config
        self._client = csgo_client(config)

    def parse_inspect_url(self, url):
        match = self._inspect_url_regex.match(url)
        if not match:
            return None, None, None
        return int(match[1]), int(match[2]), int(match[3])

    def _build_inventory_url(self, user_id, last_assetid=None):
        page_limit = 1000
        url = 'https://steamcommunity.com/inventory/{:d}/{:d}/2?l=english&count={:d}'.format(user_id, self._gameid, page_limit)
        if last_assetid:
            url += '&start_assetid={}'.format(last_assetid)
        return url

    def _build_summaries_url(self, user_ids):
        return 'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={}&steamids={}&format=json'.format(self._key, ";".join(map(str, user_ids)))

    def _build_resolve_url(self, vanityurl):
        return 'https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?key={}&vanityurl={}&url_type=1'.format(self._key, vanityurl)

    def _build_item_preview_url(self, icon):
        return 'https://steamcommunity-a.akamaihd.net/economy/image/{}/330x192'.format(icon)

    def _build_inspect_url(self, url_template, uid, assetid):
        return url_template.replace('%owner_steamid%', str(uid)).replace('%assetid%', str(assetid))

    async def get_active_players(self, user_ids):
        loop = asyncio.get_event_loop()
        max_users_per_request = 32

        res = []
        for i in range(0, len(user_ids), max_users_per_request):
            user_ids_subset = user_ids[i:i+max_users_per_request]
            url = self._build_summaries_url(user_ids_subset)
            r = await loop.run_in_executor(None, requests.get, url)
            if not r.status_code == 200: # error
                raise RuntimeError("failed to fetch active players")
            data = r.json()
            for p in data['response']['players']:
                if 'gameid' in p and p['gameid'] == str(self._gameid):
                    res.append(int(p['steamid']))
        return res

    async def get_items_info(self, user_id, asset_ids):
        # TODO: if inventory calls get ratelimited, look into using authenticated
        # ISteamEconomy/GetAssetClassInfo call -- we will have to look up the
        # classid/instanceid just once with the public inventory api and store them

        loop = asyncio.get_event_loop()
        last_asset_id = None

        result = {}
        while True:
            url = self._build_inventory_url(user_id, last_asset_id)
            r = await loop.run_in_executor(None, requests.get, url)
            if not r.status_code == 200: # error
                raise RuntimeError("failed to fetch inventory")
            data = r.json()
            if not 'assets' in data: # reached end
                break

            # we have to map the 'assets' list to the 'descriptions' list via the (classid, instanceid) tuple
            # the asset dict contains the assetid which we obtained from the inspect url, while descriptions has everything else we need
            keys = {}
            for asset in data["assets"]:
                if int(asset["assetid"]) in asset_ids:
                    keys[(asset["classid"], asset["instanceid"])] = int(asset["assetid"])

            for item in data['descriptions']:
                key = (item["classid"], item["instanceid"])
                if not key in keys: # this is not one of the requested items
                    continue
                if not 'actions' in item: # not inspectable
                    continue
                
                for action in item['actions']:
                    if action['name'].startswith('Inspect'):
                        inspect_link = self._build_inspect_url(action['link'], user_id, keys[key])
                        break
                else: # failed to find inspect link
                    continue

                s, a, d = self.parse_inspect_url(inspect_link)
                retry_count = 0
                while retry_count < 5:
                    try:
                        st_count = await loop.run_in_executor(None, self._client.get_item_killcount, s, a, d)
                    except (TypeError, ValueError):
                        # TODO: fix this dumb hack
                        await asyncio.sleep(0.25)
                        retry_count += 1
                        continue
                    except Exception as e:
                        logging.warning("failed to get st count for {} {} {}".format(s, a, d))
                        logging.exception(e)
                    break
                if retry_count == 5:
                    logging.warning("too many failures on getting st count for {} {} {}".format(s, a, d))
                    continue

                result[keys[key]] = {
                    'stattrak': st_count,
                    'name': item['name'],
                    'image': self._build_item_preview_url(item['icon_url'])
                }
            
            if 'more_items' in data and data['more_items']:
                last_asset_id = data['last_asset_id']
            else:
                break

        return result

    async def get_user_id(self, steam_profile_url):
        loop = asyncio.get_event_loop()
        parsed = urllib.parse.urlparse(steam_profile_url)
        if not parsed.netloc in ('steamcommunity.com',): # not a profile url at all
            return None
        parts = parsed.path.split('/')[1:]
        if parts[0] == 'id': # resolve vanity url
            username = parsed.path.split('/')[1]
            url = self._build_resolve_url(parts[1])
            r = await loop.run_in_executor(None, requests.get, url)
            if not r.status_code == 200: # error
                return None
            data = r.json()
            if data['response']['success']:
                return data['response']['steamid']
            else: # error
                return None
        elif parts[0] == 'profile': # url contains the id
            steamid = parts[1]
            if not steamid.isnumeric(): # invalid
                return None
            return int(steamid)
        else: # invalid url
            return None
