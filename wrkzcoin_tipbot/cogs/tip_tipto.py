import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class TipTipTo(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    ## TODO: Improve this usage.
    @commands.command(usage="tipto <amount> <coin> <to user@xxx>", description="Tip to user(s) in telegram or reddit.")
    async def tipto(self, ctx, amount: str, coin: str, to_user: str):
        # check if bot is going to restart
        if IS_RESTARTING:
            await ctx.message.add_reaction(EMOJI_REFRESH)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
            return
        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'tipto')
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

        botLogChan = bot.get_channel(LOG_CHAN)
        amount = amount.replace(",", "")
        try:
            amount = Decimal(amount)
        except Exception as e:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
            return

        COIN_NAME = coin.upper()
        if COIN_NAME not in (ENABLE_COIN + ENABLE_XMR + ENABLE_COIN_DOGE + ENABLE_COIN_NANO + ENABLE_COIN_ERC + ENABLE_COIN_TRC + ENABLE_XCH):
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.author.send(f'{COIN_NAME} is not in TipBot.')
            return
        if COIN_NAME not in ENABLE_TIPTO:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.author.send(f'{COIN_NAME} is not in this function of TipTo.')
            return

        # TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
            return

        # offline can not tipto
        try:
            if ctx.author.status == discord.Status.offline:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Offline status cannot use this.')
                return
        except Exception as e:
            traceback.print_exc(file=sys.stdout)

        try:
            if not is_coin_tipable(COIN_NAME):
                msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} TIPPING is currently disable for {COIN_NAME}.')
                await msg.add_reaction(EMOJI_OK_BOX)
                return

            if is_maintenance_coin(COIN_NAME):
                await ctx.message.add_reaction(EMOJI_MAINTENANCE)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
                return

            if COIN_NAME in ENABLE_COIN_ERC:
                coin_family = "ERC-20"
            elif COIN_NAME in ENABLE_COIN_TRC:
                coin_family = "TRC-20"
            else:
                coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")

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

            if coin_family == "ERC-20" or coin_family == "TRC-20":
                real_amount = float(amount)
                token_info = await store.get_token_info(COIN_NAME)
                MinTx = token_info['real_min_tip']
                MaxTX = token_info['real_max_tip']
                decimal_pts = token_info['token_decimal']
            else:
                real_amount = int(Decimal(amount) * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
                MinTx = get_min_mv_amount(COIN_NAME)
                MaxTX = get_max_mv_amount(COIN_NAME)
                decimal_pts = int(math.log10(get_decimal(COIN_NAME)))
            if real_amount > MaxTX:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than '
                               f'{num_format_coin(MaxTX, COIN_NAME)} '
                               f'{COIN_NAME}.')
                return
            elif real_amount > actual_balance:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to transfer tip of '
                               f'{num_format_coin(real_amount, COIN_NAME)} '
                               f'{COIN_NAME} to {to_user}.')
                return
            elif real_amount < MinTx:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than '
                               f'{num_format_coin(MinTx, COIN_NAME)} '
                               f'{COIN_NAME}.')
                return

            if '@' not in to_user:
                msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You need to have a correct format to send to. Example: username@telegram')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            else:
                userid = to_user.split("@")[0]
                serverto = to_user.split("@")[1].upper()
                if serverto not in ["TELEGRAM", "REDDIT"]:
                    msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} Unsupported or unknown **{serverto}**')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                else:
                    # Find user in DB
                    try:
                        to_teleuser = await store.sql_get_userwallet(userid, COIN_NAME, serverto)
                        if to_teleuser is None:
                            msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} User **{userid}** is not in our DB for **{serverto}**')
                            await msg.add_reaction(EMOJI_OK_BOX)
                            return
                        else:
                            # We found it
                            # Let's send
                            tipto = await store.sql_tipto_crossing(COIN_NAME, str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator), 
                                                                   SERVER_BOT, userid, userid, serverto, real_amount, decimal_pts)
                            if tipto:
                                await logchanbot('[Discord] {}#{} tipto {}{} to **{}**'.format(ctx.author.name, ctx.author.discriminator, num_format_coin(real_amount, COIN_NAME), COIN_NAME, to_user))
                                msg = await ctx.send(f'{EMOJI_CHECK} {ctx.author.mention} Successfully transfer {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME} to **{to_user}**.')
                                await msg.add_reaction(EMOJI_OK_BOX)
                                # Update tipstat
                                try:
                                    update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
                                    update_tipstat = await store.sql_user_get_tipstat(userid, COIN_NAME, True, serverto)
                                except Exception as e:
                                    await logchanbot(traceback.format_exc())
                            else:
                                msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} Internal error for tipto {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME} to **{to_user}**.')
                                await msg.add_reaction(EMOJI_OK_BOX)
                                await logchanbot(f'{EMOJI_ERROR} {ctx.author.name}#{ctx.author.discriminator} Internal error for tipto {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME} to **{to_user}**.')
                            return
                    except Exception as e:
                        print(traceback.format_exc())
                        await logchanbot(traceback.format_exc())
        except Exception as e:
            traceback.print_exc(file=sys.stdout)


def setup(bot):
    bot.add_cog(TipTipTo(bot))