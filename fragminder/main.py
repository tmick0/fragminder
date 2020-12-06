from .commands import process_command
from .database import fmdb
from .steam_utils import steamapi

import argparse
import asyncio
import configparser
import discord

class fragminder (discord.Client):
    def __init__(self, config):
        super().__init__()
        self.conf = config
        self.ready = False

    async def on_ready(self):
        self.db = await fmdb.open(self.conf['database_file'])
        self.steam = steamapi(self.conf['steam_api_key'])
        self.ready = True
        print('ready: {}'.format(self.user))
    
    async def on_message(self, message):
        if not self.ready:
            return
        prefix = self.conf['command_prefix']
        if message.content.startswith(prefix):
            text = message.content[len(prefix):]
            await process_command(self, message.author, text)

    def run(self):
        super().run(self.conf['discord_token'])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file')

    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config_file)

    bot = fragminder(config['fragminder'])
    bot.run()
