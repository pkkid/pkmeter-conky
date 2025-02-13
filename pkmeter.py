#!/usr/bin/env python3
import argparse, importlib, json5, os, sys
from datetime import datetime
from os.path import abspath, dirname, expanduser

sys.path.append(dirname(abspath(__file__)))
from pkm import ROOT, CACHE, CONFIG  # noqa
from pkm import utils  # noqa


def create_conky_config():
    """ Create the conky.config section from the config.json file. """
    conkyconfig = 'conky.config = {\n'
    for key, value in CONFIG['conky'].items():
        value = value.replace('{ROOT}', ROOT) if isinstance(value, str) else value
        value = value.lstrip('#') if 'color' in key else value
        value = f'"{value}"' if isinstance(value, str) else value
        value = str(value).lower() if isinstance(value, bool) else value
        conkyconfig += f'  {key}={value},\n'
    conkyconfig += '}\n\n'
    return conkyconfig


def create_conky_text():
    """ Create the conky.text and lua draw entries from the config.json file. """
    luaentries = []
    conkytext = 'conky.text = [[\n'
    for wconfig in CONFIG['widgets']:
        if not wconfig.get('enabled', True): continue
        modpath, clsname = wconfig['path'].rsplit('.', 1)
        module = importlib.import_module(modpath)
        widget = getattr(module, clsname)(wconfig)
        conkytext += f'{widget.get_conkyrc()}\n\\\n'
        luaentries += widget.get_lua_entries()
    conkytext += ']]\n'
    luaentries = '\n'.join(f'  {item},' for item in luaentries)
    luaentries = f'elements = {{\n{luaentries}\n}}\n'
    return conkytext, luaentries


def create_conkyrc():
    """ Create a new conkyrc from from config.json. """
    conkyconfig = create_conky_config()
    conkytext, luaentries = create_conky_text()
    utils.save_file(expanduser('~/.conkyrc'), conkyconfig + conkytext)
    utils.save_file(f'{ROOT}/pkm/config.lua', luaentries)


def get_value(key, opts):
    """ Lookup the specified key from the cached json files.
        widget: Short name of the widget to get the value from.
        key: Dict lookup key to get the value from.
    """
    try:
        widget, key = key.split('.', 1)
        filepath = f'{CACHE}/{widget}.json'
        with open(filepath, 'r') as handle:
            data = json5.load(handle)
        value = utils.rget(data, key, None)
        if value is None: return opts.default
        if opts.round: value = round(float(value), opts.round)
        if opts.int: value = int(value)
        if opts.format: value = datetime.fromtimestamp(int(value)).strftime(opts.format)
        return value
    except Exception:
        return opts.default


def update_widget(widget):
    """ Update the specified widget cache. """
    for wconfig in CONFIG['widgets']:
        if widget == utils.get_shortname(wconfig['path']):
            modpath, clsname = wconfig['path'].rsplit('.', 1)
            module = importlib.import_module(modpath)
            widget = getattr(module, clsname)(wconfig)
            widget.update_cache()
            break
    raise Exception(f'Unknown widget {widget}')


if __name__ == '__main__':
    # Command line parser. Available commands are:
    #  conkyrc: generate new conkyrc & config.lua files from config.json
    #  get <key>: get the specified widget value
    #  update <widget>: update the specified widget cache
    os.makedirs(CACHE, exist_ok=True)
    parser = argparse.ArgumentParser(description='Helper tools for pkmeter.')
    subparsers = parser.add_subparsers(title='available commands', dest='command')
    conkyrc_parser = subparsers.add_parser('conkyrc', help='generate new conkyrc & config.lua files from config.json')
    get_parser = subparsers.add_parser('get', help='get the specified widget value')
    get_parser.add_argument('key', help='value to lookup from the specified widget dataset')
    get_parser.add_argument('-d', dest='default', default='', help='default value if not found')
    get_parser.add_argument('-i', dest='int', action='store_true', default=False, help='cast value to integer')
    get_parser.add_argument('-r', dest='round', type=int, help='round to nearest decimal')
    get_parser.add_argument('-f', dest='format', help='format value to datetime')
    update_parser = subparsers.add_parser('update', help='Update cache for the specified widget')
    update_parser.add_argument('widget', help='widget class name to get value from')
    # Run the specified command
    opts = parser.parse_args()
    if opts.command == 'conkyrc': create_conkyrc()
    if opts.command == 'get': print(get_value(opts.key, opts))
    if opts.command == 'update': print(opts)
