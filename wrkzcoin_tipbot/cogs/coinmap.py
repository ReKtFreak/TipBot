import sys, traceback
import time, timeago
import discord
from discord.ext import commands
import dislash

from config import config
from Bot import *

class CoinMap(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @inter_client.slash_command(usage="coinmap",
                                description="Get view from coin360.")
    async def coinmap(self, ctx):
        try:
            map_image = await self.bot.loop.run_in_executor(None, coin360.get_coin360)
            if map_image:
                await ctx.reply(f'{config.coin360.static_coin360_link + map_image}', ephemeral=False)
            else:
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Internal error during fetch image.', ephemeral=True)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)


    @commands.command(usage="coinmap", aliases=['coin360', 'c360', 'cmap'], description="Get view from coin360.")
    async def coinmap(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel) == False and ctx.guild.id == TRTL_DISCORD:
            return

        async with ctx.typing():
            try:
                map_image = await self.bot.loop.run_in_executor(None, coin360.get_coin360)
                if map_image:
                    msg = await ctx.reply(f'{config.coin360.static_coin360_link + map_image}')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                else:
                    msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Internal error during fetch image.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
            except Exception as e:
                await logchanbot(traceback.format_exc())


def setup(bot):
    bot.add_cog(CoinMap(bot))