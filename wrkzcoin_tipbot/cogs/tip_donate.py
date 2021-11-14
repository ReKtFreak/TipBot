import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class TipDonate(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(
        usage="donate <amount> <coin>", 
        description="Donate amount coin to TipBot dev."
    )
    async def donate(
        self, 
        ctx, 
        amount: str, 
        coin: str=None
    ):
        # check if bot is going to restart
        if IS_RESTARTING:
            await ctx.message.add_reaction(EMOJI_REFRESH)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
            return
        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'donate')
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
        donate_msg = ''
        if amount.upper() == "LIST":
            # if .donate list
            donate_list = await store.sql_get_donate_list()
            item_list = []
            embed = discord.Embed(title='Donation List', timestamp=datetime.utcnow())
            for key, value in donate_list.items():
                if value:
                    coin_value = num_format_coin(value, key.upper())+key.upper()
                    item_list.append(coin_value)
                    embed.add_field(name=key.upper(), value=num_format_coin(value, key.upper())+key.upper(), inline=True)
            embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
            if len(item_list) > 0:
                try:
                    await ctx.send(embed=embed)
                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                    msg_coins = ', '.join(item_list)
                    try:
                        await ctx.send(f'Thank you for checking. So far, we got donations:\n```{msg_coins}```')
                    except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                        return
            return

        amount = amount.replace(",", "")

        # Check flood of tip
        floodTip = await store.sql_get_countLastTip(str(ctx.author.id), config.floodTipDuration)
        if floodTip >= config.floodTip:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Cool down your tip or TX. or increase your amount next time.')
            await botLogChan.send('A user reached max. TX threshold. Currently halted: `.donate`')
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
        else:
            pass
        # End Check if maintenance

        try:
            amount = Decimal(amount)
        except ValueError:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
            return

        COIN_NAME = coin.upper()
        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
            real_amount = float(amount)
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
            real_amount = float(amount)
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
            real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else Decimal(amount)
        if is_maintenance_coin(COIN_NAME):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            await ctx.send(f'{EMOJI_RED_NO} {COIN_NAME} in maintenance.')
            return
     
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

        if real_amount > actual_balance:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to donate '
                           f'{num_format_coin(real_amount, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return

        donateTx = None
        try:
            if coin_family in ["TRTL", "BCN"]:
                donateTx = await store.sql_donate(str(ctx.author.id), get_donate_address(COIN_NAME), real_amount, COIN_NAME)
            elif coin_family == "XMR":
                donateTx = await store.sql_mv_xmr_single(str(ctx.author.id), 
                                                        get_donate_account_name(COIN_NAME), 
                                                        real_amount, COIN_NAME, "DONATE")
            elif coin_family == "XCH":
                donateTx = await store.sql_mv_xch_single(str(ctx.author.id), 
                                                        get_donate_account_name(COIN_NAME), 
                                                        real_amount, COIN_NAME, "DONATE")
            elif coin_family == "NANO":
                donateTx = await store.sql_mv_nano_single(str(ctx.author.id), 
                                                          get_donate_account_name(COIN_NAME), 
                                                          real_amount, COIN_NAME, "DONATE")
            elif coin_family == "DOGE":
                donateTx = await store.sql_mv_doge_single(str(ctx.author.id), get_donate_account_name(COIN_NAME), real_amount,
                                                          COIN_NAME, "DONATE")
            elif coin_family == "ERC-20":
                token_info = await store.get_token_info(COIN_NAME)
                donateTx = await store.sql_mv_erc_single(str(ctx.author.id), token_info['donate_name'], real_amount, COIN_NAME, "DONATE", token_info['contract'])
            elif coin_family == "TRC-20":
                token_info = await store.get_token_info(COIN_NAME)
                donateTx = await store.sql_mv_trx_single(str(ctx.author.id), token_info['donate_name'], real_amount, COIN_NAME, "DONATE", token_info['contract'])
        except Exception as e:
            await logchanbot(traceback.format_exc())
        if donateTx:
            # Update tipstat
            try:
                update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
            except Exception as e:
                await logchanbot(traceback.format_exc())

            await ctx.message.add_reaction(get_emoji(COIN_NAME))
            await botLogChan.send(f'{EMOJI_MONEYFACE} TipBot got donation: {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}')
            await ctx.author.send(
                                    f'{EMOJI_MONEYFACE} TipBot got donation: {num_format_coin(real_amount, COIN_NAME)} '
                                    f'{COIN_NAME} '
                                    f'\n'
                                    f'Thank you.')
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            msg = await ctx.send(f'{ctx.author.mention} Donating failed, try again. Thank you.')
            await botLogChan.send(f'A user failed to donate `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
            await msg.add_reaction(EMOJI_OK_BOX)
            # add to failed tx table
            await store.sql_add_failed_tx(COIN_NAME, str(ctx.author.id), ctx.author.name, real_amount, "DONATE")
            return


def setup(bot):
    bot.add_cog(TipDonate(bot))