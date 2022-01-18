import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from decimal import getcontext, Decimal
from dislash import InteractionClient, ActionRow, Button, ButtonStyle, Option, OptionType, OptionChoice
import addressvalidation, addressvalidation_xch

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
        prefix: str="/",
        to_address: str=None # None if withdraw
    ):
        await self.bot_log()
        # check if bot is going to restart
        if IS_RESTARTING: return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this."}
        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'send')
        if account_lock: return {"error": f"{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}"}
        # end of check if account locked

        if action.upper == "SEND" and to_address is None:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Missing address to send to."}
        COIN_NAME = coin.upper()
        if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
            await logchanbot(f'User {ctx.author.id} tried to {prefix}{action.lower()} {amount} **{COIN_NAME}**.')
            return {"error": f"**{COIN_NAME}** Unknown Ticker."}
        if is_maintenance_coin(COIN_NAME):
            await logchanbot(f'User {ctx.author.id} tried to {prefix}{action.lower()} {amount} **{COIN_NAME}** while it is under maintenance.')
            return {"error": f"**{COIN_NAME}** Under maintenance. Try again later!"}
        if not is_coin_txable(COIN_NAME):
            await logchanbot(f'User {ctx.author.id} tried to {prefix}{action.lower()} {amount} **{COIN_NAME}** while it tx not enable.')
            return {"error": f"**{COIN_NAME}** Transaction currently disable Try again later!"}

        # Check if tx in progress
        if ctx.author.id in TX_IN_PROCESS:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention}, You have another tx in progress!"}
 
        # Check flood of tip
        floodTip = await store.sql_get_countLastTip(str(ctx.author.id), config.floodTipDuration)
        if floodTip >= config.floodTip:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention}, Cool down your tip or transaction or increase your amount next time."}
            await self.botLogChan.send(f"A user reached max. TX threshold. Currently halted: `{prefix}{action.upper()}`")
            return
        # End of Check flood of tip
        
        amount = str(amount).replace(",", "")
        try:
            amount = Decimal(amount)
        except ValueError:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention}, Invalid given amount."}

        NetFee = 0
        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
            token_info = await store.get_token_info(COIN_NAME)
            MinTx = token_info['real_min_tx']
            MaxTx = token_info['real_max_tx']
            NetFee = token_info['real_withdraw_fee']
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
            token_info = await store.get_token_info(COIN_NAME)
            MinTx = token_info['real_min_tip']
            MaxTx = token_info['real_max_tx']
            NetFee = token_info['real_withdraw_fee']
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
            MinTx = get_min_tx_amount(COIN_NAME)
            MaxTx = get_max_tx_amount(COIN_NAME)
            NetFee = get_tx_node_fee(coin = COIN_NAME)

        real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
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

        if action.upper == "SEND" and user['balance_wallet_address'] and user['balance_wallet_address'] == to_address:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} You can not send to your own deposit address."}

        if user['user_wallet_address'] is None and action.upper()=="WITHDRAW":
            extra_txt = ""
            if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                extra_txt = " " + COIN_NAME
            return {"error": f"You do not have a registered address for **{COIN_NAME}**, please use `{prefix}register wallet_address{extra_txt}` to register. Alternatively, please use `{prefix}send <amount> <coin_address>`."}
        elif user['user_wallet_address'] and action.upper()=="WITHDRAW":
            to_address = user['user_wallet_address']
        try:
            # add redis action
            random_string = str(uuid.uuid4())
            msg_content = "SLASH COMMAND"
            if hasattr(ctx, 'message'):
                msg_content = ctx.message.content
            await add_tx_action_redis(json.dumps([random_string, action.upper(), str(ctx.author.id), ctx.author.name, float("%.3f" % time.time()), msg_content, SERVER_BOT, "START"]), False)

            # If balance 0, no need to check anything
            if balance_user['actual_balance'] <= 0:
                return {"error": f"Please check your **{COIN_NAME}** balance."}
            elif real_amount + NetFee > balance_user['actual_balance']:
                extra_fee_txt = ''
                if NetFee > 0: extra_fee_txt = f' You need to leave a node/tx fee: {num_format_coin(NetFee, COIN_NAME)} {COIN_NAME}'
                return {"error": f"Insufficient balance to {action.lower()} {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}.{extra_fee_txt}"}
            elif real_amount > MaxTx:
                return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than {num_format_coin(MaxTx, COIN_NAME)} {COIN_NAME}"}
            elif real_amount < MinTx:
                return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be lower than {num_format_coin(MinTx, COIN_NAME)} {COIN_NAME}"}
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention}, Internal error for {prefix}{action.lower()}!"}

        # Check if address is in any:
        if action.upper() == "SEND":
            check_in = await store.coin_check_balance_address_in_users(to_address, COIN_NAME)
            if check_in: return {"error": f"{EMOJI_RED_NO} {ctx.author.mention}, Can not send to this address:\n```{to_address}```"}

        if ctx.author.id not in TX_IN_PROCESS:
            TX_IN_PROCESS.append(ctx.author.id)
        try:
            withdraw_txt = None
            if coin_family in ["TRTL", "BCN"]:
                main_address = getattr(getattr(config,"daemon"+COIN_NAME),"MainAddress")
                if action.upper() == "SEND" and to_address == main_address:
                    return {"error": f"{EMOJI_RED_NO} {ctx.author.mention}, Can not send to this address:\n```{to_address}```"}
                addressLength = get_addrlen(COIN_NAME)
                IntaddressLength = get_intaddrlen(COIN_NAME)
                has_payment_id = False
                if action.upper() == "SEND" and len(to_address) == int(addressLength):
                    valid_address = addressvalidation.validate_address_cn(to_address, COIN_NAME)
                    if valid_address != to_address: return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n```{to_address}```"}
                elif action.upper() == "SEND" and len(to_address) == int(IntaddressLength):
                    valid_address = addressvalidation.validate_integrated_cn(to_address, COIN_NAME)
                    if valid_address == 'invalid':
                        return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Invalid integrated address:\n```{to_address}```"}
                    elif len(valid_address) == 2:
                        iCoinAddress = to_address
                        to_address = valid_address['address']
                        paymentid = valid_address['integrated_id']
                        has_payment_id = True
                elif action.upper() == "SEND" and len(to_address) == int(addressLength) + 64 + 1:
                    valid_address = {}
                    check_address = to_address.split(".")
                    if len(check_address) != 2:
                        return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Invalid {COIN_NAME} address + paymentid"}
                    else:
                        valid_address_str = addressvalidation.validate_address_cn(check_address[0], COIN_NAME)
                        paymentid = check_address[1].strip()
                        if valid_address_str is None:
                            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n```{check_address[0]}```"}
                        else:
                            valid_address['address'] = valid_address_str
                            has_payment_id = True
                        if len(paymentid) == 64:
                            if not re.match(r'[a-zA-Z0-9]{64,}', paymentid.strip()):
                                try:
                                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} PaymentID: `{paymentid}`\n'
                                                    'Should be in 64 correct format.')
                                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                    await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} PaymentID: `{paymentid}`\nShould be in 64 correct format.')
                                return
                            else:
                                to_address = valid_address['address']
                                valid_address['paymentid'] = paymentid
                                iCoinAddress = addressvalidation.make_integrated_cn(valid_address['address'], COIN_NAME, paymentid)['integrated_address']
                                has_payment_id = True
                        else:
                            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} PaymentID: `{paymentid}`\nIncorrect length."}

                elif action.upper() == "SEND":
                    return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n```{to_address}```"}

                withdraw_txt = None
                if action.upper() == "SEND" and has_payment_id == True:
                    sendTx = await store.sql_external_cn_single_id(str(ctx.author.id), to_address, real_amount, paymentid, COIN_NAME)
                    if sendTx:
                        withdraw_txt = "Transaction hash: `{}`\nTo: `{}`\nPayment ID:`{}`\nA node/tx fee `{} {}` deducted from your balance.".format(sendTx['transactionHash'], to_address, paymentid, num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
                        await self.botLogChan.send(f'A user successfully executed `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}` with paymentid.')
                    else:
                        await self.botLogChan.send(f'A user failed to execute {prefix}{action.lower()} `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}` with paymentid.')
                        msg = await ctx.reply(f'{ctx.author.mention} Please try again or report.')
                elif action.upper() == "SEND" and has_payment_id == False:
                    sendTx = await store.sql_external_cn_single(str(ctx.author.id), to_address, real_amount, COIN_NAME, SERVER_BOT, 'SEND')
                    if sendTx:
                        withdraw_txt = "Transaction hash: `{}`\nTo: `{}`\nA node/tx fee `{} {}` deducted from your balance.".format(sendTx['transactionHash'], to_address, num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
                        await self.botLogChan.send(f'A user successfully executed `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}` with paymentid.')
                    else:
                        await self.botLogChan.send(f'A user failed to execute {prefix}{action.lower()} `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}` with paymentid.')
                        msg = await ctx.reply(f'{ctx.author.mention} Please try again or report.')
                        return
                elif action.upper() == "WITHDRAW":
                    withdrawTx = await store.sql_external_cn_single(str(ctx.author.id), user['user_wallet_address'], real_amount, COIN_NAME, SERVER_BOT, 'WITHDRAW')
                    if withdrawTx:
                        withdraw_txt = "Transaction hash: `{}`\nA node/tx fee `{} {}` deducted from your balance.".format(withdrawTx['transactionHash'], num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
                await asyncio.sleep(config.interval.tx_lap_each)
            elif coin_family == "XMR" or coin_family == "XCH":
                if action.upper() == "SEND":
                    # If not Masari
                    if COIN_NAME not in ["MSR", "UPX", "XCH", "XFX"]:
                        valid_address = await validate_address_xmr(str(CoinAddress), COIN_NAME)
                        if valid_address['valid'] == False or valid_address['nettype'] != 'mainnet':
                            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, Address is invalid: ```{CoinAddress}```')
                            return
                    elif coin_family == "XCH":
                        valid_address = addressvalidation_xch.validate_address(CoinAddress, COIN_NAME)
                        if valid_address == False:
                            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, Address is invalid:```{CoinAddress}```')
                            return
                    try:
                        SendTx = None
                        if coin_family == "XCH":
                            SendTx = await store.sql_external_xch_single(str(ctx.author.id), real_amount, CoinAddress, COIN_NAME, "SEND")
                            SendTx['tx_hash'] = SendTx['tx_hash']['name']
                        else:
                            SendTx = await store.sql_external_xmr_single(str(ctx.author.id), real_amount, CoinAddress, COIN_NAME, "SEND", NetFee)
                        # add redis
                        if SendTx:
                            SendTx_hash = SendTx['tx_hash']
                            extra_txt = "A node/tx fee `{} {}` deducted from your balance.".format(num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
                            await self.botLogChan.send(f'A user successfully executed `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                            await ctx.author.send(f'{EMOJI_ARROW_RIGHTHOOK} You have sent {num_format_coin(real_amount, COIN_NAME)} '
                                                          f'{COIN_NAME} to `{CoinAddress}`.\n'
                                                          f'Transaction hash: `{SendTx_hash}`\n'
                                                          f'{extra_txt}')
                            return
                        else:
                            await self.botLogChan.send(f'A user failed to execute `{prefix}{action.lower()} {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                            return
                    except Exception as e:
                        traceback.print_exc(file=sys.stdout)
                        await logchanbot(traceback.format_exc())
                    await asyncio.sleep(config.interval.tx_lap_each)
                elif action.upper() == "WITHDRAW":
                    if coin_family == "XCH":
                        withdrawTx = await store.sql_external_xch_single(str(ctx.author.id),
                                                                        real_amount,
                                                                        user['user_wallet_address'],
                                                                        COIN_NAME, "WITHDRAW")
                        if withdrawTx:
                            withdraw_txt = "Transaction hash: `{}`\nA node/tx fee `{} {}` deducted from your balance.".format(withdrawTx['tx_hash']['name'], num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
                    elif coin_family == "XMR":
                        withdrawTx = await store.sql_external_xmr_single(str(ctx.author.id), real_amount, user['user_wallet_address'], COIN_NAME, "WITHDRAW", NetFee)
                        if withdrawTx:
                            withdraw_txt = "Transaction hash: `{}`\nA node/tx fee `{} {}` deducted from your balance.".format(withdrawTx['tx_hash'], num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
            elif coin_family == "NANO":
                if action.upper() == "SEND":
                    # Validate address
                    valid_address = await nano_validate_address(COIN_NAME, str(CoinAddress))
                    if not valid_address == True:
                        await ctx.reply(f'{EMOJI_RED_NO} Address: `{CoinAddress}` is invalid.')
                        return
                    else:
                        try:
                            SendTx = await store.sql_external_nano_single(str(ctx.author.id), real_amount, CoinAddress, COIN_NAME, "SEND")
                            if SendTx:
                                SendTx_hash = SendTx['block']
                                await self.botLogChan.send(f'A user successfully executed `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                                await ctx.author.send(f'{EMOJI_ARROW_RIGHTHOOK} You have sent {num_format_coin(real_amount, COIN_NAME)} '
                                                              f'{COIN_NAME} to `{CoinAddress}`.\n'
                                                              f'Transaction hash: `{SendTx_hash}`')
                                return
                            else:
                                await self.botLogChan.send(f'A user failed to execute `{prefix}{action.lower()} {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                                return
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                elif action.upper() == "WITHDRAW":
                    withdrawTx = await store.sql_external_nano_single(str(ctx.author.id), real_amount, user['user_wallet_address'], COIN_NAME, "WITHDRAW")
                    if withdrawTx:
                        withdraw_txt = "Block: `{}`".format(withdrawTx['block'])
            elif action.upper() == "SEND" and (coin_family == "DOGE" or coin_family == "ERC-20" or coin_family == "TRC-20"):
                SendTx = None
                check_in = await store.coin_check_balance_address_in_users(CoinAddress, COIN_NAME)
                if check_in:
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, Can not send to this address:\n```{CoinAddress}``` ')
                    return
                if ctx.author.id not in TX_IN_PROCESS:
                    TX_IN_PROCESS.append(ctx.author.id)
                    try:
                        if COIN_NAME in ENABLE_COIN_ERC:
                            SendTx = await store.sql_external_erc_single(str(ctx.author.id), CoinAddress, real_amount, COIN_NAME, 'SEND', SERVER_BOT)
                        elif COIN_NAME in ENABLE_COIN_TRC:
                            SendTx = await store.sql_external_trx_single(str(ctx.author.id), CoinAddress, real_amount, COIN_NAME, 'SEND', SERVER_BOT)
                        else:
                            SendTx = await store.sql_external_doge_single(str(ctx.author.id), real_amount, NetFee, CoinAddress, COIN_NAME, "SEND")
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                    await asyncio.sleep(config.interval.tx_lap_each)
                    TX_IN_PROCESS.remove(ctx.author.id)
                if SendTx:
                    if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                        extra_txt = f"A node/tx `{NetFee} {COIN_NAME}` deducted from your balance."
                    else:
                        extra_txt = "A node/tx fee `{} {}` deducted from your balance.".format(num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
                    await self.botLogChan.send(f'A user successfully executed `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                    await ctx.author.send(f'{EMOJI_ARROW_RIGHTHOOK} You have sent {num_format_coin(real_amount, COIN_NAME)} '
                                          f'{COIN_NAME} to `{CoinAddress}`.\n'
                                          f'Transaction hash: `{SendTx}`\n'
                                          f'{extra_txt}')
                    return
                else:
                    await self.botLogChan.send(f'A user failed to execute `{prefix}{action.lower()} {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                    return
                return
            elif action.upper() == "WITHDRAW" and coin_family == "DOGE":
                withdrawTx = await store.sql_external_doge_single(str(ctx.author.id), real_amount, NetFee, user['user_wallet_address'], COIN_NAME, "WITHDRAW")
                if withdrawTx:
                    withdraw_txt = 'Transaction hash: `{}`\nA node/tx fee `{} {}` deducted from your balance.'.format(withdrawTx, num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
            elif action.upper() == "WITHDRAW" and coin_family == "ERC-20":
                withdrawTx = await store.sql_external_erc_single(str(ctx.author.id), user['user_wallet_address'], real_amount, COIN_NAME, 'WITHDRAW', SERVER_BOT)
                if withdrawTx:
                    withdraw_txt = f'Transaction hash: `{withdrawTx}`\nFee `{NetFee} {COIN_NAME}` deducted from your balance.'
            elif coin_family == "TRC-20": 
                withdrawTx = await store.sql_external_trx_single(str(ctx.author.id), user['user_wallet_address'], real_amount, COIN_NAME, 'WITHDRAW', SERVER_BOT)
                if withdrawTx:
                    withdraw_txt = f'Transaction hash: `{withdrawTx}`\nFee `{NetFee} {COIN_NAME}` deducted from your balance.'
            # add redis action
            msg_content = "SLASH COMMAND"
            if hasattr(ctx, 'message'):
                msg_content = ctx.message.content
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
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
            return

        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'withdraw')
        if account_lock:
            await ctx.message.add_reaction(EMOJI_LOCKED) 
            await ctx.reply(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
            return
        # end of check if account locked

        amount = amount.replace(",", "")

        prefix = await get_guild_prefix(ctx)
        if coin is None:
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Please have **ticker** (coin name) after amount for `withdraw`.')
            return

        COIN_NAME = coin.upper()
        withdrawTx = await self.withdraw_action(ctx, amount, COIN_NAME, "WITHDRAW", prefix, None)
        if withdrawTx and 'error' in withdrawTx:
            await ctx.reply('{} {}, {}'.format(EMOJI_RED_NO, ctx.author.mention, withdrawTx['error']))
            return
        elif withdrawTx and 'result' in withdrawTx:
            withdrawAddress = withdrawTx['to_address']
            withdraw_txt = withdrawTx['result']
            real_amount = withdrawTx['real_amount']
            try:
                await ctx.author.send(
                                    f'{EMOJI_ARROW_RIGHTHOOK} You have withdrawn {num_format_coin(real_amount, COIN_NAME)} '
                                    f'{COIN_NAME} to `{withdrawAddress}`.\n'
                                    f'{withdraw_txt}')
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                try:
                    await ctx.reply(f'{EMOJI_ARROW_RIGHTHOOK} You have withdrawn {num_format_coin(real_amount, COIN_NAME)} '
                                   f'{COIN_NAME} to `{withdrawAddress}`.\n'
                                   f'{withdraw_txt}')
                except Exception as e:
                    pass
            await self.botLogChan.send(f'A user successfully executed `.withdraw {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`')
            return
        else:
            msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Internal error during your withdraw, please report or try again later.')
            await self.botLogChan.send(f'A user failed to executed `{prefix}withdraw {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`')
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
        prefix = await get_guild_prefix(ctx)
        amount = amount.replace(",", "")
        try:
            amount = Decimal(amount)
        except ValueError:
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, Invalid given amount.')
            return

        # Check which coinname is it.
        COIN_NAME = get_cn_coin_from_address(CoinAddress)
        if COIN_NAME is None and CoinAddress.startswith("0x"):
            if coin is None:
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} you need to add **TOKEN NAME** after address.')
                return
            else:
                COIN_NAME = coin.upper()
                if COIN_NAME not in ENABLE_COIN_ERC:
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Unsupported Token.')
                    return
            if CoinAddress.upper().startswith("0X00000000000000000000000000000"):
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token address:\n```{CoinAddress}```')
                return
            else:
                try:
                    valid_address = await store.erc_validate_address(CoinAddress, COIN_NAME)
                    if valid_address and valid_address.upper() == CoinAddress.upper():
                        valid = True
                    else:
                        msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token address:\n```{CoinAddress}```')
                        return
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
                    await logchanbot(traceback.format_exc())
                    msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} internal error checking address:\n```{CoinAddress}```')
                    return
        elif COIN_NAME is None:
            if coin is None:
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} you need to add **COIN NAME** after address.')
                return
            else:
                COIN_NAME = coin.upper()
                if COIN_NAME not in ENABLE_COIN_DOGE:
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Unsupported coin **{COIN_NAME}**.')
                    return
        elif COIN_NAME == "TRON_TOKEN":
            if coin is None:
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} you need to add **COIN NAME** after address.')
                return
            else:
                COIN_NAME = coin.upper()
                if COIN_NAME not in ENABLE_COIN_TRC:
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Unsupported token **{COIN_NAME}**.')
                    return

        withdrawTx = await self.withdraw_action(ctx, amount, COIN_NAME, "SEND", prefix, CoinAddress)
        if withdrawTx and 'error' in withdrawTx:
            await ctx.reply('{} {}, {}'.format(EMOJI_RED_NO, ctx.author.mention, withdrawTx['error']))
            return
        elif withdrawTx and 'result' in withdrawTx:
            withdrawAddress = withdrawTx['to_address']
            withdraw_txt = withdrawTx['result']
            real_amount = withdrawTx['real_amount']
            try:
                await ctx.author.send(
                                    f'{EMOJI_ARROW_RIGHTHOOK} You have withdrawn {num_format_coin(real_amount, COIN_NAME)} '
                                    f'{COIN_NAME} to `{withdrawAddress}`.\n'
                                    f'{withdraw_txt}')
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                try:
                    await ctx.reply(f'{EMOJI_ARROW_RIGHTHOOK} You have withdrawn {num_format_coin(real_amount, COIN_NAME)} '
                                   f'{COIN_NAME} to `{withdrawAddress}`.\n'
                                   f'{withdraw_txt}')
                except Exception as e:
                    pass
            await self.botLogChan.send(f'A user successfully executed `{prefix}send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`')
            return
        else:
            msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Internal error during your sending, please report or try again later.')
            await self.botLogChan.send(f'A user failed to executed `{prefix}send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`')
            return


def setup(bot):
    bot.add_cog(TipWithdraw(bot))