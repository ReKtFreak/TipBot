import asyncio
import re
import sys
import time
import traceback
from datetime import datetime
import random

import discord
from discord.ext import commands

import store
from Bot import *

from config import config


class Deposit(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(usage='deposit [coin] <plain/embed>', description="Get your a deposit address.")
    async def deposit(self, ctx, coin_name: str, option: str=None):
        try:
            # check if account locked
            account_lock = await alert_if_userlock(ctx, 'deposit')
            if account_lock:
                await ctx.message.add_reaction(EMOJI_LOCKED) 
                await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
                return
            # end of check if account locked

            # Check if maintenance
            if IS_MAINTENANCE == 1:
                if int(ctx.author.id) in MAINTENANCE_OWNER:
                    await ctx.message.add_reaction(EMOJI_MAINTENANCE)
                    pass
                else:
                    await ctx.message.add_reaction(EMOJI_WARNING)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}')
                    return
            else:
                pass
            # End Check if maintenance

            COIN_NAME = coin_name.upper()
            if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**!')
                return

            if not is_coin_depositable(COIN_NAME):
                msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} DEPOSITING is currently disable for {COIN_NAME}.')
                await msg.add_reaction(EMOJI_OK_BOX)
                return

            if COIN_NAME in ENABLE_COIN_ERC:
                coin_family = "ERC-20"
            elif COIN_NAME in ENABLE_COIN_TRC:
                coin_family = "TRC-20"
            else:
                try:
                    coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**')
                    return
            
            if is_maintenance_coin(COIN_NAME) and (ctx.author.id not in MAINTENANCE_OWNER):
                await ctx.message.add_reaction(EMOJI_MAINTENANCE)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
                return

            if coin_family in ["TRTL", "BCN"]:
                wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                if wallet is None:
                    userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
                    wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            elif coin_family == "XMR":
                wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                if wallet is None:
                    userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
                    wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            elif coin_family == "XCH":
                wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                if wallet is None:
                    userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
                    wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            elif coin_family == "DOGE":
                wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                if wallet is None:
                    wallet = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
                    wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            elif coin_family == "NANO":
                wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                if wallet is None:
                    wallet = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
                    wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            elif coin_family == "ERC-20":
                wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                if wallet is None:
                    w = await create_address_eth()
                    wallet = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
                    wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            elif coin_family == "TRC-20":
                wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                if wallet is None:
                    result = await store.create_address_trx()
                    wallet = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, result)
                    wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
            else:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**')
                return
            if wallet is None:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Internal Error for `.info`')
                return
            if not os.path.exists(config.deposit_qr.path_deposit_qr_create + wallet['balance_wallet_address'] + ".png"):
                try:
                    # do some QR code
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=2,
                    )
                    qr.add_data(wallet['balance_wallet_address'])
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    img = img.resize((256, 256))
                    img.save(config.deposit_qr.path_deposit_qr_create + wallet['balance_wallet_address'] + ".png")
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                # https://deposit.bot.tips/
            if not os.path.exists(config.qrsettings.path + wallet['balance_wallet_address'] + ".png"):
                try:
                    # do some QR code
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=2,
                    )
                    qr.add_data(wallet['balance_wallet_address'])
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    img = img.resize((256, 256))
                    img.save(config.qrsettings.path + wallet['balance_wallet_address'] + ".png")
                except Exception as e:
                    await logchanbot(traceback.format_exc())
            if option and option.upper() in ["PLAIN", "TEXT", "NOEMBED"]:
                deposit = wallet['balance_wallet_address']
                try:
                    msg = await ctx.message.reply(f'{ctx.author.mention} Your **{COIN_NAME}**\'s deposit address: ```{deposit}```')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                    return
                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                    if isinstance(ctx.channel, discord.DMChannel) == False:
                        try:
                            msg = await ctx.author.send(f'{ctx.author.mention} Your **{COIN_NAME}**\'s deposit address: ```{deposit}```')
                            await msg.add_reaction(EMOJI_OK_BOX)
                            await ctx.message.add_reaction(EMOJI_OK_HAND)
                            return
                        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                            await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                            return
                    else:
                        await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                        return

            embed = discord.Embed(title=f'Your Deposit {ctx.author.name}#{ctx.author.discriminator} / **{COIN_NAME}**', description='{}'.format(get_notice_txt(COIN_NAME)), timestamp=datetime.utcnow(), colour=7047495)
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)
            embed.add_field(name="{} Deposit Address".format(COIN_NAME), value="`{}`".format(wallet['balance_wallet_address']), inline=False)
            if 'user_wallet_address' in wallet and wallet['user_wallet_address'] and isinstance(ctx.channel, discord.DMChannel) == True:
                embed.add_field(name="Withdraw Address", value="`{}`".format(wallet['user_wallet_address']), inline=False)
            elif 'user_wallet_address' in wallet and wallet['user_wallet_address'] and isinstance(ctx.channel, discord.DMChannel) == False:
                embed.add_field(name="Withdraw Address", value="`(Only in DM)`", inline=False)
            if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                token_info = await store.get_token_info(COIN_NAME)
                if token_info and COIN_NAME in ENABLE_COIN_ERC and token_info['contract'] and len(token_info['contract']) == 42:
                    embed.add_field(name="{} Contract".format(COIN_NAME), value="`{}`".format(token_info['contract']), inline=False)
                elif token_info and COIN_NAME in ENABLE_COIN_TRC and token_info['contract'] and len(token_info['contract']) >= 6:
                    embed.add_field(name="{} Contract/Token ID".format(COIN_NAME), value="`{}`".format(token_info['contract']), inline=False)
                if token_info and token_info['deposit_note']:
                    embed.add_field(name="{} Deposit Note".format(COIN_NAME), value="`{}`".format(token_info['deposit_note']), inline=False)
            embed.set_thumbnail(url=config.deposit_qr.deposit_url + "/tipbot_deposit_qr/" + wallet['balance_wallet_address'] + ".png")
            prefix = await get_guild_prefix(ctx)
            embed.set_footer(text=f"Use:{prefix}deposit {COIN_NAME} plain (for plain text)")
            try:
                msg = await ctx.message.reply(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                return
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                try:
                    msg = await ctx.send(embed=embed)
                    await msg.add_reaction(EMOJI_OK_BOX)
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                    return
                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                    return
        except Exception as e:
            traceback.print_exc(file=sys.stdout)


def setup(bot):
    bot.add_cog(Deposit(bot))