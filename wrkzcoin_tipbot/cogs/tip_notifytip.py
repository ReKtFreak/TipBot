import sys, traceback
import time, timeago
import discord
from discord.ext import commands
from dislash import InteractionClient, ActionRow, Button, ButtonStyle, Option, OptionType, OptionChoice, SlashInteraction
import dislash

from config import config
from Bot import *

class TipNotifyTip(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def bot_log(self):
        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def toggle_notifytip(
        self,
        ctx,
        onoff
    ):
        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'notifytip')
        if account_lock:
            return {"error": f"{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}"}
        # end of check if account locked

        if onoff.upper() not in ["ON", "OFF"]:
            return {"error": f"{ctx.author.mention} You need to use only `ON` or `OFF`."}

        onoff = onoff.upper()
        notifyList = await store.sql_get_tipnotify()
        if onoff == "ON":
            if str(ctx.author.id) in notifyList:
                await store.sql_toggle_tipnotify(str(ctx.author.id), "ON")
                await ctx.reply(f'{ctx.author.mention} OK, you will get all notification when tip.')
                return {"result": True}
            else:
                await ctx.reply(f'{ctx.author.mention} You already have notification ON by default.')
                return {"result": True}
        elif onoff == "OFF":
            if str(ctx.author.id) in notifyList:
                await ctx.reply(f'{ctx.author.mention} You already have notification OFF.')
                return {"result": True}
            else:
                await store.sql_toggle_tipnotify(str(ctx.author.id), "OFF")
                await ctx.reply(f'{ctx.author.mention} OK, you will not get any notification when anyone tips.')
                return {"result": True}


    @inter_client.slash_command(
        usage="notifytip", 
        options=[
            Option('onoff', 'onoff', OptionType.STRING, required=True, choices=[
                OptionChoice("Notification On", "ON"),
                OptionChoice("Notification Off", "OFF")
            ])
        ],
        description="Do a random tip to user."
    )
    async def notifytip(
        self, 
        ctx,
        onoff: str
    ):
        await self.bot_log()
        # TODO: If it is DM, let's make a secret tip
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.reply(f'{ctx.author.mention} This command can not be DM.')
            return

        toggle_notifytip = await self.toggle_notifytip(ctx, onoff)
        if toggle_notifytip and "error" in toggle_notifytip:
            await ctx.reply(toggle_notifytip['error'])


    @commands.command(
        usage="notifytip <on/off>", 
        description="Switch tipping notification ON/OFF."
    )
    async def notifytip(
        ctx, 
        onoff: str
    ):
        toggle_notifytip = await self.toggle_notifytip(ctx, onoff)
        if toggle_notifytip and "error" in toggle_notifytip:
            await ctx.reply(toggle_notifytip['error'])


def setup(bot):
    bot.add_cog(TipNotifyTip(bot))