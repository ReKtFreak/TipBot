import sys, traceback

import discord
from discord.ext import commands

from config import config
from Bot import *

class Admin(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.group(usage="admin <subcommand>", hidden = True, description="Various admin commands.")
    @commands.is_owner()
    async def admin(self, ctx):
        prefix = await get_guild_prefix(ctx)
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        if ctx.invoked_subcommand is None:
            await ctx.send(f'{ctx.author.mention} Invalid {prefix}admin command')
        return


    @commands.is_owner()
    @admin.command(usage="echo <some text>", description="Testing echo.")
    async def echo(self, ctx, *, text: str):
        await logchanbot(text)
        return


    @commands.is_owner()
    @admin.command(usage="eval <expression>", description="Do some eval.")
    async def eval(self, ctx, *, code):
        if config.discord.enable_eval != 1:
            return

        no_filter_word = True
        filterword = config.eval_code.logfilterword.split(",")
        for each in filterword:
            if each.lower() in code.lower():
                no_filter_word = False
                break

        if no_filter_word == False:
            await ctx.send(f"```There is some filtered words in your code.```")
            return

        await logchanbot('{}#{} is executing dangerous command of eval:'.format(ctx.author.name, ctx.author.discriminator))
        await logchanbot('py\n{}'.format(code))
        str_obj = io.StringIO() #Retrieves a stream of data
        try:
            with contextlib.redirect_stdout(str_obj):
                exec(code)
        except Exception as e:
            return await ctx.send(f"```{e.__class__.__name__}: {e}```")
        await ctx.author.send(f'```{str_obj.getvalue()}```')


    @commands.is_owner()
    @admin.command(usage="addbalance <amount> <coin> <user>", aliases=['addbalance'])
    async def credit(self, ctx, amount: str, coin: str, to_userid: str):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        COIN_NAME = coin.upper()
        if COIN_NAME not in (ENABLE_COIN + ENABLE_XMR + ENABLE_COIN_DOGE + ENABLE_COIN_NANO+ENABLE_XCH):
            await ctx.send(f'{EMOJI_ERROR} **{COIN_NAME}** is not in our list.')
            return

        # check if bot can find user
        member = bot.get_user(int(to_userid))
        if member is None:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} I cannot find user with userid **{to_userid}**.')
            return
        # check if user / address exist in database
        amount = amount.replace(",", "")

        coin_family = None
        wallet = None
        try:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
        except Exception as e:
            await logchanbot(traceback.format_exc())
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**')
            return
        if coin_family in ["BCN", "XMR", "TRTL", "NANO", "DOGE", "XCH"]:
            wallet = await store.sql_get_userwallet(to_userid, COIN_NAME)
            if wallet is None:
                userregister = await store.sql_register_user(to_userid, COIN_NAME, SERVER_BOT, 0)
                wallet = await store.sql_get_userwallet(to_userid, COIN_NAME)
        else:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} not support ticker **{COIN_NAME}**')
            return

        try:
            real_amount = int(Decimal(amount) * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else Decimal(amount)
            credit_to = await store.sql_credit(str(ctx.author.id), to_userid, real_amount, COIN_NAME, ctx.message.content)
            if credit_to:
                msg = await ctx.send(f'{ctx.author.mention} amount **{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}** has been credited to userid **{to_userid}**.')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
        except ValueError:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid credit amount.')
            return


    @commands.is_owner()
    @admin.command(usage="maint", aliases=['maintenance'])
    async def maint(self, ctx, coin: str):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        COIN_NAME = coin.upper()
        if is_maintenance_coin(COIN_NAME):
            await ctx.send(f'{EMOJI_OK_BOX} Set **{COIN_NAME}** to maintenance **OFF**.')
            set_main = set_maintenance_coin(COIN_NAME, False)
        else:
            await ctx.send(f'{EMOJI_OK_BOX} Set **{COIN_NAME}** to maintenance **ON**.')
            set_main = set_maintenance_coin(COIN_NAME, True)
        return


    @commands.is_owner()
    @admin.command(usage="txable <coin>", aliases=['tx'], description="Txable YES/NO.")
    async def txable(self, ctx, coin: str):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        COIN_NAME = coin.upper()
        if is_coin_txable(COIN_NAME):
            await ctx.send(f'{EMOJI_OK_BOX} Set **{COIN_NAME}** **DISABLE** TX.')
            set_main = set_coin_txable(COIN_NAME, False)
        else:
            await ctx.send(f'{EMOJI_OK_BOX} Set **{COIN_NAME}** **ENABLE** TX.')
            set_main = set_coin_txable(COIN_NAME, True)
        return


    @commands.is_owner()
    @admin.command(usage="tradeable <coin>", aliases=['trade'], description="Tradeable YES/NO.")
    async def tradeable(self, ctx, coin: str):
        global ENABLE_TRADE_COIN
        COIN_NAME = coin.upper()
        if COIN_NAME not in ENABLE_TRADE_COIN:
            await ctx.send(f'{EMOJI_ERROR} **{COIN_NAME}** is not in our tradable list.')
            return

        if is_tradeable_coin(COIN_NAME):
            await ctx.send(f'{EMOJI_OK_BOX} Set **{COIN_NAME}** **DISABLE** trade.')
            set_main = set_tradeable_coin(COIN_NAME, False)
        else:
            await ctx.send(f'{EMOJI_OK_BOX} Set **{COIN_NAME}** **ENABLE** trade.')
            set_main = set_tradeable_coin(COIN_NAME, True)
        return


    @commands.is_owner()
    @admin.command(usage="tipable <coin>", aliases=['tip'], description="Tipable YES/NO.")
    async def tipable(self, ctx, coin: str):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        COIN_NAME = coin.upper()
        if is_coin_tipable(COIN_NAME):
            await ctx.send(f'{EMOJI_OK_BOX} Set **{COIN_NAME}** **DISABLE** TIP.')
            set_main = set_coin_tipable(COIN_NAME, False)
        else:
            await ctx.send(f'{EMOJI_OK_BOX} Set **{COIN_NAME}** **ENABLE** TIP.')
            set_main = set_coin_tipable(COIN_NAME, True)
        return


    @commands.is_owner()
    @admin.command(usage="depositable <coin>", aliases=['deposit'], description="Depositable YES/NO.")
    async def depositable(self, ctx, coin: str):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        COIN_NAME = coin.upper()
        if is_coin_depositable(COIN_NAME):
            await ctx.send(f'{EMOJI_OK_BOX} Set **{COIN_NAME}** **DISABLE** DEPOSIT.')
            set_main = set_coin_depositable(COIN_NAME, False)
        else:
            await ctx.send(f'{EMOJI_OK_BOX} Set **{COIN_NAME}** **ENABLE** DEPOSIT.')
            set_main = set_coin_depositable(COIN_NAME, True)
        return


    @commands.is_owner()
    @admin.command(usage="auditcoin <coin>", description="Check a coin status.")
    async def auditcoin(ctx, coin: str):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        COIN_NAME = coin.upper()
        if is_maintenance_coin(COIN_NAME):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            await ctx.send(f'{EMOJI_RED_NO} {COIN_NAME} in maintenance. But I will check for you.')
            pass
        if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_COIN_NANO+ENABLE_XCH:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {COIN_NAME} not in the list.')
            return
        time_start = int(time.time())
        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
        all_user_id = await store.sql_get_all_userid_by_coin(COIN_NAME)
        if len(all_user_id) > 0:
            await ctx.send(f'{EMOJI_INFORMATION} **{COIN_NAME}** there are total {str(len(all_user_id))} user records. Wait a big while...')
            sum_balance = 0
            sum_user = 0
            sum_unfound_balance = 0
            sum_unfound_user = 0
            for each_user_id in all_user_id:
                try:
                    xfer_in = 0
                    actual_balance = 0
                    if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                        xfer_in = await store.sql_user_balance_get_xfer_in(each_user_id['user_id'], COIN_NAME, each_user_id['user_server'])
                    userdata_balance = await store.sql_user_balance(each_user_id['user_id'], COIN_NAME, each_user_id['user_server'])
                    if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                        actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
                    elif COIN_NAME in ENABLE_COIN_NANO:
                        actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
                        actual_balance = round(actual_balance / get_decimal(COIN_NAME), 6) * get_decimal(COIN_NAME)
                    else:
                        actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
                    sum_balance += actual_balance
                    sum_user += 1
                    try:
                        if each_user_id['user_server'] == SERVER_BOT:
                            member = bot.get_user(int(each_user_id['user_id']))
                            if not member:
                                # get guild
                                get_guild = bot.get_guild(id=int(each_user_id['user_id']))
                                if not get_guild:
                                    sum_unfound_user += 1
                                    sum_unfound_balance += actual_balance
                    except Exception as e:
                        pass
                except Exception as e:
                    print(traceback.format_exc())
            duration = int(time.time()) - time_start
            msg_checkcoin = f"COIN **{COIN_NAME}**\n"
            msg_checkcoin += "```"
            msg_checkcoin += "Total record id in DB: " + str(sum_user) + "\n"
            msg_checkcoin += "Total balance: " + str(num_format_coin(sum_balance, COIN_NAME)) + COIN_NAME + "\n"
            msg_checkcoin += "Total user/guild not found (discord): " + str(sum_unfound_user) + "\n"
            msg_checkcoin += "Total balance not found (discord): " + str(num_format_coin(sum_unfound_balance, COIN_NAME)) + COIN_NAME + "\n"
            msg_checkcoin += "Time token: {}s".format(duration)
            msg_checkcoin += "```"
            await ctx.author.send(msg_checkcoin)
        else:
            await ctx.send(f'{COIN_NAME}: There is no users for this.')
            return


    @commands.is_owner()
    @admin.command(usage="save <coin>", description="Save wallet file...")
    async def save(self, ctx, coin: str):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        global SAVING_ALL
        botLogChan = bot.get_channel(LOG_CHAN)
        COIN_NAME = coin.upper()
        if is_maintenance_coin(COIN_NAME):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            await ctx.send(f'{EMOJI_RED_NO} {COIN_NAME} in maintenance. But I will try to **save** as per your command.')
            pass
        
        if COIN_NAME in (ENABLE_COIN+ENABLE_XMR):
            await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
            if COIN_NAME in WALLET_API_COIN:
                duration = await walletapi.save_walletapi(COIN_NAME)
                await botLogChan.send(f'{ctx.author.name}#{ctx.author.discriminator} called `save` for {COIN_NAME}')
                if duration:
                    await ctx.author.send(f'{get_emoji(COIN_NAME)} {COIN_NAME} `save` took {round(duration, 3)}s.')
                else:
                    await ctx.author.send(f'{get_emoji(COIN_NAME)} {COIN_NAME} `save` calling error.')
                return
            else:
                duration = await rpc_cn_wallet_save(COIN_NAME)
                await botLogChan.send(f'{ctx.author.name}#{ctx.author.discriminator} called `save` for {COIN_NAME}')
                if duration:
                    await ctx.author.send(f'{get_emoji(COIN_NAME)} {COIN_NAME} `save` took {round(duration, 3)}s.')
                else:
                    await ctx.author.send(f'{get_emoji(COIN_NAME)} {COIN_NAME} `save` calling error.')
                return
        elif COIN_NAME == "ALL" or COIN_NAME == "ALLCOIN":
            if SAVING_ALL:
                await ctx.send(f'{ctx.author.mention} {EMOJI_RED_NO} another of this process is running. Wait to complete.')
                return
            start = time.time()
            duration_msg = "```"
            await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
            await botLogChan.send(f'{ctx.author.name}#{ctx.author.discriminator} called `save all`')
            SAVING_ALL = True
            for coinItem in (ENABLE_COIN+ENABLE_XMR):
                if is_maintenance_coin(coinItem):
                    duration_msg += "{} Maintenance.\n".format(coinItem)
                else:
                    if coinItem in ["BCN"]:
                        duration_msg += "{} Skipped.\n".format(coinItem)
                    else:
                        try:
                            if coinItem in WALLET_API_COIN:
                                one_save = await walletapi.save_walletapi(coinItem)
                            else:
                                one_save = await rpc_cn_wallet_save(coinItem)
                            duration_msg += "{} saved took {}s.\n".format(coinItem, round(one_save,3))
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                            duration_msg += "{} internal error. {}\n".format(coinItem, str(e))
            SAVING_ALL = None
            end = time.time()
            duration_msg += "Total took: {}s".format(round(end - start, 3))
            duration_msg += "```"
            await ctx.author.send(f'{ctx.author.mention} `save all`:\n{duration_msg}')
            return
        else:
            await ctx.send(f'{EMOJI_RED_NO} {COIN_NAME} not exists with this command.')
            return


    @commands.is_owner()
    @admin.command(usage="debug", aliases=['debugging'], description="Debug ON/OFF")
    async def debug(self, ctx):
        global IS_DEBUG
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        botLogChan = bot.get_channel(LOG_CHAN)
        if IS_DEBUG:
            IS_DEBUG == False
            await ctx.send(f'{EMOJI_REFRESH} {ctx.author.mention} Switch debug from **ON** to **OFF**')
            return
        else:
            IS_DEBUG == True
            await ctx.send(f'{EMOJI_REFRESH} {ctx.author.mention} Switch debug from **OFF** to **ON**')
        return


    @commands.is_owner()
    @admin.command(usage="shutdown", aliases=['restart'], description="Restart bot.")
    async def shutdown(self, ctx):
        global IS_RESTARTING
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        botLogChan = bot.get_channel(LOG_CHAN)
        if IS_RESTARTING:
            await ctx.send(f'{EMOJI_REFRESH} {ctx.author.mention} I already got this command earlier.')
            return
        IS_MAINTENANCE = 1
        IS_RESTARTING = True
        await ctx.send(f'{EMOJI_REFRESH} {ctx.author.mention} .. I will restarting in 30s.. back soon.')
        await botLogChan.send(f'{EMOJI_REFRESH} {ctx.author.name}#{ctx.author.discriminator} called `restart`. I am restarting in 30s and will back soon hopefully.')
        await asyncio.sleep(30)
        await bot.logout()


    @commands.is_owner()
    @admin.command(usage="addhelp <section> <what> <description here>", description="Add help for search.")
    async def addhelp(self, ctx, section: str, what: str, *, desc: str):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        if len(desc) < 16:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} descriotion too short.')
            return

        check_exist = await store.sql_help_doc_get(section, what)
        if check_exist:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} **{what.upper()}** already existed in **{section.upper()}**')
            return
        else:
            # not existed, added. Split desc by ;
            desc_items = desc.split(";")
            detail_1 = ''
            detail_2 = ''
            if len(desc_items) >= 2:
                detail_1 = desc_items[0]
                detail_2 = desc_items[1]
            else:
                detail_1 = desc_items[0]
                detail_2 = ''
                
            add_help = await store.sql_help_doc_add(section, what, detail_1, '{}#{}'.format(ctx.author.name, ctx.author.discriminator), str(ctx.author.id), detail_2)
            if add_help:
                await ctx.message.add_reaction(EMOJI_OK_HAND) 
                await ctx.send(f'{ctx.author.mention} added **{what.upper()}** from **{section.upper()}**')
            else:
                await ctx.message.add_reaction(EMOJI_ERROR) 
                await ctx.send(f'{ctx.author.mention} internal error to add **{what.upper()}** to **{section.upper()}**')
            return


    @commands.is_owner()
    @admin.command(usage="delhelp <section> <what>", description="Delete help for search.")
    async def delhelp(self, ctx, section: str, what: str):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        check_exist = await store.sql_help_doc_get(section, what)
        if check_exist is None:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} **{what.upper()}** does not exist in **{section.upper()}**')
            return
        else:
            # OK, exist, delete
            del_help = await store.sql_help_doc_del(section, what)
            if del_help:
                await ctx.message.add_reaction(EMOJI_OK_HAND) 
                await ctx.send(f'{ctx.author.mention} deleted **{what.upper()}** from **{section.upper()}**')
            else:
                await ctx.message.add_reaction(EMOJI_ERROR) 
                await ctx.send(f'{ctx.author.mention} internal error to delete **{what.upper()}** from **{section.upper()}**')
            return


    @commands.is_owner()
    @admin.command(usage="update_balance <coin>", aliases=['update_bal', 'updatebal'], description="Update balance (all addresses).")
    async def update_balance(self, ctx, coin: str):
        COIN_NAME = coin.upper()
        if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_COIN_NANO+ENABLE_XCH:
            await ctx.author.send(f'{ctx.author.mention} COIN **{COIN_NAME}** NOT SUPPORTED.')
            return

        start = time.time()
        if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            check_min = "N/A"
            try:
                if COIN_NAME in ENABLE_COIN_ERC:
                    await store.erc_check_pending_move_deposit(COIN_NAME, 'ALL')
                    check_min = await store.erc_check_minimum_deposit(COIN_NAME)
                elif COIN_NAME in ENABLE_COIN_TRC:
                    await store.trx_check_pending_move_deposit(COIN_NAME, 'ALL')
                    check_min = await store.trx_check_minimum_deposit(COIN_NAME)
            except Exception as e:
                await logchanbot(traceback.format_exc())
            end = time.time()
            await ctx.author.send(f'{ctx.author.mention} Done update balance: ' + COIN_NAME+ ' duration (s): '+str(end - start) + f"```\n{check_min}\n```")
        elif COIN_NAME in ENABLE_COIN_NANO:
            try:
                await store.sql_nano_update_balances(COIN_NAME)
            except Exception as e:
                await logchanbot(traceback.format_exc())
            end = time.time()
            await ctx.author.send(f'{ctx.author.mention} Done update balance: ' + COIN_NAME+ ' duration (s): '+str(end - start))
        else:
            try:
                await store.sql_update_balances(COIN_NAME)
            except Exception as e:
                await logchanbot(traceback.format_exc())
            end = time.time()
            await ctx.author.send(f'{ctx.author.mention} Done update balance: ' + COIN_NAME+ ' duration (s): '+str(end - start))
        return


    @commands.is_owner()
    @admin.command(usage="baluser <userid> [yes]", description="Get balance of a user.")
    async def baluser(self, ctx, user_id: str, create_wallet: str = None):
        global IS_DEBUG
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        create_acc = None
        user_server = SERVER_BOT
        # check if there is that user
        try:
            user_id = int(user_id)
            member = bot.get_user(user_id)
            if member is None:
                await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} I cannot find that user in discord. Let me find in other!')
                # Check telegram
                user_server = 'TELEGRAM'
        except ValueError:
            await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} Invalid user for discord. Let me find in other!')
            user_server = 'TELEGRAM'

        # for verification | future restoration of lost account
        table_data = [
            ['TICKER', 'Available']
        ]
        if create_wallet:
            if create_wallet.upper() == "ON":
                create_acc = True
            else:
                COIN_NAME = create_wallet.upper()
                if COIN_NAME in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
                    wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME, user_server)
                    try:
                        xfer_in = 0
                        if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                            xfer_in = await store.sql_user_balance_get_xfer_in(str(user_id), COIN_NAME, user_server)
                        userdata_balance = await store.sql_user_balance(str(user_id), COIN_NAME, user_server)
                        msg_balance = f"Balance User ID **{str(user_id)}** for: " + COIN_NAME + "\n"
                        msg_balance += "```"
                        msg_balance += "xfer_in: " + str(xfer_in) + "\n"
                        msg_balance += "userdata_balance:\n" + str(userdata_balance)
                        msg_balance += "```"
                        await ctx.author.send(msg_balance)
                    except Exception as e:
                        print(traceback.format_exc())
                        await logchanbot(traceback.format_exc())
                else:
                    await ctx.author.send(f'{EMOJI_ERROR} {ctx.author.mention} Unknown COIN_NAME **{COIN_NAME}**.')
                return
        else:
            for COIN_NAME in [coinItem.upper() for coinItem in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH]:
                if not is_maintenance_coin(COIN_NAME):
                    wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME, user_server)
                    if wallet is None and create_acc:
                        if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                            w = await create_address_eth()
                            userregister = await store.sql_register_user(str(user_id), COIN_NAME, user_server, 0, w)
                        elif COIN_NAME in ENABLE_COIN_TRC:
                            result = await store.create_address_trx()
                            userregister = await store.sql_register_user(str(user_id), COIN_NAME, user_server, 0, result)
                        else:
                            userregister = await store.sql_register_user(str(user_id), COIN_NAME, user_server, 0)
                        wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME, user_server)
                    if wallet:
                        try:
                            xfer_in = 0
                            if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                                xfer_in = await store.sql_user_balance_get_xfer_in(str(user_id), COIN_NAME, user_server)
                        except Exception as e:
                            print(traceback.format_exc())
                            await logchanbot(traceback.format_exc())

                        userdata_balance = await store.sql_user_balance(str(user_id), COIN_NAME, user_server)
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
                                msg_negative = 'Negative balance detected:\nUser: '+str(user_id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
                                await logchanbot(msg_negative)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                        if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN+ENABLE_XMR+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
                            balance_actual = num_format_coin(actual_balance, COIN_NAME)
                        elif COIN_NAME in ENABLE_COIN_NANO:
                            actual = round(actual_balance / get_decimal(COIN_NAME), 6) * get_decimal(COIN_NAME)
                            balance_actual = num_format_coin(actual, COIN_NAME)
                        if wallet['user_wallet_address'] is None:
                            COIN_NAME += '*'
                        table_data.append([COIN_NAME, balance_actual])
                    else:
                        table_data.append([COIN_NAME, "N/A"])
                else:
                    table_data.append([COIN_NAME, "***"])
            table = AsciiTable(table_data)
            table.padding_left = 0
            table.padding_right = 0
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            await ctx.author.send(f'**[ BALANCE LIST OF {user_id} ]**\n'
                                          f'```{table.table}```\n')
        return


    @commands.is_owner()
    @admin.command(usage="lockuser <userid> <reason here>", description="Lock a user from using tipping, etc.")
    async def lockuser(self, ctx, user_id: str, *, reason: str):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        get_discord_userinfo = await store.sql_discord_userinfo_get(user_id)
        if get_discord_userinfo is None:
            await store.sql_userinfo_locked(user_id, 'YES', reason, str(ctx.author.id))
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            await ctx.author.send(f'{user_id} is locked.')
            return
        else:
            if get_discord_userinfo['locked'].upper() == "YES":
                await ctx.author.send(f'{user_id} was already locked.')
            else:
                await store.sql_userinfo_locked(user_id, 'YES', reason, str(ctx.author.id))
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                await ctx.author.send(f'Turn {user_id} to locked.')
            return


    @commands.is_owner()
    @admin.command(usage="unlockuser <userid>", description="Unlock a user from using tipping, etc.")
    async def unlockuser(self, ctx, user_id: str):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        get_discord_userinfo = await store.sql_discord_userinfo_get(user_id)
        if get_discord_userinfo:
            if get_discord_userinfo['locked'].upper() == "NO":
                await ctx.author.send(f'**{user_id}** was already unlocked. Nothing to do.')
            else:
                await store.sql_change_userinfo_single(user_id, 'locked', 'NO')
                await ctx.author.send(f'Unlocked {user_id} done.')
            return      
        else:
            await ctx.author.send(f'{user_id} not stored in **discord userinfo** yet. Nothing to unlocked.')
            return


    @commands.is_owner()
    @admin.command(usage="roachadd <main_id> <secondary_id>", description="Link a roach user to main user.")
    async def roachadd(self, ctx, main_id: str, user_id: str):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        if main_id == user_id:
            await ctx.author.send(f'{main_id} and {user_id} can not be the same.')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return
        else:
            main_member = bot.get_user(int(main_id))
            roach_user = bot.get_user(int(user_id))
            if main_member and roach_user:
                add_roach = await store.sql_roach_add(main_id, user_id, roach_user.name+"#"+roach_user.discriminator, main_member.name+"#"+main_member.discriminator)
                if add_roach:
                    await ctx.author.send(f'Succesfully add new roach **{user_id}** / {roach_user.name}#{roach_user.discriminator} to Main ID: **{main_id}** / {main_member.name}#{main_member.discriminator}.')
                    await ctx.message.add_reaction(EMOJI_OK_BOX)
                else:
                    await ctx.author.send(f'{main_id} and {user_id} added fail or already existed.')
                    await ctx.message.add_reaction(EMOJI_ERROR)
                return   
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.author.send(f'{main_id} and/or {user_id} not found.')
                return


    @commands.is_owner()
    @admin.command(usage="cleartx", description="Clear pending tx.")
    async def cleartx(self, ctx):
        global TX_IN_PROCESS, GAME_INTERACTIVE_PRGORESS, GAME_SLOT_IN_PRGORESS, \
        GAME_DICE_IN_PRGORESS, GAME_MAZE_IN_PROCESS, CHART_TRADEVIEW_IN_PROCESS, \
        GAME_INTERACTIVE_ECO
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return

        if len(TX_IN_PROCESS) == 0 and len(GAME_INTERACTIVE_PRGORESS) == 0 and len(GAME_SLOT_IN_PRGORESS) == 0 \
    and len(GAME_DICE_IN_PRGORESS) == 0 and len(GAME_MAZE_IN_PROCESS) == 0 and len(CHART_TRADEVIEW_IN_PROCESS) == 0 \
    and len(GAME_INTERACTIVE_ECO) == 0:
            await ctx.author.send(f'{ctx.author.mention} Nothing in pending to clear.')
        else:
            try:
                pending_msg = []
                count = 0
                list_pending = ""
                if len(TX_IN_PROCESS) > 0:
                    string_ints = [str(num) for num in TX_IN_PROCESS]
                    list_pending += ', '.join(string_ints)
                    pending_msg.append(f"TX_IN_PROCESS: {list_pending}")
                    count += len(TX_IN_PROCESS)
                if len(GAME_INTERACTIVE_PRGORESS) > 0:
                    string_ints = [str(num) for num in GAME_INTERACTIVE_PRGORESS]
                    list_pending += ', '.join(string_ints)
                    pending_msg.append(f"GAME_INTERACTIVE_PRGORESS: {list_pending}")
                    count += len(GAME_INTERACTIVE_PRGORESS)
                if len(GAME_INTERACTIVE_ECO) > 0:
                    string_ints = [str(num) for num in GAME_INTERACTIVE_ECO]
                    list_pending += ', '.join(string_ints)
                    pending_msg.append(f"GAME_INTERACTIVE_ECO: {list_pending}")
                    count += len(GAME_INTERACTIVE_ECO)
                if len(GAME_SLOT_IN_PRGORESS) > 0:
                    string_ints = [str(num) for num in GAME_SLOT_IN_PRGORESS]
                    list_pending += ', '.join(string_ints)
                    pending_msg.append(f"GAME_SLOT_IN_PRGORESS: {list_pending}")
                    count += len(GAME_SLOT_IN_PRGORESS)
                if len(GAME_DICE_IN_PRGORESS) > 0:
                    string_ints = [str(num) for num in GAME_DICE_IN_PRGORESS]
                    list_pending += ', '.join(string_ints)
                    pending_msg.append(f"GAME_DICE_IN_PRGORESS: {list_pending}")
                    count += len(GAME_DICE_IN_PRGORESS)
                if len(GAME_MAZE_IN_PROCESS) > 0:
                    string_ints = [str(num) for num in GAME_MAZE_IN_PROCESS]
                    list_pending += ', '.join(string_ints)
                    pending_msg.append(f"GAME_MAZE_IN_PROCESS: {list_pending}")
                    count += len(GAME_MAZE_IN_PROCESS)
                if len(CHART_TRADEVIEW_IN_PROCESS) > 0:
                    string_ints = [str(num) for num in CHART_TRADEVIEW_IN_PROCESS]
                    list_pending += ', '.join(string_ints)
                    pending_msg.append(f"CHART_TRADEVIEW_IN_PROCESS: {list_pending}")
                    count += len(CHART_TRADEVIEW_IN_PROCESS)
                pending_all = '\n'.join(pending_msg)
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.author.send(f'{ctx.author.mention} Clearing:\n```{pending_all}```\nTotal: {str(count)}')
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                await logchanbot(traceback.format_exc())
            TX_IN_PROCESS = [] 
            GAME_INTERACTIVE_PRGORESS = []
            GAME_SLOT_IN_PRGORESS = []
            GAME_DICE_IN_PRGORESS = []
            GAME_MAZE_IN_PROCESS = []
            GAME_INTERACTIVE_ECO = []
        return


    @commands.is_owner()
    @admin.command(usage="pending", description="Check pending things.")
    async def pending(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be in public.')
            return
        ts = datetime.utcnow()
        embed = discord.Embed(title='Pending Actions', timestamp=ts)
        embed.add_field(name="TX_IN_PROCESS", value=str(len(TX_IN_PROCESS)), inline=True)
        embed.add_field(name="GAME_INTERACTIVE", value=str(len(GAME_INTERACTIVE_PRGORESS)), inline=True)
        embed.add_field(name="GAME_INTERACTIVE_ECO", value=str(len(GAME_INTERACTIVE_ECO)), inline=True)
        embed.add_field(name="GAME_SLOT", value=str(len(GAME_SLOT_IN_PRGORESS)), inline=True)
        embed.add_field(name="GAME_DICE", value=str(len(GAME_DICE_IN_PRGORESS)), inline=True)
        embed.add_field(name="GAME_MAZE", value=str(len(GAME_MAZE_IN_PROCESS)), inline=True)
        embed.set_footer(text=f"Pending requested by {ctx.author.name}#{ctx.author.discriminator}")
        try:
            msg = await ctx.send(embed=embed)
            await msg.add_reaction(EMOJI_OK_BOX)
        except Exception as e:
            await logchanbot(traceback.format_exc())
        return


def setup(bot):
    bot.add_cog(Admin(bot))