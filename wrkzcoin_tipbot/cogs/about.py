import sys
import traceback

import discord
from discord.ext import commands
from Bot import *

from config import config

class About(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(usage="disclaimer", description="Show disclaimer.")
    async def disclaimer(self, ctx):
        await ctx.send(f'{EMOJI_INFORMATION} **THANK YOU FOR USING** {DISCLAIM_MSG_LONG}')
        return


    @commands.command(usage="about", description="Get information about TipBot.")
    async def about(self, ctx):
        botdetails = discord.Embed(title='About Me', description='', colour=7047495)
        botdetails.add_field(name='Creator\'s Discord Name:', value='pluton#8888', inline=True)
        botdetails.add_field(name='My Github:', value="[TipBot Github](https://github.com/wrkzcoin/TipBot)", inline=True)
        botdetails.add_field(name='Invite Me:', value=f'{BOT_INVITELINK}', inline=True)
        botdetails.add_field(name='Servers I am in:', value=len(self.bot.guilds), inline=True)
        botdetails.add_field(name='Support Me:', value=f'<@{self.bot.user.id}> donate AMOUNT ticker', inline=True)
        botdetails.set_footer(text='Made in Python3.8+ with discord.py library!', icon_url='http://findicons.com/files/icons/2804/plex/512/python.png')
        botdetails.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)
        try:
            await ctx.send(embed=botdetails)
        except Exception as e:
            await ctx.author.send(embed=botdetails)
            await logchanbot(traceback.format_exc())


def setup(bot):
    bot.add_cog(About(bot))