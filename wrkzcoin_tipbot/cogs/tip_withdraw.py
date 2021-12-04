import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from decimal import getcontext, Decimal
from dislash import InteractionClient, ActionRow, Button, ButtonStyle, Option, OptionType, OptionChoice

from config import config
from Bot import *

class TipWithdraw(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def bot_log(self):
        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def withdraw_action(
        self,
        ctx,
        amount: str,
        coin: str,
        action: str, # withdraw or send
        prefix: str=".",
        to_address: str=None # None if withdraw
    ):
        await self.bot_log()
        COIN_NAME = coin.upper()
        if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
            await logchanbot(f'User {ctx.author.id} tried to withdraw {amount} {COIN_NAME}.')
            return {"error": f"**{COIN_NAME}** Unknown Ticker."}
        if is_maintenance_coin(COIN_NAME):
            await logchanbot(f'User {ctx.author.id} tried to withdraw {amount} {COIN_NAME} while it is under maintenance.')
            return {"error": f"**{COIN_NAME}** Under maintenance. Try again later!"}
        if not is_coin_txable(COIN_NAME):
            await logchanbot(f'User {ctx.author.id} tried to withdraw {amount} {COIN_NAME} while it tx not enable.')
            return {"error": f"**{COIN_NAME}** Transaction currently disable Try again later!"}

        # Check if tx in progress
        if ctx.author.id in TX_IN_PROCESS:
            return {"error": "You have another tx in progress!"}
 
        # Check flood of tip
        floodTip = await store.sql_get_countLastTip(str(ctx.author.id), config.floodTipDuration)
        if floodTip >= config.floodTip:
            return {"error": "Cool down your tip or transaction or increase your amount next time."}
            await self.botLogChan.send('A user reached max. TX threshold. Currently halted: `.withdraw`')
            return
        # End of Check flood of tip
        
        amount = str(amount).replace(",", "")
        try:
            amount = Decimal(amount)
        except ValueError:
            return {"error": "Invalid given amount."}

        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
            real_amount = float(amount)
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
            real_amount = float(amount)
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
            real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
            MinTx = get_min_tx_amount(COIN_NAME)
            MaxTx = get_max_tx_amount(COIN_NAME)

        user = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
        if user is None:
            if COIN_NAME in ENABLE_COIN_ERC:
                w = await create_address_eth()
                user = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
            elif COIN_NAME in ENABLE_COIN_TRC:
                result = await store.create_address_trx()
                user = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, result)
            else:
                user = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
            user = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)

        if user['user_wallet_address'] is None and action.upper()=="WITHDRAW":
            extra_txt = ""
            if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                extra_txt = " " + COIN_NAME
            return {"error": f"You do not have a registered address for **{COIN_NAME}**, please use `{prefix}register wallet_address{extra_txt}` to register. Alternatively, please use `{prefix}send <amount> <coin_address>`."}
        elif user['user_wallet_address'] and action.upper()=="WITHDRAW":
            to_address = user['user_wallet_address']
        try:
            NetFee = 0
            userdata_balance = await store.sql_user_balance(str(ctx.author.id), COIN_NAME)
            xfer_in = 0
            if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                xfer_in = await store.sql_user_balance_get_xfer_in(str(ctx.author.id), COIN_NAME)
            if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
            elif COIN_NAME in ENABLE_COIN_NANO:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
                actual_balance = round(actual_balance / get_decimal(COIN_NAME), 6) * get_decimal(COIN_NAME)
            else:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])

            if coin_family == "ERC-20" or coin_family == "TRC-20":
                token_info = await store.get_token_info(COIN_NAME)
                NetFee = token_info['real_withdraw_fee']
                MinTx = token_info['real_min_tx']
                MaxTx = token_info['real_max_tx']
            else:
                NetFee = get_tx_node_fee(coin = COIN_NAME)
            # Negative check
            try:
                if actual_balance < 0:
                    msg_negative = 'Negative balance detected:\nUser: '+str(ctx.author.id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
                    await logchanbot(msg_negative)
            except Exception as e:
                await logchanbot(traceback.format_exc())

            # add redis action
            random_string = str(uuid.uuid4())
            msg_content = "SLASH COMMAND"
            if hasattr(ctx, 'message'):
                msg_content = ctx.message.content
            await add_tx_action_redis(json.dumps([random_string, "WITHDRAW", str(ctx.author.id), ctx.author.name, float("%.3f" % time.time()), msg_content, SERVER_BOT, "START"]), False)

            # If balance 0, no need to check anything
            if actual_balance <= 0:
                return {"error": f"Please check your **{COIN_NAME}** balance."}
            elif real_amount + NetFee > actual_balance:
                extra_fee_txt = ''
                if NetFee > 0:
                    extra_fee_txt = f'You need to leave a node/tx fee: {num_format_coin(NetFee, COIN_NAME)} {COIN_NAME}'
                return {"error": f"Insufficient balance to {action.lower()} {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}. {extra_fee_txt}"}
            elif real_amount > MaxTx:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than '
                               f'{num_format_coin(MaxTx, COIN_NAME)} '
                               f'{COIN_NAME}')
                return {"error": f"Transactions cannot be bigger than {num_format_coin(MaxTx, COIN_NAME)} {COIN_NAME}."}
            elif real_amount < MinTx:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be lower than '
                               f'{num_format_coin(MinTx, COIN_NAME)} '
                               f'{COIN_NAME}')
                return {"error": f"Transactions cannot be lower than {num_format_coin(MinTx, COIN_NAME)} {COIN_NAME}."}
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
            return {"error": "Internal error!"}

        if ctx.author.id not in TX_IN_PROCESS:
            TX_IN_PROCESS.append(ctx.author.id)
        try:
            withdraw_txt = None
            if coin_family in ["TRTL", "BCN"]:
                withdrawTx = await store.sql_external_cn_single(str(ctx.author.id), user['user_wallet_address'], real_amount, COIN_NAME, SERVER_BOT, 'WITHDRAW')
                if withdrawTx:
                    withdraw_txt = "Transaction hash: `{}`\nA node/tx fee `{} {}` deducted from your balance.".format(withdrawTx['transactionHash'], num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
            elif coin_family == "XMR":
                withdrawTx = await store.sql_external_xmr_single(str(ctx.author.id),
                                                                real_amount,
                                                                user['user_wallet_address'],
                                                                COIN_NAME, "WITHDRAW", NetFee)
                if withdrawTx:
                    withdraw_txt = "Transaction hash: `{}`\nA node/tx fee `{} {}` deducted from your balance.".format(withdrawTx['tx_hash'], num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
            elif coin_family == "XCH":
                withdrawTx = await store.sql_external_xch_single(str(ctx.author.id),
                                                                real_amount,
                                                                user['user_wallet_address'],
                                                                COIN_NAME, "WITHDRAW")
                if withdrawTx:
                    withdraw_txt = "Transaction hash: `{}`\nA node/tx fee `{} {}` deducted from your balance.".format(withdrawTx['tx_hash']['name'], num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
            elif coin_family == "NANO":
                withdrawTx = await store.sql_external_nano_single(str(ctx.author.id), real_amount,
                                                                user['user_wallet_address'],
                                                                COIN_NAME, "WITHDRAW")
                if withdrawTx:
                    withdraw_txt = "Block: `{}`".format(withdrawTx['block'])
            elif coin_family == "DOGE": 
                withdrawTx = await store.sql_external_doge_single(str(ctx.author.id), real_amount,
                                                                NetFee, user['user_wallet_address'],
                                                                COIN_NAME, "WITHDRAW")
                if withdrawTx:
                    withdraw_txt = 'Transaction hash: `{}`\nA node/tx fee `{} {}` deducted from your balance.'.format(withdrawTx, num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
            elif coin_family == "ERC-20": 
                withdrawTx = await store.sql_external_erc_single(str(ctx.author.id), user['user_wallet_address'], real_amount, COIN_NAME, 'WITHDRAW', SERVER_BOT)
                if withdrawTx:
                    withdraw_txt = f'Transaction hash: `{withdrawTx}`\nFee `{NetFee} {COIN_NAME}` deducted from your balance.'
            elif coin_family == "TRC-20": 
                withdrawTx = await store.sql_external_trx_single(str(ctx.author.id), user['user_wallet_address'], real_amount, COIN_NAME, 'WITHDRAW', SERVER_BOT)
                if withdrawTx:
                    withdraw_txt = f'Transaction hash: `{withdrawTx}`\nFee `{NetFee} {COIN_NAME}` deducted from your balance.'
            # add redis action
            await add_tx_action_redis(json.dumps([random_string, action.upper(), str(ctx.author.id), ctx.author.name, float("%.3f" % time.time()), msg_content, SERVER_BOT, "COMPLETE"]), False)
            if ctx.author.id in TX_IN_PROCESS:
                TX_IN_PROCESS.remove(ctx.author.id)
            return {
                "result": withdraw_txt, 
                "to_address": to_address, 
                "coin_family": coin_family,
                "real_amount": real_amount
            }
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())


    @inter_client.slash_command(usage="withdraw <amount> <coin>",
                                options=[
                                    Option('amount', 'Enter amount of coin to withdraw', OptionType.NUMBER, required=True),
                                    Option("coin", "Enter coin ticker/name", OptionType.STRING)
                                ],
                                description="Withdraw to your registered address.")
    async def withdraw(
        self, 
        ctx, 
        amount: str, 
        coin: str
    ):
        await self.bot_log()
        prefix = await get_guild_prefix(ctx)
        # check if bot is going to restart
        if IS_RESTARTING:
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.', ephemeral=True)
            return

        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'withdraw')
        if account_lock:
            await ctx.reply(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}', ephemeral=True)
            return
        # end of check if account locked
        # Check if tx in progress
        if ctx.author.id in TX_IN_PROCESS:
            await ctx.reply(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.', ephemeral=True)
            return

        amount = str(amount).replace(",", "")

        # Check flood of tip
        floodTip = await store.sql_get_countLastTip(str(ctx.author.id), config.floodTipDuration)
        if floodTip >= config.floodTip:
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Cool down your tip or TX. or increase your amount next time.', ephemeral=True)
            await self.botLogChan.send('A user reached max. TX threshold. Currently halted: `.withdraw`')
            return
        # End of Check flood of tip

        # Check if maintenance
        if IS_MAINTENANCE == 1 and int(ctx.author.id) not in MAINTENANCE_OWNER:
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}', ephemeral=True)
            return
        # End Check if maintenance


    @commands.command(
        usage="withdraw <amount> <coin>", 
        description="Withdraw <amount> <coin> to your registered address."
    )
    async def withdraw(
        self, 
        ctx, 
        amount: str, 
        coin: str = None
    ):
        await self.bot_log()
        # check if bot is going to restart
        if IS_RESTARTING:
            await ctx.message.add_reaction(EMOJI_REFRESH)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
            return

        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'withdraw')
        if account_lock:
            await ctx.message.add_reaction(EMOJI_LOCKED) 
            await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
            return
        # end of check if account locked

        amount = amount.replace(",", "")

        server_prefix = '.'
        if isinstance(ctx.channel, discord.DMChannel) == False:
            serverinfo = await get_info_pref_coin(ctx)
            server_prefix = serverinfo['server_prefix']
            # check if bot channel is set:
            if serverinfo and serverinfo['botchan']:
                try: 
                    if ctx.channel.id != int(serverinfo['botchan']):
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        botChan = self.bot.get_channel(int(serverinfo['botchan']))
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, {botChan.mention} is the bot channel!!!')
                        return
                except ValueError:
                    pass
            # end of bot channel check

        if coin is None:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please have **ticker** (coin name) after amount for `withdraw`.')
            return

        COIN_NAME = coin.upper()
        withdrawTx = await self.withdraw_action(ctx, amount, COIN_NAME, "WITHDRAW", server_prefix, None)
        if withdrawTx and 'error' in withdrawTx:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send('{} {}, {}'.format(EMOJI_RED_NO, ctx.author.mention, withdrawTx['error']))
            return
        elif withdrawTx and 'result' in withdrawTx:
            withdrawAddress = withdrawTx['to_address']
            withdraw_txt = withdrawTx['result']
            real_amount = withdrawTx['real_amount']
            if withdrawTx['coin_family'] == "ERC-20" or withdrawTx['coin_family'] == "TRC-20":
                await ctx.message.add_reaction(TOKEN_EMOJI)
            else:
                await ctx.message.add_reaction(get_emoji(COIN_NAME))
            try:
                await ctx.author.send(
                                    f'{EMOJI_ARROW_RIGHTHOOK} You have withdrawn {num_format_coin(real_amount, COIN_NAME)} '
                                    f'{COIN_NAME} to `{withdrawAddress}`.\n'
                                    f'{withdraw_txt}')
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                try:
                    await ctx.send(f'{EMOJI_ARROW_RIGHTHOOK} You have withdrawn {num_format_coin(real_amount, COIN_NAME)} '
                                   f'{COIN_NAME} to `{withdrawAddress}`.\n'
                                   f'{withdraw_txt}')
                except Exception as e:
                    pass
            await self.botLogChan.send(f'A user successfully executed `.withdraw {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`')
            return
        else:
            msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Internal error during your withdraw, please report or try again later.')
            await self.botLogChan.send(f'A user failed to executed `.withdraw {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return


    @commands.command(
        usage="send <amount> <coin address> [coin]", 
        description="send <amount> to <coin address>."
    )
    async def send(
        self, 
        ctx, 
        amount: str, 
        CoinAddress: str, 
        coin: str=None
    ):
        await self.bot_log()
        # check if bot is going to restart
        if IS_RESTARTING:
            await ctx.message.add_reaction(EMOJI_REFRESH)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
            return
        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'send')
        if account_lock:
            await ctx.message.add_reaction(EMOJI_LOCKED) 
            await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
            return
        # end of check if account locked

        amount = amount.replace(",", "")

        # Check if tx in progress
        if ctx.author.id in TX_IN_PROCESS:
            await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
            msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

        # if public and there is a bot channel
        if isinstance(ctx.channel, discord.DMChannel) == False:
            serverinfo = await get_info_pref_coin(ctx)
            server_prefix = serverinfo['server_prefix']
            # check if bot channel is set:
            if serverinfo and serverinfo['botchan']:
                try: 
                    if ctx.channel.id != int(serverinfo['botchan']):
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        botChan = self.bot.get_channel(int(serverinfo['botchan']))
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, {botChan.mention} is the bot channel!!!')
                        return
                except ValueError:
                    pass
            # end of bot channel check

        # Check flood of tip
        floodTip = await store.sql_get_countLastTip(str(ctx.author.id), config.floodTipDuration)
        if floodTip >= config.floodTip:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO}{ctx.author.mention} Cool down your tip or TX. or increase your amount next time.')
            await self.botLogChan.send('A user reached max. TX threshold. Currently halted: `.send`')
            return
        # End of Check flood of tip

        # Check if maintenance
        if IS_MAINTENANCE == 1:
            if int(ctx.author.id) in MAINTENANCE_OWNER:
                pass
            else:
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}')
                return
        else:
            pass
        # End Check if maintenance

        try:
            amount = Decimal(amount)
        except ValueError:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
            return

        # Check which coinname is it.
        COIN_NAME = get_cn_coin_from_address(CoinAddress)
        if COIN_NAME is None and CoinAddress.startswith("0x"):
            if coin is None:
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} you need to add **TOKEN NAME** after address.')
                return
            else:
                COIN_NAME = coin.upper()
                if COIN_NAME not in ENABLE_COIN_ERC:
                    await ctx.message.add_reaction(EMOJI_WARNING)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Unsupported Token.')
                    return
            if CoinAddress.upper().startswith("0X00000000000000000000000000000"):
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token address:\n'
                                     f'`{CoinAddress}`')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            else:
                try:
                    valid_address = await store.erc_validate_address(CoinAddress, COIN_NAME)
                    if valid_address and valid_address.upper() == CoinAddress.upper():
                        valid = True
                    else:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token address:\n'
                                             f'`{CoinAddress}`')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
                except Exception as e:
                    print(traceback.format_exc())
                    await logchanbot(traceback.format_exc())
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} internal error checking address:\n'
                                         f'`{CoinAddress}`')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
        elif COIN_NAME is None:
            if coin is None:
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} you need to add **COIN NAME** after address.')
                return
            else:
                COIN_NAME = coin.upper()
                if COIN_NAME not in ENABLE_COIN_DOGE:
                    await ctx.message.add_reaction(EMOJI_WARNING)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Unsupported coin **{COIN_NAME}**.')
                    return
        elif COIN_NAME == "TRON_TOKEN":
            if coin is None:
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} you need to add **COIN NAME** after address.')
                return
            else:
                COIN_NAME = coin.upper()
                if COIN_NAME not in ENABLE_COIN_TRC:
                    await ctx.message.add_reaction(EMOJI_WARNING)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Unsupported token **{COIN_NAME}**.')
                    return

        coin_family = None
        if not is_coin_txable(COIN_NAME):
            msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} TX is currently disable for {COIN_NAME}.')
            await msg.add_reaction(EMOJI_OK_BOX)
            await logchanbot(f'User {ctx.author.id} tried to send {amount} {COIN_NAME} while it tx not enable.')
            return
        if COIN_NAME:
            if COIN_NAME in ENABLE_COIN_ERC:
                coin_family = "ERC-20"
            elif COIN_NAME in ENABLE_COIN_TRC:
                coin_family = "TRC-20"
            else:
                coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
        else:
            await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
            try:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} could not find what address it is.')
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                try:
                    await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} could not find what address it is.')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    return
            return

        # add redis action
        random_string = str(uuid.uuid4())
        await add_tx_action_redis(json.dumps([random_string, "SEND", str(ctx.author.id), ctx.author.name, float("%.3f" % time.time()), ctx.message.content, SERVER_BOT, "START"]), False)

        if coin_family in ["TRTL", "BCN"]:
            MinTx = get_min_tx_amount(COIN_NAME)
            MaxTx = get_max_tx_amount(COIN_NAME)
            real_amount = int(amount * get_decimal(COIN_NAME))
            addressLength = get_addrlen(COIN_NAME)
            IntaddressLength = get_intaddrlen(COIN_NAME)
            NetFee = get_tx_node_fee(coin = COIN_NAME)
            if is_maintenance_coin(COIN_NAME):
                await ctx.message.add_reaction(EMOJI_MAINTENANCE)
                try:
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    try:
                        await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        return
                return

            print('{} - {} - {}'.format(COIN_NAME, addressLength, IntaddressLength))
            if len(CoinAddress) == int(addressLength):
                valid_address = addressvalidation.validate_address_cn(CoinAddress, COIN_NAME)
                # print(valid_address)
                if valid_address != CoinAddress:
                    valid_address = None

                if valid_address is None:
                    await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
                    try:
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                       f'`{CoinAddress}`')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        try:
                            await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                                          f'`{CoinAddress}`')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            return
                    return
            elif len(CoinAddress) == int(IntaddressLength):
                valid_address = addressvalidation.validate_integrated_cn(CoinAddress, COIN_NAME)
                # print(valid_address)
                if valid_address == 'invalid':
                    await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
                    try:
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid integrated address:\n'
                                       f'`{CoinAddress}`')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        try:
                            await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid integrated address:\n'
                                                          f'`{CoinAddress}`')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            return
                    return
                if len(valid_address) == 2:
                    iCoinAddress = CoinAddress
                    CoinAddress = valid_address['address']
                    paymentid = valid_address['integrated_id']
            elif len(CoinAddress) == int(addressLength) + 64 + 1:
                valid_address = {}
                check_address = CoinAddress.split(".")
                if len(check_address) != 2:
                    await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
                    try:
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid {COIN_NAME} address + paymentid')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        try:
                            await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid {COIN_NAME} address + paymentid')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            return
                    return
                else:
                    valid_address_str = addressvalidation.validate_address_cn(check_address[0], COIN_NAME)
                    paymentid = check_address[1].strip()
                    if valid_address_str is None:
                        await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
                        try:
                            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                           f'`{check_address[0]}`')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            try:
                                await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                                              f'`{check_address[0]}`')
                            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                return
                        return
                    else:
                        valid_address['address'] = valid_address_str
                # Check payment ID
                    if len(paymentid) == 64:
                        if not re.match(r'[a-zA-Z0-9]{64,}', paymentid.strip()):
                            await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
                            try:
                                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} PaymentID: `{paymentid}`\n'
                                                'Should be in 64 correct format.')
                            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                try:
                                    await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} PaymentID: `{paymentid}`\n'
                                                                  'Should be in 64 correct format.')
                                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                    return
                            return
                        else:
                            CoinAddress = valid_address['address']
                            valid_address['paymentid'] = paymentid
                            iCoinAddress = addressvalidation.make_integrated_cn(valid_address['address'], COIN_NAME, paymentid)['integrated_address']
                            pass
                    else:
                        await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
                        try:
                            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} PaymentID: `{paymentid}`\n'
                                            'Incorrect length')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            try:
                                await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} PaymentID: `{paymentid}`\n'
                                                             'Incorrect length')
                            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                return
                        return
            else:
                await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
                try:
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                   f'`{CoinAddress}`')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    try:
                        await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                                      f'`{CoinAddress}`')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        return
                return

            user_from = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            if user_from is None:
                user_from = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
            if user_from['balance_wallet_address'] == CoinAddress:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You can not send to your own deposit address.')
                return

            userdata_balance = await store.sql_user_balance(str(ctx.author.id), COIN_NAME)
            xfer_in = 0
            if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                xfer_in = await store.sql_user_balance_get_xfer_in(str(ctx.author.id), COIN_NAME)
            if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
            elif COIN_NAME in ENABLE_COIN_NANO:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
                actual_balance = round(actual_balance / get_decimal(COIN_NAME), 6) * get_decimal(COIN_NAME)
            else:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])

            # Negative check
            try:
                if actual_balance < 0:
                    msg_negative = 'Negative balance detected:\nUser: '+str(ctx.author.id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
                    await logchanbot(msg_negative)
            except Exception as e:
                await logchanbot(traceback.format_exc())

            if real_amount + NetFee > actual_balance:
                extra_fee_txt = ''
                if NetFee > 0:
                    extra_fee_txt = f'You need to leave a node/tx fee: {num_format_coin(NetFee, COIN_NAME)} {COIN_NAME}'
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to send tx of '
                               f'{num_format_coin(real_amount, COIN_NAME)} '
                               f'{COIN_NAME} to {CoinAddress}. {extra_fee_txt}')

                return

            if real_amount > MaxTx:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than '
                               f'{num_format_coin(MaxTx, COIN_NAME)} '
                               f'{COIN_NAME}.')
                return
            elif real_amount < MinTx:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than '
                               f'{num_format_coin(MinTx, COIN_NAME)} '
                               f'{COIN_NAME}.')

                return

            # Get wallet status
            walletStatus = await daemonrpc_client.getWalletStatus(COIN_NAME)
            if walletStatus is None:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} I can not connect to wallet service or daemon.')
                return
            else:
                localDaemonBlockCount = int(walletStatus['blockCount'])
                networkBlockCount = int(walletStatus['knownBlockCount'])
                if networkBlockCount - localDaemonBlockCount >= 20:
                    # if height is different by 20
                    t_percent = '{:,.2f}'.format(truncate(localDaemonBlockCount / networkBlockCount * 100, 2))
                    t_localDaemonBlockCount = '{:,}'.format(localDaemonBlockCount)
                    t_networkBlockCount = '{:,}'.format(networkBlockCount)
                    await ctx.message.add_reaction(EMOJI_WARNING)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} Wallet service hasn\'t sync fully with network or being re-sync. More info:\n```'
                                   f'networkBlockCount:     {t_networkBlockCount}\n'
                                   f'localDaemonBlockCount: {t_localDaemonBlockCount}\n'
                                   f'Progress %:            {t_percent}\n```'
                                   )
                    return
                else:
                    pass
            # End of wallet status

            main_address = getattr(getattr(config,"daemon"+COIN_NAME),"MainAddress")
            if CoinAddress == main_address:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, Can not send to this address:\n```{CoinAddress}``` ')
                return
            
            if len(valid_address) == 2:
                tip = None
                try:
                    check_in = await store.coin_check_balance_address_in_users(CoinAddress, COIN_NAME)
                    if check_in:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, Can not send to this address:\n```{CoinAddress}``` ')
                        return
                    if ctx.author.id not in TX_IN_PROCESS:
                        TX_IN_PROCESS.append(ctx.author.id)
                        try:
                            tip = await store.sql_external_cn_single_id(str(ctx.author.id), CoinAddress, real_amount, paymentid, COIN_NAME)
                            tip_tx_tipper = "Transaction hash: `{}`".format(tip['transactionHash'])
                            tip_tx_tipper += "\nA node/tx fee `{}{}` deducted from your balance.".format(num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                        await asyncio.sleep(config.interval.tx_lap_each)
                        TX_IN_PROCESS.remove(ctx.author.id)
                    else:
                        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
                        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return                    
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                if tip:
                    await ctx.message.add_reaction(get_emoji(COIN_NAME))
                    await self.botLogChan.send(f'A user successfully executed `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}` with paymentid.')
                    await ctx.author.send(
                                           f'{EMOJI_ARROW_RIGHTHOOK} You have sent {num_format_coin(real_amount, COIN_NAME)} '
                                           f'{COIN_NAME} '
                                           f'to `{iCoinAddress}`\n\n'
                                           f'Address: `{CoinAddress}`\n'
                                           f'Payment ID: `{paymentid}`\n'
                                           f'{tip_tx_tipper}')
                    return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await self.botLogChan.send(f'A user failed to execute send `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}` with paymentid.')
                    msg = await ctx.send(f'{ctx.author.mention} Please try again or report.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
            else:
                tip = None
                try:
                    if ctx.author.id not in TX_IN_PROCESS:
                        TX_IN_PROCESS.append(ctx.author.id)
                        try:
                            tip = await store.sql_external_cn_single(str(ctx.author.id), CoinAddress, real_amount, COIN_NAME, SERVER_BOT, 'SEND')
                            tip_tx_tipper = "Transaction hash: `{}`".format(tip['transactionHash'])
                            # replace fee
                            tip['fee'] = get_tx_node_fee(COIN_NAME)
                            tip_tx_tipper += "\nTx Fee: `{}{}`".format(num_format_coin(tip['fee'], COIN_NAME), COIN_NAME)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                        await asyncio.sleep(config.interval.tx_lap_each)
                        TX_IN_PROCESS.remove(ctx.author.id)
                        # add redis
                        await add_tx_action_redis(json.dumps([random_string, "SEND", str(ctx.author.id), ctx.author.name, float("%.3f" % time.time()), ctx.message.content, SERVER_BOT, "COMPLETE"]), False)
                    else:
                        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
                        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                if tip:
                    await ctx.message.add_reaction(get_emoji(COIN_NAME))
                    await self.botLogChan.send(f'A user successfully executed `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                    await ctx.author.send(f'{EMOJI_ARROW_RIGHTHOOK} You have sent {num_format_coin(real_amount, COIN_NAME)} '
                                                  f'{COIN_NAME} '
                                                  f'to `{CoinAddress}`\n'
                                                  f'{tip_tx_tipper}')
                    return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await self.botLogChan.send(f'A user failed to execute `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                    await ctx.send(f'{ctx.author.mention} Can not deliver TX for {COIN_NAME} right now. Try again soon.')
                    # add to failed tx table
                    await store.sql_add_failed_tx(COIN_NAME, str(ctx.author.id), ctx.author.name, real_amount, "SEND")
                    return
        elif coin_family == "XMR" or coin_family == "XCH":
            MinTx = get_min_tx_amount(COIN_NAME)
            MaxTx = get_max_tx_amount(COIN_NAME)
            real_amount = int(amount * get_decimal(COIN_NAME))

            # If not Masari
            if COIN_NAME not in ["MSR", "UPX", "XCH", "XFX"]:
                valid_address = await validate_address_xmr(str(CoinAddress), COIN_NAME)
                if valid_address['valid'] == False or valid_address['nettype'] != 'mainnet':
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Address: `{CoinAddress}` '
                                       'is invalid.')
                        return
            elif coin_family == "XCH":
                valid_address = addressvalidation_xch.validate_address(CoinAddress, COIN_NAME)
                if valid_address == False:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Address: `{CoinAddress}` '
                                   'is invalid.')
                    return
            # OK valid address
            # TODO: validate XCH address
            user_from = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            if user_from is None:
                user_from = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
            userdata_balance = await store.sql_user_balance(str(ctx.author.id), COIN_NAME)
            xfer_in = 0
            if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                xfer_in = await store.sql_user_balance_get_xfer_in(str(ctx.author.id), COIN_NAME)
            if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
            elif COIN_NAME in ENABLE_COIN_NANO:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
                actual_balance = round(actual_balance / get_decimal(COIN_NAME), 6) * get_decimal(COIN_NAME)
            else:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
            # Negative check
            try:
                if actual_balance < 0:
                    msg_negative = 'Negative balance detected:\nUser: '+str(ctx.author.id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
                    await logchanbot(msg_negative)
            except Exception as e:
                await logchanbot(traceback.format_exc())

            # If balance 0, no need to check anything
            if actual_balance <= 0:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please check your **{COIN_NAME}** balance.')
                return
            NetFee = get_tx_node_fee(coin = COIN_NAME)
            # XMR
            # NetFee = await get_tx_fee_xmr(coin = COIN_NAME, amount = real_amount, to_address = CoinAddress)
            if real_amount + NetFee > actual_balance:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to send out '
                               f'{num_format_coin(real_amount, COIN_NAME)} '
                               f'{COIN_NAME}. You need to leave a node/tx fee: {num_format_coin(NetFee, COIN_NAME)} {COIN_NAME}')
                return
            if real_amount < MinTx:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transaction cannot be smaller than '
                               f'{num_format_coin(MinTx, COIN_NAME)} '
                               f'{COIN_NAME}.')
                return
            if real_amount > MaxTx:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transaction cannot be bigger than '
                               f'{num_format_coin(MaxTx, COIN_NAME)} '
                               f'{COIN_NAME}.')
                return

            SendTx = None
            check_in = await store.coin_check_balance_address_in_users(CoinAddress, COIN_NAME)
            if check_in:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, Can not send to this address:\n```{CoinAddress}``` ')
                return
            if ctx.author.id not in TX_IN_PROCESS:
                TX_IN_PROCESS.append(ctx.author.id)
                try:
                    if coin_family == "XCH":
                        SendTx = await store.sql_external_xch_single(str(ctx.author.id), real_amount,
                                                                     CoinAddress, COIN_NAME, "SEND")
                        SendTx['tx_hash'] = SendTx['tx_hash']['name']
                    else:
                        SendTx = await store.sql_external_xmr_single(str(ctx.author.id), real_amount,
                                                                     CoinAddress, COIN_NAME, "SEND", NetFee)
                    # add redis
                    await add_tx_action_redis(json.dumps([random_string, "SEND", str(ctx.author.id), ctx.author.name, float("%.3f" % time.time()), ctx.message.content, SERVER_BOT, "COMPLETE"]), False)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                await asyncio.sleep(config.interval.tx_lap_each)
                TX_IN_PROCESS.remove(ctx.author.id)
            else:
                # reject and tell to wait
                msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You have another tx in process. Please wait it to finish. ')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            if SendTx:
                SendTx_hash = SendTx['tx_hash']
                extra_txt = "A node/tx fee `{} {}` deducted from your balance.".format(num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
                await ctx.message.add_reaction(get_emoji(COIN_NAME))
                await self.botLogChan.send(f'A user successfully executed `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                await ctx.author.send(f'{EMOJI_ARROW_RIGHTHOOK} You have sent {num_format_coin(real_amount, COIN_NAME)} '
                                              f'{COIN_NAME} to `{CoinAddress}`.\n'
                                              f'Transaction hash: `{SendTx_hash}`\n'
                                              f'{extra_txt}')
                return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await self.botLogChan.send(f'A user failed to execute `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                return
            return
        elif coin_family == "NANO":
            MinTx = get_min_tx_amount(COIN_NAME)
            MaxTx = get_max_tx_amount(COIN_NAME)
            real_amount = int(amount * get_decimal(COIN_NAME))
            addressLength = get_addrlen(COIN_NAME)

            # Validate address
            valid_address = await nano_validate_address(COIN_NAME, str(CoinAddress))
            if not valid_address == True:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}` is invalid.')
                return

            # OK valid address
            user_from = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            if user_from is None:
                user_from = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
            userdata_balance = await store.sql_user_balance(str(ctx.author.id), COIN_NAME)
            xfer_in = 0
            if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                xfer_in = await store.sql_user_balance_get_xfer_in(str(ctx.author.id), COIN_NAME)
            if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
            elif COIN_NAME in ENABLE_COIN_NANO:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
                actual_balance = round(actual_balance / get_decimal(COIN_NAME), 6) * get_decimal(COIN_NAME)
            else:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
            # Negative check
            try:
                if actual_balance < 0:
                    msg_negative = 'Negative balance detected:\nUser: '+str(ctx.author.id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
                    await logchanbot(msg_negative)
            except Exception as e:
                await logchanbot(traceback.format_exc())

            # If balance 0, no need to check anything
            if actual_balance <= 0:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please check your **{COIN_NAME}** balance.')
                return

            if real_amount > actual_balance:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to send out '
                               f'{num_format_coin(real_amount, COIN_NAME)}')
                return
            if real_amount < MinTx:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transaction cannot be smaller than '
                               f'{num_format_coin(MinTx, COIN_NAME)} '
                               f'{COIN_NAME}.')
                return
            if real_amount > MaxTx:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transaction cannot be bigger than '
                               f'{num_format_coin(MaxTx, COIN_NAME)} '
                               f'{COIN_NAME}.')
                return

            SendTx = None
            check_in = await store.coin_check_balance_address_in_users(CoinAddress, COIN_NAME)
            if check_in:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, Can not send to this address:\n```{CoinAddress}``` ')
                return
            if ctx.author.id not in TX_IN_PROCESS:
                TX_IN_PROCESS.append(ctx.author.id)
                try:
                    SendTx = await store.sql_external_nano_single(str(ctx.author.id), real_amount,
                                                                  CoinAddress, COIN_NAME, "SEND")
                    # add redis
                    await add_tx_action_redis(json.dumps([random_string, "SEND", str(ctx.author.id), ctx.author.name, float("%.3f" % time.time()), ctx.message.content, SERVER_BOT, "COMPLETE"]), False)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                await asyncio.sleep(config.interval.tx_lap_each)
                TX_IN_PROCESS.remove(ctx.author.id)
            else:
                # reject and tell to wait
                msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You have another tx in process. Please wait it to finish. ')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            if SendTx:
                SendTx_hash = SendTx['block']
                await ctx.message.add_reaction(get_emoji(COIN_NAME))
                await self.botLogChan.send(f'A user successfully executed `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                await ctx.author.send(f'{EMOJI_ARROW_RIGHTHOOK} You have sent {num_format_coin(real_amount, COIN_NAME)} '
                                              f'{COIN_NAME} to `{CoinAddress}`.\n'
                                              f'Transaction hash: `{SendTx_hash}`')
                return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await self.botLogChan.send(f'A user failed to execute `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                return
            return
        if coin_family == "DOGE" or coin_family == "ERC-20" or coin_family == "TRC-20":
            if coin_family == "ERC-20" or coin_family == "TRC-20":
                token_info = await store.get_token_info(COIN_NAME)
                MinTx = token_info['real_min_tx']
                MaxTx = token_info['real_max_tx']
                NetFee = token_info['real_withdraw_fee']
            else:
                MinTx = get_min_tx_amount(coin = COIN_NAME)
                MaxTx = get_max_tx_amount(coin = COIN_NAME)
                NetFee = get_tx_node_fee(coin = COIN_NAME)
                valid_address = await doge_validaddress(str(CoinAddress), COIN_NAME)
                if 'isvalid' in valid_address:
                    if str(valid_address['isvalid']) == "True":
                        pass
                    else:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Address: `{CoinAddress}` '
                                        'is invalid.')
                        return
            extra_fee_txt = f'You need to leave a node/tx fee: {num_format_coin(NetFee, COIN_NAME)} {COIN_NAME}'
            user_from = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            if user_from is None:
                if coin_family == "ERC-20":
                    w = await create_address_eth()
                    userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
                elif coin_family == "TRC-20":
                    result = await store.create_address_trx()
                    userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, result)
                else:
                    userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
            real_amount = float(amount)
            userdata_balance = await store.sql_user_balance(str(ctx.author.id), COIN_NAME)
            xfer_in = 0
            if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                xfer_in = await store.sql_user_balance_get_xfer_in(str(ctx.author.id), COIN_NAME)
            if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
            elif COIN_NAME in ENABLE_COIN_NANO:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
                actual_balance = round(actual_balance / get_decimal(COIN_NAME), 6) * get_decimal(COIN_NAME)
            else:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
            # Negative check
            try:
                if actual_balance < 0:
                    msg_negative = 'Negative balance detected:\nUser: '+str(ctx.author.id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
                    await logchanbot(msg_negative)
            except Exception as e:
                await logchanbot(traceback.format_exc())

            if real_amount + NetFee > actual_balance:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to send out '
                               f'{num_format_coin(real_amount, COIN_NAME)} '
                               f'{COIN_NAME}. {extra_fee_txt}')
                return
            if real_amount < MinTx:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transaction cannot be smaller than '
                               f'{num_format_coin(MinTx, COIN_NAME)} '
                               f'{COIN_NAME}.')
                return
            if real_amount > MaxTx:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transaction cannot be bigger than '
                               f'{num_format_coin(MaxTx, COIN_NAME)} '
                               f'{COIN_NAME}.')
                return
            SendTx = None
            check_in = await store.coin_check_balance_address_in_users(CoinAddress, COIN_NAME)
            if check_in:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, Can not send to this address:\n```{CoinAddress}``` ')
                return
            if ctx.author.id not in TX_IN_PROCESS:
                TX_IN_PROCESS.append(ctx.author.id)
                try:
                    if COIN_NAME in ENABLE_COIN_ERC:
                        SendTx = await store.sql_external_erc_single(str(ctx.author.id), CoinAddress, real_amount, COIN_NAME, 'SEND', SERVER_BOT)
                    elif COIN_NAME in ENABLE_COIN_TRC:
                        SendTx = await store.sql_external_trx_single(str(ctx.author.id), CoinAddress, real_amount, COIN_NAME, 'SEND', SERVER_BOT)
                    else:
                        SendTx = await store.sql_external_doge_single(str(ctx.author.id), real_amount, NetFee,
                                                                      CoinAddress, COIN_NAME, "SEND")
                    # add redis
                    await add_tx_action_redis(json.dumps([random_string, "SEND", str(ctx.author.id), ctx.author.name, float("%.3f" % time.time()), ctx.message.content, SERVER_BOT, "COMPLETE"]), False)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                await asyncio.sleep(config.interval.tx_lap_each)
                TX_IN_PROCESS.remove(ctx.author.id)
            else:
                await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
                msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            if SendTx:
                if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    extra_txt = f"A node/tx `{NetFee} {COIN_NAME}` deducted from your balance."
                    await ctx.message.add_reaction(TOKEN_EMOJI)
                else:
                    await ctx.message.add_reaction(get_emoji(COIN_NAME))
                    extra_txt = "A node/tx fee `{} {}` deducted from your balance.".format(num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
                await self.botLogChan.send(f'A user successfully executed `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                await ctx.author.send(f'{EMOJI_ARROW_RIGHTHOOK} You have sent {num_format_coin(real_amount, COIN_NAME)} '
                                      f'{COIN_NAME} to `{CoinAddress}`.\n'
                                      f'Transaction hash: `{SendTx}`\n'
                                      f'{extra_txt}')
                return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await self.botLogChan.send(f'A user failed to execute `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                return
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                           f'`{CoinAddress}`')
            return


def setup(bot):
    bot.add_cog(TipWithdraw(bot))