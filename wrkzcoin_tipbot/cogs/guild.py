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


class Guild(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(usage="setting <expression>", aliases=['settings', 'set'], description="Settings view and set for prefix, default coin. Requires permission manage_channels.")
    @commands.has_permissions(manage_channels=True)
    async def setting(self, ctx, *args):
        # Check if address is valid first
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('This command is not available in DM.')
            return
        botLogChan = self.bot.get_channel(LOG_CHAN)
        tickers = '|'.join(ENABLE_COIN).lower()
        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        server_prefix = config.discord.prefixCmd
        if serverinfo is None:
            # Let's add some info if server return None
            add_server_info = await store.sql_addinfo_by_server(str(ctx.guild.id),
                                                                ctx.message.guild.name, config.discord.prefixCmd, "WRKZ")
            server_id = str(ctx.guild.id)
            server_coin = DEFAULT_TICKER
            server_reacttip = "OFF"
        else:
            server_id = str(ctx.guild.id)
            server_prefix = serverinfo['prefix']
            server_coin = serverinfo['default_coin'].upper()
            server_reacttip = serverinfo['react_tip'].upper()
        
        if len(args) == 0:
            embed = discord.Embed(title = "CHANGE {} SETTING".format(ctx.guild.name), timestamp=datetime.utcnow())
            embed.add_field(name="Change Prefix", value=f'`{server_prefix}setting prefix .|?|*|!`', inline=False)
            embed.add_field(name="Change Default Coin", value=f'`{server_prefix}setting default_coin <coin_name> Use allcoin for every supported coin`', inline=False)
            embed.add_field(name="Tip Only", value=f'`{server_prefix}setting tiponly <coin1> [coin2] ..`', inline=False)
            embed.add_field(name="Bot Channel", value=f'`{server_prefix}setting botchan #channel_name`', inline=False)
            embed.add_field(name="Ignore Tipping this Channel", value=f'`{server_prefix}setting ignorechan`', inline=False)
            embed.add_field(name="Delete Ignored Channel", value=f'`{server_prefix}setting del_ignorechan`', inline=False)
            n_mute = 0
            n_ignore = 0
            
            MUTE_CHANNEL = await store.sql_list_mutechan()
            LIST_IGNORECHAN = await store.sql_listignorechan()
            if MUTE_CHANNEL and str(ctx.guild.id) in MUTE_CHANNEL:
                n_mute = len(MUTE_CHANNEL[str(ctx.guild.id)])
            if LIST_IGNORECHAN and str(ctx.guild.id) in LIST_IGNORECHAN:
                n_ignore = len(LIST_IGNORECHAN[str(ctx.guild.id)])
            embed.add_field(name="Num. Mute/Ignore Channel", value=f'`{n_mute} / {n_ignore}`', inline=False)
            try:
                msg = await ctx.send(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
            except Exception as e:
                await logchanbot(traceback.format_exc())
                await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
            return
        elif len(args) == 1:
            if args[0].upper() == "TIPONLY":
                await ctx.send(f'{ctx.author.mention} Please tell what coins to be allowed here. Separated by space.')
                return
            # enable / disable trade
            elif args[0].upper() == "TRADE":
                if serverinfo['enable_trade'] == "YES":
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_trade', 'NO')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} DISABLE trade in their guild {ctx.guild.name} / {ctx.guild.id}')
                    await ctx.send(f'{ctx.author.mention} DISABLE TRADE feature in this guild {ctx.guild.name}.')
                    return
                elif serverinfo['enable_trade'] == "NO":
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_trade', 'YES')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} ENABLE trade in their guild {ctx.guild.name} / {ctx.guild.id}')
                    await ctx.send(f'{ctx.author.mention} ENABLE TRADE feature in this guild {ctx.guild.name}.')
                return
            # enable / disable nsfw
            elif args[0].upper() == "NSFW":
                if serverinfo['enable_nsfw'] == "YES":
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_nsfw', 'NO')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} DISABLE NSFW in their guild {ctx.guild.name} / {ctx.guild.id}')
                    await ctx.send(f'{ctx.author.mention} DISABLE NSFW command in this guild {ctx.guild.name}.')
                    return
                elif serverinfo['enable_nsfw'] == "NO":
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_nsfw', 'YES')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} ENABLE NSFW in their guild {ctx.guild.name} / {ctx.guild.id}')
                    await ctx.send(f'{ctx.author.mention} ENABLE NSFW command in this guild {ctx.guild.name}.')
                return
            # enable / disable game
            elif args[0].upper() == "GAME":
                if serverinfo['enable_game'] == "YES":
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_game', 'NO')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} DISABLE game in their guild {ctx.guild.name} / {ctx.guild.id}')
                    await ctx.send(f'{ctx.author.mention} DISABLE GAME feature in this guild {ctx.guild.name}.')
                    return
                elif serverinfo['enable_game'] == "NO":
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_game', 'YES')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} ENABLE game in their guild {ctx.guild.name} / {ctx.guild.id}')
                    await ctx.send(f'{ctx.author.mention} ENABLE GAME feature in this guild {ctx.guild.name}.')
                return
            # enable / disable game
            elif args[0].upper() == "MARKET":
                if serverinfo['enable_market'] == "YES":
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_market', 'NO')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} DISABLE market command in their guild {ctx.guild.name} / {ctx.guild.id}')
                    await ctx.send(f'{ctx.author.mention} DISABLE market command in this guild {ctx.guild.name}.')
                    return
                elif serverinfo['enable_market'] == "NO":
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_market', 'YES')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} ENABLE market command in their guild {ctx.guild.name} / {ctx.guild.id}')
                    await ctx.send(f'{ctx.author.mention} ENABLE market command in this guild {ctx.guild.name}.')
                return
            # enable / disable faucet
            elif args[0].upper() == "FAUCET":
                if serverinfo['enable_faucet'] == "YES":
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_faucet', 'NO')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} DISABLE faucet (take) command in their guild {ctx.guild.name} / {ctx.guild.id}')
                    await ctx.send(f'{ctx.author.mention} DISABLE faucet (take) command in this guild {ctx.guild.name}.')
                    return
                elif serverinfo['enable_faucet'] == "NO":
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_faucet', 'YES')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} ENABLE market command in their guild {ctx.guild.name} / {ctx.guild.id}')
                    await ctx.send(f'{ctx.author.mention} ENABLE market command in this guild {ctx.guild.name}.')
                return
            elif args[0].upper() == "IGNORE_CHAN" or args[0].upper() == "IGNORECHAN":
                if LIST_IGNORECHAN is None:
                    await store.sql_addignorechan_by_server(str(ctx.guild.id), str(ctx.channel.id), str(ctx.author.id), ctx.author.name)
                    LIST_IGNORECHAN = await store.sql_listignorechan()
                    await ctx.send(f'{ctx.author.mention} Added #{ctx.channel.name} to ignore tip action list.')
                    return
                if str(ctx.guild.id) in LIST_IGNORECHAN:
                    if str(ctx.channel.id) in LIST_IGNORECHAN[str(ctx.guild.id)]:
                        await ctx.send(f'{ctx.author.mention} This channel #{ctx.channel.name} is already in ignore list.')
                        return
                    else:
                        await store.sql_addignorechan_by_server(str(ctx.guild.id), str(ctx.channel.id), str(ctx.author.id), ctx.author.name)
                        LIST_IGNORECHAN = await store.sql_listignorechan()
                        await ctx.send(f'{ctx.author.mention} Added #{ctx.channel.name} to ignore tip action list.')
                        return
                else:
                    await store.sql_addignorechan_by_server(str(ctx.guild.id), str(ctx.channel.id), str(ctx.author.id), ctx.author.name)
                    await ctx.send(f'{ctx.author.mention} Added #{ctx.channel.name} to ignore tip action list.')
                    return
            elif args[0].upper() == "DEL_IGNORE_CHAN" or args[0].upper() == "DEL_IGNORECHAN" or args[0].upper() == "DELIGNORECHAN":
                if str(ctx.guild.id) in LIST_IGNORECHAN:
                    if str(ctx.channel.id) in LIST_IGNORECHAN[str(ctx.guild.id)]:
                        await store.sql_delignorechan_by_server(str(ctx.guild.id), str(ctx.channel.id))
                        LIST_IGNORECHAN = await store.sql_listignorechan()
                        await ctx.send(f'{ctx.author.mention} This channel #{ctx.channel.name} is deleted from ignore tip list.')
                        return
                    else:
                        await ctx.send(f'{ctx.author.mention} Channel #{ctx.channel.name} is not in ignore tip action list.')
                        return
                else:
                    await ctx.send(f'{ctx.author.mention} Channel #{ctx.channel.name} is not in ignore tip action list.')
                    return
            elif args[0].upper() == "MUTE":
                if MUTE_CHANNEL is None:
                    await store.sql_add_mutechan_by_server(str(ctx.guild.id), str(ctx.channel.id), str(ctx.author.id), ctx.author.name)
                    MUTE_CHANNEL = await store.sql_list_mutechan()
                    await ctx.send(f'{ctx.author.mention} Added #{ctx.channel.name} to mute. I will ignore anything here.')
                    return
                if str(ctx.guild.id) in MUTE_CHANNEL:
                    if str(ctx.channel.id) in MUTE_CHANNEL[str(ctx.guild.id)]:
                        await ctx.send(f'{ctx.author.mention} This channel #{ctx.channel.name} is already in mute mode.')
                        return
                    else:
                        await store.sql_add_mutechan_by_server(str(ctx.guild.id), str(ctx.channel.id), str(ctx.author.id), ctx.author.name)
                        MUTE_CHANNEL = await store.sql_list_mutechan()
                        await ctx.send(f'{ctx.author.mention} Added #{ctx.channel.name} to mute. I will ignore anything here.')
                        return
                else:
                    await store.sql_add_mutechan_by_server(str(ctx.guild.id), str(ctx.channel.id), str(ctx.author.id), ctx.author.name)
                    await ctx.send(f'{ctx.author.mention} Added #{ctx.channel.name} to mute. I will ignore anything here.')
                    return
            elif args[0].upper() == "UNMUTE":
                if str(ctx.guild.id) in MUTE_CHANNEL:
                    if str(ctx.channel.id) in MUTE_CHANNEL[str(ctx.guild.id)]:
                        await store.sql_del_mutechan_by_server(str(ctx.guild.id), str(ctx.channel.id))
                        MUTE_CHANNEL = await store.sql_list_mutechan()
                        await ctx.send(f'{ctx.author.mention} This channel #{ctx.channel.name} is unmute.')
                        return
                    else:
                        await ctx.send(f'{ctx.author.mention} Channel #{ctx.channel.name} is not mute right now!')
                        return
                else:
                    await ctx.send(f'{ctx.author.mention} Channel #{ctx.channel.name} is not mute right now!')
                    return
            elif args[0].upper() == "BOTCHAN" or args[0].upper() == "BOTCHANNEL" or args[0].upper() == "BOT_CHAN":
                if serverinfo['botchan']:
                    try: 
                        if ctx.channel.id == int(serverinfo['botchan']):
                            await ctx.send(f'{EMOJI_RED_NO} {ctx.channel.name} is already the bot channel here!')
                            return
                        else:
                            # change channel info
                            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'botchan', str(ctx.channel.id))
                            await ctx.send(f'Bot channel has set to {ctx.channel.mention}.')
                            await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} change bot channel {ctx.guild.name} / {ctx.guild.id} to #{ctx.channel.name}.')
                            return
                    except ValueError:
                        return
                else:
                    # change channel info
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'botchan', str(ctx.channel.id))
                    await ctx.send(f'Bot channel has set to {ctx.channel.mention}.')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed bot channel {ctx.guild.name} / {ctx.guild.id} to #{ctx.channel.name}.')
                    return
        elif len(args) == 2:
            if args[0].upper() == "TIPONLY":
                if (args[1].upper() not in (ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_NANO+ENABLE_XMR+ENABLE_COIN_TRC+ENABLE_XCH)) and (args[1].upper() not in ["ALLCOIN", "*", "ALL", "TIPALL", "ANY"]):
                    await ctx.send(f'{ctx.author.mention} {args[1].upper()} is not in any known coin we set.')
                    return
                else:
                    set_coin = args[1].upper()
                    if set_coin in ["ALLCOIN", "*", "ALL", "TIPALL", "ANY"]:
                        set_coin = "ALLCOIN"
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'tiponly', set_coin)
                    if set_coin == "ALLCOIN":
                        await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed tiponly in {ctx.guild.name} / {ctx.guild.id} to `ALLCOIN`')
                        await ctx.send(f'{ctx.author.mention} Any coin is **allowed** here.')
                    else:
                        await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed tiponly in {ctx.guild.name} / {ctx.guild.id} to `{args[1].upper()}`')
                        await ctx.send(f'{ctx.author.mention} {set_coin} will be the only tip here.')
                    return
            elif args[0].upper() == "PREFIX":
                if args[1] not in [".", "?", "*", "!", "$", "~"]:
                    await ctx.send(f'{ctx.author.mention} Invalid prefix **{args[1]}**')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} wanted to changed prefix in {ctx.guild.name} / {ctx.guild.id} to `{args[1].lower()}`')
                    return
                else:
                    if server_prefix == args[1]:
                        await ctx.send(f'{ctx.author.mention} That\'s the default prefix. Nothing changed.')
                        return
                    else:
                        changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'prefix', args[1].lower())
                        await ctx.send(f'{ctx.author.mention} Prefix changed from `{server_prefix}` to `{args[1].lower()}`.')
                        await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed prefix in {ctx.guild.name} / {ctx.guild.id} to `{args[1].lower()}`')
                        return
            elif args[0].upper() == "DEFAULT_COIN" or args[0].upper() == "DEFAULTCOIN" or args[0].upper() == "COIN":
                if args[1].upper() not in (ENABLE_COIN + ENABLE_XMR + ENABLE_COIN_DOGE + ENABLE_COIN_ERC + ENABLE_COIN_NANO + ENABLE_COIN_TRC + ENABLE_XCH):
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**!')
                    return
                else:
                    if server_coin.upper() == args[1].upper():
                        await ctx.send(f'{ctx.author.mention} That\'s the default coin. Nothing changed.')
                        return
                    else:
                        changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'default_coin', args[1].upper())
                        await ctx.send(f'Default Coin changed from `{server_coin}` to `{args[1].upper()}`.')
                        await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed default coin in {ctx.guild.name} / {ctx.guild.id} to {args[1].upper()}.')
                        return
            elif args[0].upper() == "REACTTIP":
                if args[1].upper() not in ["ON", "OFF"]:
                    await ctx.send('Invalid Option. **ON OFF** Only.')
                    return
                else:
                    if server_reacttip == args[1].upper():
                        await ctx.send(f'{ctx.author.mention} That\'s the default option already. Nothing changed.')
                        return
                    else:
                        changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'react_tip', args[1].upper())
                        await ctx.send(f'React Tip changed from `{server_reacttip}` to `{args[1].upper()}`.')
                        return
            elif args[0].upper() == "REACTAMOUNT" or args[0].upper() == "REACTTIP-AMOUNT":
                amount = args[1].replace(",", "")
                try:
                    amount = Decimal(amount)
                except ValueError:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
                    return
                changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'react_tip_100', amount)
                await ctx.send(f'React tip amount updated to to `{amount}{server_coin}`.')
                return
            else:
                await ctx.send(f'{ctx.author.mention} Invalid command input and parameter.')
                return
        elif len(args) >= 3:
            # If argument is more than 3, such as setting tiponly X Y ..
            if args[0].upper() == "TIPONLY":
                if args[1].upper() == "ALLCOIN" or args[1].upper() == "ALL" or args[1].upper() == "TIPALL" or args[1].upper() == "ANY" or args[1].upper() == "*":
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'tiponly', "ALLCOIN")
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed tiponly in {ctx.guild.name} / {ctx.guild.id} to `ALLCOIN`')
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                    await ctx.send(f'{ctx.author.mention} all coins will be allowed in here.')
                    return
                else:
                    try:
                        contained = [x.upper() for x in args if x.upper() in (ENABLE_COIN+ENABLE_XMR+ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_COIN_NANO+ENABLE_XCH)]
                        if contained and len(contained) >= 2:
                            tiponly_value = ','.join(contained)
                            await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed tiponly in {ctx.guild.name} / {ctx.guild.id} to `{tiponly_value}`')
                            await ctx.send(f'{ctx.author.mention} TIPONLY set to: **{tiponly_value}**.')
                            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'tiponly', tiponly_value.upper())
                            await ctx.message.add_reaction(EMOJI_OK_HAND)
                        else:
                            # Delete tiponly
                            del args[0]
                            list_coin = ', '.join(args)
                            await ctx.message.add_reaction(EMOJI_INFORMATION)
                            await ctx.send(f'{ctx.author.mention} No known coin in **{list_coin}**. TIPONLY is remained unchanged.')
                        return
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{ctx.author.mention} In valid setting command input and parameter(s).')
            return

    @commands.group(usage="guild <subcommand>", description="Various guild's command")
    async def guild(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be DM.')
            return

        prefix = await get_guild_prefix(ctx)
        if ctx.invoked_subcommand is None:
            await ctx.send(f'{ctx.author.mention} Invalid {prefix}guild command.\n Please use {prefix}help guild')
            return


    @guild.command(usage="guild deposit <coin>", description="Get deposit address of a coin for your guild.")
    async def deposit(self, ctx, amount: str, coin: str):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be DM.')
            return

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

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
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
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return
        # End of checking allowed coins

        if is_maintenance_coin(COIN_NAME):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
            return

        user_from = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
        if user_from is None:
            if COIN_NAME in ENABLE_COIN_ERC:
                w = await create_address_eth()
                user_from = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
            elif COIN_NAME in ENABLE_COIN_TRC:
                result = await store.create_address_trx()
                print(result)
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

        user_to = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
        if user_to is None:
            if coin_family == "ERC-20":
                w = await create_address_eth()
                userregister = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0, w)
            elif coin_family == "TRC-20":
                result = await store.create_address_trx()
                userregister = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0, result)
            else:
                userregister = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0)
            user_to = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)

        if coin_family == "ERC-20" or coin_family == "TRC-20":
            real_amount = float(amount)
            token_info = await store.get_token_info(COIN_NAME)
            MinTx = token_info['real_min_tip']
            MaxTX = token_info['real_max_tip']
        else:
            real_amount = int(Decimal(amount) * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
            MinTx = get_min_mv_amount(COIN_NAME)
            MaxTX = get_max_mv_amount(COIN_NAME)

        if real_amount > MaxTX:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than '
                           f'{num_format_coin(MaxTX, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return
        elif real_amount > actual_balance:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to transfer '
                           f'{num_format_coin(real_amount, COIN_NAME)} '
                           f'{COIN_NAME} to this guild **{ctx.guild.name}**.')
            return
        elif real_amount < MinTx:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than '
                           f'{num_format_coin(MinTx, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return

        # add queue also tip
        if ctx.author.id not in TX_IN_PROCESS:
            TX_IN_PROCESS.append(ctx.author.id)
        else:
            await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
            msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

        tip = None
        try:
            if coin_family in ["TRTL", "BCN"]:
                tip = await store.sql_mv_cn_single(str(ctx.author.id), str(ctx.guild.id), real_amount, 'GUILDDEPOSIT', COIN_NAME)
            elif coin_family == "XMR":
                tip = await store.sql_mv_xmr_single(str(ctx.author.id), str(ctx.guild.id), real_amount, COIN_NAME, "GUILDDEPOSIT")
            elif coin_family == "XCH":
                tip = await store.sql_mv_xch_single(str(ctx.author.id), str(ctx.guild.id), real_amount, COIN_NAME, "GUILDDEPOSIT")
            elif coin_family == "DOGE":
                tip = await store.sql_mv_doge_single(str(ctx.author.id), str(ctx.guild.id), real_amount, COIN_NAME, "GUILDDEPOSIT")
            elif coin_family == "NANO":
                tip = await store.sql_mv_nano_single(str(ctx.author.id), str(ctx.guild.id), real_amount, COIN_NAME, "GUILDDEPOSIT")
            elif coin_family == "ERC-20":
                tip = await store.sql_mv_erc_single(str(ctx.author.id), str(ctx.guild.id), real_amount, COIN_NAME, "GUILDDEPOSIT", token_info['contract'])
            elif coin_family == "TRC-20":
                tip = await store.sql_mv_trx_single(str(ctx.author.id), str(ctx.guild.id), real_amount, COIN_NAME, "GUILDDEPOSIT", token_info['contract'])
        except Exception as e:
            await logchanbot(traceback.format_exc())

        # remove queue from tip
        if ctx.author.id in TX_IN_PROCESS:
            TX_IN_PROCESS.remove(ctx.author.id)

        if tip:
            # Update tipstat
            try:
                update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
                update_tipstat = await store.sql_user_get_tipstat(str(ctx.guild.id), COIN_NAME, True, SERVER_BOT)
            except Exception as e:
                await logchanbot(traceback.format_exc())

            await ctx.message.add_reaction(get_emoji(COIN_NAME))
            # tipper shall always get DM. Ignore notifyList
            try:
                await ctx.send(f'{EMOJI_ARROW_RIGHTHOOK} {ctx.author.mention} **{num_format_coin(real_amount, COIN_NAME)} '
                               f'{COIN_NAME}** was transferred to {ctx.guild.name}.')
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                await store.sql_toggle_tipnotify(str(ctx.author.id), "OFF")
                try:
                    await ctx.author.send(f'{EMOJI_ARROW_RIGHTHOOK} {ctx.author.mention} **{num_format_coin(real_amount, COIN_NAME)} '
                                          f'{COIN_NAME}** was transferred to {ctx.guild.name}.')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    pass
            # TODO: notify guild owner, if fail, to logchannel
            guild_found = self.bot.get_guild(id=ctx.guild.id)
            if guild_found: user_found = self.bot.get_user(guild_found.owner.id)
            if guild_found and user_found:
                notifyList = await store.sql_get_tipnotify()
                if str(guild_found.owner.id) not in notifyList:
                    try:
                        await user_found.send(f'{EMOJI_MONEYFACE} Your guild **{ctx.guild.name}** got a deposit of **{num_format_coin(real_amount, COIN_NAME)} '
                                              f'{COIN_NAME}** from {ctx.author.name}#{ctx.author.discriminator} in `#{ctx.channel.name}`\n'
                                              f'{NOTIFICATION_OFF_CMD}\n')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        await store.sql_toggle_tipnotify(str(member.id), "OFF")
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{ctx.author.mention} Can not deliver TX for {COIN_NAME} right now. Try again soon.')
            # add to failed tx table
            await store.sql_add_failed_tx(COIN_NAME, str(ctx.author.id), ctx.author.name, real_amount, "TIP")
            return


    @guild.command(usage="guild tipmsg <message>", description="Set guild's tip's message.")
    @commands.has_permissions(manage_channels=True)
    async def tipmsg(self, ctx, *, tipmessage):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be DM.')
            return

        if 1000 <= len(tipmessage) <= 5:
            await ctx.send(f'{ctx.author.mention} Tip message is too short or too long.')
            return
        else:
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'tip_message', tipmessage)
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'tip_message_by', "{}#{}".format(ctx.author.name, ctx.author.discriminator))
            botLogChan = self.bot.get_channel(LOG_CHAN)
            try:
                await ctx.send(f'{ctx.author.mention} Tip message for this guild is updated.')
            except Exception as e:
                await logchanbot(traceback.format_exc())
            await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed tipmessage in {str(ctx.guild.id)}/{ctx.guild.name}.')
            return


    @guild.command(usage="createraffle <amount> <coin> <duration>", aliases=['crfl', 'create_raffle'], description="Create a raffle.")
    @commands.has_permissions(manage_channels=True)
    async def createraffle(self, ctx, amount: str, coin: str, duration: str):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be DM.')
            return
        prefix = await get_guild_prefix(ctx)
        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo['raffle_channel']:
            raffle_chan = self.bot.get_channel(int(serverinfo['raffle_channel']))
            if not raffle_chan:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Can not find raffle channel or invalid.') #Please set by {prefix}guild raffle set #channel
                return
        else:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} There is no raffle channel yet.') #Please set by {prefix}guild raffle set #channel
            return
        amount = amount.replace(",", "")
        try:
            amount = Decimal(amount)
        except ValueError:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} invalid amount {amount}!')
            return
        COIN_NAME = coin.upper()
        duration_accepted = ["1H", "2H", "3H", "4H", "5H", "6H", "12H", "1D", "2D", "3D", "4D", "5D", "6D", "7D"]
        duration_accepted_list = ", ".join(duration_accepted)
        duration = duration.upper()

        try:
            num_online = len([member for member in ctx.guild.members if member.bot == False and member.status != discord.Status.offline])
            if num_online < config.raffle.min_useronline:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Your guild needs to have at least : {str(config.raffle.min_useronline)} users online!')
                return
        except Exception as e:
            await logchanbot(traceback.format_exc())

        if COIN_NAME not in ENABLE_RAFFLE_COIN:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Un supported **TICKER**. Please choose one of this: {config.raffle.enable_coin}!')
            return

        if duration not in duration_accepted:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID DATE**! Please use {duration_accepted_list}')
            return

        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
            token_info = await store.get_token_info(COIN_NAME)
            decimal_pts = token_info['token_decimal']
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
            token_info = await store.get_token_info(COIN_NAME)
            decimal_pts = token_info['token_decimal']
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
            decimal_pts = int(math.log10(get_decimal(COIN_NAME)))

        if coin_family == "ERC-20" or coin_family == "TRC-20":
            real_amount = float(amount)
            token_info = await store.get_token_info(COIN_NAME)
            MinTx = token_info['real_min_tip']
            MaxTX = token_info['real_max_tip']
        else:
            real_amount = int(Decimal(amount) * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
            MinTx = get_min_mv_amount(COIN_NAME)
            MaxTX = get_max_mv_amount(COIN_NAME)

        if real_amount > MaxTX:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Raffle entry fee cannot be bigger than '
                           f'{num_format_coin(MaxTX, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return
        elif real_amount < MinTx:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Raffle entry fee cannot be smaller than '
                           f'{num_format_coin(MinTx, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return

        get_raffle = await store.raffle_get_from_guild(str(ctx.guild.id), False, SERVER_BOT)
        if get_raffle and get_raffle['status'] not in ["COMPLETED", "CANCELLED"]:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} There is still **ONGOING** or **OPENED** raffle!')
            return
        else:
            # Let's insert
            duration_in_s = 0
            try:
                if "D" in duration and "H" in duration:
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID DATE**! Please use {duration_accepted_list}\nExample: `{prefix}createraffle 10,000 WRKZ 2h`')
                    return
                elif "D" in duration:
                    duration_in_s = int(duration.replace("D", ""))*3600*24 # convert to second
                elif "H" in duration:
                    duration_in_s = int(duration.replace("H", ""))*3600 # convert to second
            except ValueError:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} invalid duration!\nExample: `{prefix}createraffle 10,000 WRKZ 2h`')
                return

            if duration_in_s <= 0:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} invalid duration!\nExample: `{prefix}createraffle 10,000 WRKZ 2h`')
                return
            try:
                start_ts = int(time.time())
                message_raffle = "{}#{} created a raffle for **{} {}** in guild `{}`. Raffle in **{}**.".format(ctx.author.name, ctx.author.discriminator, num_format_coin(real_amount, COIN_NAME), COIN_NAME,
                                                                                                         ctx.guild.name, duration)
                try:
                    msg = await ctx.send(message_raffle)
                    insert_raffle = await store.raffle_insert_new(str(ctx.guild.id), ctx.guild.name, real_amount, decimal_pts, COIN_NAME,
                                                                  str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator), 
                                                                  start_ts, start_ts+duration_in_s, SERVER_BOT)
                    await logchanbot(message_raffle)
                except Exception as e:
                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                    await logchanbot(traceback.format_exc())
                    print(traceback.format_exc())
            except Exception as e:
                await logchanbot(traceback.format_exc())
                print(traceback.format_exc())


    @guild.command(usage="guild raffle", aliases=['rfl'], description="Check current raffle.")
    async def raffle(self, ctx, subc: str=None):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be DM.')
            return
        prefix = await get_guild_prefix(ctx)
        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo['raffle_channel']:
            raffle_chan = self.bot.get_channel(int(serverinfo['raffle_channel']))
            if not raffle_chan:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Can not find raffle channel or invalid.') #Please set by {prefix}guild raffle set #channel
                return
        else:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} There is no raffle channel yet.') #Please set by {prefix}guild raffle set #channel
            return

        if subc is None:
            subc = "INFO"
        else:
            subc = subc.upper()

        get_raffle = await store.raffle_get_from_guild(str(ctx.guild.id), False, SERVER_BOT)
        list_raffle_id = None
        if get_raffle:
            list_raffle_id = await store.raffle_get_from_by_id(get_raffle['id'], SERVER_BOT, str(ctx.author.id))
        subc_list = ["INFO", "LAST", "JOIN", "CHECK"]
        if subc not in subc_list:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID SUB COMMAND**!')
            return
        else:
            if get_raffle is None:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} There is no information of current raffle yet!')
                return
        try:
            if ctx.author.bot == True:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is not allowed!')
                return
        except Exception as e:
            pass

        if subc == "INFO":
            try:
                ending_ts = datetime.utcfromtimestamp(int(get_raffle['ending_ts']))
                embed = discord.Embed(title = "RAFFLE #{} / {}".format(get_raffle['id'], ctx.guild.name), color = 0xFF0000, timestamp=ending_ts)
                embed.add_field(name="ENTRY FEE", value="{} {}".format(num_format_coin(get_raffle['amount'], get_raffle['coin_name']), get_raffle['coin_name']), inline=True)
                create_ts = datetime.utcfromtimestamp(int(get_raffle['created_ts'])).strftime("%Y-%m-%d %H:%M:%S")
                create_ts_ago = str(timeago.format(create_ts, datetime.utcnow()))
                embed.add_field(name="CREATED", value=create_ts_ago, inline=True)
                if list_raffle_id and list_raffle_id['entries']:
                    embed.add_field(name="PARTICIPANTS", value=len(list_raffle_id['entries']), inline=True)
                    if 0 < len(list_raffle_id['entries']) < 20:
                        list_ping = []
                        for each_user in list_raffle_id['entries']:
                            list_ping.append(each_user['user_name'])
                        embed.add_field(name="PARTICIPANT LIST", value=", ".join(list_ping), inline=False)
                    embed.add_field(name="RAFFLE JAR", value=num_format_coin(len(list_raffle_id['entries'])*float(get_raffle['amount']), get_raffle['coin_name'])+" "+get_raffle['coin_name'], inline=True)
                else:
                    embed.add_field(name="PARTICIPANTS", value="0", inline=True)
                embed.add_field(name="STATUS", value=get_raffle['status'], inline=True)
                if get_raffle['status'] in ["OPENED", "ONGOING"]:
                    if int(get_raffle['ending_ts'])-int(time.time()) < 0:
                        embed.add_field(name="WHEN", value="(ON QUEUE UPDATING)", inline=False)
                    else:
                        embed.add_field(name="WHEN", value=seconds_str_days(int(get_raffle['ending_ts'])-int(time.time())), inline=False)
                embed.set_footer(text="Raffle for {} by {}".format(ctx.guild.name, get_raffle['created_username']))
                msg = await ctx.send(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
            except Exception as e:
                print(traceback.format_exc())
                await logchanbot(traceback.format_exc())
        elif subc == "JOIN":
            if get_raffle is None:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} There is no information of current raffle yet for this guild {ctx.guild.name}!')
                return
            else:
                # Check if already in:
                # If not in, add to DB
                # If current is not opened
                try:
                    if get_raffle['status'] != "OPENED":
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} There is no **OPENED** game raffle on this guild {ctx.guild.name}!')
                        return
                    else:
                        raffle_id = get_raffle['id']
                        if list_raffle_id and list_raffle_id['user_joined']:
                            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You already join this raffle #**{str(raffle_id)}** in guild {ctx.guild.name}!')
                            return
                        else:
                            COIN_NAME = get_raffle['coin_name']
                            # Get balance user first
                            user_entry = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                            if user_entry is None:
                                if COIN_NAME in ENABLE_COIN_ERC:
                                    w = await create_address_eth()
                                    user_entry = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
                                elif COIN_NAME in ENABLE_COIN_TRC:
                                    result = await store.create_address_trx()
                                    user_entry = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, result)
                                else:
                                    user_entry = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
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
                            if actual_balance < get_raffle['amount']:
                                fee_str = num_format_coin(get_raffle['amount'], COIN_NAME) + " " + COIN_NAME
                                having_str = num_format_coin(actual_balance, COIN_NAME) + " " + COIN_NAME
                                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to join raffle entry. '
                                               f'Fee: {fee_str}, having: {having_str}.')
                                return
                            # Let's add
                            try:
                                ## add QUEUE:
                                if ctx.author.id not in GAME_RAFFLE_QUEUE:
                                    GAME_RAFFLE_QUEUE.append(ctx.author.id)
                                else:
                                    await ctx.send(f'{ctx.author.mention} You already on queue of joinining.')
                                    return
                                insert_entry = await store.raffle_insert_new_entry(get_raffle['id'], str(ctx.guild.id), get_raffle['amount'], get_raffle['decimal'],
                                                                                   get_raffle['coin_name'], str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator),
                                                                                   SERVER_BOT)
                                note_entry = num_format_coin(get_raffle['amount'], get_raffle['coin_name']) + " " + get_raffle['coin_name'] + " is deducted from your balance."
                                msg = await ctx.send(f'{EMOJI_CHECK} {ctx.author.mention} Successfully registered your Entry for raffle #**{raffle_id}** in {ctx.guild.name}! {note_entry}')
                                await msg.add_reaction(EMOJI_OK_BOX)
                                # Update tipstat
                                try:
                                    update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), get_raffle['coin_name'], True, SERVER_BOT)
                                except Exception as e:
                                    await logchanbot(traceback.format_exc())
                            except Exception as e:
                                print(traceback.format_exc())
                                await logchanbot(traceback.format_exc())
                            ## remove QUEUE:
                            if ctx.author.id in GAME_RAFFLE_QUEUE:
                                GAME_RAFFLE_QUEUE.remove(ctx.author.id)
                            return
                except Exception as e:
                    print(traceback.format_exc())
                    await logchanbot(traceback.format_exc())
        elif subc == "CHECK":
            if get_raffle is None:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} There is no information of current raffle yet!')
                return
            else:
                # If current is not opened
                try:
                    raffle_id = get_raffle['id']
                    if get_raffle['status'] == "OPENED":
                        await ctx.send(f'{ctx.author.mention} Current raffle #{raffle_id} for guild {ctx.guild.name} is **OPENED**!')
                        return
                    elif get_raffle['status'] == "ONGOING":
                        await ctx.send(f'{ctx.author.mention} Current raffle #{raffle_id} for guild {ctx.guild.name} is **ONGOING**!')
                        return
                    elif get_raffle['status'] == "COMPLETED":
                        await ctx.send(f'{ctx.author.mention} Current raffle #{raffle_id} for guild {ctx.guild.name} is **COMPLETED**!')
                        return
                    elif get_raffle['status'] == "CANCELLED":
                        await ctx.send(f'{ctx.author.mention} Current raffle #{raffle_id} for guild {ctx.guild.name} is **CANCELLED**!')
                        return
                except Exception as e:
                    print(traceback.format_exc())
                    await logchanbot(traceback.format_exc())
        elif subc == "LAST":
            if get_raffle is None:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} There is no information of current raffle yet!')
                return

    async def check_raffle_status():
        time_lap = 20 # seconds
        announce_lap = 3600 # seconds
        to_close_fromopen = 300 # second
        while not self.bot.is_closed():
            await asyncio.sleep(time_lap)
            # Announce every announce_lap in raffle channel if there is any raffle opened
            # Get all list of raffle
            # Change guild_raffle status from OPENED to ONGOING (1h) if less than 1h to start
            # Change guild_raffle status from ONGOING to CANCELLED if less than 3 users registered, => change `guild_raffle_entries` status to CANCELLED
            # Change guild_raffle status from ONGOING to COMPLETED, random users for winner and update => 
            #       winner_userid_1st	varchar(32) NULL	
            #       winner_name_1st	varchar(64) NULL	
            #       winner_1st_amount	decimal(64,20) NULL	
            #       winner_userid_2nd	varchar(32) NULL	
            #       winner_name_2nd	varchar(64) NULL	
            #       winner_2nd_amount	decimal(64,20) NULL	
            #       winner_userid_3rd	varchar(32) NULL	
            #       winner_name_3rd	varchar(64) NULL	
            #       winner_3rd_amount	decimal(64,20) NULL	
            #       raffle_fund_pot	decimal(64,20) NULL
            # Try DM user if they are winner, and if they are loser
            get_all_active_raffle = await store.raffle_get_all(SERVER_BOT)
            if get_all_active_raffle and len(get_all_active_raffle) > 0:
                for each_raffle in get_all_active_raffle:
                    # loop each raffle
                    try:
                        if each_raffle['status'] == "OPENED":
                            if each_raffle['ending_ts'] - to_close_fromopen < int(time.time()):
                                # less than 3 participants, cancel
                                list_raffle_id = await store.raffle_get_from_by_id(each_raffle['id'], SERVER_BOT, None)
                                if (list_raffle_id and list_raffle_id['entries'] and len(list_raffle_id['entries']) < 3) or \
                                (list_raffle_id and list_raffle_id['entries'] is None):
                                    # Cancel game
                                    cancelled_status = await store.raffle_cancel_id(each_raffle['id'])
                                    msg_raffle = "Cancelled raffle #{} in guild {}: **Shortage of users**. User entry fee refund!".format(each_raffle['id'], each_raffle['guild_name'])
                                    serverinfo = await store.sql_info_by_server(each_raffle['guild_id'])
                                    if serverinfo['raffle_channel']:
                                        raffle_chan = self.bot.get_channel(int(serverinfo['raffle_channel']))
                                        if raffle_chan:
                                            await raffle_chan.send(msg_raffle)
                                    await logchanbot(msg_raffle)                                
                                else:
                                    # change status from Open to ongoing
                                    update_status = await store.raffle_update_id(each_raffle['id'], 'ONGOING', None, None)
                                    if update_status:
                                        msg_raffle = "Changed raffle #{} status to **ONGOING** in guild {}/{}! ".format(each_raffle['id'], each_raffle['guild_name'], each_raffle['guild_id'])
                                        msg_raffle += "Raffle will start in **{}**".format(seconds_str(to_close_fromopen))
                                        serverinfo = await store.sql_info_by_server(each_raffle['guild_id'])                                        
                                        if serverinfo['raffle_channel']:
                                            raffle_chan = self.bot.get_channel(int(serverinfo['raffle_channel']))
                                            if raffle_chan:
                                                await raffle_chan.send(msg_raffle)
                                                try:
                                                    # Ping users
                                                    list_ping = []
                                                    for each_user in list_raffle_id['entries']:
                                                        list_ping.append("<@{}>".format(each_user['user_id']))
                                                    await raffle_chan.send(", ".join(list_ping))
                                                except Exception as e:
                                                    print(traceback.format_exc())
                                                    await logchanbot(traceback.format_exc()) 
                                        await logchanbot(msg_raffle)
                                    else:
                                        await logchanbot(f"Internal error to {msg_raffle}")
                        elif each_raffle['status'] == "ONGOING":
                            if each_raffle['ending_ts'] < int(time.time()):
                                # Let's random and update
                                list_raffle_id = await store.raffle_get_from_by_id(each_raffle['id'], SERVER_BOT, None)
                                # This is redundant with above!
                                if list_raffle_id and list_raffle_id['entries'] and len(list_raffle_id['entries']) < 3:
                                    # Cancel game
                                    cancelled_status = await store.raffle_cancel_id(each_raffle['id'])
                                    msg_raffle = "Cancelled raffle #{} in guild {}: shortage of users. User entry fee refund!".format(each_raffle['id'], each_raffle['guild_id'])
                                    serverinfo = await store.sql_info_by_server(each_raffle['guild_id'])
                                    if serverinfo['raffle_channel']:
                                        raffle_chan = self.bot.get_channel(int(serverinfo['raffle_channel']))
                                        if raffle_chan:
                                            await raffle_chan.send(msg_raffle)
                                    await logchanbot(msg_raffle)
                                if list_raffle_id and list_raffle_id['entries'] and len(list_raffle_id['entries']) >= 3:
                                    entries_id = []
                                    user_entries_id = {}
                                    user_entries_name = {}
                                    list_winners = []
                                    won_amounts = []
                                    total_reward = 0
                                    for each_entry in list_raffle_id['entries']:
                                        entries_id.append(each_entry['entry_id'])
                                        user_entries_id[each_entry['entry_id']] = each_entry['user_id']
                                        user_entries_name[each_entry['entry_id']] = each_entry['user_name']
                                        total_reward += each_entry['amount']
                                    winner_1 = random.choice(entries_id)
                                    winner_1_user = user_entries_id[winner_1]
                                    winner_1_name = user_entries_name[winner_1]
                                    entries_id.remove(winner_1)
                                    list_winners.append(winner_1_user)
                                    won_amounts.append(float(total_reward) * 0.5)

                                    winner_2 = random.choice(entries_id)
                                    winner_2_user = user_entries_id[winner_2]
                                    winner_2_name = user_entries_name[winner_2]
                                    entries_id.remove(winner_2)
                                    list_winners.append(winner_2_user)
                                    won_amounts.append(float(total_reward) * 0.3)

                                    winner_3 = random.choice(entries_id)
                                    winner_3_user = user_entries_id[winner_3]
                                    winner_3_name = user_entries_name[winner_3]
                                    entries_id.remove(winner_3)
                                    list_winners.append(winner_3_user)
                                    won_amounts.append(float(total_reward) * 0.19)
                                    won_amounts.append(float(total_reward) * 0.01)
                                    update_status = await store.raffle_update_id(each_raffle['id'], 'COMPLETED', list_winners, won_amounts)
                                    embed = discord.Embed(title = "RAFFLE #{} / {}".format(each_raffle['id'], each_raffle['guild_name']), color = 0xFF0000, timestamp=datetime.utcnow())
                                    embed.add_field(name="ENTRY FEE", value="{} {}".format(num_format_coin(each_raffle['amount'], each_raffle['coin_name']), each_raffle['coin_name']), inline=True)
                                    embed.add_field(name="1st WINNER: {}".format(winner_1_name), value="{} {}".format(num_format_coin(won_amounts[0], each_raffle['coin_name']), each_raffle['coin_name']), inline=False)
                                    embed.add_field(name="2nd WINNER: {}".format(winner_2_name), value="{} {}".format(num_format_coin(won_amounts[1], each_raffle['coin_name']), each_raffle['coin_name']), inline=False)
                                    embed.add_field(name="3rd WINNER: {}".format(winner_3_name), value="{} {}".format(num_format_coin(won_amounts[2], each_raffle['coin_name']), each_raffle['coin_name']), inline=False)
                                    embed.set_footer(text="Raffle for {} by {}".format(each_raffle['guild_name'], each_raffle['created_username']))
                                    
                                    msg_raffle = "**Completed raffle #{} in guild {}! Winner entries: #1: {}, #2: {}, #3: {}**\n".format(each_raffle['id'], each_raffle['guild_name'], winner_1_name, winner_2_name, winner_3_name)
                                    msg_raffle += "```Three winners get reward of #1: {}{}, #2: {}{}, #3: {}{}```".format(num_format_coin(won_amounts[0], each_raffle['coin_name']), each_raffle['coin_name'],
                                                                                                                   num_format_coin(won_amounts[1], each_raffle['coin_name']), each_raffle['coin_name'],
                                                                                                                   num_format_coin(won_amounts[2], each_raffle['coin_name']), each_raffle['coin_name'])
                                    serverinfo = await store.sql_info_by_server(each_raffle['guild_id'])
                                    if serverinfo['raffle_channel']:
                                        raffle_chan = self.bot.get_channel(int(serverinfo['raffle_channel']))
                                        if raffle_chan:
                                            await raffle_chan.send(embed=embed)
                                    await logchanbot(msg_raffle)
                                    for each_entry in list_winners:
                                        # Update tipstat
                                        try:
                                            update_tipstat = await store.sql_user_get_tipstat(str(each_entry), each_raffle['coin_name'], True, SERVER_BOT)
                                        except Exception as e:
                                            await logchanbot(traceback.format_exc())
                                        try:
                                            # Find user
                                            user_found = self.bot.get_user(int(each_entry))
                                            if user_found:
                                                try:
                                                    await user_found.send(embed=embed)
                                                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                                    print(traceback.format_exc())
                                                    await logchanbot(f"[Discord]/Raffle can not message to {user_found.name}#{user_found.discriminator} about winning raffle.")
                                                # TODO update alert win
                                            else:
                                                await logchanbot('[Discord]/Raffle Can not find entry id: {}'.format(each_entry))
                                        except Exception as e:
                                            print(traceback.format_exc())
                                            await logchanbot(traceback.format_exc())
                    except Exception as e:
                        print(traceback.format_exc())
                        await logchanbot(traceback.format_exc())
            await asyncio.sleep(time_lap)


    @guild.command(usage="botchan", aliases=['botchannel', 'bot_chan'], description="Set bot channel to the said channel.")
    @commands.has_permissions(manage_channels=True)
    async def botchan(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be DM.')
            return

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo['botchan']:
            try: 
                botLogChan = self.bot.get_channel(LOG_CHAN)
                if ctx.channel.id == int(serverinfo['botchan']):
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.channel.mention} is already the bot channel here!')
                    return
                else:
                    # change channel info
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'botchan', str(ctx.channel.id))
                    await ctx.message.reply(f'Bot channel has set to {ctx.channel.mention}.')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} change bot channel {ctx.guild.name} / {ctx.guild.id} to #{ctx.channel.name}.')
                    return
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                await logchanbot(traceback.format_exc())
        else:
            # change channel info
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'botchan', str(ctx.channel.id))
            await ctx.message.reply(f'Bot channel has set to {ctx.channel.mention}.')
            await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed bot channel {ctx.guild.name} / {ctx.guild.id} to #{ctx.channel.name}.')
            return


    @guild.command(usage="gamechan <game name>", aliases=['gamechannel', 'game_chan'], description="Set game channel to the said channel.")
    @commands.has_permissions(manage_channels=True)
    async def gamechan(self, ctx, *, game: str=None):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be DM.')
            return

        game_list = config.game.game_list.split(",")
        if game is None:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.channel.mention} please mention a game name to set game channel for it. Game list: {config.game.game_list}.')
            return
        else:
            game = game.lower()
            if game not in game_list:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.channel.mention} please mention a game name within this list: {config.game.game_list}.')
                return
            else:
                botLogChan = self.bot.get_channel(LOG_CHAN)
                serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                index_game = "game_" + game + "_channel"
                if serverinfo[index_game]:
                    try: 
                        if ctx.channel.id == int(serverinfo[index_game]):
                            await ctx.send(f'{EMOJI_RED_NO} {ctx.channel.mention} is already for game **{game}** channel here!')
                            return
                        else:
                            # change channel info
                            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), index_game, str(ctx.channel.id))
                            await ctx.send(f'{ctx.channel.mention} Game **{game}** channel has set to {ctx.channel.mention}.')
                            await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed game **{game}** in channel {ctx.guild.name} / {ctx.guild.id} to #{ctx.channel.name}.')
                            return
                    except Exception as e:
                        traceback.print_exc(file=sys.stdout)
                        await logchanbot(traceback.format_exc())
                else:
                    # change channel info
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), index_game, str(ctx.channel.id))
                    await ctx.send(f'{ctx.channel.mention} Game **{game}** channel has set to {ctx.channel.mention}.')
                    await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} set game **{game}** channel in {ctx.guild.name} / {ctx.guild.id} to #{ctx.channel.name}.')
                    return


    @guild.command(usage="guild prefix <prefix>", description="Change prefix command in your guild.")
    @commands.has_permissions(manage_channels=True)
    async def prefix(self, ctx, prefix_char: str=None):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.send(f'{ctx.author.mention} This command can not be DM.')
            return
        if prefix_char is None:
            await ctx.send(f'{ctx.author.mention} Default prefix to `{config.discord.prefixCmd}`.')
            return

        if prefix_char not in [".", "?", "*", "!", "$", "~"]:
            await ctx.send(f'{ctx.author.mention} Invalid prefix **{prefix_char}**')
            await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} wanted to changed prefix in {ctx.guild.name} / {ctx.guild.id} to `{prefix_char.lower()}`')
            return
        else:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            server_prefix = serverinfo['server_prefix']
            if server_prefix == prefix_char:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{ctx.author.mention} That\'s the default prefix. Nothing changed.')
                return
            else:
                changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'prefix', prefix_char.lower())
                await ctx.send(f'{ctx.author.mention} Prefix changed from `{server_prefix}` to `{prefix_char.lower()}`.')
                await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed prefix in {ctx.guild.name} / {ctx.guild.id} to `{prefix_char.lower()}`')
                return


    @commands.command(usage='mdeposit [coin] <plain/embed>', description="Get your a deposit address for a guild.")
    async def mdeposit(self, ctx, coin_name: str, option: str=None):
        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'mdeposit')
        if account_lock:
            await ctx.message.add_reaction(EMOJI_LOCKED) 
            await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
            return
        # end of check if account locked

        # disable guild tip for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

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

        try:
            if COIN_NAME in ENABLE_COIN_ERC:
                coin_family = "ERC-20"
            elif COIN_NAME in ENABLE_COIN_TRC:
                coin_family = "TRC-20"
            else:
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
            wallet = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
            if wallet is None:
                userregister = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0)
                wallet = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
        elif coin_family == "XMR":
            wallet = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
            if wallet is None:
                userregister = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0)
                wallet = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
        elif coin_family == "DOGE":
            wallet = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
            if wallet is None:
                wallet = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0)
                wallet = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
        elif coin_family == "NANO":
            wallet = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
            if wallet is None:
                wallet = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0)
                wallet = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
        elif coin_family == "ERC-20":
            wallet = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
            if wallet is None:
                w = await create_address_eth()
                wallet = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0, w)
                wallet = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
        elif coin_family == "TRC-20":
            wallet = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
            if wallet is None:
                result = await store.create_address_trx()
                wallet = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0, result)
                wallet = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
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
                msg = await ctx.message.reply(f'{ctx.author.mention} Guild {ctx.guild.name} **{COIN_NAME}**\'s deposit address (not yours): ```{deposit}```')
                await msg.add_reaction(EMOJI_OK_BOX)
                await ctx.message.add_reaction(EMOJI_OK_HAND)
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
            return

        embed = discord.Embed(title=f'**Guild {ctx.guild.name}** deposit / **{COIN_NAME}**', description='`This is guild\'s tipjar address. Do not deposit here unless you want to deposit to this guild and not yours!`', timestamp=datetime.utcnow(), colour=7047495)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
        embed.add_field(name="{} Deposit Address".format(COIN_NAME), value="`{}`".format(wallet['balance_wallet_address']), inline=False)
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
        embed.set_footer(text=f"Use:{prefix}mdeposit {COIN_NAME} plain (for plain text)")
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


    @commands.command(usage='mbalance [coin]', aliases=['mbal'], description="Get your guild's balance.")
    async def mbalance(self, ctx, coin: str = None):
        prefix = await get_guild_prefix(ctx)
        botLogChan = self.bot.get_channel(LOG_CHAN)
        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'mbalance')
        if account_lock:
            await ctx.message.add_reaction(EMOJI_LOCKED) 
            await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
            return
        # end of check if account locked

        # disable guild tip for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        # If DM, error
        if isinstance(ctx.message.channel, discord.DMChannel) == True:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} This command is available only in public channel (Guild).')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return

        COIN_NAME = None
        embed = discord.Embed(title=f'[ GUILD {ctx.guild.name} BALANCE ]', timestamp=datetime.utcnow())
        any_balance = 0
        if coin is None:
            for COIN_NAME in [coinItem.upper() for coinItem in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH]:
                if not is_maintenance_coin(COIN_NAME):
                    wallet = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
                    if wallet is None:
                        if COIN_NAME in ENABLE_COIN_ERC:
                            w = await create_address_eth()
                            userregister = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0, w)
                        elif COIN_NAME in ENABLE_COIN_TRC:
                            result = await store.create_address_trx()
                            userregister = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0, result)
                        else:
                            userregister = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0)
                        wallet = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
                    if wallet is None:
                        await botLogChan.send(f'A user call `{prefix}mbalance` failed with {COIN_NAME} in guild {ctx.guild.id} / {ctx.guild.name} / # {ctx.message.channel.name} ')
                        return
                    else:
                        userdata_balance = await store.sql_user_balance(str(ctx.guild.id), COIN_NAME)
                        xfer_in = 0
                        if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                            xfer_in = await store.sql_user_balance_get_xfer_in(str(ctx.guild.id), COIN_NAME)
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
                                msg_negative = 'Negative balance detected:\nGuild: '+str(ctx.guild.id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
                                await logchanbot(msg_negative)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                        balance_actual = num_format_coin(actual_balance, COIN_NAME)
                        coinName = COIN_NAME
                        if actual_balance > 0:
                            any_balance += 1
                            embed.add_field(name=COIN_NAME, value=balance_actual+" "+COIN_NAME, inline=True)
            if any_balance == 0:
                embed.add_field(name="INFO", value='`This guild has no balance for any coin yet.`', inline=True)
            embed.add_field(name='Related commands', value=f'`{prefix}mbalance TICKER` or `{prefix}mdeposit TICKER`', inline=False)
            embed.set_footer(text=f"Guild balance requested by {ctx.author.name}#{ctx.author.discriminator}")
            try:
                msg = await ctx.message.reply(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
            return
        else:
            COIN_NAME = coin.upper()

        if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**!')
            return

        try:
            if COIN_NAME in ENABLE_COIN_ERC:
                coin_family = "ERC-20"
            elif COIN_NAME in ENABLE_COIN_TRC:
                coin_family = "TRC-20"
            else:
                coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
        except Exception as e:
            await logchanbot(traceback.format_exc())
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**')
            return

        if is_maintenance_coin(COIN_NAME) and ctx.author.id not in MAINTENANCE_OWNER:
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            msg = await ctx.message.reply(f'{EMOJI_RED_NO} {COIN_NAME} in maintenance.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

        if COIN_NAME in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
            wallet = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
            if wallet is None:
                if COIN_NAME in ENABLE_COIN_ERC:
                    w = await create_address_eth()
                    userregister = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0, w)
                elif COIN_NAME in ENABLE_COIN_TRC:
                    result = await store.create_address_trx()
                    userregister = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0, result)
                else:
                    userregister = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0)
            userdata_balance = await store.sql_user_balance(str(ctx.guild.id), COIN_NAME)
            xfer_in = 0
            if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                xfer_in = await store.sql_user_balance_get_xfer_in(str(ctx.guild.id), COIN_NAME)
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
                    msg_negative = 'Negative balance detected:\nGuild: '+str(ctx.guild.id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
                    await logchanbot(msg_negative)
            except Exception as e:
                await logchanbot(traceback.format_exc())

            balance_actual = num_format_coin(actual_balance, COIN_NAME)
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            msg = await ctx.message.reply(f'**[GUILD {ctx.guild.name} - {COIN_NAME} BALANCE ]**\n\n'
                    f'{EMOJI_MONEYBAG} Available: {balance_actual} '
                    f'{COIN_NAME}\n'
                    f'{get_notice_txt(COIN_NAME)}')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        else:
            msg = await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} There is no such ticker {COIN_NAME}.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return


def setup(bot):
    bot.add_cog(Guild(bot))