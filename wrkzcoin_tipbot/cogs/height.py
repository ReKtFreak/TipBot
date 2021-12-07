import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class Height(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(
        usage="height <coin>", 
        description="Get a coin's network height (only supported coin)."
    )
    async def height(
        self, 
        ctx, 
        coin: str = None
    ):
        COIN_NAME = None
        serverinfo = None
        if coin is None:
            if isinstance(ctx.message.channel, discord.DMChannel):
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply('Please add ticker: '+ ', '.join(ENABLE_COIN).lower() + ' with this command if in DM.')
                return
            else:
                serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                try:
                    COIN_NAME = args[0].upper()
                    if COIN_NAME not in ENABLE_COIN:
                        if COIN_NAME in ENABLE_COIN_DOGE:
                            pass
                        elif 'default_coin' in serverinfo:
                            COIN_NAME = serverinfo['default_coin'].upper()
                    else:
                        pass
                except:
                    if 'default_coin' in serverinfo:
                        COIN_NAME = serverinfo['default_coin'].upper()
                pass
        else:
            COIN_NAME = coin.upper()

        # check if bot channel is set:
        if serverinfo and serverinfo['botchan']:
            try: 
                if ctx.channel.id != int(serverinfo['botchan']):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    botChan = bot.get_channel(int(serverinfo['botchan']))
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, {botChan.mention} is the bot channel!!!')
                    return
            except ValueError:
                pass
        # end of bot channel check

        # TRTL discord
        if isinstance(ctx.message.channel, discord.DMChannel) == False and ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
            return

        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
        if COIN_NAME not in (ENABLE_COIN + ENABLE_XMR + ENABLE_XCH):
            await ctx.message.add_reaction(EMOJI_ERROR)
            msg = await ctx.reply(f'{ctx.author.mention} Unsupported or Unknown Ticker: **{COIN_NAME}**')
            return
        elif is_maintenance_coin(COIN_NAME):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} is under maintenance.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

        gettopblock = None
        timeout = 60
        try:
            gettopblock = await daemonrpc_client.gettopblock(COIN_NAME, time_out=timeout)
        except asyncio.TimeoutError:
            msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} connection to daemon timeout after {str(timeout)} seconds.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        except Exception as e:
            await logchanbot(traceback.format_exc())

        if gettopblock:
            height = ""
            if coin_family in [ "BCN", "TRTL", "XMR"] and COIN_NAME != "TRTL":
                height = "{:,}".format(gettopblock['block_header']['height'])
            else:
                height = "{:,}".format(gettopblock['height'])
            msg = await ctx.reply(f'**[ {COIN_NAME} HEIGHT]**: {height}\n')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        else:
            msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME}\'s status unavailable.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return


def setup(bot):
    bot.add_cog(Height(bot))