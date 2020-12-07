from steam.client import SteamClient
from csgo.client import CSGOClient
from csgo.enums import ECsgoGCMsg

__all__ = ['csgo_client']

class csgo_client (object):
    def __init__(self, config):
        self._client = SteamClient()
        self._client.set_credential_location(config["steam_credential_location"])
        self._cs = CSGOClient(self._client)

        self._ready = False

        @self._client.on('logged_on')
        def start_csgo():
            self._cs.launch()

        @self._cs.on('ready')
        def gc_ready():
            self._ready = True

        self._client.cli_login(username=config["steam_bot_username"], password=config["steam_bot_password"])

        while not self._ready:
            self._client.sleep(0.125)
    
    def send(self, *args, **kwargs):
        self._cs.send(*args, **kwargs)

    def wait_event(self, *args, **kwargs):
        return self._cs.wait_event(*args, **kwargs)

    def get_item_killcount(self, s, a, d):
        self.send(ECsgoGCMsg.EMsgGCCStrike15_v2_Client2GCEconPreviewDataBlockRequest, {
            'param_s': s,
            'param_a': a,
            'param_d': d,
            'param_m': 0
        })
        response, = self.wait_event(ECsgoGCMsg.EMsgGCCStrike15_v2_Client2GCEconPreviewDataBlockResponse, timeout=2)
        if response.iteminfo.itemid != a:
            raise ValueError("mismatched req/rep, pls retry")
        return response.iteminfo.killeatervalue
