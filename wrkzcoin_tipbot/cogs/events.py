import json
import sys
import time
import traceback

import disnake
from disnake.ext import commands

from Bot import *
import store
from config import config


class Events(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def bot_log(self):
        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)


    @commands.Cog.listener()
    async def on_button_click(self, ctx):
        # bot's message and click is close_message
        if ctx.message.author == self.bot.user and ctx.component.custom_id == "close_message":
            get_message = await store.get_discord_bot_message(str(ctx.message.id), "NO")
            if get_message and get_message['owner_id'] == str(ctx.author.id):
                try:
                    await ctx.message.delete()
                    await store.delete_discord_bot_message(str(ctx.message.id), str(ctx.author.id))
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
            elif get_message and get_message['owner_id'] != str(ctx.author.id):
                # Not your message.
                return
            else:
                # no record, just delete
                try:
                    await ctx.message.delete()
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
        # bot's message and click is close_any_message
        elif ctx.message.author == self.bot.user and ctx.component.custom_id == "close_any_message":
            try:
                await ctx.message.delete()
            except Exception as e:
                traceback.print_exc(file=sys.stdout)



    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.bot_log()
        add_server_info = await store.sql_addinfo_by_server(str(guild.id), guild.name,
                                                            config.discord.prefixCmd, "WRKZ", True)
        await self.botLogChan.send(f'Bot joins a new guild {guild.name} / {guild.id} / Users: {len(guild.members)}. Total guilds: {len(self.bot.guilds)}.')
        return


    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.bot_log()
        add_server_info = await store.sql_updateinfo_by_server(str(guild.id), "status", "REMOVED")
        await self.botLogChan.send(f'Bot was removed from guild {guild.name} / {guild.id}. Total guilds: {len(self.bot.guilds)}')
        return


    @commands.Cog.listener()
    async def on_message(self, message):
        # should ignore webhook message
        if isinstance(message.channel, disnake.DMChannel) == False and message.webhook_id:
            return

        if isinstance(message.channel, disnake.DMChannel) == False and message.author.bot == False and len(message.content) > 0 and message.author != self.bot.user:
            if config.Enable_Message_Logging == 1:
                await add_msg_redis(json.dumps([str(message.guild.id), message.guild.name, str(message.channel.id), message.channel.name, 
                                                 str(message.author.id), message.author.name, str(message.id), message.content, int(time.time())]), False)
            else:
                await add_msg_redis(json.dumps([str(message.guild.id), message.guild.name, str(message.channel.id), message.channel.name, 
                                                 str(message.author.id), message.author.name, str(message.id), '', int(time.time())]), False)

        # mute channel
        if isinstance(message.channel, disnake.DMChannel) == False and MUTE_CHANNEL and str(message.guild.id) in MUTE_CHANNEL:
            if str(message.channel.id) in MUTE_CHANNEL[str(message.guild.id)] and message.content[1:].upper() != "SETTING UNMUTE":
                # Ignore
                return

        # filter ignorechan
        commandList = ('TIP', 'TIPALL', 'DONATE', 'HELP', 'DONATE', 'SEND', 'WITHDRAW', 'BOTBAL', 'BAL PUB', 'GAME')
        try:
            # remove first char
            if LIST_IGNORECHAN:
                if isinstance(message.channel, disnake.DMChannel) == False and str(message.guild.id) in LIST_IGNORECHAN:
                    if message.content[1:].upper().startswith(commandList) \
                        and (str(message.channel.id) in LIST_IGNORECHAN[str(message.guild.id)]):
                        await message.add_reaction(EMOJI_ERROR)
                        await message.channel.send(f'Bot not respond to #{message.channel.name}. It is set to ignore list by channel manager or discord server owner.')
                        return
        except Exception as e:
            await logchanbot(traceback.format_exc())


def setup(bot):
    bot.add_cog(Events(bot))
