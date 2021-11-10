import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class TipRegister(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(usage="register <wallet address> [coin]", aliases=['registerwallet', 'reg', 'updatewallet'], description="Register a withdraw address.")
    async def register(self, ctx, wallet_address: str, coin: str=None):
        # check if bot is going to restart
        if IS_RESTARTING:
            await ctx.message.add_reaction(EMOJI_REFRESH)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
            return

        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'register')
        if account_lock:
            await ctx.message.add_reaction(EMOJI_LOCKED) 
            await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
            return
        # end of check if account locked

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

        if not re.match(r'^[A-Za-z0-9_]+$', wallet_address):
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                           f'`{wallet_address}`')
            return

        COIN_NAME = get_cn_coin_from_address(wallet_address)
        if COIN_NAME:
            if COIN_NAME == "TRON_TOKEN":
                if coin is None:
                    await ctx.message.add_reaction(EMOJI_WARNING)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} you need to add **TOKEN NAME** address.')
                    return
                else:
                    valid_address = await store.trx_validate_address(wallet_address)
                    if not valid_address:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token address:\n'
                                             f'`{wallet_address}`')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
                    else:
                        COIN_NAME = coin.upper()
                        valid_address = wallet_address
            else:
                pass
        else:
            if wallet_address.startswith("0x"):
                if wallet_address.upper().startswith("0X00000000000000000000000000000"):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token:\n'
                                         f'`{wallet_address}`')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                if coin is None:
                    await ctx.message.add_reaction(EMOJI_WARNING)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} you need to add **TOKEN NAME** address.')
                    return
                else:
                    COIN_NAME = coin.upper()
                    if COIN_NAME not in ENABLE_COIN_ERC:
                        await ctx.message.add_reaction(EMOJI_WARNING)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Unsupported Token.')
                        return
                    else:
                        # validate
                        valid_address = await store.erc_validate_address(wallet_address, COIN_NAME)
                        valid = False
                        if valid_address and valid_address.upper() == wallet_address.upper():
                            valid = True
                        else:
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token address:\n'
                                                 f'`{wallet_address}`')
                            await msg.add_reaction(EMOJI_OK_BOX)
                            return
            else:
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

        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
        elif COIN_NAME in ENABLE_XCH:
            coin_family = "XCH"
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")

        if is_maintenance_coin(COIN_NAME):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
            return

        if coin_family in ["TRTL", "BCN", "XMR", "NANO"]:
            main_address = getattr(getattr(config,"daemon"+COIN_NAME),"MainAddress")
            if wallet_address == main_address:
                await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} do not register with main address. You could lose your coin when withdraw.')
                return
        elif coin_family == "ERC-20":
            # Check if register address in any of user balance address
            check_in_balance_users = await store.erc_check_balance_address_in_users(wallet_address, COIN_NAME)
            if check_in_balance_users:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You can not register with any of user\'s tipjar\'s token address.\n'
                                     f'`{wallet_address}`')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
        elif coin_family == "XCH":
            # Check if register address in any of user balance address
            check_in_balance_users = await store.coin_check_balance_address_in_users(wallet_address, COIN_NAME)
            if check_in_balance_users:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You can not register with any of user\'s tipjar\'s address.\n'
                                     f'`{wallet_address}`')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
        elif coin_family == "TRC-20":
            # Check if register address in any of user balance address
            check_in_balance_users = await store.trx_check_balance_address_in_users(wallet_address, COIN_NAME)
            if check_in_balance_users:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You can not register with any of user\'s tipjar\'s token address.\n'
                                     f'`{wallet_address}`')
                await msg.add_reaction(EMOJI_OK_BOX)
                return

        user = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
        if user is None:
            if coin_family == "ERC-20":
                w = await create_address_eth()
                userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
            elif coin_family == "TRC-20":
                result = await store.create_address_trx()
                userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, result)
            else:
                userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
            user = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)

        existing_user = user

        valid_address = None
        if COIN_NAME in ENABLE_COIN_DOGE:
            user_from = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            if user_from is None:
                user_from = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
                user_from = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            user_from['address'] = user_from['balance_wallet_address']
            if COIN_NAME in ENABLE_COIN_DOGE:
                valid_address = await doge_validaddress(str(wallet_address), COIN_NAME)
                if ('isvalid' in valid_address):
                    if str(valid_address['isvalid']) == "True":
                        valid_address = wallet_address
                    else:
                        valid_address = None
                    pass
                pass
        elif COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            # already validated above
            pass
        else:
            if coin_family in ["TRTL", "BCN"]:
                valid_address = addressvalidation.validate_address_cn(wallet_address, COIN_NAME)
            elif coin_family in ["NANO"]:
                valid_address = await nano_validate_address(COIN_NAME, wallet_address)
                if valid_address == True:
                    valid_address = wallet_address
            elif coin_family in ["XCH"]:
                try:
                    valid_address = addressvalidation_xch.validate_address(wallet_address, COIN_NAME)
                    if valid_address == True:
                        valid_address = wallet_address
                    else:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid {COIN_NAME} address.')
                        return
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
            elif coin_family == "XMR":
                if COIN_NAME not in ["MSR", "UPX", "XAM"]:
                    valid_address = await validate_address_xmr(str(wallet_address), COIN_NAME)
                    if valid_address is None:
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                       f'`{wallet_address}`')
                    if valid_address['valid'] == True and valid_address['integrated'] == False \
                        and valid_address['subaddress'] == False and valid_address['nettype'] == 'mainnet':
                        # re-value valid_address
                        valid_address = str(wallet_address)
                    else:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please use {COIN_NAME} main address.')
                        return
                else:
                    if COIN_NAME == "MSR":
                        valid_address = address_msr(wallet_address)
                        if type(valid_address).__name__ != "Address":
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please use {COIN_NAME} main address.')
                            return
                    elif COIN_NAME == "WOW":
                        valid_address = address_wow(wallet_address)
                        if type(valid_address).__name__ != "Address":
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please use {COIN_NAME} main address.')
                            return
                    elif COIN_NAME == "XOL":
                        valid_address = address_xol(wallet_address)
                        if type(valid_address).__name__ != "Address":
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please use {COIN_NAME} main address.')
                            return
                    elif COIN_NAME == "UPX":
                        #
                        valid_address = None
                        try:	
                            valid_address = address_upx(wallet_address)
                            print(valid_address)
                            if type(valid_address).__name__ != "Address":	
                                await ctx.message.add_reaction(EMOJI_ERROR)	
                                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please use {COIN_NAME} main address.')	
                                return
                        except Exception as e:	
                            traceback.print_exc(file=sys.stdout)	
                            pass
            else:
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Unknown Ticker.')
                return
        # correct print(valid_address)
        if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            if valid_address is None: 
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid {COIN_NAME} address:\n'
                               f'`{wallet_address}`')
                return

            if valid_address != wallet_address:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid {COIN_NAME} address:\n'
                               f'`{wallet_address}`')
                return

        # if they want to register with tipjar address
        try:
            if user['balance_wallet_address'] == wallet_address:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You can not register with your {COIN_NAME} tipjar\'s address.\n'
                               f'`{wallet_address}`')
                return
            else:
                pass
        except Exception as e:
            await ctx.message.add_reaction(EMOJI_ERROR)
            print('Error during register user address:' + str(e))
            return

        serverinfo = await get_info_pref_coin(ctx)
        server_prefix = serverinfo['server_prefix']
        if existing_user['user_wallet_address']:
            prev_address = existing_user['user_wallet_address']
            if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                if prev_address.upper() != wallet_address.upper():
                    await store.sql_update_user(str(ctx.author.id), wallet_address, COIN_NAME)
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                    await ctx.send(f'Your {COIN_NAME} {ctx.author.mention} withdraw address has changed from:\n'
                                   f'`{prev_address}`\n to\n '
                                   f'`{wallet_address}`')
                    try:
                        await store.redis_delete_userwallet(str(ctx.author.id), COIN_NAME, SERVER_BOT)
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                else:
                    await ctx.message.add_reaction(EMOJI_WARNING)
                    await ctx.send(f'{ctx.author.mention} Your {COIN_NAME} previous and new address is the same.')
                return

            else:
                if prev_address != valid_address:
                    await store.sql_update_user(str(ctx.author.id), wallet_address, COIN_NAME)
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                    await ctx.send(f'Your {COIN_NAME} {ctx.author.mention} withdraw address has changed from:\n'
                                   f'`{prev_address}`\n to\n '
                                   f'`{wallet_address}`')
                    try:
                        await store.redis_delete_userwallet(str(ctx.author.id), COIN_NAME, SERVER_BOT)
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                else:
                    await ctx.message.add_reaction(EMOJI_WARNING)
                    await ctx.send(f'{ctx.author.mention} Your {COIN_NAME} previous and new address is the same.')
                return
        else:
            await store.sql_update_user(str(ctx.author.id), wallet_address, COIN_NAME)
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            await ctx.send(f'{ctx.author.mention} You have registered {COIN_NAME} withdraw address.\n'
                           f'You can use `{server_prefix}withdraw AMOUNT {COIN_NAME}` anytime.')
            try:
                await store.redis_delete_userwallet(str(ctx.author.id), COIN_NAME, SERVER_BOT)
            except Exception as e:
                await logchanbot(traceback.format_exc())
            return


def setup(bot):
    bot.add_cog(TipRegister(bot))