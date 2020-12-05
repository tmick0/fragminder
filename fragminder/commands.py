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

