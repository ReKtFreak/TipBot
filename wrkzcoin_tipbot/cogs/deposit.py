import sys, traceback, os
import os.path
import asyncio
import re
import sys
import time
import traceback
from datetime import datetime
import random
import qrcode
import uuid
from PIL import Image, ImageDraw, ImageFont

import discord
from discord.ext import commands
from dislash import InteractionClient, ActionRow, Button, ButtonStyle, Option, OptionType, OptionChoice

import store
from Bot import *

from config import config


class Deposit(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    async def generate_qr_address(self, address: str):
        # return path to image
        # address = wallet['balance_wallet_address']
        # return address if success, else None
        if not os.path.exists(config.deposit_qr.path_deposit_qr_create + address + ".png"):
            try:
                # do some QR code
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=2,
                )
                qr.add_data(address)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                img = img.resize((256, 256))
                img.save(config.deposit_qr.path_deposit_qr_create + address + ".png")
            except Exception as e:
                await logchanbot(traceback.format_exc())
                return None
        # https://deposit.bot.tips/
        if not os.path.exists(config.qrsettings.path + address + ".png"):
            try:
                # do some QR code
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=2,
                )
                qr.add_data(address)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                img = img.resize((256, 256))
                img.save(config.qrsettings.path + address + ".png")
            except Exception as e:
                await logchanbot(traceback.format_exc())
                return None
        return address


    async def get_deposit_coin_user(self, user_id, coin_name: str):
        COIN_NAME = coin_name.upper()
        if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
            return {"error": f"INVALID TICKER **{COIN_NAME}**!"}

        if not is_coin_depositable(COIN_NAME):
            return {"error": f"DEPOSITING is currently disable for **{COIN_NAME}**."}

        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
        else:
            try:
                coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
            except Exception as e:
                await logchanbot(traceback.format_exc())
                return {"error": f"INVALID TICKER **{COIN_NAME}**!"}
            
        if is_maintenance_coin(COIN_NAME) and (user_id not in MAINTENANCE_OWNER):
            return {"error": f"**{COIN_NAME}** in maintenance mode."}

        if coin_family in ["TRTL", "BCN"]:
            wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
            if wallet is None:
                userregister = await store.sql_register_user(str(user_id), COIN_NAME, SERVER_BOT, 0)
                wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
        elif coin_family == "XMR":
            wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
            if wallet is None:
                userregister = await store.sql_register_user(str(user_id), COIN_NAME, SERVER_BOT, 0)
                wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
        elif coin_family == "XCH":
            wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
            if wallet is None:
                userregister = await store.sql_register_user(str(user_id), COIN_NAME, SERVER_BOT, 0)
                wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
        elif coin_family == "DOGE":
            wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
            if wallet is None:
                wallet = await store.sql_register_user(str(user_id), COIN_NAME, SERVER_BOT, 0)
                wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
        elif coin_family == "NANO":
            wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
            if wallet is None:
                wallet = await store.sql_register_user(str(user_id), COIN_NAME, SERVER_BOT, 0)
                wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
        elif coin_family == "ERC-20":
            wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
            if wallet is None:
                w = await create_address_eth()
                wallet = await store.sql_register_user(str(user_id), COIN_NAME, SERVER_BOT, 0, w)
                wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
        elif coin_family == "TRC-20":
            wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
            if wallet is None:
                result = await store.create_address_trx()
                wallet = await store.sql_register_user(str(user_id), COIN_NAME, SERVER_BOT, 0, result)
                wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)

        if wallet is None:
            return {"error": f"**{COIN_NAME}** internal error, please report."}
        else:
            return {
                'balance_wallet_address': wallet['balance_wallet_address'], 
                'user_wallet_address': wallet['user_wallet_address'] if 'user_wallet_address' in wallet and wallet['user_wallet_address'] else None
            }



    @inter_client.slash_command(usage="deposit <coin> [plain]",
                                options=[
                                    Option('coin', 'Enter coin ticker/name', OptionType.STRING, required=True),
                                    Option('option', 'plain/embed', OptionType.STRING, required=True, choices=[
                                        OptionChoice("plain", "plain"),
                                        OptionChoice("embed", "embed")
                                    ]
                                    )
                                ],
                                description="Get your tipjar's deposit address.")
    async def deposit(
        self, 
        inter, 
        coin: str, 
        option: str="plain"
    ):
        prefix = "/"
        COIN_NAME = coin.upper()
        option = option.upper()
        user_id = inter.author.id
        botLogChan = self.bot.get_channel(LOG_CHAN)
        # check if account locked
        account_lock = await alert_if_userlock(inter, 'balance')
        if account_lock:
            await inter.reply(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
            return
        # end of check if account locked

        try:
            wallet = await self.get_deposit_coin_user(inter.author.id, COIN_NAME)
            if 'error' in wallet:
                error_msg = wallet['error']
                await inter.reply(f"{EMOJI_RED_NO} {error_msg}", ephemeral=True)
                return
            else:
                deposit_address = wallet['balance_wallet_address']
                # generate QR if not exists
                gen_qr_address = await self.generate_qr_address(deposit_address)
                if gen_qr_address is None:
                    await inter.reply(f"'{EMOJI_RED_NO} Failed to generate QR.", ephemeral=True)
                    return
                if option == "PLAIN":
                    await inter.reply(f"Your **{COIN_NAME}**\'s deposit address: ```{deposit_address}```", ephemeral=True)
                else:
                    # embed
                    embed = discord.Embed(title=f'Your Deposit {inter.author.name}#{inter.author.discriminator} / **{COIN_NAME}**', description='{}'.format(get_notice_txt(COIN_NAME)), timestamp=datetime.utcnow(), colour=7047495)
                    embed.set_author(name=inter.author.name, icon_url=inter.author.display_avatar)
                    embed.add_field(name="{} Deposit Address".format(COIN_NAME), value=f"`{deposit_address}`", inline=False)
                    if wallet['user_wallet_address']:
                        embed.add_field(name="Withdraw Address", value="`{}`".format(wallet['user_wallet_address']), inline=False)
                    if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                        token_info = await store.get_token_info(COIN_NAME)
                        if token_info and COIN_NAME in ENABLE_COIN_ERC and token_info['contract'] and len(token_info['contract']) == 42:
                            embed.add_field(name="{} Contract".format(COIN_NAME), value="`{}`".format(token_info['contract']), inline=False)
                        elif token_info and COIN_NAME in ENABLE_COIN_TRC and token_info['contract'] and len(token_info['contract']) >= 6:
                            embed.add_field(name="{} Contract/Token ID".format(COIN_NAME), value="`{}`".format(token_info['contract']), inline=False)
                        if token_info and token_info['deposit_note']:
                            embed.add_field(name="{} Deposit Note".format(COIN_NAME), value="`{}`".format(token_info['deposit_note']), inline=False)
                    embed.set_thumbnail(url=config.deposit_qr.deposit_url + "/tipbot_deposit_qr/" + deposit_address + ".png")
                    prefix = "/"
                    embed.set_footer(text=f"Use:{prefix}deposit {COIN_NAME} plain (for plain text)")
                    try:
                        return await inter.reply(embed=embed, ephemeral=True)
                    except Exception as e:
                        traceback.print_exc(file=sys.stdout)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await inter.reply(f"Internal error to get deposit for: {COIN_NAME}. Please report.", ephemeral=True)


    @commands.command(usage='deposit [coin] <plain/embed>', description="Get your a deposit address.")
    async def deposit(self, ctx, coin_name: str, option: str=None):
        COIN_NAME = coin_name.upper()
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

            wallet = await self.get_deposit_coin_user(ctx.author.id, coin_name)
            if 'error' in wallet:
                error_msg = wallet['error']
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {error_msg}')
                return

            deposit_address = wallet['balance_wallet_address']
            # generate QR if not exists
            gen_qr_address = await self.generate_qr_address(deposit_address)
            if gen_qr_address is None:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Failed to generate QR.')
                return

            if option and option.upper() in ["PLAIN", "TEXT", "NOEMBED"]:
                try:
                    msg = await ctx.message.reply(f'{ctx.author.mention} Your **{COIN_NAME}**\'s deposit address: ```{deposit_address}```')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                    return
                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                    if isinstance(ctx.channel, discord.DMChannel) == False:
                        try:
                            msg = await ctx.author.send(f'{ctx.author.mention} Your **{COIN_NAME}**\'s deposit address: ```{deposit_address}```')
                            await msg.add_reaction(EMOJI_OK_BOX)
                            await ctx.message.add_reaction(EMOJI_OK_HAND)
                            return
                        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                            await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                            return
                    else:
                        await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                        return
            elif option is None or (option and option.lower() == "embed"):
                embed = discord.Embed(title=f'Your Deposit {ctx.author.name}#{ctx.author.discriminator} / **{COIN_NAME}**', description='{}'.format(get_notice_txt(COIN_NAME)), timestamp=datetime.utcnow(), colour=7047495)
                embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)
                embed.add_field(name="{} Deposit Address".format(COIN_NAME), value=f"`{deposit_address}`", inline=False)
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
                embed.set_thumbnail(url=config.deposit_qr.deposit_url + "/tipbot_deposit_qr/" + deposit_address + ".png")
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