from .steam_utils import *

__all__ = ['process_command']

COMMANDS = {}


def cmd(name):
    def decorator(fn):
        COMMANDS[name] = fn
    return decorator


async def process_command(ctx, who, message):
    cmd, *args = message.split(" ")
    # TODO: handle undefined command
    # TODO: handle exceptions
    if cmd in COMMANDS:
        return await COMMANDS[cmd](ctx, who, *args)
        

@cmd("register")
async def register(ctx, who, steam_url):
    # TODO: handle case where user is already registered
    # TODO: handle failure to resolve steam id
    await ctx.db.add_user(str(who), await get_user_id(steam_url))
    return None


@cmd("weapon")
async def weapon(ctx, who, inspect_url, *name):
    name = " ".join(name)
    key = "assetid%"
    idx = inspect_url.find(key)
    asset = inspect_url[idx+len(key):]
    # TODO: handle bad inspect url
    # TODO: handle get_user_id failure (user not registered)
    # TODO: verify that the item is in the user's inventory and is stattrak
    uid = await ctx.db.get_user_id(str(who))
    await ctx.db.add_weapon(uid, asset, name)


@cmd("watch")
async def watch(ctx, who, count, *name):
    name = " ".join(name)
    # TODO: handle get_user_id failure (user not registered)
    # TODO: handle get_weapon_id failure (weapon not added)
    # TODO: handle requested count <= current count
    uid = await ctx.db.get_user_id(str(who))
    wid = await ctx.db.get_weapon_id(uid, name)
    await ctx.db.add_watch(wid, int(count))

