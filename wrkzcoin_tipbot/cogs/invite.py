import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class Invite(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(usage="invite", description="Get TipBpt's invite link.")
    async def invite(self, ctx):
        await ctx.send(f'**[INVITE LINK]**: {BOT_INVITELINK_PLAIN}')


def setup(bot):
    bot.add_cog(Invite(bot))