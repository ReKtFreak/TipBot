import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class TipTip(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    ## TODO: Improve this usage.
    @commands.command(usage="tip <amount> [option]", description="Tip to user(s).")
    async def tip(self, ctx, amount: str, *args):
        global TRTL_DISCORD, IS_RESTARTING, TX_IN_PROCESS
        secrettip = False
        fromDM = False
        # check if bot is going to restart
        if IS_RESTARTING:
            await ctx.message.add_reaction(EMOJI_REFRESH)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
            return
        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'tip')
        if account_lock:
            await ctx.message.add_reaction(EMOJI_LOCKED) 
            await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
            return
        # end of check if account locked

        # Check if tx in progress
        if ctx.author.id in TX_IN_PROCESS:
            await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
            msg = await ctx.message.reply(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

        botLogChan = self.bot.get_channel(LOG_CHAN)
        amount = amount.replace(",", "")

        try:
            amount = Decimal(amount)
        except ValueError:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
            return

        if isinstance(ctx.channel, discord.DMChannel) and args[-1].isdigit() == False and config.discord.enable_secrettip != 1:
            await ctx.message.reply(f'{EMOJI_RED_NO} This command can not be in private.')
            return

        if isinstance(ctx.channel, discord.DMChannel):
            if len(args) != 2:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You are using a secret tip. Please tip in public!')
                return
            else:
                COIN_NAME = args[0].upper()
                if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_COIN_NANO+ENABLE_XCH:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You are using a secret tip command. Please tip in public! **{COIN_NAME}** not available!')
                    return
                try:
                    member = self.bot.get_user(int(args[1]))
                    if member:
                        secrettip = True
                        fromDM = True
                    else:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {args[1]} not found!')
                        return
                except Exception as e:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    try:
                        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You are using a secret tip command. Please tip in public!')
                    except Exception as e:
                        return
        else:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            COIN_NAME = None
            try:
                COIN_NAME = args[0].upper()
                if COIN_NAME in ENABLE_XMR+ENABLE_XCH+ENABLE_COIN_NANO:
                    pass
                elif COIN_NAME not in ENABLE_COIN:
                    if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                        pass
                    elif 'default_coin' in serverinfo:
                        COIN_NAME = serverinfo['default_coin'].upper()
            except:
                if 'default_coin' in serverinfo:
                    COIN_NAME = serverinfo['default_coin'].upper()
        print("COIN_NAME: " + COIN_NAME)

        # TRTL discord
        if isinstance(ctx.channel, discord.DMChannel) == False and ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
            return

        if not is_coin_tipable(COIN_NAME):
            msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} TIPPING is currently disable for {COIN_NAME}.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
        if fromDM == False:
            # Check allowed coins
            tiponly_coins = serverinfo['tiponly'].split(",")
            if COIN_NAME == serverinfo['default_coin'].upper() or serverinfo['tiponly'].upper() == "ALLCOIN":
                pass
            elif COIN_NAME not in tiponly_coins:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} not in allowed coins set by server manager.')
                return
            # End of checking allowed coins

        if is_maintenance_coin(COIN_NAME):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
            return

        if len(ctx.message.mentions) == 0 and len(ctx.message.role_mentions) == 0 and fromDM == False:
            # Use how time.
            if len(args) >= 2:
                time_given = None
                if args[0].upper() == "LAST" or args[1].upper() == "LAST":
                    # try if the param is 1111u
                    num_user = None
                    if args[0].upper() == "LAST":
                        num_user = args[1].lower()
                    elif args[1].upper() == "LAST":
                        num_user = args[2].lower()
                    if 'u' in num_user or 'user' in num_user or 'users' in num_user or 'person' in num_user or 'people' in num_user:
                        num_user = num_user.replace("people", "")
                        num_user = num_user.replace("person", "")
                        num_user = num_user.replace("users", "")
                        num_user = num_user.replace("user", "")
                        num_user = num_user.replace("u", "")
                        try:
                            num_user = int(num_user)
                            if len(ctx.guild.members) <= 10:
                                await ctx.message.add_reaction(EMOJI_ERROR)
                                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please use normal tip command. There are only few users.')
                                return
                            # Check if we really have that many user in the guild 20%
                            elif num_user >= len(ctx.guild.members):
                                try:
                                    await ctx.message.add_reaction(EMOJI_INFORMATION)
                                    await ctx.message.reply(f'{ctx.author.mention} Boss, you want to tip more than the number of people in this guild!?.'
                                                            ' Can be done :). Wait a while.... I am doing it. (**counting..**)')
                                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                    # No need to tip if failed to message
                                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                    return
                                message_talker = await store.sql_get_messages(str(ctx.message.guild.id), str(ctx.message.channel.id), 0, len(ctx.guild.members))
                                if ctx.author.id in message_talker:
                                    message_talker.remove(ctx.author.id)
                                if len(message_talker) == 0:
                                    await ctx.message.add_reaction(EMOJI_ERROR)
                                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} There is not sufficient user to count.')
                                elif len(message_talker) < len(ctx.guild.members) - 1: # minus bot
                                    await ctx.message.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} I could not find sufficient talkers up to **{num_user}**. I found only **{len(message_talker)}**'
                                                            f' and tip to those **{len(message_talker)}** users if they are still here.')
                                    # tip all user who are in the list
                                    try:
                                        async with ctx.typing():
                                            await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                                    except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                        await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                        # zipped mouth but still need to do tip talker
                                        await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                                    except Exception as e:
                                        await logchanbot(traceback.format_exc())
                                return
                            elif num_user > 0:
                                message_talker = await store.sql_get_messages(str(ctx.message.guild.id), str(ctx.message.channel.id), 0, num_user + 1)
                                if ctx.author.id in message_talker:
                                    message_talker.remove(ctx.author.id)
                                else:
                                    # remove the last one
                                    message_talker.pop()
                                if len(message_talker) == 0:
                                    await ctx.message.add_reaction(EMOJI_ERROR)
                                    await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} There is not sufficient user to count.')
                                elif len(message_talker) < num_user:
                                    try:
                                        await ctx.message.add_reaction(EMOJI_INFORMATION)
                                        await ctx.message.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} I could not find sufficient talkers up to **{num_user}**. I found only **{len(message_talker)}**'
                                                                f' and tip to those **{len(message_talker)}** users if they are still here.')
                                    except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                        # No need to tip if failed to message
                                        await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                        return
                                    # tip all user who are in the list
                                    try:
                                        async with ctx.typing():
                                            await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                                    except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                        await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                        # zipped mouth but still need to do tip talker
                                        await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                                    except Exception as e:
                                        await logchanbot(traceback.format_exc())
                                else:
                                    try:
                                        async with ctx.typing():
                                            await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                                    except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                        await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                        # zipped mouth but still need to do tip talker
                                        await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                                    except Exception as e:
                                        await logchanbot(traceback.format_exc())
                                    return
                                return
                            else:
                                await ctx.message.add_reaction(EMOJI_ERROR)
                                await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} What is this **{num_user}** number? Please give a number bigger than 0 :) ')
                                return
                        except ValueError:
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid param after **LAST**.')
                        return
                    time_string = ctx.message.content.lower().split("last", 1)[1].strip()
                    time_second = None
                    try:
                        time_string = time_string.replace("years", "y")
                        time_string = time_string.replace("yrs", "y")
                        time_string = time_string.replace("yr", "y")
                        time_string = time_string.replace("year", "y")
                        time_string = time_string.replace("months", "mon")
                        time_string = time_string.replace("month", "mon")
                        time_string = time_string.replace("mons", "mon")
                        time_string = time_string.replace("weeks", "w")
                        time_string = time_string.replace("week", "w")

                        time_string = time_string.replace("day", "d")
                        time_string = time_string.replace("days", "d")

                        time_string = time_string.replace("hours", "h")
                        time_string = time_string.replace("hour", "h")
                        time_string = time_string.replace("hrs", "h")
                        time_string = time_string.replace("hr", "h")

                        time_string = time_string.replace("minutes", "mn")
                        time_string = time_string.replace("mns", "mn")
                        time_string = time_string.replace("mins", "mn")
                        time_string = time_string.replace("min", "mn")
                        time_string = time_string.replace("m", "mn")

                        mult = {'y': 12*30*24*60*60, 'mon': 30*24*60*60, 'w': 7*24*60*60, 'd': 24*60*60, 'h': 60*60, 'mn': 60}
                        time_second = sum(int(num) * mult.get(val, 1) for num, val in re.findall('(\d+)(\w+)', time_string))
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid time given. Please use this example: `.tip 1,000 last 5h 12mn`')
                        return
                    try:
                        time_given = int(time_second)
                    except ValueError:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid time given check.')
                        return
                    if time_given:
                        if time_given < 5*60 or time_given > 60*24*60*60:
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Please try time interval between 5minutes to 24hours.')
                            return
                        else:
                            message_talker = await store.sql_get_messages(str(ctx.message.guild.id), str(ctx.message.channel.id), time_given, None)
                            if len(message_talker) == 0:
                                await ctx.message.add_reaction(EMOJI_ERROR)
                                await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} There is no active talker in such period.')
                                return
                            else:
                                try:
                                    async with ctx.typing():
                                        await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                    # zipped mouth but still need to do tip talker
                                    await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                                except Exception as e:
                                    await logchanbot(traceback.format_exc())
                                return
                else:
                    if len(args) == 2 and args[1].isdigit():
                        try:
                            member = bot.get_user(int(args[1]))
                            secrettip = True
                        except Exception as e:
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            try:
                                await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                try:
                                    await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                    return
                            return
                    else:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        try:
                            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            try:
                                await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                return
                        return
            elif len(args) == 1 and args[0].isdigit():
                try:
                    member = self.bot.get_user(int(args[0]))
                    secrettip = True
                except Exception as e:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    try:
                        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        try:
                            await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            return
                    return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                try:
                    await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    try:
                        await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        return
                return
        elif len(ctx.message.mentions) == 1 and (self.bot.user in ctx.message.mentions) and fromDM == False:
            # Tip to TipBot
            member = ctx.message.mentions[0]
        elif len(ctx.message.mentions) == 1 and (self.bot.user not in ctx.message.mentions) and fromDM == False:
            member = ctx.message.mentions[0]
            if ctx.author.id == member.id:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Tip me if you want.')
                return
            pass
        elif len(ctx.message.role_mentions) >= 1 and fromDM == False:
            mention_roles = ctx.message.role_mentions
            if "@everyone" in mention_roles:
                mention_roles.remove("@everyone")
                if len(mention_roles) < 1:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Can not find user to tip to.')
                    return
            try:
                await _tip(ctx, amount, COIN_NAME)
            except Exception as e:
                await logchanbot(traceback.format_exc())
            return
        elif len(ctx.message.mentions) > 1 and fromDM == False:
            try:
                await _tip(ctx, amount, COIN_NAME)
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                pass
            except Exception as e:
                await logchanbot(traceback.format_exc())
            return


        # Check flood of tip
        floodTip = await store.sql_get_countLastTip(str(ctx.author.id), config.floodTipDuration)
        if floodTip >= config.floodTip:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Cool down your tip or TX. or increase your amount next time.')
            await botLogChan.send('A user reached max. TX threshold. Currently halted: `.tip`')
            return
        # End of Check flood of tip

        # Check if maintenance
        if IS_MAINTENANCE == 1:
            if int(ctx.author.id) in MAINTENANCE_OWNER:
                pass
            else:
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}')
                return
        # End Check if maintenance

        notifyList = await store.sql_get_tipnotify()

        user_from = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
        if user_from is None:
            if COIN_NAME in ENABLE_COIN_ERC:
                w = await create_address_eth()
                user_from = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
            elif COIN_NAME in ENABLE_COIN_TRC:
                result = await store.create_address_trx()
                user_from = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, result)
            else:
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

        user_to = await store.sql_get_userwallet(str(member.id), COIN_NAME)
        if user_to is None:
            if coin_family == "ERC-20":
                w = await create_address_eth()
                userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0, w)
            elif coin_family == "TRC-20":
                result = await store.create_address_trx()
                userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0, result)
            else:
                userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0)
            user_to = await store.sql_get_userwallet(str(member.id), COIN_NAME)

        if coin_family == "ERC-20" or coin_family == "TRC-20":
            real_amount = float(amount)
            token_info = await store.get_token_info(COIN_NAME)
            MinTx = token_info['real_min_tip']
            MaxTX = token_info['real_max_tip']
        else:
            real_amount = int(Decimal(amount) * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
            MinTx = get_min_mv_amount(COIN_NAME)
            MaxTX = get_max_mv_amount(COIN_NAME)

        if real_amount > MaxTX:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than '
                                    f'{num_format_coin(MaxTX, COIN_NAME)} '
                                    f'{COIN_NAME}.')
            return
        elif real_amount > actual_balance:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to send tip of '
                                    f'{num_format_coin(real_amount, COIN_NAME)} '
                                    f'{COIN_NAME} to {member.name}#{member.discriminator}.')
            return
        elif real_amount < MinTx:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than '
                                    f'{num_format_coin(MinTx, COIN_NAME)} '
                                    f'{COIN_NAME}.')
            return

        # add queue also tip
        if ctx.author.id not in TX_IN_PROCESS:
            TX_IN_PROCESS.append(ctx.author.id)
        else:
            await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
            msg = await ctx.message.reply(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

        tip = None
        try:
            if coin_family in ["TRTL", "BCN"]:
                tip = await store.sql_mv_cn_single(str(ctx.author.id), str(member.id), real_amount, 'TIP', COIN_NAME)
            elif coin_family == "XMR":
                tip = await store.sql_mv_xmr_single(str(ctx.author.id), str(member.id), real_amount, COIN_NAME, "TIP")
            elif coin_family == "XCH":
                tip = await store.sql_mv_xch_single(str(ctx.author.id), str(member.id), real_amount, COIN_NAME, "TIP")
            elif coin_family == "DOGE":
                tip = await store.sql_mv_doge_single(str(ctx.author.id), str(member.id), real_amount, COIN_NAME, "TIP")
            elif coin_family == "NANO":
                tip = await store.sql_mv_nano_single(str(ctx.author.id), str(member.id), real_amount, COIN_NAME, "TIP")
            elif coin_family == "ERC-20":
                tip = await store.sql_mv_erc_single(str(ctx.author.id), str(member.id), real_amount, COIN_NAME, "TIP", token_info['contract'])
            elif coin_family == "TRC-20":
                tip = await store.sql_mv_trx_single(str(ctx.author.id), str(member.id), real_amount, COIN_NAME, "TIP", token_info['contract'])
            if ctx.author.bot == False and fromDM == False and serverinfo['react_tip'] == "ON":
                await ctx.message.add_reaction(EMOJI_TIP)
        except Exception as e:
            await logchanbot(traceback.format_exc())

        # remove queue from tip
        if ctx.author.id in TX_IN_PROCESS:
            TX_IN_PROCESS.remove(ctx.author.id)

        if tip:
            # Update tipstat
            try:
                update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
                update_tipstat = await store.sql_user_get_tipstat(str(member.id), COIN_NAME, True, SERVER_BOT)
            except Exception as e:
                await logchanbot(traceback.format_exc())

            await ctx.message.add_reaction(get_emoji(COIN_NAME))
            # tipper shall always get DM. Ignore notifyList
            try:
                if fromDM == True:
                    in_server = ""
                else:
                    in_server = f" in server `{ctx.guild.name}`"
                await ctx.author.send(
                    f'{EMOJI_ARROW_RIGHTHOOK} Tip of {num_format_coin(real_amount, COIN_NAME)} '
                    f'{COIN_NAME} '
                    f'was sent to {member.name}#{member.discriminator}{in_server}')
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                await store.sql_toggle_tipnotify(str(ctx.author.id), "OFF")
            if self.bot.user.id != member.id and str(member.id) not in notifyList:
                try:
                    fromtipper = f"{ctx.author.name}#{ctx.author.discriminator}"
                    if fromDM == True:
                        from_server = ""
                    else:
                        from_server = f" in server `{ctx.guild.name}` #{ctx.channel.name}"
                    if secrettip:
                        fromtipper = "someone"
                    await member.send(
                        f'{EMOJI_MONEYFACE} You got a tip of {num_format_coin(real_amount, COIN_NAME)} '
                        f'{COIN_NAME} from {fromtipper}{from_server}\n'
                        f'{NOTIFICATION_OFF_CMD}\n')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    await store.sql_toggle_tipnotify(str(member.id), "OFF")
            if secrettip:
                await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} using a secret tip command {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}.')
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.reply(f'{ctx.author.mention} Can not deliver TX for {COIN_NAME} right now. Try again soon.')
            # add to failed tx table
            await store.sql_add_failed_tx(COIN_NAME, str(ctx.author.id), ctx.author.name, real_amount, "TIP")
            return


def setup(bot):
    bot.add_cog(TipTip(bot))