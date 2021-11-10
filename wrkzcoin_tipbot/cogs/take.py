import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class Faucet(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(usage="take <info>", description="Claim a random coin faucet.")
    async def take(self, ctx, info: str=None):
        async def bot_faucet(ctx):
            global TRTL_DISCORD
            get_game_stat = await store.sql_game_stat()
            table_data = [
                ['TICKER', 'Available', 'Claimed / Game']
            ]
            for COIN_NAME in [coinItem.upper() for coinItem in FAUCET_COINS]:
                sum_sub = 0
                wallet = await store.sql_get_userwallet(str(bot.user.id), COIN_NAME)
                if wallet is None:
                    if COIN_NAME in ENABLE_COIN_ERC:
                        coin_family = "ERC-20"
                        w = await create_address_eth()
                        wallet = await store.sql_register_user(str(bot.user.id), COIN_NAME, SERVER_BOT, 0, w)
                    elif COIN_NAME in ENABLE_COIN_TRC:
                        coin_family = "TRC-20"
                        result = await store.create_address_trx()
                        wallet = await store.sql_register_user(str(bot.user.id), COIN_NAME, SERVER_BOT, 0, result)
                    else:
                        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                        wallet = await store.sql_register_user(str(bot.user.id), COIN_NAME, SERVER_BOT, 0)
                userdata_balance = await store.sql_user_balance(str(bot.user.id), COIN_NAME)
                xfer_in = 0
                if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    xfer_in = await store.sql_user_balance_get_xfer_in(str(bot.user.id), COIN_NAME)
                if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
                elif COIN_NAME in ENABLE_COIN_NANO:
                    actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
                    actual_balance = round(actual_balance / get_decimal(COIN_NAME), 6) * get_decimal(COIN_NAME)
                else:
                    actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
                if COIN_NAME in ENABLE_COIN_ERC:
                    coin_family = "ERC-20"
                elif COIN_NAME in ENABLE_COIN_TRC:
                    coin_family = "TRC-20"
                else:
                    coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")           
                try:
                    if COIN_NAME in get_game_stat and coin_family in ["TRTL", "BCN", "XMR", "NANO", "XCH"]:
                        actual_balance = actual_balance - int(get_game_stat[COIN_NAME])
                        sum_sub = int(get_game_stat[COIN_NAME])
                    elif COIN_NAME in get_game_stat and coin_family in ["DOGE", "ERC-20", "TRC-20"]:
                        actual_balance = actual_balance - float(get_game_stat[COIN_NAME])
                        sum_sub = float(get_game_stat[COIN_NAME])
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                balance_actual = num_format_coin(actual_balance, COIN_NAME)
                get_claimed_count = await store.sql_faucet_sum_count_claimed(COIN_NAME)
                if coin_family in ["TRTL", "BCN", "XMR", "NANO", "XCH"]:
                    sub_claim = num_format_coin(int(get_claimed_count['claimed']) + sum_sub, COIN_NAME) if get_claimed_count['count'] > 0 else f"0.00{COIN_NAME}"
                elif coin_family in ["DOGE", "ERC-20", "TRC-20"]:
                    sub_claim = num_format_coin(float(get_claimed_count['claimed']) + sum_sub, COIN_NAME) if get_claimed_count['count'] > 0 else f"0.00{COIN_NAME}"
                if actual_balance != 0:
                    table_data.append([COIN_NAME, balance_actual, sub_claim])
                else:
                    table_data.append([COIN_NAME, '0', sub_claim])
            table = AsciiTable(table_data)
            table.padding_left = 0
            table.padding_right = 0
            return table.table

        botLogChan = bot.get_channel(LOG_CHAN)
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send(f'{EMOJI_RED_NO} This command can not be in private.')
            return

        faucet_simu = False
        # bot check in the first place
        if ctx.author.bot == True:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is not allowed using this.')
            await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} (Bot) using **take** {ctx.guild.name} / {ctx.guild.id}')
            return

        # Check if tx in progress
        if ctx.author.id in TX_IN_PROCESS:
            await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
            msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        remaining = ''
        try:
            remaining = await bot_faucet(ctx) or ''
        except Exception as e:
            await logchanbot(traceback.format_exc())
        total_claimed = '{:,.0f}'.format(await store.sql_faucet_count_all())
        if info and info.upper() not in FAUCET_COINS:
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            msg = await ctx.send(f'{ctx.author.mention} Faucet balance:\n```{remaining}```'
                                 f'Total user claims: **{total_claimed}** times. '
                                 f'Tip me if you want to feed these faucets.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

        # check if bot is going to restart
        if IS_RESTARTING:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
            await ctx.message.add_reaction(EMOJI_REFRESH)
            return

        # disable faucet for TRTL discord
        if ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        # offline can not take
        if ctx.author.status == discord.Status.offline:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Offline status cannot claim faucet.')
            await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
            return

        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'take')
        if account_lock:
            await ctx.message.add_reaction(EMOJI_LOCKED) 
            await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
            return
        # end of check if account locked

        # check if guild has very small number of online
        try:
            num_online = len([member for member in ctx.guild.members if member.bot == False and member.status != discord.Status.offline])
            if num_online < 7:
                await botLogChan.send(f'{ctx.author.name}#{ctx.author.discriminator} / {ctx.author.id} using **take** {ctx.guild.name} / {ctx.guild.id} while there are only {str(num_online)} online. Rejected!')
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} This guild has less than 7 online users. Faucet is disable.')
                await ctx.message.add_reaction(EMOJI_INFORMATION)
                return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
        except Exception as e:
            pass

        # check if user create account less than 3 days
        try:
            account_created = ctx.author.created_at
            if (datetime.utcnow() - account_created).total_seconds() <= config.faucet.account_age_to_claim:
                msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Your account is very new. Wait a few days before using .take')
                await ctx.message.add_reaction(EMOJI_ERROR)
                return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            pass
        except Exception as e:
            await logchanbot(traceback.format_exc())

        try: 
            # check if bot channel is set:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if serverinfo and serverinfo['botchan']:
                if ctx.channel.id != int(serverinfo['botchan']):
                    try:
                        botChan = bot.get_channel(int(serverinfo['botchan']))
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, {botChan.mention} is the bot channel!!!')
                        await ctx.message.add_reaction(EMOJI_ERROR)
                    except Exception as e:
                        pass
                    # add penalty:
                    try:
                        faucet_penalty = await store.sql_faucet_penalty_checkuser(str(ctx.author.id), True, SERVER_BOT)
                    except Exception as e:
                        traceback.print_exc(file=sys.stdout)
                        await logchanbot(traceback.format_exc())
                    return
            if serverinfo and serverinfo['enable_faucet'] == "NO":
                await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **take** in {ctx.guild.name} / {ctx.guild.id} which is disable.')
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, **Faucet** in this guild is disable.')
                return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            pass
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
        # end of bot channel check

        try:
            claim_interval = config.faucet.interval
            half_claim_interval = int(config.faucet.interval / 2)
            # check penalty:
            try:
                faucet_penalty = await store.sql_faucet_penalty_checkuser(str(ctx.author.id), False, SERVER_BOT)
                if faucet_penalty and not info:
                    if half_claim_interval*3600 - int(time.time()) + int(faucet_penalty['penalty_at']) > 0:
                        time_waiting = seconds_str(half_claim_interval*3600 - int(time.time()) + int(faucet_penalty['penalty_at']))
                        try:
                            msg = await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You claimed in a wrong channel within last {str(half_claim_interval)}h. '
                                                          f'Waiting time {time_waiting} for next **take** and be sure to be the right channel set by the guild.')
                            await msg.add_reaction(EMOJI_OK_BOX)
                            await ctx.message.add_reaction(EMOJI_ALARMCLOCK)
                        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                            await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                        return
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                await logchanbot(traceback.format_exc())
                return
            # check user claim:
            
            check_claimed = await store.sql_faucet_checkuser(str(ctx.author.id), SERVER_BOT)
            if check_claimed:
                # limit 12 hours
                if int(time.time()) - check_claimed['claimed_at'] <= claim_interval*3600:
                    time_waiting = seconds_str(claim_interval*3600 - int(time.time()) + check_claimed['claimed_at'])
                    user_claims = await store.sql_faucet_count_user(str(ctx.author.id))
                    number_user_claimed = '{:,.0f}'.format(user_claims, SERVER_BOT)
                    try:
                        msg = await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You just claimed within last {claim_interval}h. '
                                                      f'Waiting time {time_waiting} for next **take**. Faucet balance:\n```{remaining}```'
                                                      f'Total user claims: **{total_claimed}** times. '
                                                      f'You have claimed: **{number_user_claimed}** time(s). '
                                                      f'Tip me if you want to feed these faucets.')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        await ctx.message.add_reaction(EMOJI_ERROR)
                    except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                        await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                    return
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
            return


        COIN_NAME = random.choice(FAUCET_COINS)
        while is_maintenance_coin(COIN_NAME):
            COIN_NAME = random.choice(FAUCET_COINS)
        if info and info.upper() in FAUCET_COINS:
            COIN_NAME = info.upper()
        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
        try:
            if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                token_info = await store.get_token_info(COIN_NAME)
                decimal_pts = token_info['token_decimal']
                coin_decimal = 1
            else:
                decimal_pts = int(math.log10(get_decimal(COIN_NAME)))
                coin_decimal = get_decimal(COIN_NAME)

            if coin_family in ["DOGE", "ERC-20"]:
                amount = random.uniform(FAUCET_MINMAX[COIN_NAME][0], FAUCET_MINMAX[COIN_NAME][1])
            else:
                amount = random.randint(FAUCET_MINMAX[COIN_NAME][0]*coin_decimal, FAUCET_MINMAX[COIN_NAME][1]*coin_decimal)

            if COIN_NAME == "DOGE":
                amount = float(amount / 400)
            elif COIN_NAME in HIGH_DECIMAL_COIN:
                amount = float("%.5f" % (amount / get_decimal(COIN_NAME))) * get_decimal(COIN_NAME)
        except Exception as e:
            await logchanbot(traceback.format_exc())
            return

        def myround_number(x, base=5):
            return base * round(x/base)

        if amount == 0:
            await ctx.message.add_reaction(EMOJI_ERROR)
            amount_msg_zero = 'Get 0 random amount requested faucet by: {}#{}'.format(ctx.author.name, ctx.author.discriminator)
            await logchanbot(amount_msg_zero)
            return

        if COIN_NAME in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
            real_amount = float(amount) if coin_family in ["DOGE", "ERC-20"] else int(amount) # already real amount
            user_from = await store.sql_get_userwallet(str(bot.user.id), COIN_NAME)
            if user_from is None:
                if COIN_NAME in ENABLE_COIN_ERC:
                    w = await create_address_eth()
                    user_from = await store.sql_register_user(str(bot.user.id), COIN_NAME, SERVER_BOT, 0, w)
                elif COIN_NAME in ENABLE_COIN_TRC:
                    result = await store.create_address_trx()
                    user_from = await store.sql_register_user(str(bot.user.id), COIN_NAME, SERVER_BOT, 0, result)
                else:
                    user_from = await store.sql_register_user(str(bot.user.id), COIN_NAME, SERVER_BOT, 0)
            userdata_balance = await store.sql_user_balance(str(bot.user.id), COIN_NAME)
            xfer_in = 0
            if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                xfer_in = await store.sql_user_balance_get_xfer_in(str(bot.user.id), COIN_NAME)
            if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
            elif COIN_NAME in ENABLE_COIN_NANO:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
                actual_balance = round(actual_balance / get_decimal(COIN_NAME), 6) * get_decimal(COIN_NAME)
            else:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
            user_to = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            # Negative check
            try:
                if actual_balance < 0:
                    msg_negative = 'Negative balance detected:\nBot User: '+str(bot.user.id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
                    await logchanbot(msg_negative)
            except Exception as e:
                await logchanbot(traceback.format_exc())
            
            if user_to is None:
                if COIN_NAME in ENABLE_COIN_ERC:
                    w = await create_address_eth()
                    userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
                elif COIN_NAME in ENABLE_COIN_TRC:
                    result = await store.create_address_trx()
                    userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, result)
                else:
                    userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
                user_to = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)

            if real_amount > actual_balance:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{ctx.author.mention} Please try again later. Bot runs out of **{COIN_NAME}**')
                return
            
            tip = None
            if ctx.author.id not in TX_IN_PROCESS:
                TX_IN_PROCESS.append(ctx.author.id)
                try:
                    if not info:
                        if coin_family in ["TRTL", "BCN"]:
                            tip = await store.sql_mv_cn_single(str(bot.user.id), str(ctx.author.id), real_amount, 'FAUCET', COIN_NAME)
                        elif coin_family == "XMR":
                            tip = await store.sql_mv_xmr_single(str(bot.user.id), str(ctx.author.id), real_amount, COIN_NAME, "FAUCET")
                        elif coin_family == "XCH":
                            tip = await store.sql_mv_xch_single(str(bot.user.id), str(ctx.author.id), real_amount, COIN_NAME, "FAUCET")
                        elif coin_family == "NANO":
                            tip = await store.sql_mv_nano_single(str(bot.user.id), str(ctx.author.id), real_amount, COIN_NAME, "FAUCET")
                        elif coin_family == "DOGE":
                            tip = await store.sql_mv_doge_single(str(bot.user.id), str(ctx.author.id), real_amount, COIN_NAME, "FAUCET")
                        elif coin_family == "ERC-20":
                            token_info = await store.get_token_info(COIN_NAME)
                            tip = await store.sql_mv_erc_single(str(bot.user.id), str(ctx.author.id), real_amount, COIN_NAME, "FAUCET", token_info['contract'])
                        elif coin_family == "TRC-20":
                            token_info = await store.get_token_info(COIN_NAME)
                            tip = await store.sql_mv_trx_single(str(bot.user.id), str(ctx.author.id), real_amount, COIN_NAME, "FAUCET", token_info['contract'])
                    else:
                        try:
                            msg = await ctx.message.reply(f'{EMOJI_MONEYFACE} {ctx.author.mention} Simulated faucet {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}. This is a test only. Use without **ticker** to do real faucet claim.')
                            await msg.add_reaction(EMOJI_OK_BOX)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                        TX_IN_PROCESS.remove(ctx.author.id)
                        return
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                TX_IN_PROCESS.remove(ctx.author.id)
            else:
                msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
                await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            if tip:
                # Update tipstat
                try:
                    update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
                    update_tipstat = await store.sql_user_get_tipstat(str(bot.user.id), COIN_NAME, True, SERVER_BOT)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                try:
                    faucet_add = await store.sql_faucet_add(str(ctx.author.id), str(ctx.guild.id), COIN_NAME, real_amount, 10**decimal_pts, SERVER_BOT)
                    msg = await ctx.send(f'{EMOJI_MONEYFACE} {ctx.author.mention} You got a random faucet {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}')
                    await logchanbot(f'[Discord] User {ctx.author.name}#{ctx.author.discriminator} claimed faucet {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME} in guild {ctx.guild.name}/{ctx.guild.id}')
                    await ctx.message.add_reaction(get_emoji(COIN_NAME))
                    await msg.add_reaction(EMOJI_OK_BOX)
                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                    msg = await ctx.author.send(f'{EMOJI_MONEYFACE} {ctx.author.mention} You got a random faucet {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}. Claimed in guild `{ctx.guild.name}`.')
                except Exception as e:
                    await logchanbot(traceback.format_exc())
            else:
                await ctx.send(f'{ctx.author.mention} Please try again later. Failed during executing tx **{COIN_NAME}**.')
                await ctx.message.add_reaction(EMOJI_ERROR)

def setup(bot):
    bot.add_cog(Faucet(bot))