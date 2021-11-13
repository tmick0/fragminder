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

    def add_watch(self, watch_id, count, wild):
        self.watches.append((watch_id, count, wild))


def get_next_wildcard_match(key, digits, current):
    mod = 10 ** digits
    target = mod * ((current + mod - 1) // mod) + key
    return target


default_alert_deltas = [20, 10, 5, 3, 2, 1]

async def do_update(ctx):

    users = await ctx.db.get_users()
    online_users = await ctx.steam.get_active_players([steam_id for _, _, _, steam_id, _ in users])

    for guild_id, user_id, discord_id, steam_id, alert_deltas in users:

        if alert_deltas is not None:
            alert_deltas = list(map(int, alert_deltas.split(",")))
        else:
            alert_deltas = default_alert_deltas

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

            if len(watches) == 0:
                continue

            # build lookup table for user's watched assets
            assets = asset_dict(asset_info)
            for watch_id, weapon_id, name, asset_id, class_id, instance_id, count, last_count, last_check, wildcard in watches:
                if wildcard:
                    count = get_next_wildcard_match(count, wildcard, last_count)
                assets[(asset_id, class_id, instance_id)].name = name
                assets[(asset_id, class_id, instance_id)].weapon_id = weapon_id
                assets[(asset_id, class_id, instance_id)].last_count = last_count
                assets[(asset_id, class_id, instance_id)].last_check = last_check
                assets[(asset_id, class_id, instance_id)].add_watch(watch_id, count, wildcard)

            # get steam inventory data
            data, missing = await ctx.steam.get_items_info(steam_id, list(assets.keys()))

            # notify user of missing items
            for a, c, i in missing:
                if not await ctx.db.known_missing(steam_id, c, i, a):
                    item = assets[(a, c, i)]
                    msg = '{}: your item `{}` is missing from your inventory, you might need to change its id or remove it'.format(user.mention, item.name)
                    await dest.send(msg)
                    await ctx.db.mark_missing(steam_id, c, i, a)

            # find items which need alerting
            alerts = []
            for key, data in data.items():

                a = assets[key]
                await ctx.db.update_weapon(a.weapon_id, data['stattrak'], datetime.now(tz=timezone.utc).timestamp())

                if a.last_count is None:
                    a.last_count = 0

                # check that count has changed since last update, otherwise do nothing
                if data['stattrak'] > a.last_count:

                    for watch_id, watch_count, is_wild in a.watches:

                        # check if we already hit the threshold
                        if data['stattrak'] >= watch_count:
                            if not is_wild:
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
