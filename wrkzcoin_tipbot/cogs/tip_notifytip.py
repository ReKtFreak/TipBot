import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class TipNotifyTip(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(
        usage="notifytip <on/off>", 
        description="Switch tipping notification ON/OFF."
    )
    async def notifytip(
        ctx, 
        onoff: str
    ):
        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'notifytip')
        if account_lock:
            await ctx.message.add_reaction(EMOJI_LOCKED) 
            await ctx.reply(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
            return
        # end of check if account locked

        if onoff.upper() not in ["ON", "OFF"]:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} You need to use only `ON` or `OFF`.')
            return

        onoff = onoff.upper()
        notifyList = await store.sql_get_tipnotify()
        if onoff == "ON":
            if str(ctx.author.id) in notifyList:
                await store.sql_toggle_tipnotify(str(ctx.author.id), "ON")
                await ctx.reply(f'{ctx.author.mention} OK, you will get all notification when tip.')
                return
            else:
                await ctx.reply(f'{ctx.author.mention} You already have notification ON by default.')
                return
        elif onoff == "OFF":
            if str(ctx.author.id) in notifyList:
                await ctx.reply(f'{ctx.author.mention} You already have notification OFF.')
                return
            else:
                await store.sql_toggle_tipnotify(str(ctx.author.id), "OFF")
                await ctx.reply(f'{ctx.author.mention} OK, you will not get any notification when anyone tips.')
                return


def setup(bot):
    bot.add_cog(TipNotifyTip(bot))