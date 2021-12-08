import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class Invite(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @inter_client.slash_command(description="Get TipBpt's invite link.")
    async def invite(self, ctx):
        await ctx.reply(f"**[INVITE LINK]**: {BOT_INVITELINK_PLAIN}", ephemeral=False)


    @commands.command(usage="invite", description="Get TipBpt's invite link.")
    async def invite(self, ctx):
        await ctx.reply(f"**[INVITE LINK]**: {BOT_INVITELINK_PLAIN}")


def setup(bot):
    bot.add_cog(Invite(bot))