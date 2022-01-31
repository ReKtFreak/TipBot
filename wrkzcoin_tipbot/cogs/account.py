import asyncio
import re
import sys
import time
import traceback
from datetime import datetime
import random

import disnake
from disnake.ext import commands
from disnake.enums import OptionType
from disnake.app_commands import Option, OptionChoice

import store
from Bot import *

from config import config


class Account(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.slash_command(description="Various Account commands.")
    async def account(self, ctx):
        # This is just a parent for subcommands
        # It's not necessary to do anything here,
        # but if you do, it runs for any subcommand nested below
        pass

    @account.sub_command(
        usage="account tradeapi", 
        options=[
            Option('regen', 'y or n', OptionType.string, required=False, choices=[
                OptionChoice("y", "y"),
                OptionChoice("n", "n")
            ]
            )
        ],
        description="Create API for Trading."
    )
    async def tradeapi(
        self, 
        ctx, 
        regen: str=None
    ):
        re_create = False
        if regen and regen.upper() == "Y":
            re_create = True
        
        # Create API trade
        get_trade_api = await store.get_api_trade(str(ctx.author.id), SERVER_BOT)
        if get_trade_api is None:
            api_key = str(uuid.uuid4())
            trade_api = await store.create_api_trade(str(ctx.author.id), api_key, re_create, SERVER_BOT)
            if trade_api:
                await ctx.reply('Copy your api key and store in a safe place:```authorization-user: {}\nauthorization-key: {}```'.format(str(ctx.author.id), api_key), ephemeral=True)
            else:
                await ctx.reply('Internal error.', ephemeral=True)
        else:
            if re_create == False:
                await ctx.reply('Copy your api key and store in a safe place:```authorization-user: {}\nauthorization-key: {}```'.format(str(ctx.author.id), get_trade_api['api_key']), ephemeral=True)
            else:
                api_key = str(uuid.uuid4())
                trade_api = await store.create_api_trade(str(ctx.author.id), api_key, re_create, SERVER_BOT)
                if trade_api:
                    await ctx.reply('Copy your api key and store in a safe place:```authorization-user: {}\nauthorization-key: {}```'.format(str(ctx.author.id), api_key), ephemeral=True)
                else:
                    await ctx.reply('Internal error updating API keys.', ephemeral=True)


    @account.sub_command(
        usage="account deposit_link", 
        options=[
            Option('option', 'DISABLE, OFF, HIDE, PUBLIC', OptionType.string, required=False, choices=[
                OptionChoice("DISABLE", "DISABLE"),
                OptionChoice("OFF", "OFF"),
                OptionChoice("HIDE", "HIDE"),
                OptionChoice("PUBLIC", "PUBLIC")
            ]
            )
        ],
        description="Get a web deposit link for all your deposit addresses."
    )
    async def deposit_link(
        self, 
        ctx, 
        option: str=None
    ):
        async def create_qr_on_remote(ctx, coin):
            COIN_NAME = coin.upper()
            if not is_maintenance_coin(COIN_NAME):
                wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                if wallet is None:
                    userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
                    wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                try:
                    if os.path.exists(config.deposit_qr.path_deposit_qr_create + wallet['balance_wallet_address'] + ".png"):
                        pass
                    else:
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
        local_address = await store.sql_deposit_getall_address_user(str(ctx.author.id), SERVER_BOT)
        remote_address = await store.sql_deposit_getall_address_user_remote(str(ctx.author.id), SERVER_BOT)
        diff_address = local_address
        get_depositlink = await store.sql_depositlink_user(str(ctx.author.id), SERVER_BOT)
        if remote_address and len(remote_address) > 0:
            # https://stackoverflow.com/questions/35187165/python-how-to-subtract-2-dictionaries
            all(map( diff_address.pop, remote_address))

        if diff_address and len(diff_address) > 0:
            for key, value in diff_address.items():
                if key in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_XCH and not is_maintenance_coin(key):
                    await store.sql_depositlink_user_insert_address(str(ctx.author.id), key, value, SERVER_BOT)
                    await create_qr_on_remote(ctx, key)

        if remote_address and len(remote_address) > 0:
            diff_address = remote_address
            removing_address = {}
            for k, v in remote_address.items():
                if k not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_XCH or is_maintenance_coin(k):
                    removing_address[k] = v
                elif k in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_XCH and not is_maintenance_coin(k):
                    # check if exist in remote, or create QR
                    await create_qr_on_remote(ctx, k)

            if removing_address and len(removing_address) > 0:
                for key, value in removing_address.items():
                    await store.sql_depositlink_user_delete_address(str(ctx.author.id), key, SERVER_BOT)

        if get_depositlink:
            # if we have result, show link or disable if there id disable
            if get_depositlink['enable'] == 'YES' and option and option.upper() in ["DISABLE", "OFF", "0", "FALSE", "HIDE"]:
                # Turn it off
                update = await store.sql_depositlink_user_update(str(ctx.author.id), "enable", "NO", SERVER_BOT)
                if update:
                    msg = await ctx.reply(f'{ctx.author.mention} Your deposit link status successfully.', ephemeral=True)
                else:
                    await ctx.reply(f'{ctx.author.mention} Internal error during update status from ENABLE to DISABLE. Try again later.')
                return
            elif get_depositlink['enable'] == 'YES' and option and option.upper() in ["ENABLE", "ON", "1", "TRUE", "SHOW"]:
                await ctx.reply(f'{ctx.author.mention} Your deposit link is already public. Nothing to do.', ephemeral=True)
                return
            elif get_depositlink['enable'] == 'NO' and option and option.upper() in ["ENABLE", "ON", "1", "TRUE", "SHOW"]:
                # Turn it on
                update = await store.sql_depositlink_user_update(str(ctx.author.id), "enable", "YES", SERVER_BOT)
                if update:
                    msg = await ctx.reply(f'{ctx.author.mention} Your deposit link status successfully.', ephemeral=True)
                else:
                    await ctx.reply(f'{ctx.author.mention} Internal error during update status from DISABLE to ENABLE. Try again later.')
                return
            elif get_depositlink['enable'] == 'NO' and option and option.upper() in ["DISABLE", "OFF", "0", "FALSE", "HIDE"]:
                await ctx.reply(f'{ctx.author.mention} Your deposit link is already private. Nothing to do.', ephemeral=True)
                return
            elif option and (option.upper() == "PUB" or option.upper() == "PUBLIC"):
                # display link
                status = "public" if get_depositlink['enable'] == 'YES' else "private"
                link = config.deposit_qr.deposit_url + '/key/' + get_depositlink['link_key']
                msg = await ctx.reply(f'{ctx.author.mention} Your deposit link can be accessed from:\n{link}', ephemeral=False)
            else:
                # display link
                status = "public" if get_depositlink['enable'] == 'YES' else "private"
                link = config.deposit_qr.deposit_url + '/key/' + get_depositlink['link_key']
                try:
                    msg = await ctx.reply(f'{ctx.author.mention} Your deposit link can be accessed from:\n{link}', ephemeral=True)
                except Exception as e:
                    msg = await ctx.reply(f'{ctx.author.mention} Internal error.')
            return
        else:
            # generate a deposit link for him but need QR first
            for COIN_NAME in [coinItem.upper() for coinItem in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_XCH]:
                await create_qr_on_remote(ctx, COIN_NAME)
            # link stuff
            random_string = str(uuid.uuid4())
            create_link = await store.sql_depositlink_user_create(str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator), random_string, SERVER_BOT)
            if create_link:
                link = config.deposit_qr.deposit_url + '/key/' + random_string
                try:
                    msg = await ctx.reply(f'{ctx.author.mention} Link generate successfully.\n{link}', ephemeral=True)
                except Exception as e:
                    msg = await ctx.reply(f'{ctx.author.mention} Internal error.')
            else:
                await ctx.reply(f'{ctx.author.mention} Internal error during link generation. Try later.')
            return


    # Message commands
    @commands.group(
        usage="acc <subcommand>", 
        aliases=['acc'], 
        description="Various account's command"
    )
    async def account(self, ctx):
        prefix = await get_guild_prefix(ctx)
        if ctx.invoked_subcommand is None:
            await ctx.reply(f'{ctx.author.mention} Invalid {prefix}account command')
            return


    @account.command(
        usage='tradeapi', 
        aliases=['trade_api', 'api_trade'], 
        description="Create API for Trading."
    )
    async def tradeapi(
        self, 
        ctx, 
        regen: str=None
    ):
        # acc tradeapi | acc tradeapi regen
        if isinstance(ctx.channel, disnake.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.reply(f'{ctx.author.mention} This command can not be in public.')
            return
        re_create = False
        if regen and regen.upper() in ["REGEN", "RECREATE", "GEN"]:
            re_create = True
        
        # Create API trade
        get_trade_api = await store.get_api_trade(str(ctx.author.id), SERVER_BOT)
        if get_trade_api is None:
            api_key = str(uuid.uuid4())
            trade_api = await store.create_api_trade(str(ctx.author.id), api_key, re_create, SERVER_BOT)
            if trade_api:
                await ctx.reply('Copy your api key and store in a safe place:```authorization-user: {}\nauthorization-key: {}```'.format(str(ctx.author.id), api_key))
            else:
                await ctx.reply('Internal error.')
        else:
            if re_create == False:
                await ctx.reply('Copy your api key and store in a safe place:```authorization-user: {}\nauthorization-key: {}```'.format(str(ctx.author.id), get_trade_api['api_key']))
            else:
                api_key = str(uuid.uuid4())
                trade_api = await store.create_api_trade(str(ctx.author.id), api_key, re_create, SERVER_BOT)
                if trade_api:
                    await ctx.reply('Copy your api key and store in a safe place:```authorization-user: {}\nauthorization-key: {}```'.format(str(ctx.author.id), api_key))
                else:
                    await ctx.reply('Internal error updating API keys.')


    @account.command(
        usage='deposit_link [disable]', 
        aliases=['deposit'], 
        description="Get a web deposit link for all your deposit addresses."
    )
    async def deposit_link(
        self, 
        ctx, 
        disable: str=None
    ):
        prefix = await get_guild_prefix(ctx)
        async def create_qr_on_remote(ctx, coin):
            COIN_NAME = coin.upper()
            if not is_maintenance_coin(COIN_NAME):
                wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                if wallet is None:
                    userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
                    wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                try:
                    if os.path.exists(config.deposit_qr.path_deposit_qr_create + wallet['balance_wallet_address'] + ".png"):
                        pass
                    else:
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
        local_address = await store.sql_deposit_getall_address_user(str(ctx.author.id), SERVER_BOT)
        remote_address = await store.sql_deposit_getall_address_user_remote(str(ctx.author.id), SERVER_BOT)
        diff_address = local_address
        get_depositlink = await store.sql_depositlink_user(str(ctx.author.id), SERVER_BOT)
        if remote_address and len(remote_address) > 0:
            # https://stackoverflow.com/questions/35187165/python-how-to-subtract-2-dictionaries
            all(map( diff_address.pop, remote_address))

        if diff_address and len(diff_address) > 0:
            for key, value in diff_address.items():
                if key in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_XCH and not is_maintenance_coin(key):
                    await store.sql_depositlink_user_insert_address(str(ctx.author.id), key, value, SERVER_BOT)
                    await create_qr_on_remote(ctx, key)

        if remote_address and len(remote_address) > 0:
            diff_address = remote_address
            removing_address = {}
            for k, v in remote_address.items():
                if k not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_XCH or is_maintenance_coin(k):
                    removing_address[k] = v
                elif k in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_XCH and not is_maintenance_coin(k):
                    # check if exist in remote, or create QR
                    await create_qr_on_remote(ctx, k)

            if removing_address and len(removing_address) > 0:
                for key, value in removing_address.items():
                    await store.sql_depositlink_user_delete_address(str(ctx.author.id), key, SERVER_BOT)

        if get_depositlink:
            # if we have result, show link or disable if there id disable
            if get_depositlink['enable'] == 'YES' and disable and disable.upper() in ["DISABLE", "OFF", "0", "FALSE", "HIDE"]:
                # Turn it off
                update = await store.sql_depositlink_user_update(str(ctx.author.id), "enable", "NO", SERVER_BOT)
                if update:
                    await ctx.message.add_reaction(EMOJI_OK_HAND) 
                    msg = await ctx.reply(f'{ctx.author.mention} Your deposit link status successfully and **not be accessible by public**.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR) 
                    await ctx.reply(f'{ctx.author.mention} Internal error during update status from ENABLE to DISABLE. Try again later.')
                    return
            elif get_depositlink['enable'] == 'YES' and disable and disable.upper() in ["ENABLE", "ON", "1", "TRUE", "SHOW"]:
                await ctx.message.add_reaction(EMOJI_ERROR) 
                await ctx.reply(f'{ctx.author.mention} Your deposit link is already public. Nothing to do.')
                return
            elif get_depositlink['enable'] == 'NO' and disable and disable.upper() in ["ENABLE", "ON", "1", "TRUE", "SHOW"]:
                # Turn it on
                update = await store.sql_depositlink_user_update(str(ctx.author.id), "enable", "YES", SERVER_BOT)
                if update:
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                    msg = await ctx.reply(f'{ctx.author.mention} Your deposit link status successfully and **will be accessible by public**.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR) 
                    await ctx.reply(f'{ctx.author.mention} Internal error during update status from DISABLE to ENABLE. Try again later.')
                    return
            elif get_depositlink['enable'] == 'NO' and disable and disable.upper() in ["DISABLE", "OFF", "0", "FALSE", "HIDE"]:
                await ctx.message.add_reaction(EMOJI_ERROR) 
                await ctx.reply(f'{ctx.author.mention} Your deposit link is already private. Nothing to do.')
                return
            elif disable and (disable.upper() == "PUB" or disable.upper() == "PUBLIC"):
                # display link
                status = "public" if get_depositlink['enable'] == 'YES' else "private"
                link = config.deposit_qr.deposit_url + '/key/' + get_depositlink['link_key']
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                msg = await ctx.reply(f'{ctx.author.mention} Your deposit link can be accessed from (**{status}**):\n{link}')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            else:
                # display link
                status = "public" if get_depositlink['enable'] == 'YES' else "private"
                link = config.deposit_qr.deposit_url + '/key/' + get_depositlink['link_key']
                try:
                    msg = await ctx.author.send(f'{ctx.author.mention} Your deposit link can be accessed from (**{status}**):\n{link}')
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                    await msg.add_reaction(EMOJI_OK_BOX)
                except (disnake.errors.NotFound, disnake.errors.Forbidden) as e:
                    await msg.add_reaction(EMOJI_ERROR)
                    msg = await ctx.reply(f'{ctx.author.mention} I failed to DM you. You can also use **{prefix}account deposit pub**, if you want it to be in public.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                return
        else:
            # generate a deposit link for him but need QR first
            for COIN_NAME in [coinItem.upper() for coinItem in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_XCH]:
                await create_qr_on_remote(ctx, COIN_NAME)
            # link stuff
            random_string = str(uuid.uuid4())
            create_link = await store.sql_depositlink_user_create(str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator), random_string, SERVER_BOT)
            if create_link:
                link = config.deposit_qr.deposit_url + '/key/' + random_string
                try:
                    msg = await ctx.author.send(f'{ctx.author.mention} Link generate successfully.\n{link}')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                except (disnake.errors.NotFound, disnake.errors.Forbidden) as e:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    msg = await ctx.reply(f'{ctx.author.mention} I failed to DM you. You can also use **{prefix}account deposit pub**, if you want it to be in public.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR) 
                await ctx.reply(f'{ctx.author.mention} Internal error during link generation. Try later.')
                return


def setup(bot):
    bot.add_cog(Account(bot))