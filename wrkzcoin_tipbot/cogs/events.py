import json
import sys
import time
import traceback

import discord
from discord.ext import commands

from Bot import *
import store
from config import config


class Events(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        botLogChan = self.bot.get_channel(LOG_CHAN)
        add_server_info = await store.sql_addinfo_by_server(str(guild.id), guild.name,
                                                            config.discord.prefixCmd, "WRKZ", True)
        await botLogChan.send(f'Bot joins a new guild {guild.name} / {guild.id} / Users: {len(guild.members)}. Total guilds: {len(self.bot.guilds)}.')
        return


    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        botLogChan = self.bot.get_channel(LOG_CHAN)
        add_server_info = await store.sql_updateinfo_by_server(str(guild.id), "status", "REMOVED")
        await botLogChan.send(f'Bot was removed from guild {guild.name} / {guild.id}. Total guilds: {len(self.bot.guilds)}')
        return


    @commands.Cog.listener()
    async def on_message(self, message):
        # should ignore webhook message
        if isinstance(message.channel, discord.DMChannel) == False and message.webhook_id:
            return

        if isinstance(message.channel, discord.DMChannel) == False and message.author.bot == False and len(message.content) > 0 and message.author != self.bot.user:
            if config.Enable_Message_Logging == 1:
                await add_msg_redis(json.dumps([str(message.guild.id), message.guild.name, str(message.channel.id), message.channel.name, 
                                                 str(message.author.id), message.author.name, str(message.id), message.content, int(time.time())]), False)
            else:
                await add_msg_redis(json.dumps([str(message.guild.id), message.guild.name, str(message.channel.id), message.channel.name, 
                                                 str(message.author.id), message.author.name, str(message.id), '', int(time.time())]), False)

        # mute channel
        if isinstance(message.channel, discord.DMChannel) == False and MUTE_CHANNEL and str(message.guild.id) in MUTE_CHANNEL:
            if str(message.channel.id) in MUTE_CHANNEL[str(message.guild.id)] and message.content[1:].upper() != "SETTING UNMUTE":
                # Ignore
                return

        # filter ignorechan
        commandList = ('TIP', 'TIPALL', 'DONATE', 'HELP', 'DONATE', 'SEND', 'WITHDRAW', 'BOTBAL', 'BAL PUB', 'GAME')
        try:
            # remove first char
            if LIST_IGNORECHAN:
                if isinstance(message.channel, discord.DMChannel) == False and str(message.guild.id) in LIST_IGNORECHAN:
                    if message.content[1:].upper().startswith(commandList) \
                        and (str(message.channel.id) in LIST_IGNORECHAN[str(message.guild.id)]):
                        await message.add_reaction(EMOJI_ERROR)
                        await message.channel.send(f'Bot not respond to #{message.channel.name}. It is set to ignore list by channel manager or discord server owner.')
                        return
        except Exception as e:
            await logchanbot(traceback.format_exc())


def setup(bot):
    bot.add_cog(Events(bot))
