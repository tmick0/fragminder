from .steam_utils import *
from .help import format_help
from . import emoji

__all__ = ['process_command']

COMMANDS = {}


def cmd(name):
    def decorator(fn):
        COMMANDS[name] = fn
        return fn
    return decorator


async def process_command(ctx, msg, message):
    cmd, *args = message.split(" ")
    # TODO: handle undefined command
    # TODO: handle exceptions
    if cmd in COMMANDS:
        return await COMMANDS[cmd](ctx, msg, *args)
        

@cmd("register")
async def register(ctx, msg, steam_url):
    """ * desc: tell me who you are
        * args: steam_profile_url
        * example: https://steamcommunity.com/id/ql0000/
        * tip: do this first!
    """
    # TODO: handle bot receiving dm (guild will be null)
    # TODO: handle case where user is already registered
    # TODO: handle failure to resolve steam id
    await ctx.db.add_or_update_guild(msg.guild.id)
    await ctx.db.add_user(msg.guild.id, msg.author.id, await ctx.steam.get_user_id(steam_url))
    return {
        'react': emoji.party,
        'reply': 'welcome to the party!!!111'
    }


@cmd("weapon")
async def weapon(ctx, msg, inspect_url, *name):
    """ * desc: track a new stattrak item
        * args: inspect_url item_name...
        * example: steam://rungame/730/76561202255233023/+csgo_econ_action_preview%20S76561198116123325A17495329572D2918438303529470971 my fancy ak
        * tip: get the inspect url from your steam profile: <https://steamcommunity.com/my/inventory#730>
    """
    # TODO: handle bot receiving dm (guild will be null)
    # TODO: handle get_user_id failure (user not registered)
    # TODO: verify that the item is in the user's inventory and is stattrak

    name = " ".join(name)
    uid, sid = await ctx.db.get_user_id(msg.guild.id, msg.author.id)
    assetid, classid, instanceid = await ctx.steam.resolve_item_url(inspect_url)
    await ctx.db.add_weapon(uid, assetid, classid, instanceid, name)
    return {'react': emoji.thumbsup}


@cmd("weapons")
async def weapons(ctx, msg, *args):
    """ * desc: show the weapons you've registered with me
    """
    
    uid, _ = await ctx.db.get_user_id(msg.guild.id, msg.author.id)
    weapons = await ctx.db.get_user_weapons(uid)

    if len(weapons) == 0:
        return {'reply': "you haven't registered weapons, type `{}help weapon` to find out how".format(ctx.conf['command_prefix'])}

    msg = ""
    for _, name, last_count in weapons:
        msg += '\n * `{}` (last count: {})'.format(name, last_count)

    return {'reply': msg}


@cmd("rename")
async def rename(ctx, msg, *args):
    """ * desc: rename a registered weapon
        * args: old_name... -> new_name...
        * example: my fancy ak -> my crappy ak
    """
    
    delim = args.index('->')
    old_name = (" ".join(args[:delim])).strip()
    new_name = (" ".join(args[delim+1:])).strip()

    uid, _ = await ctx.db.get_user_id(msg.guild.id, msg.author.id)
    wid = await ctx.db.get_weapon_id(uid, old_name)

    if uid is None or wid is None:
        return {'react': emoji.thumbsdown}
    
    await ctx.db.rename_weapon(wid, new_name)

    return {'react': emoji.thumbsup}


@cmd("watches")
async def watches(ctx, msg):
    """ * desc: list your stattrak watches
    """
    uid, _ = await ctx.db.get_user_id(msg.guild.id, msg.author.id)
    watches = await ctx.db.get_user_watches(uid)
    msg = ""
    for _, _, name, _, _, _, count, _, _ in watches:
        msg += "\n * `{}`: {:d}".format(name, count)
    return {'reply': msg}


@cmd("unwatch")
async def unwatch(ctx, msg, count, *name):
    """ * desc: remove a stattrak count watch
        * args: number item_name...
        * example: 6969my fancy ak
    """
    name = " ".join(name)
    # TODO: handle bot receiving dm (guild will be null)
    # TODO: handle get_user_id failure (user not registered)
    # TODO: handle get_weapon_id failure (weapon not added)
    # TODO: handle requested count <= current count
    uid, _ = await ctx.db.get_user_id(msg.guild.id, msg.author.id)
    wid = await ctx.db.get_watch_id(uid, name, count)
    await ctx.db.remove_watch(wid)
    return {'react': emoji.thumbsup}


@cmd("watch")
async def watch(ctx, msg, count, *name):
    """ * desc: set a stattrak count to watch for
        * args: number item_name...
        * example: 6969 my fancy ak
        * tip: you can add multiple watches for an item
    """
    name = " ".join(name)
    # TODO: handle bot receiving dm (guild will be null)
    # TODO: handle get_user_id failure (user not registered)
    # TODO: handle get_weapon_id failure (weapon not added)
    # TODO: handle requested count <= current count
    uid, _ = await ctx.db.get_user_id(msg.guild.id, msg.author.id)
    wid = await ctx.db.get_weapon_id(uid, name)
    await ctx.db.add_watch(wid, int(count))
    return {'react': emoji.thumbsup}


@cmd("setchannel")
async def setchannel(ctx, msg, *args):
    """ * desc: set the channel for me to send alerts in (admin)
        * tip: just send this command in the desired channel
    """
    channel = msg.channel
    guild = channel.guild
    perms = msg.author.permissions_in(channel)

    if not perms.administrator:
        return {'react': emoji.thumbsdown}
    
    await ctx.db.add_or_update_guild(guild.id, channel.id)
    return {'react': emoji.thumbsup}


@cmd("help")
async def help(ctx, msg, *key):
    """ * desc: (psst, you're already here!)
        * args: [command]
    """
    
    if len(key) == 0:
        all_commands = []
        for cmd in sorted(COMMANDS.keys()):
            try:
                all_commands.append(format_help(cmd, COMMANDS[cmd].__doc__, prefix=ctx.conf['command_prefix'], short=True))
            except AttributeError: # no help
                pass
        return {
            'reply': """\
i'm a bot that reminds you when your stattrak stuff is about to reach a cool number. here are my commands:

{}

protip: try `{}help <command>` for help on a specific command
""".format('\n'.join(all_commands), ctx.conf['command_prefix'])
        }
    else:
        key, *_ = key
        key = key.lower()
        if not key in COMMANDS:
            return {
                'reply': "sorry, i don't have a '{}' command".format(key)
            }
        try:
            return {
                'reply': '\n' + format_help(key, COMMANDS[key].__doc__, prefix=ctx.conf['command_prefix'])
            }
        except AttributeError:
            return {
                'reply': "sorry, i don't have help for the '{}' command".format(key)
            }
