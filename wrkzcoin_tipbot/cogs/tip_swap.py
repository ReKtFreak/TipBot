import sys, traceback
import time, timeago
import disnake
from disnake.ext import commands

from config import config
from Bot import *

class TipSwap(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def bot_log(self):
        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)


    @commands.command(
        usage="swap <amount> <from coin> <to coin>", 
        description="Swap supported coin / token."
    )
    async def swap(
        self, 
        ctx, 
        amount: str, 
        coin_from: str, 
        coin_to: str
    ):
        await self.bot_log()
        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'swap')
        if account_lock:
            await ctx.message.add_reaction(EMOJI_LOCKED) 
            await ctx.reply(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
            return
        # end of check if account locked

        # Check if tx in progress
        if ctx.author.id in TX_IN_PROCESS:
            await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
            msg = await ctx.reply(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

        # check if bot is going to restart
        if IS_RESTARTING:
            await ctx.message.add_reaction(EMOJI_REFRESH)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
            return

        COIN_NAME_FROM = coin_from.upper()
        COIN_NAME_TO = coin_to.upper()
        if is_maintenance_coin(COIN_NAME_FROM):	
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)	
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME_FROM} in maintenance.')	
            return

        if is_maintenance_coin(COIN_NAME_TO):	
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)	
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME_TO} in maintenance.')	
            return
        
        PAIR_NAME = COIN_NAME_FROM + "-" + COIN_NAME_TO
        if PAIR_NAME not in SWAP_PAIR:
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {PAIR_NAME} is not available.')	
            return

        amount = amount.replace(",", "")	
        try:
            if COIN_NAME_FROM == "WRKZ" or COIN_NAME_TO == "WRKZ":
                amount = float("%.2f" % float(amount))
            else:
                amount = float("%.4f" % float(amount))
        except ValueError:	
            await ctx.message.add_reaction(EMOJI_ERROR)	
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')	
            return

        try:
            SwapCount = await store.sql_swap_count_user(str(ctx.author.id), config.swap_token_setting.allow_second)
            if SwapCount >= config.swap_token_setting.allow_for:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Reduce your swapping in the last **{seconds_str(config.swap_token_setting.allow_second)}**.')
                await logchanbot(f'A user {ctx.author.name}#{ctx.author.discriminator} reached max. swap threshold.')
                return
            # End of Check swap of tip

            real_from_amount = amount
            real_to_amount = amount * SWAP_PAIR[PAIR_NAME]

            if COIN_NAME_FROM in ENABLE_COIN_ERC:
                coin_family = "ERC-20"
                token_info = await store.get_token_info(COIN_NAME_FROM)
                from_decimal = token_info['token_decimal']
                Min_Tip = token_info['real_min_tip']
                Max_Tip = token_info['real_max_tip']
            elif COIN_NAME_FROM in ENABLE_COIN_TRC:
                coin_family = "TRC-20"
                token_info = await store.get_token_info(COIN_NAME_FROM)
                from_decimal = token_info['token_decimal']
                Min_Tip = token_info['real_min_tip']
                Max_Tip = token_info['real_max_tip']
            else:
                coin_family = getattr(getattr(config,"daemon"+COIN_NAME_FROM),"coin_family","TRTL")
                from_decimal = int(math.log10(get_decimal(COIN_NAME_FROM)))
                Min_Tip = get_min_mv_amount(COIN_NAME_FROM) / 10**from_decimal
                Max_Tip = get_max_mv_amount(COIN_NAME_FROM) / 10**from_decimal * 5 # Increase x5 for swap

            if COIN_NAME_FROM == "WRKZ" or COIN_NAME_TO == "WRKZ":
                Min_Tip_str = "{:,.2f}".format(Min_Tip)
                Max_Tip_str = "{:,.2f}".format(Max_Tip)
            else:
                Min_Tip_str = "{:,.4f}".format(Min_Tip)
                Max_Tip_str = "{:,.4f}".format(Max_Tip)
            if COIN_NAME_TO in ENABLE_COIN_ERC:
                coin_family = "ERC-20"
                token_info = await store.get_token_info(COIN_NAME_TO)
                to_decimal = token_info['token_decimal']
            elif COIN_NAME_TO in ENABLE_COIN_TRC:
                coin_family = "TRC-20"
                token_info = await store.get_token_info(COIN_NAME_TO)
                to_decimal = token_info['token_decimal']
            else:
                coin_family = getattr(getattr(config,"daemon"+COIN_NAME_TO),"coin_family","TRTL")
                to_decimal = int(math.log10(get_decimal(COIN_NAME_TO)))
                

            userdata_balance = await store.sql_user_balance(str(ctx.author.id), COIN_NAME_FROM)
            xfer_in = 0
            if COIN_NAME_FROM not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                xfer_in = await store.sql_user_balance_get_xfer_in(str(ctx.author.id), COIN_NAME_FROM)
            if COIN_NAME_FROM in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
            elif COIN_NAME_FROM in ENABLE_COIN_NANO:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
                actual_balance = round(actual_balance / get_decimal(COIN_NAME_FROM), 6) * get_decimal(COIN_NAME_FROM)
            else:
                actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
            
            if COIN_NAME_FROM in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                real_actual_balance = actual_balance
            else:
                real_actual_balance = actual_balance / 10**from_decimal

            if real_from_amount > Max_Tip:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Swap cannot be bigger than '
                               f'{Max_Tip_str} {COIN_NAME_FROM}.')
                return
            elif real_from_amount < Min_Tip:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Swap cannot be smaller than '
                               f'{Min_Tip_str} {COIN_NAME_FROM}.')
                return
            elif real_from_amount > real_actual_balance:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to do a swap of '
                               f'{num_format_coin(real_from_amount if COIN_NAME_FROM in ENABLE_COIN_ERC+ENABLE_COIN_TRC else real_from_amount*10**from_decimal, COIN_NAME_FROM)} '
                               f'{COIN_NAME_FROM}. Having {num_format_coin(real_actual_balance if COIN_NAME_FROM in ENABLE_COIN_ERC+ENABLE_COIN_TRC else real_from_amount*10**from_decimal, COIN_NAME_FROM)}{COIN_NAME_FROM}.')
                return

            swapit = None	
            try:	
                if ctx.author.id not in TX_IN_PROCESS:	
                    TX_IN_PROCESS.append(ctx.author.id)	
                    swapit = await store.sql_swap_balance_token(COIN_NAME_FROM, real_from_amount, from_decimal, COIN_NAME_TO,
                                                                real_to_amount, to_decimal, str(ctx.author.id), "{}#{}".format(ctx.author.name, ctx.author.discriminator),
                                                                SERVER_BOT)
                    TX_IN_PROCESS.remove(ctx.author.id)	
                else:	
                    await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)	
                    msg = await ctx.reply(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')	
                    await msg.add_reaction(EMOJI_OK_BOX)	
                    return	
            except Exception as e:	
                await logchanbot(traceback.format_exc())	
            if swapit:
                real_from_str = "{:,.4f}".format(real_from_amount)
                real_to_str = "{:,.4f}".format(real_to_amount)
                await ctx.message.add_reaction(EMOJI_OK_BOX)	
                await ctx.author.send(
                        f'{EMOJI_ARROW_RIGHTHOOK} You swapped {real_from_amount} '	
                        f'{COIN_NAME_FROM} to **{real_to_amount} {COIN_NAME_TO}**.')
                await logchanbot(f'[Discord] User {ctx.author.name}#{ctx.author.discriminator} swapped {real_from_amount} '	
                                 f'{COIN_NAME_FROM} to **{real_to_amount} {COIN_NAME_TO}**.')
                return	
            else:	
                await ctx.message.add_reaction(EMOJI_ERROR)	
                await self.botLogChan.send(f'A user call failed to swap {COIN_NAME_FROM} to {COIN_NAME_TO}')	
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Internal error during swap.')	
                return
        except Exception as e:
            traceback.print_exc(file=sys.stdout)


def setup(bot):
    bot.add_cog(TipSwap(bot))