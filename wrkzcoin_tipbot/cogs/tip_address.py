import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class TipAddress(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    ## TODO: Improve this usage.
    @commands.command(
        usage="address <arguments>", 
        description="Check address."
    )
    async def address(
        self, 
        ctx, 
        *args
    ):
        prefix = await get_guild_prefix(ctx)

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

        if len(args) == 0:
            if isinstance(ctx.message.channel, discord.DMChannel):
                COIN_NAME = 'WRKZ'
            else:
                serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                try:
                    COIN_NAME = args[0].upper()
                    if COIN_NAME not in ENABLE_COIN:
                        if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                            pass
                        elif 'default_coin' in serverinfo:
                            COIN_NAME = serverinfo['default_coin'].upper()
                    else:
                        pass
                except:
                    if 'default_coin' in serverinfo:
                        COIN_NAME = serverinfo['default_coin'].upper()
                print("COIN_NAME: " + COIN_NAME)
            # TODO: change this.
            if COIN_NAME:
                main_address = getattr(getattr(config,"daemon"+COIN_NAME),"MainAddress")
                await ctx.send('**[ ADDRESS CHECKING EXAMPLES ]**\n\n'
                               f'```.address {main_address}\n'
                               'That will check if the address is valid. Integrated address is also supported. '
                               'If integrated address is input, bot will tell you the result of :address + paymentid\n\n'
                               f'{prefix}address <coin_address> <paymentid>\n'
                               'This will generate an integrate address.\n\n'
                               f'If you would like to get your address, please use {prefix}deposit {COIN_NAME} instead.```')
            else:
                await ctx.send('**[ ADDRESS CHECKING EXAMPLES ]**\n\n'
                               f'```.address coin_address\n'
                               'That will check if the address is valid. '
                               f'If you would like to get your address, please use {prefix}deposit {COIN_NAME} instead.```')
            return

        # Check if a user request address coin of another user
        # .addr COIN @mention
        if len(args) == 2 and len(ctx.message.mentions) == 1:
            COIN_NAME = None
            member = None
            try:
                COIN_NAME = args[0].upper()
                member = ctx.message.mentions[0]
                if COIN_NAME not in (ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_COIN_NANO+ENABLE_XMR+ENABLE_COIN_ERC+ENABLE_COIN_TRC):
                    COIN_NAME = None
            except Exception as e:
                pass

            if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**!')
                return

            if not is_coin_depositable(COIN_NAME):
                msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} DEPOSITING is currently disable for {COIN_NAME}.')
                await msg.add_reaction(EMOJI_OK_BOX)
                return

            if COIN_NAME and member and isinstance(ctx.channel, discord.DMChannel) == False and member.bot == False:
                # OK there is COIN_NAME and member
                if member.id == ctx.author.id:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    return
                msg = await ctx.send(f'**ADDRESS REQ {COIN_NAME} **: {member.mention}, {str(ctx.author)} would like to get your address.')
                await msg.add_reaction(EMOJI_CHECKMARK)
                await msg.add_reaction(EMOJI_ZIPPED_MOUTH)
                def check(reaction, user):
                    return user == member and reaction.message.author == self.bot.user and reaction.message.id == msg.id and str(reaction.emoji) \
                    in (EMOJI_CHECKMARK, EMOJI_ZIPPED_MOUTH)
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=120, check=check)
                except asyncio.TimeoutError:
                    await ctx.send(f'{ctx.author.mention} address requested timeout (120s) from {str(member.mention)}.')
                    try:
                        await msg.delete()
                    except Exception as e:
                        pass
                    return
                    
                if str(reaction.emoji) == EMOJI_CHECKMARK:
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                    wallet = await store.sql_get_userwallet(str(member.id), COIN_NAME)
                    if wallet is None:
                        if COIN_NAME in ENABLE_COIN_ERC:
                            w = await create_address_eth()
                            userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0, w)
                        elif COIN_NAME in ENABLE_COIN_TRC:
                            result = await store.create_address_trx()
                            userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0, result)
                        else:
                            userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0)
                        wallet = await store.sql_get_userwallet(str(member.id), COIN_NAME)
                    user_address = wallet['balance_wallet_address']
                    msg = await ctx.send(f'{ctx.author.mention} Here is the deposit **{COIN_NAME}** of {member.mention}:```{user_address}```')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                elif str(reaction.emoji) == EMOJI_ZIPPED_MOUTH:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{ctx.author.mention} your address request is rejected.')
                    return

        CoinAddress = args[0]
        COIN_NAME = None

        if not re.match(r'^[A-Za-z0-9_]+$', CoinAddress):
            msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                 f'`{CoinAddress}`')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        # Check which coinname is it.
        COIN_NAME = get_cn_coin_from_address(CoinAddress)

        if COIN_NAME:
            if COIN_NAME == "TRON_TOKEN":
                validate_address = await store.trx_validate_address(CoinAddress)
                if validate_address:
                    await ctx.message.add_reaction(EMOJI_CHECK)
                    msg = await ctx.send(f'Token address: `{CoinAddress}`\n'
                                         'Checked: Valid.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token address:\n'
                                         f'`{CoinAddress}`')
                    await msg.add_reaction(EMOJI_OK_BOX)
                return
            else:
                coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
        else:
            if CoinAddress.startswith("0x"):
                if CoinAddress.upper().startswith("0X00000000000000000000000000000"):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token:\n'
                                         f'`{CoinAddress}`')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                else:
                    valid_address = await store.erc_validate_address(CoinAddress, "XMOON") # placeholder
                    if valid_address and valid_address.upper() == CoinAddress.upper():
                        await ctx.message.add_reaction(EMOJI_CHECK)
                        msg = await ctx.send(f'Token address: `{CoinAddress}`\n'
                                             'Checked: Valid.')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
                    else:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token address:\n'
                                             f'`{CoinAddress}`')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                    f'`{CoinAddress}`')
                await msg.add_reaction(EMOJI_OK_BOX)
                return

        addressLength = get_addrlen(COIN_NAME)
        if coin_family in [ "BCN", "TRTL", "XMR"]:
            IntaddressLength = get_intaddrlen(COIN_NAME)

        if len(args) == 1:
            if coin_family == "DOGE":
                valid_address = await doge_validaddress(str(CoinAddress), COIN_NAME)
                if 'isvalid' in valid_address:
                    if str(valid_address['isvalid']) == "True":
                        await ctx.message.add_reaction(EMOJI_CHECK)
                        msg = await ctx.send(f'Address: `{CoinAddress}`\n'
                                             f'Checked: Valid {COIN_NAME}.')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
                    else:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        msg = await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                             'Checked: Invalid.')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    msg = await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                        'Checked: Invalid.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
            if coin_family == "NANO":
                valid_address = await nano_validate_address(COIN_NAME, str(CoinAddress))
                if valid_address == True:
                    await ctx.message.add_reaction(EMOJI_CHECK)
                    msg = await ctx.send(f'Address: `{CoinAddress}`\n'
                                         f'Checked: Valid {COIN_NAME}.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    msg = await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                         'Checked: Invalid.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
            elif COIN_NAME == "LTC":
                valid_address = await doge_validaddress(str(CoinAddress), COIN_NAME)
                if 'isvalid' in valid_address:
                    if str(valid_address['isvalid']) == "True":
                        await ctx.message.add_reaction(EMOJI_CHECK)
                        msg = await ctx.send(f'Address: `{CoinAddress}`\n'
                                             f'Checked: Valid {COIN_NAME}.')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
                    else:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        msg = await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                             'Checked: Invalid.')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                    'Checked: Invalid.')
                    return
            elif COIN_NAME == "KVA":
                valid_address = await doge_validaddress(str(CoinAddress), COIN_NAME)
                if 'isvalid' in valid_address:
                    if str(valid_address['isvalid']) == "True":
                        await ctx.message.add_reaction(EMOJI_CHECK)
                        msg = await ctx.send(f'Address: `{CoinAddress}`\n'
                                             f'Checked: Valid {COIN_NAME}.')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
                    else:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        msg = await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                             'Checked: Invalid.')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                    'Checked: Invalid.')
                    return
            elif COIN_NAME == "PGO":
                valid_address = await doge_validaddress(str(CoinAddress), COIN_NAME)
                if 'isvalid' in valid_address:
                    if str(valid_address['isvalid']) == "True":
                        await ctx.message.add_reaction(EMOJI_CHECK)
                        msg = await ctx.send(f'Address: `{CoinAddress}`\n'
                                             f'Checked: Valid {COIN_NAME}.')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
                    else:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        msg = await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                             'Checked: Invalid.')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    msg = await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                        'Checked: Invalid.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
            elif COIN_NAME in ENABLE_XMR:
                if COIN_NAME == "MSR":
                    addr = None
                    if len(CoinAddress) == 95:
                        try:
                            addr = address_msr(CoinAddress)
                        except Exception as e:
                            # await logchanbot(traceback.format_exc())
                            pass
                    elif len(CoinAddress) == 106:
                        addr = None
                        try:
                            addr = address_msr(CoinAddress)
                        except Exception as e:
                            # await logchanbot(traceback.format_exc())
                            pass
                    if addr == CoinAddress:
                        address_result = 'Valid: `{}`\n'.format(addr)                    
                        if type(addr).__name__ == "Address":
                            address_result += 'Main Address: `{}`\n'.format('True')
                        else:
                            address_result += 'Main Address: `{}`\n'.format('False')
                        if type(addr).__name__ == "IntegratedAddress":
                            address_result += 'Integrated: `{}`\n'.format('True')
                        else:
                            address_result += 'Integrated: `{}`\n'.format('False')
                        if type(addr).__name__ == "SubAddress":
                            address_result += 'Subaddress: `{}`\n'.format('True')
                        else:
                            address_result += 'Subaddress: `{}`\n'.format('False')
                        await ctx.message.add_reaction(EMOJI_CHECK)
                        await ctx.send(f'{EMOJI_CHECK} Address: `{CoinAddress}`\n{address_result}')
                        return
                    else:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                        'Checked: Invalid.')
                        return
                elif COIN_NAME == "UPX":	
                    addr = None	
                    if len(CoinAddress) == 98 or len(CoinAddress) == 97:	
                        try:	
                            addr = address_upx(CoinAddress)	
                        except Exception as e:	
                            traceback.print_exc(file=sys.stdout)	
                            pass	
                    elif len(CoinAddress) == 109:	
                        addr = None	
                        try:	
                            addr = address_upx(CoinAddress)	
                        except Exception as e:	
                            traceback.print_exc(file=sys.stdout)	
                            pass	
                    if addr == CoinAddress:	
                        address_result = 'Valid: `{}`\n'.format(addr)                    	
                        if type(addr).__name__ == "Address":	
                            address_result += 'Main Address: `{}`\n'.format('True')	
                        else:	
                            address_result += 'Main Address: `{}`\n'.format('False')	
                        if type(addr).__name__ == "IntegratedAddress":	
                            address_result += 'Integrated: `{}`\n'.format('True')	
                        else:	
                            address_result += 'Integrated: `{}`\n'.format('False')	
                        if type(addr).__name__ == "SubAddress":	
                            address_result += 'Subaddress: `{}`\n'.format('True')	
                        else:	
                            address_result += 'Subaddress: `{}`\n'.format('False')	
                        await ctx.message.add_reaction(EMOJI_CHECK)	
                        await ctx.send(f'{EMOJI_CHECK} Address: `{CoinAddress}`\n{address_result}')	
                        return	
                    else:	
                        await ctx.message.add_reaction(EMOJI_ERROR)	
                        await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'	
                                        'Checked: Invalid.')	
                        return
                else:
                    valid_address = None
                    try:
                        valid_address = await validate_address_xmr(str(CoinAddress), COIN_NAME)
                    except Exception as e:
                        traceback.print_exc(file=sys.stdout)
                    if valid_address is None or valid_address['valid'] == False:
                        await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                        'Checked: Invalid.')
                        return
                    elif valid_address['valid'] == True:
                        address_result = 'Valid: `{}`\n'.format(str(valid_address['valid'])) + \
                                       'Integrated: `{}`\n'.format(str(valid_address['integrated'])) + \
                                       'Net Type: `{}`\n'.format(str(valid_address['nettype'])) + \
                                       'Subaddress: `{}`\n'.format(str(valid_address['subaddress']))
                        await ctx.message.add_reaction(EMOJI_CHECK)
                        await ctx.send(f'{EMOJI_CHECK} Address: `{CoinAddress}`\n{address_result}')
                        return

            if len(CoinAddress) == int(addressLength):
                valid_address = addressvalidation.validate_address_cn(CoinAddress, COIN_NAME)
                print(valid_address)
                if valid_address is None:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                    'Checked: Invalid.')
                    return
                else:
                    await ctx.message.add_reaction(EMOJI_CHECK)
                    if (valid_address == CoinAddress):
                        await ctx.send(f'Address: `{CoinAddress}`\n'
                                        'Checked: Valid.')
                    return
                return
            elif len(CoinAddress) == int(IntaddressLength):
                # Integrated address
                valid_address = addressvalidation.validate_integrated_cn(CoinAddress, COIN_NAME)
                if valid_address == 'invalid':
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} Integrated Address: `{CoinAddress}`\n'
                                    'Checked: Invalid.')
                    return
                if len(valid_address) == 2:
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                    iCoinAddress = CoinAddress
                    CoinAddress = valid_address['address']
                    paymentid = valid_address['integrated_id']
                    await ctx.send(f'\nIntegrated Address: `{iCoinAddress}`\n\n'
                                    f'Address: `{CoinAddress}`\n'
                                    f'PaymentID: `{paymentid}`')
                    return
            else:
                # incorrect length
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                'Checked: Incorrect length')
                return
        if len(args) == 2:
            CoinAddress = args[0]
            paymentid = args[1]
            # generate integrated address:
            if len(CoinAddress) == int(addressLength):
                valid_address = addressvalidation.validate_address_cn(CoinAddress, COIN_NAME)
                if (valid_address is None):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                    'Checked: Incorrect given address.')
                    return
                else:
                    pass
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                'Checked: Incorrect length')
                return
            # Check payment ID
            if len(paymentid) == 64:
                if not re.match(r'[a-zA-Z0-9]{64,}', paymentid.strip()):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} PaymentID: `{paymentid}`\n'
                                    'Checked: Invalid. Should be in 64 correct format.')
                    return
                else:
                    pass
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} PaymentID: `{paymentid}`\n'
                                'Checked: Incorrect length')
                return
            # Make integrated address:
            integrated_address = addressvalidation.make_integrated_cn(CoinAddress, COIN_NAME, paymentid)
            if 'integrated_address' in integrated_address:
                iCoinAddress = integrated_address['integrated_address']
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                await ctx.send(f'\nNew integrated address: `{iCoinAddress}`\n\n'
                                f'Main address: `{CoinAddress}`\n'
                                f'Payment ID: `{paymentid}`\n')
                return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} ERROR Can not make integrated address.\n')
                return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send('**[ ADDRESS CHECKING EXAMPLES ]**\n\n'
                           '`.address WrkzRNDQDwFCBynKPc459v3LDa1gEGzG3j962tMUBko1fw9xgdaS9mNiGMgA9s1q7hS1Z8SGRVWzcGc8Sh8xsvfZ6u2wJEtoZB`\n'
                           'That will check if the address is valid. Integrated address is also supported. '
                           'If integrated address is input, bot will tell you the result of :address + paymentid\n\n'
                           '`.address <coin_address> <paymentid>`\n'
                           'This will generate an integrate address.\n\n')
            return


    @commands.command(
        usage="paymentid [coin]", 
        description="Generate paymentId for supported coin(s)."
    )
    async def paymentid(
        self, 
        ctx, 
        coin: str = None
    ):
        paymentid = None
        if coin and (coin.upper() in ENABLE_XMR):
            paymentid = addressvalidation.paymentid(8)
        else:
            paymentid = addressvalidation.paymentid()
        await ctx.message.add_reaction(EMOJI_OK_HAND)
        await ctx.send('**[ RANDOM PAYMENT ID ]**\n'
                       f'`{paymentid}`\n')
        return


def setup(bot):
    bot.add_cog(TipAddress(bot))