import sys, traceback
import time, timeago
import discord
from discord.ext import commands
from datetime import datetime
from dislash import InteractionClient, ActionRow, Button, ButtonStyle, Option, OptionType

from config import config
from Bot import *

class Userinfo(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    async def get_userinfo(self, intx):
        user_claims = await store.sql_faucet_count_user(str(intx.id))
        sub_intip = 0
        sub_outtip = 0
        tip_text = "N/A"
        for each_coin in ENABLE_COIN+ENABLE_XMR+ENABLE_COIN_DOGE+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
            tipstat = await store.sql_user_get_tipstat(str(intx.id), each_coin, False, SERVER_BOT)
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

        embed = discord.Embed(title="{}'s info".format(intx.name), description="Here's what I could find.", color=0x00ff00)
        embed.add_field(name="Name", value="{}#{}".format(intx.name, intx.discriminator), inline=True)
        embed.add_field(name="Display Name", value=intx.display_name, inline=True)
        embed.add_field(name="ID", value=intx.id, inline=True)
        embed.add_field(name="Status", value=intx.status, inline=True)
        embed.add_field(name="Highest role", value=intx.top_role)
        embed.add_field(name="Tip In/Out", value="{}/{} - {}".format('{:,}'.format(sub_intip), '{:,}'.format(sub_outtip), tip_text), inline=False)
        if intx.guild.id != TRTL_DISCORD:
            user_claims = await store.sql_faucet_count_user(str(intx.id))
            if user_claims and user_claims > 0:
                take_level = get_roach_level(user_claims)
                embed.add_field(name="Faucet Taking Level", value=take_level, inline=False)
        embed.add_field(name="Joined", value=str(intx.joined_at.strftime("%d-%b-%Y") + ': ' + timeago.format(intx.joined_at, datetime.utcnow().astimezone())))
        embed.add_field(name="Created", value=str(intx.created_at.strftime("%d-%b-%Y") + ': ' + timeago.format(intx.created_at, datetime.utcnow().astimezone())))
        embed.set_thumbnail(url=intx.display_avatar)
        return embed


    @inter_client.slash_command(usage="userinfo <member>",
                                options=[
                                    Option("user", "Enter user", OptionType.USER, required=True)
                                    # By default, Option is optional
                                    # Pass required=True to make it a required arg
                                ],
                                description="Get user information.")
    async def userinfo(
        self, 
        inter, 
        user: discord.Member
    ):
        prefix = "/"
        try:
            get_stat = await self.get_userinfo(user)
            await inter.reply(embed=get_stat)
        except:
            traceback.print_exc(file=sys.stdout)
            error = discord.Embed(title=":exclamation: Error", description=" :warning: You need to mention the user you want this info for!", color=0xe51e1e)
            await ctx.send(embed=error)


    @commands.command(
        usage="userinfo <member>", 
        description="Get user info in discord server."
    )
    async def userinfo(
        self, 
        ctx, 
        member: discord.Member = None
    ):
        if isinstance(ctx.channel, discord.DMChannel) == True:
            await ctx.send(f'{ctx.author.mention} This command can not be in Direct Message.')
            return
        if member is None:
            member = ctx.author
        try:
            get_stat = await self.get_userinfo(member)
            await ctx.send(embed=get_stat)
        except:
            traceback.print_exc(file=sys.stdout)
            error = discord.Embed(title=":exclamation: Error", description=" :warning: You need to mention the user you want this info for!", color=0xe51e1e)
            await ctx.send(embed=error)


def setup(bot):
    bot.add_cog(Userinfo(bot))