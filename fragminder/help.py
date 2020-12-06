
__all__ = ['format_help']

def format_help(command, docstring, prefix="!", short=False):
    info = {}
    for line in docstring.split("\n"):
        line = line.lstrip()
        p = "* "
        if not line.startswith(p):
            continue
        line = line[len(p):]
        parts = line.split(":")
        if not len(parts) >= 2:
            continue
        key = parts[0]
        info[key] = line[len(key)+2:].lstrip()

    if 'args' in info:
        usage = "`{}{} {}`".format(prefix, command, info['args'])
    else:
        usage = "`{}{}`".format(prefix, command)
    
    if short:
        return usage

    res = usage
    if 'desc' in info:
        res += "\n{}".format(info['desc'])
    if 'example' in info:
        res += "\n*example:* `{}{} {}`".format(prefix, command, info['example'])
    if 'tip' in info:
        res += "\n*protip:* {}".format(info['tip'])

    return res
