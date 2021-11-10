import sys, traceback
import time, timeago
import discord
from discord.ext import commands
import json

from config import config
from Bot import *


class Balance(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(usage="balance <coin>", aliases=['bal'], description="Check your (coin's) tipjar's balance.")
    async def balance(self, ctx, coin: str = None):
        prefix = await get_guild_prefix(ctx)
        botLogChan = self.bot.get_channel(LOG_CHAN)
        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'balance')
        if account_lock:
            await ctx.message.add_reaction(EMOJI_LOCKED) 
            await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
            return
        # end of check if account locked

        PUBMSG = ctx.message.content.strip().split(" ")[-1].upper()

        # Get wallet status
        walletStatus = None
        COIN_NAME = None
        embed = discord.Embed(title='[ YOUR BALANCE LIST ]', timestamp=datetime.utcnow())
        num_coins = 0
        per_page = 25
        if (coin is None) or (PUBMSG == "PUB") or (PUBMSG == "PUBLIC") or (PUBMSG == "LIST"):
            table_data = [
                ['TICKER', 'Available', 'Tx']
            ]
            table_data_str = []
            for COIN_NAME in [coinItem.upper() for coinItem in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH]:
                if not is_maintenance_coin(COIN_NAME):
                    wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                    if wallet is None:
                        if COIN_NAME in ENABLE_COIN_ERC:
                            w = await create_address_eth()
                            userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
                        elif COIN_NAME in ENABLE_COIN_TRC:
                            result = await store.create_address_trx()
                            userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, result)
                        else:
                            userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
                        wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                    if wallet is None:
                        if coin: table_data.append([COIN_NAME, "N/A", "N/A"])
                        await botLogChan.send(f'A user call `{prefix}balance` failed with {COIN_NAME}')
                    else:
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
                        balance_actual = num_format_coin(actual_balance, COIN_NAME)
                        coinName = COIN_NAME
                        if actual_balance != 0:
                            if coin:
                                table_data.append([coinName, balance_actual, "YES" if is_coin_txable(COIN_NAME) else "NO"])
                            else:
                                if actual_balance > 0:
                                    table_data_str.append("{} {}".format(balance_actual, coinName))
                                    embed.add_field(name=COIN_NAME, value=balance_actual+" "+COIN_NAME, inline=True)
                                    num_coins += 1
                                    if num_coins > 0 and num_coins % per_page == 0:
                                        embed.set_footer(text="Continue... Page {}".format(int(num_coins/per_page)))
                                        try:
                                            msg = await ctx.author.send(embed=embed)
                                            await msg.add_reaction(EMOJI_OK_BOX)
                                            ## New embed
                                            embed = discord.Embed(title='[ YOUR BALANCE LIST CONTINUE - {}]'.format(int(num_coins/per_page+1)), timestamp=datetime.utcnow())
                                        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                            await ctx.add_reaction(EMOJI_ZIPPED_MOUTH)
                                            break
                                            return
                                    
                        pass
                else:
                    if coin: table_data.append([COIN_NAME, "***", "***"])
            table = AsciiTable(table_data)
            # table.inner_column_border = False
            # table.outer_border = False
            table.padding_left = 0
            table.padding_right = 0
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            if coin is None:
                # table_data_str = ", ".join(table_data_str)
                embed.add_field(name='Related commands', value=f'`{prefix}balance TICKER` or `{prefix}deposit TICKER` or `{prefix}balance LIST`', inline=False)
                if num_coins > 0 and num_coins / per_page > 1:
                    embed.set_footer(text="Last Page {}".format(int(np.ceil(num_coins/per_page))))
                try:
                    msg = await ctx.author.send(embed=embed)
                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                    return
            else:
                if PUBMSG.upper() == "PUB" or PUBMSG.upper() == "PUBLIC":
                    msg = await ctx.message.reply('**[ BALANCE LIST ]**\n'
                                    f'```{table.table}```'
                                    f'Related command: `{prefix}balance TICKER` or `{prefix}deposit TICKER`\n`***`: On Maintenance\n')
                else:
                    msg = await ctx.author.send('**[ BALANCE LIST ]**\n'
                                    f'```{table.table}```'
                                    f'Related command: `{prefix}balance TICKER` or `{prefix}deposit TICKER`\n`***`: On Maintenance\n'
                                    f'{get_notice_txt(COIN_NAME)}')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        else:
            COIN_NAME = coin.upper()

        if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**!')
            return

        if is_maintenance_coin(COIN_NAME) and ctx.author.id not in MAINTENANCE_OWNER:
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            msg = await ctx.message.reply(f'{EMOJI_RED_NO} {COIN_NAME} in maintenance.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        if COIN_NAME in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
            wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            if wallet is None:
                if COIN_NAME in ENABLE_COIN_ERC:
                    w = await create_address_eth()
                    userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
                elif COIN_NAME in ENABLE_COIN_TRC:
                    result = await store.create_address_trx()
                    userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, result)
                else:
                    userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
                wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            if COIN_NAME in ENABLE_COIN_ERC:
                token_info = await store.get_token_info(COIN_NAME)
                deposit_balance = await store.http_wallet_getbalance(wallet['balance_wallet_address'], COIN_NAME, True)
                real_deposit_balance = round(deposit_balance / 10**token_info['token_decimal'], 6)
            elif COIN_NAME in ENABLE_COIN_TRC:
                token_info = await store.get_token_info(COIN_NAME)
                deposit_balance = await store.trx_wallet_getbalance(wallet['balance_wallet_address'], COIN_NAME)
                real_deposit_balance = round(deposit_balance, 6)
            userdata_balance = await store.sql_user_balance(str(ctx.author.id), COIN_NAME, SERVER_BOT)
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

            balance_actual = num_format_coin(actual_balance, COIN_NAME)
            locked_openorder = userdata_balance['OpenOrder']
            raffle_spent = userdata_balance['raffle_fee']
            raffle_reward = userdata_balance['raffle_reward']
            economy_amount = userdata_balance['economy_balance']
            embed = discord.Embed(title=f'[ {ctx.author.name}#{ctx.author.discriminator}\'s {COIN_NAME} balance ]', timestamp=datetime.utcnow())
            try:
                if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    embed.add_field(name="Deposited", value="`{} {}`".format(num_format_coin(float(real_deposit_balance), COIN_NAME), COIN_NAME), inline=True)
                embed.add_field(name="Spendable", value=balance_actual+COIN_NAME, inline=True)
                if locked_openorder > 0 and COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    embed.add_field(name="Opened Order", value=num_format_coin(locked_openorder, COIN_NAME)+" "+COIN_NAME, inline=True)
                    embed.add_field(name="Total", value=num_format_coin(actual_balance+locked_openorder, COIN_NAME)+" "+COIN_NAME, inline=True)
                elif locked_openorder > 0 and COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    embed.add_field(name="Opened Order", value=num_format_coin(locked_openorder, COIN_NAME)+" "+COIN_NAME, inline=True)
                    embed.add_field(name="Total", value=num_format_coin(actual_balance+locked_openorder+float(real_deposit_balance), COIN_NAME)+" "+COIN_NAME, inline=True)
                elif locked_openorder == 0 and COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    embed.add_field(name="Total", value=num_format_coin(actual_balance+float(real_deposit_balance), COIN_NAME)+" "+COIN_NAME, inline=True)
                if raffle_spent and raffle_spent > 0:
                    embed.add_field(name="Raffle Spent / Won", value="{} / {} {}".format(num_format_coin(raffle_spent, COIN_NAME), num_format_coin(raffle_reward, COIN_NAME), COIN_NAME), inline=False)
            except Exception as e:
                print(traceback.format_exc())
            if userdata_balance['economy_balance'] and userdata_balance['economy_balance'] != 0:
                embed.add_field(name="Economy Expense (+/-)", value=num_format_coin(userdata_balance['economy_balance'], COIN_NAME)+ " " + COIN_NAME, inline=True)
            embed.add_field(name='Related commands', value=f'`{prefix}balance` or `{prefix}deposit {COIN_NAME}` or `{prefix}balance LIST`', inline=False)
            if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                min_deposit_txt = " Min. deposit for moving to spendable: " + num_format_coin(token_info['min_move_deposit'], COIN_NAME) + " "+ COIN_NAME
                embed.set_footer(text=f"{token_info['deposit_note'] + min_deposit_txt}")
            else:
                embed.set_footer(text=f"{get_notice_txt(COIN_NAME)}")
            try:
                msg = await ctx.author.send(embed=embed)
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                await msg.add_reaction(EMOJI_OK_BOX)
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                try:
                    msg = await ctx.message.reply(embed=embed)
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                    await msg.add_reaction(EMOJI_OK_BOX)
                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                return
        else:
            msg = await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} There is no such ticker {COIN_NAME}.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return


def setup(bot):
    bot.add_cog(Balance(bot))