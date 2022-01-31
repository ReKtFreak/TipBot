import sys, traceback
import time, timeago
import disnake
from disnake.ext import commands

from disnake.enums import OptionType
from disnake.app_commands import Option, OptionChoice

from config import config
from Bot import *

class TipDonate(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def bot_log(self):
        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def donate_list(
        self,
        ctx
    ):
        donate_list = await store.sql_get_donate_list()
        item_list = []
        embed = disnake.Embed(title='Donation List', timestamp=datetime.utcnow())
        for key, value in donate_list.items():
            if value:
                coin_value = num_format_coin(value, key.upper())+key.upper()
                item_list.append(coin_value)
                embed.add_field(name=key.upper(), value=num_format_coin(value, key.upper())+key.upper(), inline=True)
        embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
        if len(item_list) > 0:
            try:
                msg = await ctx.reply(embed=embed)
            except (disnake.errors.NotFound, disnake.errors.Forbidden) as e:
                msg_coins = ', '.join(item_list)
                try:
                    msg = await ctx.reply(f'Thank you for checking. So far, we got donations:\n```{msg_coins}```')
                except (disnake.errors.NotFound, disnake.errors.Forbidden) as e:
                    return


    async def process_donate(
        self,
        ctx,
        amount,
        coin
    ):
        await self.bot_log()
        COIN_NAME = coin.upper()
        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")

        real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)     
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
        balance_user = await get_balance_coin_user(str(ctx.author.id), COIN_NAME, discord_guild=False, server__bot=SERVER_BOT)
        if real_amount > balance_user['actual_balance']:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to donate {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}"}
        elif real_amount <= 0:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Please check your {COIN_NAME}'s balance."}

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
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
        if donateTx:
            # Update tipstat
            try:
                update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                await logchanbot(traceback.format_exc())

            await self.botLogChan.send(f'{EMOJI_MONEYFACE} TipBot got donation: {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}')
            msg = await ctx.reply(f"{EMOJI_MONEYFACE} TipBot got donation: {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}. Thank you.")
            return
        else:
            msg = await ctx.reply(f'{ctx.author.mention} Donating failed, try again. Thank you.')
            await self.botLogChan.send(f'A user failed to donate `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
            # add to failed tx table
            await store.sql_add_failed_tx(COIN_NAME, str(ctx.author.id), ctx.author.name, real_amount, "DONATE")
            return


    @commands.slash_command(
        usage="donate", 
        options=[
            Option('amount', 'amount number or list', OptionType.string, required=True),
            Option('coin', 'coin', OptionType.string, required=False)
        ],
        description="Donate amount coin to TipBot dev."
    )
    async def donate(
        self, 
        ctx,
        amount: str,
        coin: str=None
    ):
        if amount.upper() == "LIST":
            return await self.donate_list(ctx)
        else:
            if coin is None:
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Missing coin name.')
                return
            amount = amount.replace(",", "")
            try:
                amount = Decimal(amount)
            except ValueError:
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
                return

            process_donate = await self.process_donate(ctx, amount, coin.upper())
            if process_donate and "error" in process_donate:
                msg = await ctx.reply(process_donate['error'])


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
        if amount.upper() == "LIST":
            return await self.donate_list(ctx)
        else:
            if coin is None:
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Missing coin name.')
                return
            amount = amount.replace(",", "")
            try:
                amount = Decimal(amount)
            except ValueError:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
                return

            process_donate = await self.process_donate(ctx, amount, coin.upper())
            if process_donate and "error" in process_donate:
                msg = await ctx.reply(process_donate['error'])



def setup(bot):
    bot.add_cog(TipDonate(bot))