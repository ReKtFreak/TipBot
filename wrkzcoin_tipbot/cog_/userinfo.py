import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class Userinfo(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(usage="userinfo <member>", description="Get user info in discord server.")
    async def userinfo(self, ctx, member: discord.Member = None):
        global TRTL_DISCORD
        if isinstance(ctx.channel, discord.DMChannel) == True:
            await ctx.send(f'{ctx.author.mention} This command can not be in Direct Message.')
            return
        if member is None:
            member = ctx.author
            userid = str(ctx.author.id)
        else:
            userid = str(member.id)
        try:
            embed = discord.Embed(title="{}'s info".format(member.name), description="Here's what I could find.", color=0x00ff00)
            embed.add_field(name="Name", value="{}#{}".format(member.name, member.discriminator), inline=True)
            embed.add_field(name="Display Name", value=member.display_name, inline=True)
            embed.add_field(name="ID", value=member.id, inline=True)
            embed.add_field(name="Status", value=member.status, inline=True)
            embed.add_field(name="Highest role", value=member.top_role)
            if ctx.guild.id != TRTL_DISCORD:
                user_claims = await store.sql_faucet_count_user(str(ctx.author.id))
                if user_claims and user_claims > 0:
                    take_level = get_roach_level(user_claims)
                    embed.add_field(name="Faucet Taking Level", value=take_level)
            try:
                sub_intip = 0
                sub_outtip = 0
                tip_text = "N/A"
                for each_coin in ENABLE_COIN+ENABLE_XMR+ENABLE_COIN_DOGE+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
                    tipstat = await store.sql_user_get_tipstat(userid, each_coin, False, SERVER_BOT)
                    if tipstat:
                        sub_intip += tipstat['tx_in']
                        sub_outtip += tipstat['tx_out']
                if sub_intip > 0 and sub_outtip > 0:
                    ratio_tip = float("%.3f" % float(sub_outtip / sub_intip))
                    if sub_intip + sub_outtip < 50:
                        tip_text = "CryptoTip Beginner"
                    else:
                        if ratio_tip < 0.1:
                            tip_text = "CryptoTip Rig"
                        elif 0.5 > ratio_tip >= 0.1:
                            tip_text = "CryptoTip Excavator"
                        elif 1 > ratio_tip >= 0.5:
                            tip_text = "CryptoTip Farmer"
                        elif 5 > ratio_tip >= 1:
                            tip_text = "CryptoTip Seeder"
                        elif ratio_tip >= 5:
                            tip_text = "CryptoTip AirDropper"
                embed.add_field(name="Tip In/Out", value="{}/{} - {}".format('{:,}'.format(sub_intip), '{:,}'.format(sub_outtip), tip_text), inline=False)
            except Exception as e:
                print(traceback.format_exc())
                await logchanbot(traceback.format_exc())
            embed.add_field(name="Joined", value=str(member.joined_at.strftime("%d-%b-%Y") + ': ' + timeago.format(member.joined_at, datetime.utcnow().astimezone())))
            embed.add_field(name="Created", value=str(member.created_at.strftime("%d-%b-%Y") + ': ' + timeago.format(member.created_at, datetime.utcnow().astimezone())))
            embed.set_thumbnail(url=member.display_avatar)
            await ctx.send(embed=embed)
        except:
            traceback.print_exc(file=sys.stdout)
            error = discord.Embed(title=":exclamation: Error", description=" :warning: You need to mention the user you want this info for!", color=0xe51e1e)
            await ctx.send(embed=error)


def setup(bot):
    bot.add_cog(Userinfo(bot))