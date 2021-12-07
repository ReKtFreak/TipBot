import sys, traceback
import time, timeago
import discord
from discord.ext import commands
import json
from dislash import InteractionClient, ActionRow, Button, ButtonStyle, Option, OptionType


from config import config
from Bot import *
from utils import EmbedPaginator, EmbedPaginatorInter


class Balance(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def bot_log(self):
        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)


    @inter_client.slash_command(description="Ping command")
    async def ping(self, ctx):
        await ctx.reply(f"Pong! ({self.bot.latency*1000}ms)")


    async def show_balance(
        self,
        ctx,
        coin: str=None
    ):
        await self.bot_log()
        prefix = await get_guild_prefix(ctx)
        user_id = ctx.author.id
        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'balance')
        if account_lock:
            await ctx.reply(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
            return
        # end of check if account locked
        if coin is None: coin = "ALL"
        if coin.upper() == "ALL":
            #await ctx.reply('You selected all', ephemeral=True)
            all_pages = []
            page = discord.Embed(title='[ YOUR BALANCE LIST ]',
                                  description="Thank you for using TipBot!",
                                  color=discord.Color.blue(),
                                  timestamp=datetime.utcnow(), )
            page.add_field(name="Total Coin/Tokens: [{}]".format(len(ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH)), 
                           value="```"+", ".join(ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH)+"```", inline=True)
            page.set_thumbnail(url=ctx.author.display_avatar)
            page.set_footer(text="Use the reactions to flip pages.")
            all_pages.append(page)
            num_coins = 0
            per_page = 12
            tmp_msg = await ctx.send("Loading...")
            user_coins = await get_balance_list_user(user_id)
            total_coins = len(user_coins)
            for COIN_NAME, value in user_coins.items():
                if num_coins == 0 or num_coins % per_page == 0:
                    page = discord.Embed(title='[ YOUR BALANCE LIST ]',
                                         description="Thank you for using TipBot!",
                                         color=discord.Color.blue(),
                                         timestamp=datetime.utcnow(), )
                    page.set_thumbnail(url=ctx.author.display_avatar)
                    page.set_footer(text="Use the reactions to flip pages.")
                page.add_field(name=COIN_NAME, value=value['balance_actual']+" "+COIN_NAME, inline=True)
                num_coins += 1
                if num_coins > 0 and num_coins % per_page == 0:
                    all_pages.append(page)
                    if num_coins < total_coins:
                        page = discord.Embed(title='[ YOUR BALANCE LIST ]',
                                             description="Thank you for using TipBot!",
                                             color=discord.Color.blue(),
                                             timestamp=datetime.utcnow(), )
                        page.set_thumbnail(url=ctx.author.display_avatar)
                        page.set_footer(text="Use the reactions to flip pages.")
                    else:
                        all_pages.append(page)
                        break
                elif num_coins == total_coins:
                    all_pages.append(page)
                    break
            await tmp_msg.delete()
            paginator = EmbedPaginatorInter(self.bot, ctx, all_pages, True)
            await paginator.paginate_with_slash()
            # If there is still page
        elif coin.upper() in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
            COIN_NAME = coin.upper()
            balance_user = await get_balance_coin_user(user_id, COIN_NAME, discord_guild=False, server__bot=SERVER_BOT)
            embed = discord.Embed(title=f'[ {ctx.author.name}#{ctx.author.discriminator}\'s {COIN_NAME} balance ]', timestamp=datetime.utcnow())
            try:
                if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    embed.add_field(name="Deposited", value="`{} {}`".format(num_format_coin(float(balance_user['real_deposit_balance']), COIN_NAME), COIN_NAME), inline=True)
                embed.add_field(name="Spendable", value=balance_user['balance_actual']+COIN_NAME, inline=True)
                if balance_user['locked_openorder'] > 0 and COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    embed.add_field(name="Opened Order", value=num_format_coin(balance_user['locked_openorder'], COIN_NAME)+" "+COIN_NAME, inline=True)
                    embed.add_field(name="Total", value=num_format_coin(balance_user['actual_balance']+balance_user['locked_openorder'], COIN_NAME)+" "+COIN_NAME, inline=True)
                elif balance_user['locked_openorder'] > 0 and COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    embed.add_field(name="Opened Order", value=num_format_coin(balance_user['locked_openorder'], COIN_NAME)+" "+COIN_NAME, inline=True)
                    embed.add_field(name="Total", value=num_format_coin(balance_user['actual_balance']+balance_user['locked_openorder']+float(real_deposit_balance), COIN_NAME)+" "+COIN_NAME, inline=True)
                elif balance_user['locked_openorder'] == 0 and COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    embed.add_field(name="Total", value=num_format_coin(balance_user['actual_balance']+float(real_deposit_balance), COIN_NAME)+" "+COIN_NAME, inline=True)
                if balance_user['raffle_spent'] and balance_user['raffle_spent'] > 0:
                    embed.add_field(name="Raffle Spent / Won", value="{} / {} {}".format(num_format_coin(balance_user['raffle_spent'], COIN_NAME), num_format_coin(balance_user['raffle_reward'], COIN_NAME), COIN_NAME), inline=False)
            except Exception as e:
                print(traceback.format_exc())
            if balance_user['economy_balance'] and balance_user['economy_balance'] != 0:
                embed.add_field(name="Economy Expense (+/-)", value=num_format_coin(balance_user['economy_balance'], COIN_NAME)+ " " + COIN_NAME, inline=True)
            embed.add_field(name='Related commands', value=f'`{prefix}balance` or `{prefix}deposit {COIN_NAME}`', inline=False)
            if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                
                embed.set_footer(text="{}{}".format(balance_user['deposit_note'], balance_user['min_deposit_txt']))
            else:
                embed.set_footer(text=f"{get_notice_txt(COIN_NAME)}")
            try:
                msg = await ctx.reply(embed=embed, ephemeral=True)
            except:
                pass
        else:
            await ctx.reply(f'There is no such ticker {COIN_NAME}', ephemeral=True)


    @inter_client.slash_command(usage="balance [coin]",
                                options=[
                                    Option("coin", "Enter coin ticker/name", OptionType.STRING, required=False)
                                    # By default, Option is optional
                                    # Pass required=True to make it a required arg
                                ],
                                description="Check your (coin's) tipjar's balance.")
    async def balance(
        self, 
        ctx, 
        coin: str=None
    ):
        show_balance = await self.show_balance(ctx, coin)
        if show_balance and "error" in show_balance:
            await ctx.reply(show_balance['error'], ephemeral=True)


    @commands.command(
        usage="balance <coin>", 
        aliases=['bal'], 
        description="Check your (coin's) tipjar's balance."
    )
    async def balance(
        self, 
        ctx, 
        coin: str = None
    ):
        show_balance = await self.show_balance(ctx, coin)
        if show_balance and "error" in show_balance:
            await ctx.reply(show_balance['error'], ephemeral=True)


def setup(bot):
    bot.add_cog(Balance(bot))