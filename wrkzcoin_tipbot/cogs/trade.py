import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class Trade(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(usage="sell <sell amount> <coin> <buy amount> <coin>", aliases=['selling'], description="Make an opened sell of a coin for another coin.")
    async def sell(self, ctx, sell_amount: str, sell_ticker: str, buy_amount: str, buy_ticker: str):
        if isinstance(ctx.message.channel, discord.DMChannel) == False and ctx.guild and ctx.guild.id == TRTL_DISCORD:
            return

        botLogChan = self.bot.get_channel(LOG_CHAN)
        try:
            if isinstance(ctx.message.channel, discord.DMChannel) == True:
                pass
            else:
                serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                if isinstance(ctx.message.channel, discord.DMChannel) == False and serverinfo \
                and 'enable_trade' in serverinfo and serverinfo['enable_trade'] == "NO":
                    prefix = serverinfo['prefix']
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Trade Command is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING TRADE`')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}sell command** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
                    return
        except Exception as e:
            if isinstance(ctx.message.channel, discord.DMChannel) == False:
                return
            await logchanbot(traceback.format_exc())
            return

        # check if bot is going to restart
        if IS_RESTARTING:
            await ctx.message.add_reaction(EMOJI_REFRESH)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
            return

        sell_ticker = sell_ticker.upper()
        buy_ticker = buy_ticker.upper()
        sell_amount = sell_amount.replace(",", "")
        buy_amount = buy_amount.replace(",", "")
        try:
            sell_amount = Decimal(sell_amount)
            buy_amount = Decimal(buy_amount)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid sell/buy amount.')
            return
        if (sell_ticker not in ENABLE_TRADE_COIN) or (buy_ticker not in ENABLE_TRADE_COIN):
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid trade ticker (buy/sell). Available right now: **{config.trade.enable_coin}**')
            return

        if not is_tradeable_coin(sell_ticker):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            await ctx.send(f'{EMOJI_RED_NO} **{sell_ticker}** trading is currently disable.')
            return

        if not is_tradeable_coin(buy_ticker):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            await ctx.send(f'{EMOJI_RED_NO} **{buy_ticker}** trading is currently disable.')
            return

        if buy_ticker == sell_ticker:
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            await ctx.send(f'{EMOJI_RED_NO} {buy_ticker} you cannot trade the same coins.')
            return

        # get opened order:
        user_count_order = await store.sql_count_open_order_by_sellerid(str(ctx.author.id), SERVER_BOT)
        if user_count_order >= config.trade.Max_Open_Order:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You have maximum opened selling **{config.trade.Max_Open_Order}**. Please cancel some or wait.')
            return

        if sell_ticker in ENABLE_COIN_ERC:
            coin_family_sell = "ERC-20"
            sell_token_info = await store.get_token_info(sell_ticker)
        elif sell_ticker in ENABLE_COIN_TRC:
            coin_family_sell = "TRC-20"
            sell_token_info = await store.get_token_info(sell_ticker)
        else:
            coin_family_sell = getattr(getattr(config,"daemon"+sell_ticker),"coin_family","TRTL")
            sell_token_info = None

        real_amount_sell = int(sell_amount * get_decimal(sell_ticker)) if coin_family_sell in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(sell_amount)

        if real_amount_sell == 0:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {sell_amount}{sell_ticker} = 0 {sell_ticker} (below smallest unit).')
            return

        if real_amount_sell < get_min_sell(sell_ticker, sell_token_info):
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **{sell_amount}{sell_ticker}** below minimum trade **{num_format_coin(get_min_sell(sell_ticker, sell_token_info), sell_ticker)}{sell_ticker}**.')
            return
        if real_amount_sell > get_max_sell(sell_ticker, sell_token_info):
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **{sell_amount}{sell_ticker}** above maximum trade **{num_format_coin(get_max_sell(sell_ticker, sell_token_info), sell_ticker)}{sell_ticker}**.')
            return

        if buy_ticker in ENABLE_COIN_ERC:
            coin_family_buy = "ERC-20"
            buy_token_info = await store.get_token_info(buy_ticker)
        elif buy_ticker in ENABLE_COIN_TRC:
            coin_family_buy = "TRC-20"
            buy_token_info = await store.get_token_info(buy_ticker)
        else:
            coin_family_buy = getattr(getattr(config,"daemon"+buy_ticker),"coin_family","TRTL")
            buy_token_info = None

        real_amount_buy = int(buy_amount * get_decimal(buy_ticker)) if coin_family_buy in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(buy_amount)

        if real_amount_buy == 0:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {buy_amount}{buy_ticker} = 0 {buy_ticker} (below smallest unit).')
            return
        if real_amount_buy < get_min_sell(buy_ticker, buy_token_info):
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **{buy_amount}{buy_ticker}** below minimum trade **{num_format_coin(get_min_sell(buy_ticker, buy_token_info), buy_ticker)}{buy_ticker}**.')
            return
        if real_amount_buy > get_max_sell(buy_ticker, buy_token_info):
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **{buy_amount}{buy_ticker}** above maximum trade **{num_format_coin(get_max_sell(buy_ticker, buy_token_info), buy_ticker)}{buy_ticker}**.')
            return

        if not is_maintenance_coin(sell_ticker):
            balance_actual = 0
            wallet = await store.sql_get_userwallet(str(ctx.author.id), sell_ticker, SERVER_BOT)
            if wallet is None:
                userregister = await store.sql_register_user(str(ctx.author.id), sell_ticker, SERVER_BOT, 0)
            userdata_balance = await store.sql_user_balance(str(ctx.author.id), sell_ticker)
            xfer_in = 0
            if sell_ticker not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                xfer_in = await store.sql_user_balance_get_xfer_in(str(ctx.author.id), sell_ticker)
            if sell_ticker in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
            elif sell_ticker in ENABLE_COIN_NANO:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
                actual_balance = round(actual_balance / get_decimal(sell_ticker), 6) * get_decimal(sell_ticker)
            else:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])

            # Negative check
            try:
                if actual_balance < 0:
                    msg_negative = 'Negative balance detected:\nUser: '+str(ctx.author.id)+'\nCoin: '+sell_ticker+'\nAtomic Balance: '+str(actual_balance)
                    await logchanbot(msg_negative)
            except Exception as e:
                await logchanbot(traceback.format_exc())

            if actual_balance < real_amount_sell:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You do not have enough '
                               f'**{sell_ticker}**. You have currently: {num_format_coin(actual_balance, sell_ticker)}{sell_ticker}.')
                return
            if (sell_amount / buy_amount) < MIN_TRADE_RATIO or (buy_amount / sell_amount) < MIN_TRADE_RATIO:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} ratio buy/sell rate is so low.')
                return
            # call other function
            return await sell_process(ctx, real_amount_sell, sell_ticker, real_amount_buy, buy_ticker)


    async def sell_process(ctx, real_amount_sell: float, sell_ticker: str, real_amount_buy: float, buy_ticker: str):
        botLogChan = self.bot.get_channel(LOG_CHAN)

        sell_ticker = sell_ticker.upper()
        buy_ticker = buy_ticker.upper()
        if sell_ticker in ["NANO", "BAN"]:
            real_amount_sell = round(real_amount_sell, 20)
        else:
            real_amount_sell = round(real_amount_sell, 8)
        if buy_ticker in ["NANO", "BAN"]:
            real_amount_buy = round(real_amount_buy, 20)
        else:
            real_amount_buy = round(real_amount_buy, 8)
        sell_div_get = round(real_amount_sell / real_amount_buy, 32)
        fee_sell = round(TRADE_PERCENT * real_amount_sell, 8)
        fee_buy = round(TRADE_PERCENT * real_amount_buy, 8)
        if fee_sell == 0: fee_sell = 0.00000100
        if fee_buy == 0: fee_buy = 0.00000100
        # Check if user already have another open order with the same rate
        # Check if user make a sell process of his buy coin which already in open order
        check_if_same_rate = await store.sql_get_order_by_sellerid_pair_rate(SERVER_BOT, str(ctx.author.id), sell_ticker, 
                             buy_ticker, sell_div_get, real_amount_sell, real_amount_buy, fee_sell, fee_buy, 'OPEN')
        if check_if_same_rate and check_if_same_rate['error'] == True and check_if_same_rate['msg']:
            get_message = check_if_same_rate['msg']
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {get_message}')
            return
        elif check_if_same_rate and check_if_same_rate['error'] == False:
            get_message = check_if_same_rate['msg']
            await ctx.message.add_reaction(EMOJI_OK_BOX)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {get_message}')
            return
        elif check_if_same_rate == False:
            await logchanbot(f'Interal error: selling real amount {real_amount_sell}{sell_ticker} '
                             f'for real amount {real_amount_buy}{buy_ticker} and sell_div_get {sell_div_get}')
            await ctx.send(f'{EMOJI_INFORMATION} {ctx.author.mention} internal error to create open order, please report this.')
            return

        order_add = await store.sql_store_openorder(str(ctx.message.id), (ctx.message.content)[:120], sell_ticker, 
                                real_amount_sell, real_amount_sell-fee_sell, str(ctx.author.id), 
                                buy_ticker, real_amount_buy, real_amount_buy-fee_buy, sell_div_get, SERVER_BOT)
        if order_add:
            get_message = "New open order created: #**{}**```Selling: {}{}\nFor: {}{}\nFee: {}{}```".format(order_add, 
                                                                            num_format_coin(real_amount_sell, sell_ticker), sell_ticker,
                                                                            num_format_coin(real_amount_buy, buy_ticker), buy_ticker,
                                                                            num_format_coin(fee_sell, sell_ticker), sell_ticker)
            await ctx.message.add_reaction(EMOJI_OK_BOX)
            try:
                await ctx.send(f'{ctx.author.mention} {get_message}')
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                await logchanbot(traceback.format_exc())
            # add message to trade channel as well.
            if ctx.message.channel.id != NOTIFY_TRADE_CHAN or isinstance(ctx.message.channel, discord.DMChannel) == True:
                botLogChan = self.bot.get_channel(NOTIFY_TRADE_CHAN)
                await botLogChan.send(get_message)
            return


    @commands.command(usage="buy <ref_number>", aliases=['buying'], description="Buy coin from a referenced number.")
    async def buy(self, ctx, ref_number: str):
        # TRTL discord
        if isinstance(ctx.message.channel, discord.DMChannel) == False and ctx.guild and ctx.guild.id == TRTL_DISCORD:
            return

        botLogChan = self.bot.get_channel(LOG_CHAN)
        try:
            if isinstance(ctx.message.channel, discord.DMChannel) == True:
                pass
            else:
                serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                if isinstance(ctx.message.channel, discord.DMChannel) == False and serverinfo \
                and 'enable_trade' in serverinfo and serverinfo['enable_trade'] == "NO":
                    prefix = serverinfo['prefix']
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Trade Command is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING TRADE`')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}buy command** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
                    return
        except Exception as e:
            if isinstance(ctx.message.channel, discord.DMChannel) == False:
                return
            await logchanbot(traceback.format_exc())
            return

        # check if bot is going to restart
        if IS_RESTARTING:
            await ctx.message.add_reaction(EMOJI_REFRESH)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
            return

        # check if the argument is ref or ticker by length
        if len(ref_number) < 6:
            # assume it is ticker
            # ,buy trtl (example)
            COIN_NAME = ref_number.upper()
            if COIN_NAME not in ENABLE_TRADE_COIN:
                await ctx.send(f'{EMOJI_ERROR} **{COIN_NAME}** is not in our list.')
                return
            
            # get list of all coin where they sell XXX
            get_markets = await store.sql_get_open_order_by_alluser_by_coins(COIN_NAME, "ALL", "OPEN", "ASC")
            if get_markets and len(get_markets) > 0:
                list_numb = 0
                table_data = [
                    ['PAIR', 'Selling', 'For', 'Rate', 'Order #']
                    ]
                for order_item in get_markets:
                    list_numb += 1
                    if is_tradeable_coin(order_item['coin_get']) and is_tradeable_coin(order_item['coin_sell']):
                        table_data.append([order_item['pair_name'], num_format_coin(order_item['amount_sell_after_fee'], order_item['coin_sell'])+order_item['coin_sell'],
                                          num_format_coin(order_item['amount_get_after_fee'], order_item['coin_get'])+order_item['coin_get'], 
                                          '{:.8f}'.format(round(order_item['amount_sell']/order_item['amount_get']/get_decimal(order_item['coin_sell'])*get_decimal(order_item['coin_get']), 8)), 
                                          order_item['order_id']])
                    else:
                        table_data.append([order_item['pair_name']+"*", num_format_coin(order_item['amount_sell_after_fee'], order_item['coin_sell'])+order_item['coin_sell'],
                                          num_format_coin(order_item['amount_get_after_fee'], order_item['coin_get'])+order_item['coin_get'], 
                                          '{:.8f}'.format(round(order_item['amount_sell']/order_item['amount_get']/get_decimal(order_item['coin_sell'])*get_decimal(order_item['coin_get']), 8)), 
                                          order_item['order_id']])
                    if list_numb > 20:
                        break
                table = AsciiTable(table_data)
                # table.inner_column_border = False
                # table.outer_border = False
                table.padding_left = 0
                table.padding_right = 0
                title = "MARKET SELLING **{}**".format(COIN_NAME)
                await ctx.send(f'[ {title} ]\n'
                               f'```{table.table}```')
                return
            else:
                await ctx.send(f'{ctx.author.mention} Currently, no opening selling **{COIN_NAME}**. Please make some open order for others.')
                return
        else:
            # assume reference number
            get_order_num = await store.sql_get_order_numb(ref_number)
            if get_order_num:
                # check if own order
                if get_order_num['sell_user_server'] == SERVER_BOT and ctx.author.id == int(get_order_num['userid_sell']):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} #**{ref_number}** is your own selling order.')
                    return
                else:
                    # check if sufficient balance
                    wallet = await store.sql_get_userwallet(str(ctx.author.id), get_order_num['coin_get'], SERVER_BOT)
                    if wallet is None:
                        if get_order_num['coin_get'] in ENABLE_COIN_ERC:
                            w = await create_address_eth()
                            userregister = await store.sql_register_user(str(ctx.author.id), get_order_num['coin_get'], SERVER_BOT, 0, w)
                        elif get_order_num['coin_get'] in ENABLE_COIN_TRC:
                            result = await store.create_address_trx()
                            userregister = await store.sql_register_user(str(ctx.author.id), get_order_num['coin_get'], SERVER_BOT, 0, result)
                        else:
                            userregister = await store.sql_register_user(str(ctx.author.id), get_order_num['coin_get'], SERVER_BOT, 0)
                        wallet = await store.sql_get_userwallet(str(ctx.author.id), get_order_num['coin_get'], SERVER_BOT)
                    if wallet:
                        userdata_balance = await store.sql_user_balance(str(ctx.author.id), get_order_num['coin_get'], SERVER_BOT)
                        xfer_in = 0
                        if get_order_num['coin_get'] not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                            xfer_in = await store.sql_user_balance_get_xfer_in(str(ctx.author.id), get_order_num['coin_get'])
                        if get_order_num['coin_get'] in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                            actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
                        elif get_order_num['coin_get'] in ENABLE_COIN_NANO:
                            actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
                            actual_balance = round(actual_balance / get_decimal(get_order_num['coin_get']), 6) * get_decimal(get_order_num['coin_get'])
                        else:
                            actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
                        # Negative check
                        try:
                            if actual_balance < 0:
                                msg_negative = 'Negative balance detected:\nUser: '+str(ctx.author.id)+'\nCoin: '+get_order_num['coin_get']+'\nAtomic Balance: '+str(actual_balance)
                                await logchanbot(msg_negative)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    if actual_balance < get_order_num['amount_get_after_fee']:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send('{} {} You do not have sufficient balance.'
                                       '```Needed: {}{}\n'
                                       'Have:   {}{}```'.format(EMOJI_RED_NO, ctx.author.mention, 
                                                         num_format_coin(get_order_num['amount_get'], 
                                                         get_order_num['coin_get']), get_order_num['coin_get'],
                                                         num_format_coin(actual_balance, get_order_num['coin_get']), 
                                                         get_order_num['coin_get']))
                        return
                    else:
                        # let's make order update
                        match_order = await store.sql_match_order_by_sellerid(str(ctx.author.id), ref_number, SERVER_BOT, get_order_num['sell_user_server'], get_order_num['userid_sell'], True)
                        if match_order:
                            await ctx.message.add_reaction(EMOJI_OK_BOX)
                            try:
                                await ctx.send('{} #**{}** Order completed!'
                                               '```'
                                               'Get: {}{}\n'
                                               'From selling: {}{}\n'
                                               'Fee: {}{}\n'
                                               '```'.format(ctx.author.mention, ref_number, num_format_coin(get_order_num['amount_sell_after_fee'], 
                                                            get_order_num['coin_sell']), get_order_num['coin_sell'], 
                                                            num_format_coin(get_order_num['amount_get_after_fee'], 
                                                            get_order_num['coin_get']), get_order_num['coin_get'],
                                                            num_format_coin(get_order_num['amount_get']-get_order_num['amount_get_after_fee'], 
                                                            get_order_num['coin_get']), get_order_num['coin_get']))
                                try:
                                    sold = num_format_coin(get_order_num['amount_sell'], get_order_num['coin_sell']) + get_order_num['coin_sell']
                                    bought = num_format_coin(get_order_num['amount_get_after_fee'], get_order_num['coin_get']) + get_order_num['coin_get']
                                    fee = str(num_format_coin(get_order_num['amount_get']-get_order_num['amount_get_after_fee'], get_order_num['coin_get']))
                                    fee += get_order_num['coin_get']
                                    if get_order_num['sell_user_server'] == SERVER_BOT:
                                        member = self.bot.get_user(int(get_order_num['userid_sell']))
                                        if member:
                                            try:
                                                await member.send(f'A user has bought #**{ref_number}**\n```Sold: {sold}\nGet: {bought}```')
                                            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                                pass
                                    # add message to trade channel as well.
                                    if ctx.message.channel.id != NOTIFY_TRADE_CHAN:
                                        botLogChan = self.bot.get_channel(NOTIFY_TRADE_CHAN)
                                        await botLogChan.send(f'A user has bought #**{ref_number}**\n```Sold: {sold}\nGet: {bought}\nFee: {fee}```')
                                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                    pass
                            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                pass
                            return
                        else:
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **{ref_number}** internal error, please report.')
                            return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} #**{ref_number}** does not exist or already completed.')
                return


    @commands.command(usage="trade <coin/pair> <desc|asc>", aliases=['market'], description="Check market for opened orders.")
    async def trade(self, ctx, coin: str=None, option_order: str=None):
        # TRTL discord
        if isinstance(ctx.message.channel, discord.DMChannel) == False and ctx.guild and ctx.guild.id == TRTL_DISCORD:
            return

        botLogChan = self.bot.get_channel(LOG_CHAN)
        try:
            if isinstance(ctx.message.channel, discord.DMChannel) == True:
                pass
            else:
                serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                if isinstance(ctx.message.channel, discord.DMChannel) == False and serverinfo \
                and 'enable_trade' in serverinfo and serverinfo['enable_trade'] == "NO":
                    prefix = serverinfo['prefix']
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Trade Command is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING TRADE`')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}trade/market command** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
                    return
        except Exception as e:
            if isinstance(ctx.message.channel, discord.DMChannel) == False:
                return
            await logchanbot(traceback.format_exc())
            return

        if option_order is None:
            option_order = "ASC" # ascending
        elif option_order and (option_order.upper() not in ["DESC", "ASC"]):
            option_order = "asc" # ascending
        elif option_order:
            option_order = option_order.upper()

        if coin is None:
            await ctx.send(f'{ctx.author.mention} Please tell me the coin or pair you want to show the trade list (Ex. `doge/xmr` or `doge`).')
            return
        else:
            # check if there is / or -
            coin_pair = None
            COIN_NAME = None
            get_markets = None
            coin = coin.upper()
            if "/" in coin:
                coin_pair = coin.split("/")
            elif "." in coin:
                coin_pair = coin.split(".")
            elif "-" in coin:
                coin_pair = coin.split("-")
            if coin_pair is None:
                COIN_NAME = coin.upper()
                if COIN_NAME not in ENABLE_TRADE_COIN:
                    await ctx.message.add_reaction(EMOJI_RED_NO)
                    await ctx.send(f'{EMOJI_RED_NO} {COIN_NAME} in not in our list.')
                    return
                else:
                    get_markets = await store.sql_get_open_order_by_alluser(COIN_NAME, 'OPEN', False, 50)
            elif coin_pair and len(coin_pair) == 2:
                if coin_pair[0] not in ENABLE_TRADE_COIN:
                    await ctx.send(f'{EMOJI_ERROR} **{coin_pair[0]}** is not in our list. Available right now: **{config.trade.enable_coin}**')
                    return
                elif coin_pair[1] not in ENABLE_TRADE_COIN:
                    await ctx.send(f'{EMOJI_ERROR} **{coin_pair[1]}** is not in our list. Available right now: **{config.trade.enable_coin}**')
                    return
                else:
                    get_markets = await store.sql_get_open_order_by_alluser_by_coins(coin_pair[0], coin_pair[1], "OPEN", option_order)
            if get_markets and len(get_markets) > 0:
                list_numb = 0
                table_data = [
                    ['PAIR', 'Selling', 'For', 'Rate', 'Order #']
                    ]
                for order_item in get_markets:
                    list_numb += 1
                    # coin_get
                    coin_sell_decimal = 1
                    coin_get_decimal = 1
                    if order_item['coin_get'] not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                        coin_get_decimal = get_decimal(order_item['coin_get'])
                    # coin_get
                    if order_item['coin_sell'] not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                        coin_sell_decimal = get_decimal(order_item['coin_sell'])
                    if is_tradeable_coin(order_item['coin_get']) and is_tradeable_coin(order_item['coin_sell']):
                        table_data.append([order_item['pair_name'], num_format_coin(order_item['amount_sell_after_fee'], order_item['coin_sell'])+order_item['coin_sell'],
                                          num_format_coin(order_item['amount_get_after_fee'], order_item['coin_get'])+order_item['coin_get'], 
                                          '{:.8f}'.format(round(order_item['amount_sell']/order_item['amount_get']/coin_sell_decimal*coin_get_decimal, 8)), 
                                          order_item['order_id']])
                    else:
                        table_data.append([order_item['pair_name']+"*", num_format_coin(order_item['amount_sell_after_fee'], order_item['coin_sell'])+order_item['coin_sell'],
                                          num_format_coin(order_item['amount_get_after_fee'], order_item['coin_get'])+order_item['coin_get'], 
                                          '{:.8f}'.format(round(order_item['amount_sell']/order_item['amount_get']/coin_sell_decimal*coin_get_decimal, 8)), 
                                          order_item['order_id']])
                    if list_numb > 15:
                        break
                table = AsciiTable(table_data)
                # table.inner_column_border = False
                # table.outer_border = False
                table.padding_left = 0
                table.padding_right = 0
                extra_text = f"Check specifically for a coin *{config.trade.enable_coin}*."
                if coin_pair:
                    title = "**MARKET {}/{}**".format(coin_pair[0], coin_pair[1])
                else:
                    title = "**MARKET {}**".format(COIN_NAME)
                await ctx.send(f'[ {title} ]\n'
                               f'```{table.table}```{extra_text}')
                return
            else:
                if coin_pair is None:
                    # get another buy of ticker
                    get_markets = await store.sql_get_open_order_by_alluser(COIN_NAME, 'OPEN', True, 50)
                    if get_markets and len(get_markets) > 0:
                        list_numb = 0
                        table_data = [
                            ['PAIR', 'Selling', 'For', 'Rate', 'Order #']
                            ]
                        for order_item in get_markets:
                            list_numb += 1
                            # coin_get
                            coin_sell_decimal = 1
                            coin_get_decimal = 1
                            if order_item['coin_get'] not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                                coin_get_decimal = get_decimal(order_item['coin_get'])
                            # coin_get
                            if order_item['coin_sell'] not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                                coin_sell_decimal = get_decimal(order_item['coin_sell'])
                            if is_tradeable_coin(order_item['coin_get']) and is_tradeable_coin(order_item['coin_sell']):
                                table_data.append([order_item['pair_name'], num_format_coin(order_item['amount_sell_after_fee'], order_item['coin_sell'])+order_item['coin_sell'],
                                                  num_format_coin(order_item['amount_get_after_fee'], order_item['coin_get'])+order_item['coin_get'], 
                                                  '{:.8f}'.format(round(order_item['amount_sell']/order_item['amount_get']/coin_sell_decimal*coin_get_decimal, 8)), 
                                                  order_item['order_id']])
                            else:
                                table_data.append([order_item['pair_name']+"*", num_format_coin(order_item['amount_sell_after_fee'], order_item['coin_sell'])+order_item['coin_sell'],
                                                  num_format_coin(order_item['amount_get_after_fee'], order_item['coin_get'])+order_item['coin_get'], 
                                                  '{:.8f}'.format(round(order_item['amount_sell']/order_item['amount_get']/coin_sell_decimal*coin_get_decimal, 8)), 
                                                  order_item['order_id']])
                            if list_numb > 15:
                                break
                        table = AsciiTable(table_data)
                        table.padding_left = 0
                        table.padding_right = 0
                        title = "MARKET **{}**".format(COIN_NAME)
                        extra_text = f"Check specifically for a coin *{config.trade.enable_coin}*."
                        await ctx.send(f'There is no selling for {COIN_NAME} but there are buy order of {COIN_NAME}.\n[ {title} ]\n'
                                       f'```{table.table}```{extra_text}')
                        return
                    else:
                        await ctx.send(f'{ctx.author.mention} Currently, no opening selling or buying market for {COIN_NAME}. Please make some open order for others.')
                else:
                    await ctx.send(f'{ctx.author.mention} Currently, no opening selling market pair for {coin}. Please make some open order for others.')
                return


    @commands.command(usage="cancel <ref_number|all>", description="Cancel an opened order or all.")
    async def cancel(self, ctx, order_num: str = 'ALL'):
        # TRTL discord
        if isinstance(ctx.message.channel, discord.DMChannel) == False and ctx.guild and ctx.guild.id == TRTL_DISCORD:
            return

        botLogChan = self.bot.get_channel(LOG_CHAN)
        try:
            if isinstance(ctx.message.channel, discord.DMChannel) == True:
                pass
            else:
                serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                if isinstance(ctx.message.channel, discord.DMChannel) == False and serverinfo \
                and 'enable_trade' in serverinfo and serverinfo['enable_trade'] == "NO":
                    prefix = serverinfo['prefix']
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Trade Command is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING TRADE`')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}cancel trade command** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
                    return
        except Exception as e:
            if isinstance(ctx.message.channel, discord.DMChannel) == False:
                return
            await logchanbot(traceback.format_exc())
            return

        if order_num.upper() == 'ALL':
            get_open_order = await store.sql_get_open_order_by_sellerid_all(str(ctx.author.id), 'OPEN')
            if len(get_open_order) == 0:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You do not have any open order.')
                return
            else:
                cancel_order = await store.sql_cancel_open_order_by_sellerid(str(ctx.author.id), 'ALL')
                await ctx.message.add_reaction(EMOJI_OK_BOX)
                await ctx.send(f'{ctx.author.mention} You have cancelled all opened order(s).')
                return
        else:
            if len(order_num) < 6:
                # use coin name
                COIN_NAME = order_num.upper()
                if COIN_NAME not in ENABLE_TRADE_COIN:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **{COIN_NAME}** is not valid.')
                    return
                else:
                    get_open_order = await store.sql_get_open_order_by_sellerid(str(ctx.author.id), COIN_NAME, 'OPEN')
                    if len(get_open_order) == 0:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{ctx.author.mention} You do not have any open order for **{COIN_NAME}**.')
                        return
                    else:
                        cancel_order = await store.sql_cancel_open_order_by_sellerid(str(ctx.author.id), COIN_NAME)
                        await ctx.message.add_reaction(EMOJI_OK_BOX)
                        await ctx.send(f'{ctx.author.mention} You have cancelled all opened sell(s) for **{COIN_NAME}**.')
                        return
            else:
                # open order number
                get_open_order = await store.sql_get_open_order_by_sellerid_all(str(ctx.author.id), 'OPEN')
                if len(get_open_order) == 0:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You do not have any open order.')
                    return
                else:
                    cancelled = False
                    for open_order_list in get_open_order:
                        if order_num == str(open_order_list['order_id']):
                            cancel_order = await store.sql_cancel_open_order_by_sellerid(str(ctx.author.id), order_num) 
                            if cancel_order: cancelled = True
                    if cancelled == False:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You do not have sell #**{order_num}**. Please check command `myorder`')
                        return
                    else:
                        await ctx.message.add_reaction(EMOJI_OK_BOX)
                        await ctx.send(f'{ctx.author.mention} You cancelled #**{order_num}**.')
                        return


    @commands.command(usage="order <ref_number>", aliases=['order_num'], description="Check an opened order.")
    async def order(self, ctx, order_num: str):
        # TRTL discord
        if isinstance(ctx.message.channel, discord.DMChannel) == False and ctx.guild and ctx.guild.id == TRTL_DISCORD:
            return

        botLogChan = self.bot.get_channel(LOG_CHAN)
        try:
            if isinstance(ctx.message.channel, discord.DMChannel) == True:
                pass
            else:
                serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                if isinstance(ctx.message.channel, discord.DMChannel) == False and serverinfo \
                and 'enable_trade' in serverinfo and serverinfo['enable_trade'] == "NO":
                    prefix = serverinfo['prefix']
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Trade Command is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING TRADE`')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}order command** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
                    return
        except Exception as e:
            if isinstance(ctx.message.channel, discord.DMChannel) == False:
                return
            await logchanbot(traceback.format_exc())
            return

        # assume this is reference number
        try:
            ref_number = int(order_num)
            ref_number = str(ref_number)
        except ValueError:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid # number.')
            return
        get_order_num = await store.sql_get_order_numb(ref_number, 'ANY')
        if get_order_num:
            # check if own order
            response_text = "```"
            response_text += "Order #: " + ref_number + "\n"
            response_text += "Sell (After Fee): " + num_format_coin(get_order_num['amount_sell_after_fee'], get_order_num['coin_sell'])+get_order_num['coin_sell'] + "\n"
            response_text += "For (After Fee): " + num_format_coin(get_order_num['amount_get_after_fee'], get_order_num['coin_get'])+get_order_num['coin_get'] + "\n"
            if get_order_num['status'] == "COMPLETE":
                response_text = response_text.replace("Sell", "Sold")
                response_text += "Status: COMPLETED"
            elif get_order_num['status'] == "OPEN":
                response_text += "Status: OPENED"
            elif get_order_num['status'] == "CANCEL":
                response_text += "Status: CANCELLED"
            response_text += "```"

            if get_order_num['sell_user_server'] == SERVER_BOT and ctx.author.id == int(get_order_num['userid_sell']):
                # if he is the seller
                response_text = response_text.replace("Sell", "You sell")
                response_text = response_text.replace("Sold", "You sold")
            if get_order_num['buy_user_server'] and get_order_num['buy_user_server'] == SERVER_BOT \
            and 'userid_get' in get_order_num and (ctx.author.id == int(get_order_num['userid_get'] if get_order_num['userid_get'] else 0)):
                # if he bought this
                response_text = response_text.replace("Sold", "You bought: ")
                response_text = response_text.replace("For (After Fee):", "From selling (After Fee): ")
            await ctx.send(f'{ctx.author.mention} {response_text}')
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} I could not find #**{ref_number}**.')
        return


    @commands.command(usage="myorder [coin]", aliases=['myorders'], description="Check your opened orders.")
    async def myorder(self, ctx, ticker: str = None):
        # TRTL discord
        if isinstance(ctx.message.channel, discord.DMChannel) == False and ctx.guild and ctx.guild.id == TRTL_DISCORD:
            return

        botLogChan = self.bot.get_channel(LOG_CHAN)
        try:
            if isinstance(ctx.message.channel, discord.DMChannel) == True:
                pass
            else:
                serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                if isinstance(ctx.message.channel, discord.DMChannel) == False and serverinfo \
                and 'enable_trade' in serverinfo and serverinfo['enable_trade'] == "NO":
                    prefix = serverinfo['prefix']
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Trade Command is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING TRADE`')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}myorder command** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
                    return
        except Exception as e:
            if isinstance(ctx.message.channel, discord.DMChannel) == False:
                return
            await logchanbot(traceback.format_exc())
            return

        if ticker:
            if len(ticker) < 6:
                # assume it is a coin
                COIN_NAME = ticker.upper()
                if COIN_NAME not in ENABLE_TRADE_COIN:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid ticker **{COIN_NAME}**.')
                    return
                else:
                    get_open_order = await store.sql_get_open_order_by_sellerid(str(ctx.author.id), COIN_NAME, 'OPEN')
                    if get_open_order and len(get_open_order) > 0:
                        table_data = [
                            ['PAIR', 'Selling', 'For', 'Order #']
                            ]
                        for order_item in get_open_order:
                            if is_tradeable_coin(order_item['coin_get']) and is_tradeable_coin(order_item['coin_sell']):
                                table_data.append([order_item['pair_name'], num_format_coin(order_item['amount_sell'], order_item['coin_sell'])+order_item['coin_sell'],
                                                  num_format_coin(order_item['amount_get_after_fee'], order_item['coin_get'])+order_item['coin_get'], 
                                                  order_item['order_id']])
                            else:
                                table_data.append([order_item['pair_name']+"*", num_format_coin(order_item['amount_sell'], order_item['coin_sell'])+order_item['coin_sell'],
                                                  num_format_coin(order_item['amount_get_after_fee'], order_item['coin_get'])+order_item['coin_get'], 
                                                  order_item['order_id']])
                        table = AsciiTable(table_data)
                        # table.inner_column_border = False
                        # table.outer_border = False
                        table.padding_left = 0
                        table.padding_right = 0
                        msg = await ctx.author.send(f'**[ OPEN SELLING LIST {COIN_NAME}]**\n'
                                                            f'```{table.table}```')
                        
                        return
                    else:
                        await ctx.send(f'{ctx.author.mention} You do not have any active selling of **{COIN_NAME}**.')
                        return
            else:
                # assume this is reference number
                try:
                    ref_number = int(ticker)
                    ref_number = str(ref_number)
                except ValueError:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid # number.')
                    return
                get_order_num = await store.sql_get_order_numb(ref_number)
                if get_order_num:
                    # check if own order
                    response_text = "```"
                    response_text += "Order #: " + ref_number + "\n"
                    response_text += "Sell (After Fee): " + num_format_coin(get_order_num['amount_sell_after_fee'], get_order_num['coin_sell'])+get_order_num['coin_sell'] + "\n"
                    response_text += "For (After Fee): " + num_format_coin(get_order_num['amount_get_after_fee'], get_order_num['coin_get'])+get_order_num['coin_get'] + "\n"
                    if get_order_num['status'] == "COMPLETE":
                        response_text = response_text.replace("Sell", "Sold")
                        response_text += "Status: COMPLETED"
                    elif get_order_num['status'] == "OPEN":
                        response_text += "Status: OPENED"
                    elif get_order_num['status'] == "CANCEL":
                        response_text += "Status: CANCELLED"
                    response_text += "```"

                    if get_order_num['sell_user_server'] == SERVER_BOT and ctx.author.id == int(get_order_num['userid_sell']):
                        # if he is the seller
                        response_text = response_text.replace("Sell", "You sell")
                        response_text = response_text.replace("Sold", "You sold")
                    if get_order_num['sell_user_server'] and get_order_num['sell_user_server'] == SERVER_BOT and \
                        'userid_get' in get_order_num and (ctx.author.id == int(get_order_num['userid_get'] if get_order_num['userid_get'] else 0)):
                        # if he bought this
                        response_text = response_text.replace("Sold", "You bought: ")
                        response_text = response_text.replace("For (After Fee):", "From selling (After Fee): ")
                    await ctx.send(f'{ctx.author.mention} {response_text}')
                    return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} I could not find #**{ref_number}**.')
                return
        else:
            get_open_order = await store.sql_get_open_order_by_sellerid_all(str(ctx.author.id), 'OPEN')
            if get_open_order and len(get_open_order) > 0:
                table_data = [
                    ['PAIR', 'Selling', 'For', 'Order #']
                    ]
                for order_item in get_open_order:
                    if is_tradeable_coin(order_item['coin_get']) and is_tradeable_coin(order_item['coin_sell']):
                        table_data.append([order_item['pair_name'], num_format_coin(order_item['amount_sell'], order_item['coin_sell'])+order_item['coin_sell'],
                                          num_format_coin(order_item['amount_get_after_fee'], order_item['coin_get'])+order_item['coin_get'], order_item['order_id']])
                    else:
                        table_data.append([order_item['pair_name']+"*", num_format_coin(order_item['amount_sell'], order_item['coin_sell'])+order_item['coin_sell'],
                                          num_format_coin(order_item['amount_get_after_fee'], order_item['coin_get'])+order_item['coin_get'], order_item['order_id']])
                table = AsciiTable(table_data)
                # table.inner_column_border = False
                # table.outer_border = False
                table.padding_left = 0
                table.padding_right = 0
                msg = await ctx.author.send(f'**[ OPEN SELLING LIST ]**\n'
                                                    f'```{table.table}```')
                
                return
            else:
                await ctx.send(f'{ctx.author.mention} You do not have any active selling.')
                return


def setup(bot):
    bot.add_cog(Trade(bot))