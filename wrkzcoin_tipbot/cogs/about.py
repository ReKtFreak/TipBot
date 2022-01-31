import sys
import traceback

import disnake
from disnake.ext import commands
from Bot import *
import store

from config import config

class About(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    def about_embed(self):
        botdetails = disnake.Embed(title='About Me', description='')
        botdetails.add_field(name='Creator\'s Discord Name:', value='pluton#8888', inline=True)
        botdetails.add_field(name='My Github:', value="[TipBot Github](https://github.com/wrkzcoin/TipBot)", inline=True)
        botdetails.add_field(name='Invite Me:', value=config.discord.invite_link, inline=True)
        botdetails.add_field(name='Servers I am in:', value=len(self.bot.guilds), inline=True)
        botdetails.add_field(name='Support Me:', value=f'<@{self.bot.user.id}> donate AMOUNT ticker', inline=True)
        botdetails.set_footer(text='Made in Python3.8+', icon_url='http://findicons.com/files/icons/2804/plex/512/python.png')
        botdetails.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)
        return botdetails


    @commands.slash_command(description="Show disclaimer.")
    async def disclaimer(self, ctx):
        msg = await ctx.reply(f"{EMOJI_INFORMATION} **THANK YOU FOR USING** {DISCLAIM_MSG_LONG}", ephemeral=True)


    @commands.slash_command(description="Get information about TipBot.")
    async def about(self, ctx):
        try:
            msg = await ctx.reply(embed=self.about_embed(), view=RowButton_close_message())
            await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, disnake.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
        except Exception as e:
            await logchanbot(traceback.format_exc())


    @commands.command(usage="disclaimer", description="Show disclaimer.")
    async def disclaimer(self, ctx):
        msg = await ctx.reply(f'{EMOJI_INFORMATION} **THANK YOU FOR USING** {DISCLAIM_MSG_LONG}', view=RowButton_close_message())
        await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, disnake.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
        return


    @commands.command(usage="about", description="Get information about TipBot.")
    async def about(self, ctx):
        try:
            msg = await ctx.reply(embed=self.about_embed(), view=RowButton_close_message())
            await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, disnake.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
        except Exception as e:
            await ctx.author.send(embed=self.about_embed())
            await logchanbot(traceback.format_exc())


def setup(bot):
    bot.add_cog(About(bot))