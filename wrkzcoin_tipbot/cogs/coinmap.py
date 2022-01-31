import sys, traceback
import time, timeago
from disnake.ext import commands
import disnake

from config import config
from Bot import *

class CoinMap(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.guild_only()
    @commands.slash_command(usage="coinmap",
                            description="Get view from coin360.")
    async def coinmap(self, ctx):
        try:
            tmp_msg = await ctx.send("Loading...")
            map_image = await self.bot.loop.run_in_executor(None, coin360.get_coin360)
            await tmp_msg.delete()
            if map_image:
                msg = await ctx.reply(f'{config.coin360.static_coin360_link + map_image}', ephemeral=False, view=RowButton_close_message())
                await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, disnake.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
            else:
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Internal error during fetch image.', ephemeral=True)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)


    @commands.guild_only()
    @commands.command(usage="coinmap", aliases=['coin360', 'c360', 'cmap'], description="Get view from coin360.")
    async def coinmap(self, ctx):
        async with ctx.typing():
            try:
                tmp_msg = await ctx.send("Loading...")
                map_image = await self.bot.loop.run_in_executor(None, coin360.get_coin360)
                await tmp_msg.delete()
                if map_image:
                    msg = await ctx.reply(f'{config.coin360.static_coin360_link + map_image}', view=RowButton_close_message())
                    await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, disnake.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
                    return
                else:
                    msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Internal error during fetch image.', view=RowButton_row_close_any_message())
                    return
            except Exception as e:
                await logchanbot(traceback.format_exc())


def setup(bot):
    bot.add_cog(CoinMap(bot))