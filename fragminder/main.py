from .commands import process_command
from .database import fmdb
from .steam_utils import steamapi
from .async_utils import recurring_task
from .update import do_update
from . import emoji

import argparse
import asyncio
import configparser
import discord
import logging

logging.basicConfig(level=logging.INFO)

class fragminder (discord.Client):
    def __init__(self, config):
        super().__init__()
        self.conf = config
        self.ready = False

    async def on_ready(self):
        loop = asyncio.get_event_loop()
        if not self.ready:
            self.db = await fmdb.open(self.conf['database_file'])
            self.steam = steamapi(self.conf['steam_api_key'])
            self._user_poller = recurring_task(float(self.conf['user_poll_interval']), do_update, self)
            self.ready = True
            await self._user_poller.start()
    
    async def on_message(self, message):
        if not self.ready: # ignore messages received before we're ready
            return
        if message.author == self.user: # ignore self
            return
        prefix = self.conf['command_prefix']
        if message.content.startswith(prefix):
            text = message.content[len(prefix):]

            try:
                result = await process_command(self, message, text)
            except Exception as e:
                logging.exception(e)
                result = None

            if result is None:
                result = {'react': emoji.shrug}
            if 'reply' in result:
                await message.channel.send("{}: {}".format(message.author.mention, result['reply']))
            if 'react' in result:
                await message.add_reaction(result['react'])

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
