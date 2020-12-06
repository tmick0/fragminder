from collections import defaultdict
from datetime import datetime, timezone
import discord

__all__ = ['do_update']

class asset_dict (defaultdict):
    def __missing__(self, key):
        self[key] = self.default_factory(key)
        return self[key]


class asset_info (object):
    def __init__(self, asset_id):
        self.asset_id = asset_id
        self.name = None
        self.weapon_id = None
        self.last_count = None
        self.last_check = None
        self.watches = []

    def add_watch(self, watch_id, count):
        self.watches.append((watch_id, count))
    

alert_deltas = [20, 10, 5, 3, 2, 1]

async def do_update(ctx):

    await ctx.wait_until_ready()

    users = await ctx.db.get_users()
    online_users = await ctx.steam.get_active_players([steam_id for _, _, _, steam_id in users])

    for guild_id, user_id, discord_id, steam_id in users:

        if steam_id in online_users:

            # look up user
            user = await ctx.fetch_user(discord_id)

            # determine where we should send notifications for this user
            channel_id = await ctx.db.get_guild(guild_id)
            if channel_id:
                dest = ctx.get_channel(channel_id)
            else:
                dest = user

            # TODO: handle a user being registered in multiple guilds, in which case we should elide duplicate inventory lookups
            watches = await ctx.db.get_user_watches(user_id)

            # build lookup table for user's watched assets
            assets = asset_dict(asset_info)
            for watch_id, weapon_id, name, asset_id, count, last_count, last_check in watches:
                assets[asset_id].name = name
                assets[asset_id].weapon_id = weapon_id
                assets[asset_id].last_count = last_count
                assets[asset_id].last_check = last_check
                assets[asset_id].add_watch(watch_id, count)

            # get steam inventory data
            data = await ctx.steam.get_items_info(steam_id, list(assets.keys()))

            # find items which need alerting
            alerts = []
            for asset_id, data in data.items():

                a = assets[asset_id]
                await ctx.db.update_weapon(a.weapon_id, data['stattrak'], datetime.now(tz=timezone.utc).timestamp())

                if a.last_count is None:
                    a.last_count = 0

                # check that count has changed since last update, otherwise do nothing
                if data['stattrak'] > a.last_count:

                    for watch_id, watch_count in a.watches:

                        # check if we already hit the threshold
                        if data['stattrak'] >= watch_count:
                            await ctx.db.remove_watch(watch_id)
                            alerts.append({
                                'hit': True,
                                'delta': 0,
                                'watch_count': watch_count,
                                'asset': a,
                                'data': data
                            })
                            continue

                        # determine the last alert we would have sent
                        last_delta = watch_count - a.last_count
                        try:
                            last_alert = [a for a in alert_deltas if a >= last_delta][-1]
                        except IndexError:
                            last_alert = alert_deltas[0] + 1

                        # determine the current alert we would send
                        delta = watch_count - data['stattrak']
                        try:
                            this_alert = [a for a in alert_deltas if a >= delta][-1]
                        except IndexError: # we haven't passed the first alert threshold yet
                            continue

                        # skip if this is a duplicate alert
                        if last_alert == this_alert: 
                            continue

                        alerts.append({
                            'hit': False,
                            'delta': delta,
                            'watch_count': watch_count,
                            'asset': a,
                            'data': data
                        })
            
            for a in alerts:
                embed = discord.Embed()
                embed.set_image(url=a['data']['image'])
                if a['hit']:
                    msg = "{}: you've hit your goal of {:d} on your {:s} (`{:s}`)! hope you got the screenshot~~".format(user.mention, a['watch_count'], a['data']['name'], a['asset'].name)
                else:
                    msg = "{}: you're {:d} away from your goal of {:d} on your {:s} (`{:s}`)!".format(user.mention, a['delta'], a['watch_count'], a['data']['name'], a['asset'].name)
                await dest.send(msg, embed=embed)
