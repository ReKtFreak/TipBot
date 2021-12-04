import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class TipFreeTip(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def bot_log(self):
        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)


    ## TODO: Improve this usage.
    @commands.command(
        usage="freetip <amount> <coin> <duration>", 
        description="Distribute free tips to re-actors."
    )
    async def freetip(
        self, 
        ctx, 
        amount: str, 
        coin: str, 
        duration: str='60s', 
        *, 
        comment: str=None
    ):
        await self.bot_log()
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

        amount = amount.replace(",", "")
        try:
            amount = Decimal(amount)
        except ValueError:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
            return

        def hms_to_seconds(time_string):
            duration_in_second = 0
            try:
                time_string = time_string.replace("hours", "h")
                time_string = time_string.replace("hour", "h")
                time_string = time_string.replace("hrs", "h")
                time_string = time_string.replace("hr", "h")

                time_string = time_string.replace("minutes", "mn")
                time_string = time_string.replace("mns", "mn")
                time_string = time_string.replace("mins", "mn")
                time_string = time_string.replace("min", "mn")
                time_string = time_string.replace("m", "mn")
                mult = {'h': 60*60, 'mn': 60}
                duration_in_second = sum(int(num) * mult.get(val, 1) for num, val in re.findall('(\d+)(\w+)', time_string))
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
            return duration_in_second

        duration_s = 0
        try:
            duration_s = hms_to_seconds(duration)
        except Exception as e:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid duration.')
            return

        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send(f'{EMOJI_RED_NO} This command can not be in private.')
            return

        if duration_s == 0:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid time given. Please use time format: XXs')
            return
        elif duration_s < config.freetip.duration_min or duration_s > config.freetip.duration_max:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid duration. Please use between {str(config.freetip.duration_min)}s to {str(config.freetip.duration_max)}s.')
            return

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        COIN_NAME = coin.upper()
        print("COIN_NAME: " + COIN_NAME)

        # TRTL discord
        if ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
            return

        if COIN_NAME not in (ENABLE_COIN + ENABLE_XMR + ENABLE_COIN_DOGE + ENABLE_COIN_NANO + ENABLE_COIN_ERC + ENABLE_COIN_TRC + ENABLE_XCH):
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
            await self.botLogChan.send('A user reached max. TX threshold. Currently halted: `.tip`')
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

        notifyList = await store.sql_get_tipnotify()
        if coin_family == "ERC-20" or coin_family == "TRC-20":
            token_info = await store.get_token_info(COIN_NAME)
            real_amount = float(amount)
            MinTx = token_info['real_min_tip']
            MaxTX = token_info['real_max_tip']
        else:
            real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["XMR", "TRTL", "BCN", "NANO", "XCH"] else float(amount)
            MinTx = get_min_mv_amount(COIN_NAME)
            MaxTX = get_max_mv_amount(COIN_NAME)
        if comment and len(comment) > 0:
            MinTx = MinTx * config.freetip.with_comment_x_amount
            MaxTX = MaxTX * config.freetip.with_comment_x_amount

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
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to do a free tip of '
                           f'{num_format_coin(real_amount, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return

        attend_list_id = []
        attend_list_names = []
        ts = timestamp=datetime.utcnow()

        if ctx.author.id not in TX_IN_PROCESS:
            TX_IN_PROCESS.append(ctx.author.id)
        try:
            embed = discord.Embed(title=f"Free Tip appears {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}", description=f"Re-act {EMOJI_PARTY} to collect", timestamp=ts, color=0x00ff00)
            msg = await ctx.message.reply(embed=embed)
            await msg.add_reaction(EMOJI_PARTY)
            if comment and len(comment) > 0:
                embed.add_field(name="Comment", value=comment, inline=False)
            embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, timeout: {seconds_str(duration_s)}")
            await msg.edit(embed=embed)
            await ctx.message.add_reaction(EMOJI_OK_HAND)
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            if ctx.author.id in TX_IN_PROCESS:
                TX_IN_PROCESS.remove(ctx.author.id)
            await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
            return
        def check(reaction, user):
            return user != ctx.author and user.bot == False and reaction.message.author == self.bot.user \
    and reaction.message.id == msg.id and str(reaction.emoji) == EMOJI_PARTY
        
        if comment and len(comment) > 0:
            # multiple free tip
            while True:
                start_time = int(time.time())
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=duration_s, check=check)
                except asyncio.TimeoutError:
                    if ctx.author.id in TX_IN_PROCESS:
                        TX_IN_PROCESS.remove(ctx.author.id)
                    if len(attend_list_id) == 0:
                        embed = discord.Embed(title=f"Free Tip appears {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}", description=f"Already expired", timestamp=ts, color=0x00ff00)
                        embed.add_field(name="Comment", value=comment, inline=False)
                        embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, and no one collected!")
                        await msg.edit(embed=embed)
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
                    break

                if str(reaction.emoji) == EMOJI_PARTY and user.id not in attend_list_id:
                    attend_list_id.append(user.id)
                    attend_list_names.append('{}#{}'.format(user.name, user.discriminator))
                    embed = discord.Embed(title=f"Free Tip appears {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}", description=f"Re-act {EMOJI_PARTY} to collect", timestamp=ts, color=0x00ff00)
                    embed.add_field(name="Comment", value=comment, inline=False)
                    embed.add_field(name="Attendees", value=", ".join(attend_list_names), inline=False)
                    embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, timeout: {seconds_str(duration_s)}")
                    await msg.edit(embed=embed)
                    duration_s -= int(time.time()) - start_time
                    if duration_s <= 1:
                        break

            # re-check balance
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

            if real_amount > actual_balance:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to do a free tip of '
                               f'{num_format_coin(real_amount, COIN_NAME)} '
                               f'{COIN_NAME}.')
                return
            # end of re-check balance

            # Multiple tip here
            notifyList = await store.sql_get_tipnotify()

            if len(attend_list_id) == 0:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} divided by 0!!!')
                return

            amountDiv = int(round(real_amount / len(attend_list_id), 2))  # cut 2 decimal only
            if coin_family == "DOGE" or coin_family == "ERC-20" or coin_family == "TRC-20":
                amountDiv = round(real_amount / len(attend_list_id), 4)

            tip = None
            try:
                if coin_family in ["TRTL", "BCN"]:
                    tip = await store.sql_mv_cn_multiple(str(ctx.author.id), amountDiv, attend_list_id, 'TIPALL', COIN_NAME)
                elif coin_family == "XMR":
                    tip = await store.sql_mv_xmr_multiple(str(ctx.author.id), attend_list_id, amountDiv, COIN_NAME, "TIPALL")
                elif coin_family == "XCH":
                    tip = await store.sql_mv_xch_multiple(str(ctx.author.id), attend_list_id, amountDiv, COIN_NAME, "TIPALL")
                elif coin_family == "NANO":
                    tip = await store.sql_mv_nano_multiple(str(ctx.author.id), attend_list_id, amountDiv, COIN_NAME, "TIPALL")
                elif coin_family == "DOGE":
                    tip = await store.sql_mv_doge_multiple(str(ctx.author.id), attend_list_id, amountDiv, COIN_NAME, "TIPALL")
                elif coin_family == "ERC-20":
                    tip = await store.sql_mv_erc_multiple(str(ctx.author.id), attend_list_id, amountDiv, COIN_NAME, "TIPALL", token_info['contract'])
                elif coin_family == "TRC-20":
                    tip = await store.sql_mv_trx_multiple(str(ctx.author.id), attend_list_id, amountDiv, COIN_NAME, "TIPALL", token_info['contract'])
            except Exception as e:
                await logchanbot(traceback.format_exc())

            # remove queue from tipall
            if ctx.author.id in TX_IN_PROCESS:
                TX_IN_PROCESS.remove(ctx.author.id)
            if tip:
                # Update tipstat
                try:
                    update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                tipAmount = num_format_coin(real_amount, COIN_NAME)
                ActualSpend_str = num_format_coin(amountDiv * len(attend_list_id), COIN_NAME)
                amountDiv_str = num_format_coin(amountDiv, COIN_NAME)
                if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    await ctx.message.add_reaction(TOKEN_EMOJI)
                else:
                    await ctx.message.add_reaction(get_emoji(COIN_NAME))
                # tipper shall always get DM. Ignore notifyList
                try:
                    await ctx.author.send(
                        f'{EMOJI_ARROW_RIGHTHOOK} Free Tip of {tipAmount} '
                        f'{COIN_NAME} '
                        f'was collected by ({len(attend_list_id)}) members in server `{ctx.guild.name}`.\n'
                        f'Each member got: `{amountDiv_str} {COIN_NAME}`\n'
                        f'Actual spending: `{ActualSpend_str} {COIN_NAME}`')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    await store.sql_toggle_tipnotify(str(ctx.author.id), "OFF")
                numMsg = 0
                for member_id in attend_list_id:
                    member = self.bot.get_user(member_id)
                    if ctx.author.id != member.id and member.id != self.bot.user.id:
                        if str(member.id) not in notifyList:
                            # random user to DM
                            dm_user = bool(random.getrandbits(1)) if len(attend_list_id) > config.tipallMax_LimitDM else True
                            if dm_user:
                                try:
                                    await member.send(
                                        f'{EMOJI_MONEYFACE} You collected a free tip of {amountDiv_str} '
                                        f'{COIN_NAME} from {ctx.author.name}#{ctx.author.discriminator} in server `{ctx.guild.name}` #{ctx.channel.name}\n'
                                        f'{NOTIFICATION_OFF_CMD}')
                                    numMsg += 1
                                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                    await store.sql_toggle_tipnotify(str(member.id), "OFF")
                    if numMsg >= config.tipallMax_LimitDM:
                        # stop DM if reaches
                        break
                # Edit embed
                try:
                    embed = discord.Embed(title=f"Free Tip appears {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}", description=f"Re-act {EMOJI_PARTY} to collect", timestamp=ts, color=0x00ff00)
                    embed.add_field(name="Comment", value=comment, inline=False)
                    embed.add_field(name="Attendees", value=", ".join(attend_list_names), inline=False)
                    embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, completed! Collected by {len(attend_list_id)} member(s)")
                    await msg.edit(embed=embed)
                    await msg.add_reaction(EMOJI_OK_BOX)
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                return
        else:
            # single free tip
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=duration_s, check=check)
            except asyncio.TimeoutError:
                if ctx.author.id in TX_IN_PROCESS:
                    TX_IN_PROCESS.remove(ctx.author.id)
                embed = discord.Embed(title=f"Free Tip appears {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}", description=f"Already expired", timestamp=ts, color=0x00ff00)
                embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, and no one collected!")
                await msg.edit(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            if str(reaction.emoji) == EMOJI_PARTY:
                # re-check balance
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

                if real_amount > actual_balance:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to do a free tip of '
                                   f'{num_format_coin(real_amount, COIN_NAME)} '
                                   f'{COIN_NAME}.')
                    return
                # end of re-check balance

                tip = None
                user_to = await store.sql_get_userwallet(str(user.id), COIN_NAME)
                if user_to is None:
                    if COIN_NAME in ENABLE_COIN_ERC:
                        w = await create_address_eth()
                        userregister = await store.sql_register_user(str(user.id), COIN_NAME, SERVER_BOT, 0, w)
                    elif COIN_NAME in ENABLE_COIN_TRC:
                        result = await store.create_address_trx()
                        userregister = await store.sql_register_user(str(user.id), COIN_NAME, SERVER_BOT, 0, result)
                    else:
                        userregister = await store.sql_register_user(str(user.id), COIN_NAME, SERVER_BOT, 0)
                    user_to = await store.sql_get_userwallet(str(user.id), COIN_NAME)
                if coin_family in ["TRTL", "BCN"]:
                    tip = await store.sql_mv_cn_single(str(ctx.author.id), str(user.id), real_amount, 'FREETIP', COIN_NAME)
                elif coin_family == "XMR":
                    tip = await store.sql_mv_xmr_single(str(ctx.author.id), str(user.id), real_amount, COIN_NAME, "FREETIP")
                elif coin_family == "XCH":
                    tip = await store.sql_mv_xch_single(str(ctx.author.id), str(user.id), real_amount, COIN_NAME, "FREETIP")
                elif coin_family == "NANO":
                    tip = await store.sql_mv_nano_single(str(ctx.author.id), str(user.id), real_amount, COIN_NAME, "FREETIP")
                elif coin_family == "DOGE":
                    tip = await store.sql_mv_doge_single(str(ctx.author.id), str(user.id), real_amount, COIN_NAME, "FREETIP")
                elif coin_family == "ERC-20":
                    tip = await store.sql_mv_erc_single(str(ctx.author.id), str(user.id), real_amount, COIN_NAME, "FREETIP", token_info['contract'])
                elif coin_family == "TRC-20":
                    tip = await store.sql_mv_trx_single(str(ctx.author.id), str(user.id), real_amount, COIN_NAME, "FREETIP", token_info['contract'])
                # remove queue from freetip
                if ctx.author.id in TX_IN_PROCESS:
                    TX_IN_PROCESS.remove(ctx.author.id)

                if tip:
                    # Update tipstat
                    try:
                        update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
                        update_tipstat = await store.sql_user_get_tipstat(str(user.id), COIN_NAME, True, SERVER_BOT)
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                    embed = discord.Embed(title=f"Free Tip appeared {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}", description=f"Already collected", color=0x00ff00)
                    embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, collected by: {user.name}#{user.discriminator}")
                    await msg.edit(embed=embed)
                    # tipper shall always get DM. Ignore notifyList
                    try:
                        await ctx.author.send(
                            f'{EMOJI_ARROW_RIGHTHOOK} Tip of {num_format_coin(real_amount, COIN_NAME)} '
                            f'{COIN_NAME} '
                            f'has been collected by {user.name}#{user.discriminator} in server `{ctx.guild.name}`')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        await store.sql_toggle_tipnotify(str(ctx.author.id), "OFF")
                    if str(user.id) not in notifyList:
                        try:
                            await user.send(
                                f'{EMOJI_MONEYFACE} You had collected a tip of {num_format_coin(real_amount, COIN_NAME)} '
                                f'{COIN_NAME} from {ctx.author.name}#{ctx.author.discriminator} in server `{ctx.guild.name}`\n'
                                f'{NOTIFICATION_OFF_CMD}')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            await store.sql_toggle_tipnotify(str(user.id), "OFF")
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return


def setup(bot):
    bot.add_cog(TipFreeTip(bot))