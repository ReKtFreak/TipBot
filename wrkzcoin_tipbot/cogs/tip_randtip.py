import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class TipRandomTip(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(
        usage="randtip <amount> <coin> [option]", 
        aliases=['randomtip'], 
        description="Do a random tip to user."
    )
    async def randtip(
        self, 
        ctx, 
        amount: str, 
        coin: str, 
        *, 
        rand_option: str=None
    ):
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
            msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

        botLogChan = self.bot.get_channel(LOG_CHAN)
        amount = amount.replace(",", "")

        try:
            amount = Decimal(amount)
        except ValueError:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
            return

        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send(f'{EMOJI_RED_NO} This command can not be in private.')
            return

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        COIN_NAME = coin.upper()
        print("COIN_NAME: " + COIN_NAME)

        # TRTL discord
        if ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
            return

        if COIN_NAME not in (ENABLE_COIN_ERC + ENABLE_COIN_TRC + ENABLE_COIN + ENABLE_XMR + ENABLE_COIN_DOGE + ENABLE_COIN_NANO + ENABLE_XCH):
            msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} **{COIN_NAME}** is not in our supported coins.')
            await msg.add_reaction(EMOJI_OK_BOX)
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
        # Check allowed coins
        tiponly_coins = serverinfo['tiponly'].split(",")
        if COIN_NAME == serverinfo['default_coin'].upper() or serverinfo['tiponly'].upper() == "ALLCOIN":
            pass
        elif COIN_NAME not in tiponly_coins:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} not in allowed coins set by server manager.')
            return
        # End of checking allowed coins

        if is_maintenance_coin(COIN_NAME):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
            return

        # Check flood of tip
        floodTip = await store.sql_get_countLastTip(str(ctx.author.id), config.floodTipDuration)
        if floodTip >= config.floodTip:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Cool down your tip or TX. or increase your amount next time.')
            await botLogChan.send('A user reached max. TX threshold. Currently halted: `.tip`')
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
        # End Check if maintenance

        # Get a random user in the guild, except bots. At least 3 members for random.
        has_last = False
        message_talker = None
        listMembers = None
        minimum_users = 3
        try:
            # Check random option
            if rand_option is None or rand_option.upper().startswith("ALL"):
                listMembers = [member for member in ctx.guild.members if member.bot == False]
            elif rand_option and rand_option.upper().startswith("ONLINE"):
                listMembers = [member for member in ctx.guild.members if member.bot == False and member.status != discord.Status.offline]
            elif rand_option and rand_option.upper().strip().startswith("LAST "):
                argument = rand_option.strip().split(" ")            
                if len(argument) == 2:
                    # try if the param is 1111u
                    num_user = argument[1].lower()
                    if 'u' in num_user or 'user' in num_user or 'users' in num_user or 'person' in num_user or 'people' in num_user:
                        num_user = num_user.replace("people", "")
                        num_user = num_user.replace("person", "")
                        num_user = num_user.replace("users", "")
                        num_user = num_user.replace("user", "")
                        num_user = num_user.replace("u", "")
                        try:
                            num_user = int(num_user)
                            if num_user < minimum_users:
                                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Number of random users cannot below **{minimum_users}**.')
                                return
                            elif num_user >= minimum_users:
                                message_talker = await store.sql_get_messages(str(ctx.message.guild.id), str(ctx.channel.id), 0, num_user + 1)
                                if ctx.author.id in message_talker:
                                    message_talker.remove(ctx.author.id)
                                else:
                                    # remove the last one
                                    message_talker.pop()
                                if len(message_talker) < minimum_users:
                                    await ctx.message.add_reaction(EMOJI_ERROR)
                                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} There is not sufficient user to count for random tip.')
                                    return
                                elif len(message_talker) < num_user:
                                    try:
                                        await ctx.message.add_reaction(EMOJI_INFORMATION)
                                        await ctx.send(f'{EMOJI_INFORMATION} {ctx.author.mention} I could not find sufficient talkers up to **{num_user}**. I found only **{len(message_talker)}**'
                                                       f' and will random to one of those **{len(message_talker)}** users.')
                                    except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                        # No need to tip if failed to message
                                        await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                        # Let it still go through
                                        #return
                            has_last = True
                        except ValueError:
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid param after **LAST** for random tip. Support only *LAST* **X**u right now.')
                            return
                    else:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid param after **LAST** for random tip. Support only *LAST* **X**u right now.')
                        return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid param after **LAST** for random tip. Support only *LAST* **X**u right now.')
                    return
            if has_last == False and listMembers and len(listMembers) >= minimum_users:
                rand_user = random.choice(listMembers)
                max_loop = 0
                while True:
                    if rand_user != ctx.author and rand_user.bot == False:
                        break
                    else:
                        rand_user = random.choice(listMembers)
                    max_loop += 1
                    if max_loop >= 5:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} Please try again, maybe guild doesnot have so many users.')
                        return
                        break
            elif has_last == True and message_talker and len(message_talker) >= minimum_users:
                rand_user_id = random.choice(message_talker)
                max_loop = 0
                while True:
                    rand_user = self.bot.get_user(rand_user_id)
                    if rand_user and rand_user != ctx.author and rand_user.bot == False and rand_user in ctx.guild.members:
                        break
                    else:
                        rand_user_id = random.choice(message_talker)
                        rand_user = self.bot.get_user(rand_user_id)
                    max_loop += 1
                    if max_loop >= 10:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} Please try again, maybe guild doesnot have so many users.')
                        return
                        break
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} not enough member for random tip.')
                return
        except Exception as e:
            await logchanbot(traceback.format_exc())
            return
            
        notifyList = await store.sql_get_tipnotify()

        if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            real_amount = float(amount)
            token_info = await store.get_token_info(COIN_NAME)
            MinTx = token_info['real_min_tip']
            MaxTX = token_info['real_max_tip']
        else:
            real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["XMR", "TRTL", "BCN", "NANO", "XCH"] else float(amount)
            MinTx = get_min_mv_amount(COIN_NAME)
            MaxTX = get_max_mv_amount(COIN_NAME)

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

        if real_amount > MaxTX:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than '
                           f'{num_format_coin(MaxTX, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return
        elif real_amount < MinTx:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than '
                           f'{num_format_coin(MinTx, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return
        elif real_amount > actual_balance:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to do a random tip of '
                           f'{num_format_coin(real_amount, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return

        # add queue also randtip
        if ctx.author.id not in TX_IN_PROCESS:
            TX_IN_PROCESS.append(ctx.author.id)
        else:
            await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
            msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

        print('random get user: {}/{}'.format(rand_user.name, rand_user.id))

        tip = None
        user_to = await store.sql_get_userwallet(str(rand_user.id), COIN_NAME)
        if user_to is None:
            if COIN_NAME in ENABLE_COIN_ERC:
                coin_family = "ERC-20"
                w = await create_address_eth()
                wallet = await store.sql_register_user(str(rand_user.id), COIN_NAME, SERVER_BOT, 0, w)
            elif COIN_NAME in ENABLE_COIN_TRC:
                coin_family = "TRC-20"
                result = await store.create_address_trx()
                wallet = await store.sql_register_user(str(rand_user.id), COIN_NAME, SERVER_BOT, 0, result)
            else:
                coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                wallet = await store.sql_register_user(str(rand_user.id), COIN_NAME, SERVER_BOT, 0)
            user_to = await store.sql_get_userwallet(str(rand_user.id), COIN_NAME)

        if coin_family in ["TRTL", "BCN"]:
            tip = await store.sql_mv_cn_single(str(ctx.author.id), str(rand_user.id), real_amount, 'RANDTIP', COIN_NAME)
        elif coin_family == "XMR":
            tip = await store.sql_mv_xmr_single(str(ctx.author.id), str(rand_user.id), real_amount, COIN_NAME, "RANDTIP")
        elif coin_family == "XCH":
            tip = await store.sql_mv_xch_single(str(ctx.author.id), str(rand_user.id), real_amount, COIN_NAME, "RANDTIP")
        elif coin_family == "NANO":
            tip = await store.sql_mv_nano_single(str(ctx.author.id), str(rand_user.id), real_amount, COIN_NAME, "RANDTIP")
        elif coin_family == "DOGE":
            tip = await store.sql_mv_doge_single(str(ctx.author.id), str(rand_user.id), real_amount, COIN_NAME, "RANDTIP")
        elif coin_family == "ERC-20":
            tip = await store.sql_mv_erc_single(str(ctx.author.id), str(rand_user.id), real_amount, COIN_NAME, "RANDTIP", token_info['contract'])
        elif coin_family == "TRC-20":
            tip = await store.sql_mv_trx_single(str(ctx.author.id), str(rand_user.id), real_amount, COIN_NAME, "RANDTIP", token_info['contract'])
        # remove queue from randtip
        if ctx.author.id in TX_IN_PROCESS:
            TX_IN_PROCESS.remove(ctx.author.id)

        if tip:
            # Update tipstat
            try:
                update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
                update_tipstat = await store.sql_user_get_tipstat(str(rand_user.id), COIN_NAME, True, SERVER_BOT)
            except Exception as e:
                await logchanbot(traceback.format_exc())

            randtip_public_respond = False
            # tipper shall always get DM. Ignore notifyList
            try:
                await ctx.author.send(
                    f'{EMOJI_ARROW_RIGHTHOOK} {rand_user.name}#{rand_user.discriminator} got your random tip of {num_format_coin(real_amount, COIN_NAME)} '
                    f'{COIN_NAME} in server `{ctx.guild.name}`')
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                await store.sql_toggle_tipnotify(str(ctx.author.id), "OFF")
            if str(rand_user.id) not in notifyList:
                try:
                    await rand_user.send(
                        f'{EMOJI_MONEYFACE} You got a random tip of {num_format_coin(real_amount, COIN_NAME)} '
                        f'{COIN_NAME} from {ctx.author.name}#{ctx.author.discriminator} in server `{ctx.guild.name}`\n'
                        f'{NOTIFICATION_OFF_CMD}')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    await store.sql_toggle_tipnotify(str(user.id), "OFF")
            try:
                # try message in public also
                msg = await ctx.message.reply(
                                f'{rand_user.name}#{rand_user.discriminator} got a random tip of {num_format_coin(real_amount, COIN_NAME)} '
                                f'{COIN_NAME} from {ctx.author.name}#{ctx.author.discriminator}')
                await msg.add_reaction(EMOJI_OK_BOX)
                randtip_public_respond = True
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                pass
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if randtip_public_respond == False and serverinfo and 'botchan' in serverinfo and serverinfo['botchan']:
                # It has bot channel, let it post in bot channel
                try:
                    bot_channel = self.bot.get_channel(int(serverinfo['botchan']))
                    msg = await bot_channel.send(
                                f'{rand_user.name}#{rand_user.discriminator} got a random tip of {num_format_coin(real_amount, COIN_NAME)} '
                                f'{COIN_NAME} from {ctx.author.name}#{ctx.author.discriminator} in {ctx.channel.mention}')
                    await msg.add_reaction(EMOJI_OK_BOX)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
            await ctx.message.add_reaction(EMOJI_OK_BOX)
            return


def setup(bot):
    bot.add_cog(TipRandomTip(bot))