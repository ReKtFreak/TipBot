import asyncio
import re
import sys
import time
import traceback
from datetime import datetime
import random
import qrcode

import discord
from discord.ext import tasks, commands
from dislash import InteractionClient, ActionRow, Button, ButtonStyle, Option, OptionType, OptionChoice, SlashInteraction
import dislash

import store
from Bot import *

from config import config


class Guild(commands.Cog):

    def __init__(self, bot):
        self.check_raffle_status.start()
        self.bot = bot
        self.botLogChan = self.bot.get_channel(LOG_CHAN)


    @tasks.loop(seconds=10.0)
    async def check_raffle_status(self):
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
                                                    traceback.print_exc(file=sys.stdout)
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
                                                    traceback.print_exc(file=sys.stdout)
                                                    await logchanbot(f"[Discord]/Raffle can not message to {user_found.name}#{user_found.discriminator} about winning raffle.")
                                                # TODO update alert win
                                            else:
                                                await logchanbot('[Discord]/Raffle Can not find entry id: {}'.format(each_entry))
                                        except Exception as e:
                                            traceback.print_exc(file=sys.stdout)
                                            await logchanbot(traceback.format_exc())
                    except Exception as e:
                        traceback.print_exc(file=sys.stdout)
                        await logchanbot(traceback.format_exc())
            await asyncio.sleep(time_lap)
            break


    async def bot_log(self):
        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def guild_createraffle(
        self,
        ctx,
        amount: float, 
        coin: str, 
        duration: str
    ):
        await self.bot_log()
        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        prefix = await get_guild_prefix(ctx)
        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo['raffle_channel']:
            raffle_chan = self.bot.get_channel(int(serverinfo['raffle_channel']))
            if not raffle_chan:
                return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Can not find raffle channel or invalid."}
        else:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} There is no raffle channel yet."}

        try:
            amount = Decimal(amount)
        except ValueError:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} invalid amount {amount}!"}
        COIN_NAME = coin.upper()
        duration_accepted = ["1H", "2H", "3H", "4H", "5H", "6H", "12H", "1D", "2D", "3D", "4D", "5D", "6D", "7D"]
        duration_accepted_list = ", ".join(duration_accepted)
        duration = duration.upper()

        try:
            num_online = len([member for member in ctx.guild.members if member.bot == False and member.status != discord.Status.offline])
            if num_online < config.raffle.min_useronline and config.raffle.test_mode != 1:
                return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Your guild needs to have at least: {str(config.raffle.min_useronline)} users online!"}
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())

        if COIN_NAME not in ENABLE_RAFFLE_COIN:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Unsupported **TICKER**. Please choose one of this: {config.raffle.enable_coin}!"}

        if duration not in duration_accepted:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} **INVALID DATE**! Please use {duration_accepted_list}"}

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
            MaxTx = token_info['real_max_tip']
        else:
            real_amount = int(Decimal(amount) * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
            MinTx = get_min_mv_amount(COIN_NAME)
            MaxTx = get_max_mv_amount(COIN_NAME)

        if real_amount > MaxTx:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Raffle entry fee cannot be bigger than {num_format_coin(MaxTx, COIN_NAME)} {COIN_NAME}."}
        elif real_amount < MinTx:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Raffle entry fee cannot be smaller than {num_format_coin(MinTx, COIN_NAME)} {COIN_NAME}."}

        get_raffle = await store.raffle_get_from_guild(str(ctx.guild.id), False, SERVER_BOT)
        if get_raffle and get_raffle['status'] not in ["COMPLETED", "CANCELLED"]:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} There is still **ONGOING** or **OPENED** raffle!"}
        else:
            # Let's insert
            duration_in_s = 0
            try:
                if "D" in duration and "H" in duration:
                    return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} **INVALID DATE**! Please use {duration_accepted_list}\nExample: `{prefix}createraffle 10,000 WRKZ 2h`"}
                elif "D" in duration:
                    duration_in_s = int(duration.replace("D", ""))*3600*24 # convert to second
                elif "H" in duration:
                    duration_in_s = int(duration.replace("H", ""))*3600 # convert to second
            except ValueError:
                return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} invalid duration!\nExample: `{prefix}createraffle 10,000 WRKZ 2h`"}

            if duration_in_s <= 0:
                return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} invalid duration!\nExample: `{prefix}createraffle 10,000 WRKZ 2h`"}
            try:
                start_ts = int(time.time())
                message_raffle = "{}#{} created a raffle for **{} {}** in guild `{}`. Raffle in **{}**.".format(ctx.author.name, ctx.author.discriminator, num_format_coin(real_amount, COIN_NAME), COIN_NAME,
                                                                                                         ctx.guild.name, duration)
                try:
                    msg = await ctx.reply(message_raffle)
                    insert_raffle = await store.raffle_insert_new(str(ctx.guild.id), ctx.guild.name, real_amount, decimal_pts, COIN_NAME,
                                                                  str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator), 
                                                                  start_ts, start_ts+duration_in_s, SERVER_BOT)
                    await logchanbot(message_raffle)
                    return {"result": True}
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
                    await logchanbot(f"Failed to message raffle creation in guild {ctx.guild.name} / {ctx.guild.id} ")
            except Exception as e:
                await logchanbot(traceback.format_exc())
                traceback.print_exc(file=sys.stdout)


    async def guild_raffle(
        self,
        ctx,
        subc: str=None
    ):
        await self.bot_log()
        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        prefix = await get_guild_prefix(ctx)
        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo['raffle_channel']:
            raffle_chan = self.bot.get_channel(int(serverinfo['raffle_channel']))
            if not raffle_chan:
                return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Can not find raffle channel or invalid."}
        else:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} There is no raffle channel yet."}

        if subc is None:
            subc = "INFO"
        subc = subc.upper()

        get_raffle = await store.raffle_get_from_guild(str(ctx.guild.id), False, SERVER_BOT)
        list_raffle_id = None
        if get_raffle:
            list_raffle_id = await store.raffle_get_from_by_id(get_raffle['id'], SERVER_BOT, str(ctx.author.id))
        subc_list = ["INFO", "LAST", "JOIN", "CHECK"]
        if subc not in subc_list:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} **INVALID SUB COMMAND**!"}
        else:
            if get_raffle is None:
                return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} There is no information of current raffle yet!"}
        try:
            if ctx.author.bot == True:
                return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Bot is not allowed!"}
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
                msg = await ctx.reply(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                await logchanbot(traceback.format_exc())
        elif subc == "JOIN":
            if get_raffle is None:
                return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} There is no information of current raffle yet for this guild {ctx.guild.name}!"}
            else:
                # Check if already in:
                # If not in, add to DB
                # If current is not opened
                try:
                    if get_raffle['status'] != "OPENED":
                        return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} There is no **OPENED** game raffle on this guild {ctx.guild.name}!"}
                    else:
                        raffle_id = get_raffle['id']
                        if list_raffle_id and list_raffle_id['user_joined']:
                            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} You already join this raffle #**{str(raffle_id)}** in guild {ctx.guild.name}!"}
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
                                return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to join raffle entry. Fee: {fee_str}, having: {having_str}."}
                            # Let's add
                            try:
                                ## add QUEUE:
                                if ctx.author.id not in GAME_RAFFLE_QUEUE:
                                    GAME_RAFFLE_QUEUE.append(ctx.author.id)
                                else:
                                    return {"error": f"{ctx.author.mention} You already on queue of joinining."}
                                insert_entry = await store.raffle_insert_new_entry(get_raffle['id'], str(ctx.guild.id), get_raffle['amount'], get_raffle['decimal'],
                                                                                   get_raffle['coin_name'], str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator),
                                                                                   SERVER_BOT)
                                note_entry = num_format_coin(get_raffle['amount'], get_raffle['coin_name']) + " " + get_raffle['coin_name'] + " is deducted from your balance."
                                msg = await ctx.reply(f'{EMOJI_CHECK} {ctx.author.mention} Successfully registered your Entry for raffle #**{raffle_id}** in {ctx.guild.name}! {note_entry}')
                                await msg.add_reaction(EMOJI_OK_BOX)
                            except Exception as e:
                                traceback.print_exc(file=sys.stdout)
                                await logchanbot(traceback.format_exc())
                            ## remove QUEUE:
                            if ctx.author.id in GAME_RAFFLE_QUEUE:
                                GAME_RAFFLE_QUEUE.remove(ctx.author.id)
                            return
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
                    await logchanbot(traceback.format_exc())
        elif subc == "CHECK":
            if get_raffle is None:
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} There is no information of current raffle yet!')
                return
            else:
                # If current is not opened
                try:
                    raffle_id = get_raffle['id']
                    if get_raffle['status'] == "OPENED":
                        await ctx.reply(f'{ctx.author.mention} Current raffle #{raffle_id} for guild {ctx.guild.name} is **OPENED**!')
                        return
                    elif get_raffle['status'] == "ONGOING":
                        await ctx.reply(f'{ctx.author.mention} Current raffle #{raffle_id} for guild {ctx.guild.name} is **ONGOING**!')
                        return
                    elif get_raffle['status'] == "COMPLETED":
                        await ctx.reply(f'{ctx.author.mention} Current raffle #{raffle_id} for guild {ctx.guild.name} is **COMPLETED**!')
                        return
                    elif get_raffle['status'] == "CANCELLED":
                        await ctx.reply(f'{ctx.author.mention} Current raffle #{raffle_id} for guild {ctx.guild.name} is **CANCELLED**!')
                        return
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
                    await logchanbot(traceback.format_exc())
        elif subc == "LAST":
            if get_raffle is None:
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} There is no information of current raffle yet!')
                return


    async def guild_deposit(
        self, 
        ctx,
        amount,
        coin: str
    ):
        await self.bot_log()
        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            return {"error": f"{EMOJI_ERROR} {ctx.author.mention} Not available in this guild."}

        COIN_NAME = coin.upper()
        if not is_coin_tipable(COIN_NAME):
            return {"error": f"{EMOJI_ERROR} {ctx.author.mention} TIPPING is currently disable for {COIN_NAME}."}

        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
        # Check allowed coins
        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        tiponly_coins = serverinfo['tiponly'].split(",")
        if COIN_NAME == serverinfo['default_coin'].upper() or serverinfo['tiponly'].upper() == "ALLCOIN":
            pass
        elif COIN_NAME not in tiponly_coins:
            return {"error": f"{EMOJI_LOCKED} {ctx.author.mention} TIPPING is currently disable for {COIN_NAME} in this guild `{ctx.guild.name}`."}
        # End of checking allowed coins

        if is_maintenance_coin(COIN_NAME):
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance."}

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
            traceback.print_exc(file=sys.stdout)
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
            MaxTx = token_info['real_max_tip']
        else:
            real_amount = int(Decimal(amount) * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
            MinTx = get_min_mv_amount(COIN_NAME)
            MaxTx = get_max_mv_amount(COIN_NAME)

        if real_amount > MaxTx:
            if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ERROR)
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than {num_format_coin(MaxTx, COIN_NAME)} {COIN_NAME}."}
        elif real_amount > actual_balance:
            if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ERROR)
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to transfer {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME} to this guild **{ctx.guild.name}**."}
        elif real_amount < MinTx:
            if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ERROR)
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than {num_format_coin(MinTx, COIN_NAME)} {COIN_NAME}."}

        # add queue also tip
        if ctx.author.id not in TX_IN_PROCESS:
            TX_IN_PROCESS.append(ctx.author.id)
        else:
            if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
            return {"error": f"{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress."}

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
            traceback.print_exc(file=sys.stdout)
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
                traceback.print_exc(file=sys.stdout)
                await logchanbot(traceback.format_exc())
            if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction:
                await ctx.message.add_reaction(get_emoji(COIN_NAME))
            # tipper shall always get DM. Ignore notifyList
            try:
                await ctx.reply(f'{EMOJI_ARROW_RIGHTHOOK} {ctx.author.mention} **{num_format_coin(real_amount, COIN_NAME)} '
                                f'{COIN_NAME}** was transferred to {ctx.guild.name}.')
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
            # TODO: notify guild owner, if fail, to logchannel
            guild_found = self.bot.get_guild(ctx.guild.id)
            if guild_found: user_found = self.bot.get_user(guild_found.owner.id)
            if guild_found and user_found:
                if user_found == ctx.author:
                    return {"result": True}
                notifyList = await store.sql_get_tipnotify()
                if str(guild_found.owner.id) not in notifyList:
                    try:
                        await user_found.send(f'{EMOJI_MONEYFACE} Your guild **{ctx.guild.name}** got a deposit of **{num_format_coin(real_amount, COIN_NAME)} '
                                              f'{COIN_NAME}** from {ctx.author.name}#{ctx.author.discriminator} in `#{ctx.channel.name}`\n'
                                              f'{NOTIFICATION_OFF_CMD}\n')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        await store.sql_toggle_tipnotify(str(member.id), "OFF")
            return {"result": True}
        else:
            if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction:
                await ctx.message.add_reaction(EMOJI_ERROR)
            # add to failed tx table
            await store.sql_add_failed_tx(COIN_NAME, str(ctx.author.id), ctx.author.name, real_amount, "TIP")
            return {"error": f"{ctx.author.mention} Can not deliver TX for {COIN_NAME} right now. Try again soon."}


    async def guild_mdeposit(
        self, 
        ctx, 
        coin_name: str, 
        option: str=None
    ):
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        prefix = await get_guild_prefix(ctx)
        COIN_NAME = coin_name.upper()
        # disable guild tip for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            return {"error": f"{EMOJI_LOCKED} Not available in this guild."}

        # Check if maintenance
        if IS_MAINTENANCE == 1:
            if int(ctx.author.id) in MAINTENANCE_OWNER:
                if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction:
                    await ctx.message.add_reaction(EMOJI_MAINTENANCE)
                pass
            else:
                return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}"}
        # End Check if maintenance

        if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**!'"}

        if not is_coin_depositable(COIN_NAME):
            return {"error": f"{EMOJI_ERROR} {ctx.author.mention} DEPOSITING is currently disable for {COIN_NAME}."}

        try:
            if COIN_NAME in ENABLE_COIN_ERC:
                coin_family = "ERC-20"
            elif COIN_NAME in ENABLE_COIN_TRC:
                coin_family = "TRC-20"
            else:
                coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
        except Exception as e:
            await logchanbot(traceback.format_exc())
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**"}

        if is_maintenance_coin(COIN_NAME) and (ctx.author.id not in MAINTENANCE_OWNER):
            if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance."}

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
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**"}
        if wallet is None:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Internal Error for `mdeposit`"}
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
                msg = await ctx.reply(f'{ctx.author.mention} Guild {ctx.guild.name} **{COIN_NAME}**\'s deposit address (not yours): ```{deposit}```')
                await msg.add_reaction(EMOJI_OK_BOX)
                if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_OK_HAND)
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
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
        embed.set_footer(text=f"Use:{prefix}guild mdeposit {COIN_NAME}")
        try:
            msg = await ctx.reply(embed=embed)
            await msg.add_reaction(EMOJI_OK_BOX)
            if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_OK_HAND)
            return
        except Exception as e:
            traceback.print_exc(file=sys.stdout)


    async def guild_mbalance(
        self, 
        ctx,
        coin: str=None
    ):
        await self.bot_log()

        prefix = await get_guild_prefix(ctx)
        # disable guild tip for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            return {"error": f"{EMOJI_LOCKED} Not available in this guild."}

        # If DM, error
        if isinstance(ctx.channel, discord.DMChannel) == True:
            return {"error": f"{ctx.author.mention} This command can not be DM."}

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
                        await self.botLogChan.send(f'A user call `{prefix}mbalance` failed with {COIN_NAME} in guild {ctx.guild.id} / {ctx.guild.name} / # {ctx.message.channel.name} ')
                        return
                    else:
                        get_user_balance = await get_balance_coin_user(ctx.guild.id, COIN_NAME, discord_guild=True, server__bot=SERVER_BOT)
                        actual_balance = get_user_balance['actual_balance']
                        if actual_balance > 0:
                            any_balance += 1
                            embed.add_field(name=COIN_NAME, value=num_format_coin(actual_balance, COIN_NAME)+" "+COIN_NAME, inline=True)
            if any_balance == 0:
                embed.add_field(name="INFO", value='`This guild has no balance for any coin yet.`', inline=True)
            embed.add_field(name='Related commands', value=f'`{prefix}mbalance TICKER` or `{prefix}mdeposit TICKER`', inline=False)
            embed.set_footer(text=f"Guild balance requested by {ctx.author.name}#{ctx.author.discriminator}")
            try:
                msg = await ctx.reply(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
            except Exception as e:
                if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction:
                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
            return
        else:
            COIN_NAME = coin.upper()
            if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
                return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**!"}
            else:
                try:
                    if COIN_NAME in ENABLE_COIN_ERC:
                        coin_family = "ERC-20"
                    elif COIN_NAME in ENABLE_COIN_TRC:
                        coin_family = "TRC-20"
                    else:
                        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
                    return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**!"}

                if is_maintenance_coin(COIN_NAME) and ctx.author.id not in MAINTENANCE_OWNER:
                    return {"error": f"{EMOJI_RED_NO} {COIN_NAME} in maintenance."}

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
                get_user_balance = await get_balance_coin_user(ctx.guild.id, COIN_NAME, discord_guild=True, server__bot=SERVER_BOT)
                balance_actual = num_format_coin(get_user_balance['actual_balance'], COIN_NAME)
                if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction:
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                embed = discord.Embed(title=f'[ GUILD {ctx.guild.name} BALANCE ]', timestamp=datetime.utcnow())
                embed.add_field(name="Available "+COIN_NAME, value=balance_actual+" "+COIN_NAME, inline=False)
                embed.add_field(name="Balance In / Out", value="{} / {} {}".format(num_format_coin(get_user_balance['actual_tip_income'], COIN_NAME), num_format_coin(get_user_balance['actual_tip_expense'], COIN_NAME), COIN_NAME), inline=False)
                embed.add_field(name="Deposited", value="{} {}".format(num_format_coin(get_user_balance['actual_deposit'], COIN_NAME), COIN_NAME), inline=False)
                if get_user_balance['economy_balance'] != 0:
                    embed.add_field(name="Economy", value="{} {}".format(num_format_coin(get_user_balance['economy_balance'], COIN_NAME), COIN_NAME), inline=False)
                if get_notice_txt(COIN_NAME):
                    embed.add_field(name='NOTICE', value=get_notice_txt(COIN_NAME), inline=False)
                embed.add_field(name='Related commands', value=f'`{prefix}mbalance TICKER` or `{prefix}mdeposit TICKER`', inline=False)
                embed.set_footer(text=f"Guild balance requested by {ctx.author.name}#{ctx.author.discriminator}")
                try:
                    msg = await ctx.reply(embed=embed)
                    await msg.add_reaction(EMOJI_OK_BOX)
                except Exception as e:
                    if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction:
                        await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                return {"result": True}


    async def guild_info(
        self, 
        ctx
    ):
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.reply(f'{ctx.author.mention} This command can not be DM.')
            return
        prefix = await get_guild_prefix(ctx)
        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        server_coin = DEFAULT_TICKER
        server_tiponly = "ALLCOIN"
        react_tip_value = "N/A"
        if serverinfo is None:
            # Let's add some info if server return None
            add_server_info = await store.sql_addinfo_by_server(str(ctx.guild.id),
                                                                ctx.guild.name, config.discord.prefixCmd, "WRKZ")
        else:
            server_coin = serverinfo['default_coin'].upper()
            server_tiponly = serverinfo['tiponly'].upper()
            if serverinfo['react_tip'].upper() == "ON":
                COIN_NAME = serverinfo['default_coin'].upper()
                react_tip_value = str(serverinfo['react_tip_100']) + COIN_NAME
        try:
            MUTE_CHANNEL = await store.sql_list_mutechan()
            LIST_IGNORECHAN = await store.sql_listignorechan()
            chanel_ignore_list = ''
            if LIST_IGNORECHAN and str(ctx.guild.id) in LIST_IGNORECHAN:
                for item in LIST_IGNORECHAN[str(ctx.guild.id)]:
                    try:
                        chanel_ignore = bot.get_channel(int(item))
                        chanel_ignore_list += '#'  + chanel_ignore.name + ' '
                    except Exception as e:
                        pass
            if chanel_ignore_list == '': chanel_ignore_list = 'N/A'

            chanel_mute_list = ''
            if MUTE_CHANNEL and str(ctx.guild.id) in MUTE_CHANNEL:
                for item in MUTE_CHANNEL[str(ctx.guild.id)]:
                    try:
                        chanel_mute = bot.get_channel(int(item))
                        chanel_mute_list += '#'  + chanel_mute.name + ' '
                    except Exception as e:
                        pass
            if chanel_mute_list == '': chanel_mute_list = 'N/A'
        except Exception as e:
            await logchanbot(traceback.format_exc())
        extra_text = f'Type: {prefix}setting or {prefix}help setting for more info. (Required permission)'
        try:
            embed = discord.Embed(title=f'Guild {ctx.guild.id} / {ctx.guild.name}', timestamp=datetime.utcnow())
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
            embed.add_field(name="Default Ticker", value=f'`{server_coin}`', inline=True)
            embed.add_field(name="Default Prefix", value=f'`{prefix}`', inline=True)
            embed.add_field(name="TipOnly Coins", value=f'`{server_tiponly}`', inline=True)
            embed.add_field(name=f"Re-act Tip {EMOJI_TIP}", value=f'`{react_tip_value}`', inline=True)
            embed.add_field(name="Ignored Tip", value=f'`{chanel_ignore_list}`', inline=True)
            embed.add_field(name="Mute in", value=f'`{chanel_mute_list}`', inline=True)
            embed.set_footer(text=f"{extra_text}")
            msg = await ctx.reply(embed=embed)
            await msg.add_reaction(EMOJI_OK_BOX)
        except (discord.errors.NotFound, discord.errors.Forbidden, Exception) as e:
            msg = await ctx.reply(
                '\n```'
                f'Server ID:      {ctx.guild.id}\n'
                f'Server Name:    {ctx.guild.name}\n'
                f'Default Ticker: {server_coin}\n'
                f'Default Prefix: {prefix}\n'
                f'TipOnly Coins:  {server_tiponly}\n'
                f'Re-act Tip:     {react_tip_value}\n'
                f'Ignored Tip in: {chanel_ignore_list}\n'
                f'Mute in:        {chanel_mute_list}\n'
                f'```{extra_text}')
            await msg.add_reaction(EMOJI_OK_BOX)


    async def guild_botchan(
        self, 
        ctx
    ):
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo['botchan']:
            try: 
                if ctx.channel.id == int(serverinfo['botchan']):
                    return {"error": f"{EMOJI_RED_NO} {ctx.channel.mention} is already the bot channel here!"}
                else:
                    # change channel info
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'botchan', str(ctx.channel.id))
                    await ctx.reply(f'Bot channel has set to {ctx.channel.mention}.')
                    await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} change bot channel {ctx.guild.name} / {ctx.guild.id} to #{ctx.channel.name}.')
                    return {"result": True}
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                await logchanbot(traceback.format_exc())
        else:
            # change channel info
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'botchan', str(ctx.channel.id))
            await ctx.reply(f'Bot channel has set to {ctx.channel.mention}.')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed bot channel {ctx.guild.name} / {ctx.guild.id} to #{ctx.channel.name}.')
            return {"result": True}


    async def guild_raffle_channel(
        self, 
        ctx
    ):
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo['raffle_channel']:
            try: 
                if ctx.channel.id == int(serverinfo['raffle_channel']):
                    return {"error": f"{EMOJI_RED_NO} {ctx.channel.mention} is already the raffle channel here!"}
                else:
                    # change channel info
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'raffle_channel', str(ctx.channel.id))
                    await ctx.reply(f'Raffle channel has set to {ctx.channel.mention}.')
                    await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} change raffle channel {ctx.guild.name} / {ctx.guild.id} to #{ctx.channel.name}.')
                    return {"result": True}
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                await logchanbot(traceback.format_exc())
        else:
            # change channel info
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'raffle_channel', str(ctx.channel.id))
            await ctx.reply(f'Raffle channel has set to {ctx.channel.mention}.')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed raffle channel {ctx.guild.name} / {ctx.guild.id} to #{ctx.channel.name}.')
            return {"result": True}


    async def guild_gamechan(
        self, 
        ctx,
        game: str=None
    ):
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        game_list = config.game.game_list.split(",")
        if game is None:
            return {"error": f"{EMOJI_RED_NO} {ctx.channel.mention} please mention a game name to set game channel for it. Game list: {config.game.game_list}."}
        else:
            game = game.lower()
            if game not in game_list:
                return {"error": f"{EMOJI_RED_NO} {ctx.channel.mention} please mention a game name within this list: {config.game.game_list}."}
            else:
                serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                index_game = "game_" + game + "_channel"
                if serverinfo[index_game]:
                    try: 
                        if ctx.channel.id == int(serverinfo[index_game]):
                            return {"error": f"{EMOJI_RED_NO} {ctx.channel.mention} is already for game **{game}** channel here!"}
                        else:
                            # change channel info
                            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), index_game, str(ctx.channel.id))
                            await ctx.reply(f'{ctx.channel.mention} Game **{game}** channel has set to {ctx.channel.mention}.')
                            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed game **{game}** in channel {ctx.guild.name} / {ctx.guild.id} to #{ctx.channel.name}.')
                            return {"result": True}
                    except Exception as e:
                        traceback.print_exc(file=sys.stdout)
                        await logchanbot(traceback.format_exc())
                else:
                    # change channel info
                    changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), index_game, str(ctx.channel.id))
                    await ctx.reply(f'{ctx.channel.mention} Game **{game}** channel has set to {ctx.channel.mention}.')
                    await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} set game **{game}** channel in {ctx.guild.name} / {ctx.guild.id} to #{ctx.channel.name}.')
                    return {"result": True}


    async def guild_setting_tiponly(
        self, 
        ctx,
        coin_list: str
    ):
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        coin_list = coin_list.upper()
        if coin_list in ["ALLCOIN", "*", "ALL", "TIPALL", "ANY"]:
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'tiponly', "ALLCOIN")
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed tiponly in {ctx.guild.name} / {ctx.guild.id} to `ALLCOIN`')
            if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_OK_HAND)
            await ctx.reply(f'{ctx.author.mention} all coins will be allowed in here.')
            return {"result": True}
        elif " " in coin_list or "," in coin_list:
            # multiple coins
            if " " in coin_list:
                coins = coin_list.split()
            elif "," in coin_list:
                coins = coin_list.split(",")
            contained = [x.upper() for x in coins if x.upper() in ENABLE_COIN+ENABLE_XMR+ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_COIN_NANO+ENABLE_XCH]
            if contained and len(contained) >= 2:
                tiponly_value = ','.join(contained)
                await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed tiponly in {ctx.guild.name} / {ctx.guild.id} to `{tiponly_value}`')
                await ctx.reply(f'{ctx.author.mention} TIPONLY set to: **{tiponly_value}**.')
                changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'tiponly', tiponly_value.upper())
                if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_OK_HAND)
            else:
                if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_INFORMATION)
                await ctx.reply(f'{ctx.author.mention} No known coin in **{coin_list}**. TIPONLY is remained unchanged.')
            return {"result": True}
        else:
            # Single coin
            if coin_list not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_NANO+ENABLE_XMR+ENABLE_COIN_TRC+ENABLE_XCH:
                await ctx.reply(f'{ctx.author.mention} {coin_list} is not in any known coin we set.')
                return {"result": True}
            else:
                # coin_list is single coin set_coin
                changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'tiponly', coin_list)
                await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed tiponly in {ctx.guild.name} / {ctx.guild.id} to `{coin_list}`')
                await ctx.reply(f'{ctx.author.mention} {coin_list} will be the only tip here.')
                return {"result": True}


    async def guild_setting_info(
        self, 
        ctx
    ):
        prefix = await get_guild_prefix(ctx)
        await self.bot_log()
        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        embed = discord.Embed(title = "GUILD {} SETTING / INFO".format(ctx.guild.name), timestamp=datetime.utcnow())
        embed.add_field(name="Tip Only", value=f'`{prefix}setting tiponly <coin1> [coin2] ..`', inline=False)
        embed.add_field(name="Bot Channel", value=f'`{prefix}setting botchan #channel_name`', inline=False)
        embed.add_field(name="Ignore Tipping this Channel", value=f'`{prefix}setting ignorechan`', inline=False)
        embed.add_field(name="Delete Ignored Channel", value=f'`{prefix}setting del_ignorechan`', inline=False)
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
            msg = await ctx.reply(embed=embed)
            await msg.add_reaction(EMOJI_OK_BOX)
        except Exception as e:
            await logchanbot(traceback.format_exc())
        return


    async def guild_setting_trade(
        self, 
        ctx
    ):
        prefix = await get_guild_prefix(ctx)
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo is None:
            # Let's add some info if server return None
            add_server_info = await store.sql_addinfo_by_server(str(ctx.guild.id), ctx.guild.name, prefix, DEFAULT_TICKER)
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                                                                
        if serverinfo and serverinfo['enable_trade'] == "YES":
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_trade', 'NO')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} DISABLE trade in their guild {ctx.guild.name} / {ctx.guild.id}')
            await ctx.reply(f"{ctx.author.mention} DISABLE TRADE feature in this guild {ctx.guild.name}.")
            return {"result": True}
        elif serverinfo and serverinfo['enable_trade'] == "NO":
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_trade', 'YES')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} ENABLE trade in their guild {ctx.guild.name} / {ctx.guild.id}')
            await ctx.reply(f"{ctx.author.mention} ENABLE TRADE feature in this guild {ctx.guild.name}.")
            return {"result": True}
        else:
            return {"error": f"{ctx.author.mention} Internal error when calling serverinfo function."}


    async def guild_setting_nsfw(
        self, 
        ctx
    ):
        prefix = await get_guild_prefix(ctx)
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo is None:
            # Let's add some info if server return None
            add_server_info = await store.sql_addinfo_by_server(str(ctx.guild.id), ctx.guild.name, prefix, DEFAULT_TICKER)
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))

        if serverinfo and serverinfo['enable_nsfw'] == "YES":
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_nsfw', 'NO')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} DISABLE NSFW in their guild {ctx.guild.name} / {ctx.guild.id}')
            await ctx.reply(f"{ctx.author.mention} DISABLE NSFW command in this guild {ctx.guild.name}.")
            return {"result": True}
        elif serverinfo and serverinfo['enable_nsfw'] == "NO":
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_nsfw', 'YES')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} ENABLE NSFW in their guild {ctx.guild.name} / {ctx.guild.id}')
            await ctx.reply(f"{ctx.author.mention} ENABLE NSFW command in this guild {ctx.guild.name}.")
            return {"result": True}
        else:
            return {"error": f"{ctx.author.mention} Internal error when calling serverinfo function."}


    async def guild_setting_game(
        self, 
        ctx
    ):
        prefix = await get_guild_prefix(ctx)
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo is None:
            # Let's add some info if server return None
            add_server_info = await store.sql_addinfo_by_server(str(ctx.guild.id), ctx.guild.name, prefix, DEFAULT_TICKER)
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo and serverinfo['enable_game'] == "YES":
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_game', 'NO')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} DISABLE game in their guild {ctx.guild.name} / {ctx.guild.id}')
            await ctx.reply(f"{ctx.author.mention} DISABLE GAME feature in this guild {ctx.guild.name}.")
            return {"result": True}
        elif serverinfo and serverinfo['enable_game'] == "NO":
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_game', 'YES')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} ENABLE game in their guild {ctx.guild.name} / {ctx.guild.id}')
            await ctx.reply(f"{ctx.author.mention} ENABLE GAME feature in this guild {ctx.guild.name}.")
            return {"result": True}
        else:
            return {"error": f"{ctx.author.mention} Internal error when calling serverinfo function."}


    async def guild_setting_market(
        self, 
        ctx
    ):
        prefix = await get_guild_prefix(ctx)
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo is None:
            # Let's add some info if server return None
            add_server_info = await store.sql_addinfo_by_server(str(ctx.guild.id), ctx.guild.name, prefix, DEFAULT_TICKER)
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))

        if serverinfo and serverinfo['enable_market'] == "YES":
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_market', 'NO')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} DISABLE market command in their guild {ctx.guild.name} / {ctx.guild.id}')
            await ctx.reply(f"{ctx.author.mention} DISABLE market command in this guild {ctx.guild.name}.")
            return {"result": True}
        elif serverinfo and serverinfo['enable_market'] == "NO":
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_market', 'YES')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} ENABLE market command in their guild {ctx.guild.name} / {ctx.guild.id}')
            await ctx.reply(f"{ctx.author.mention} ENABLE market command in this guild {ctx.guild.name}.")
            return {"result": True}
        else:
            return {"error": f"{ctx.author.mention} Internal error when calling serverinfo function."}


    async def guild_setting_faucet(
        self, 
        ctx
    ):
        prefix = await get_guild_prefix(ctx)
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo is None:
            # Let's add some info if server return None
            add_server_info = await store.sql_addinfo_by_server(str(ctx.guild.id), ctx.guild.name, prefix, DEFAULT_TICKER)
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))

        if serverinfo and serverinfo['enable_faucet'] == "YES":
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_faucet', 'NO')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} DISABLE faucet (take) command in their guild {ctx.guild.name} / {ctx.guild.id}')
            await ctx.reply(f"{ctx.author.mention} DISABLE faucet (take) command in this guild {ctx.guild.name}.")
            return {"result": True}
        elif serverinfo and serverinfo['enable_faucet'] == "NO":
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'enable_faucet', 'YES')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} ENABLE faucet (take) command in their guild {ctx.guild.name} / {ctx.guild.id}')
            await ctx.reply(f"{ctx.author.mention} ENABLE faucet (take) command in this guild {ctx.guild.name}.")
            return {"result": True}
        else:
            return {"error": f"{ctx.author.mention} Internal error when calling serverinfo function."}


    async def guild_setting_defaultcoin(
        self, 
        ctx,
        default_coin: str
    ):
        prefix = await get_guild_prefix(ctx)
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        server_coin = DEFAULT_TICKER
        if serverinfo is None:
            # Let's add some info if server return None
            add_server_info = await store.sql_addinfo_by_server(str(ctx.guild.id), ctx.guild.name, prefix, DEFAULT_TICKER)
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        server_coin = serverinfo['default_coin'].upper()

        if default_coin.upper() not in ENABLE_COIN + ENABLE_XMR + ENABLE_COIN_DOGE + ENABLE_COIN_ERC + ENABLE_COIN_NANO + ENABLE_COIN_TRC + ENABLE_XCH:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**!"}
        elif server_coin and server_coin.upper() == default_coin.upper():
            await ctx.reply(f"{ctx.author.mention} **{default_coin.upper()}** was guild's default coin. Nothing changed.")
            return {"result": True}
        elif server_coin:
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'default_coin', default_coin.upper())
            await ctx.reply(f"Guild {ctx.guild.name}'s default coin changed from `{server_coin}` to `{default_coin.upper()}`.")
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed default coin in {ctx.guild.name} / {ctx.guild.id} to {default_coin.upper()}.')
            return {"result": True}
        else:
            return {"error": f"{ctx.author.mention} Internal error when calling serverinfo function."}


    async def guild_setting_mutechan(
        self, 
        ctx
    ):
        prefix = await get_guild_prefix(ctx)
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        if MUTE_CHANNEL is None:
            await store.sql_add_mutechan_by_server(str(ctx.guild.id), str(ctx.channel.id), str(ctx.author.id), ctx.author.name)
            MUTE_CHANNEL = await store.sql_list_mutechan()
            await ctx.reply(f'{ctx.author.mention} Added #{ctx.channel.name} to mute. I will ignore anything here.')
            return {"result": True}
        if str(ctx.guild.id) in MUTE_CHANNEL:
            if str(ctx.channel.id) in MUTE_CHANNEL[str(ctx.guild.id)]:
                await ctx.reply(f'{ctx.author.mention} This channel #{ctx.channel.name} is already in mute mode.')
                return {"result": True}
            else:
                await store.sql_add_mutechan_by_server(str(ctx.guild.id), str(ctx.channel.id), str(ctx.author.id), ctx.author.name)
                MUTE_CHANNEL = await store.sql_list_mutechan()
                await ctx.reply(f'{ctx.author.mention} Added #{ctx.channel.name} to mute. I will ignore anything here.')
                return {"result": True}
        else:
            await store.sql_add_mutechan_by_server(str(ctx.guild.id), str(ctx.channel.id), str(ctx.author.id), ctx.author.name)
            await ctx.reply(f'{ctx.author.mention} Added #{ctx.channel.name} to mute. I will ignore anything here.')
            return {"result": True}


    async def guild_setting_unmutechan(
        self, 
        ctx
    ):
        prefix = await get_guild_prefix(ctx)
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        if MUTE_CHANNEL and str(ctx.guild.id) in MUTE_CHANNEL:
            if str(ctx.channel.id) in MUTE_CHANNEL[str(ctx.guild.id)]:
                await store.sql_del_mutechan_by_server(str(ctx.guild.id), str(ctx.channel.id))
                MUTE_CHANNEL = await store.sql_list_mutechan()
                await ctx.reply(f'{ctx.author.mention} This channel #{ctx.channel.name} is unmute.')
                return {"result": True}
            else:
                await ctx.reply(f'{ctx.author.mention} Channel #{ctx.channel.name} is not mute right now!')
                return {"result": True}
        else:
            await ctx.reply(f'{ctx.author.mention} Channel #{ctx.channel.name} is not mute right now!')
            return {"result": True}


    async def guild_setting_reacttip(
        self, 
        ctx
    ):
        prefix = await get_guild_prefix(ctx)
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo is None:
            # Let's add some info if server return None
            add_server_info = await store.sql_addinfo_by_server(str(ctx.guild.id), ctx.guild.name, prefix, DEFAULT_TICKER)
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))

        if serverinfo and serverinfo['react_tip'] == "ON":
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'react_tip', 'OFF')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} DISABLE react tip in their guild {ctx.guild.name} / {ctx.guild.id}')
            await ctx.reply(f"{ctx.author.mention} DISABLE react tip in this guild {ctx.guild.name}.")
            return {"result": True}
        elif serverinfo and serverinfo['react_tip'] == "OFF":
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'react_tip', 'ON')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} ENABLE react tip in their guild {ctx.guild.name} / {ctx.guild.id}')
            await ctx.reply(f"{ctx.author.mention} ENABLE react tip in this guild {ctx.guild.name}.")
            return {"result": True}
        else:
            return {"error": f"{ctx.author.mention} Internal error when calling serverinfo function."}


    async def guild_setting_reacttip_amount(
        self, 
        ctx,
        amount,
        coin: str
    ):
        await self.bot_log()

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{ctx.author.mention} This command can not be DM."}

        COIN_NAME = coin.upper()
        if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**!'"}

        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
            token_info = await store.get_token_info(COIN_NAME)
            MinTx = token_info['real_min_tip']
            MaxTx = token_info['real_max_tip']
            decimal_pts = token_info['token_decimal']
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
            token_info = await store.get_token_info(COIN_NAME)
            MinTx = token_info['real_min_tip']
            MaxTx = token_info['real_max_tip']
            decimal_pts = token_info['token_decimal']
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
            MinTx = get_min_mv_amount(COIN_NAME)
            MaxTx = get_max_mv_amount(COIN_NAME)
            decimal_pts = int(math.log10(get_decimal(COIN_NAME)))
        try:
            amount = Decimal(amount)
        except ValueError:
            if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ERROR)
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Invalid amount."}
        real_amount = int(Decimal(amount) * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
        if real_amount < MinTx or real_amount >  MaxTx:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} amount of **{COIN_NAME}** out of range!"}
        else:
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'react_tip_100', real_amount)
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'react_tip_coin', COIN_NAME)
            await ctx.reply(f'{ctx.author.mention} changed react tip amount updated to to `{num_format_coin(real_amount, COIN_NAME)}{COIN_NAME}`.')
            return {"result": True}


    @inter_client.slash_command(description="Guild setting commands.")
    async def setting(self, ctx):
        pass


    @setting.sub_command(
        usage="setting tiponly <coin1, coin2, ....>", 
        options=[
            Option('coin_list', 'coin_list', OptionType.STRING, required=True)
        ],
        description="Deposit from your balance to guild's balance"
    )
    @dislash.has_permissions(manage_channels=True)
    async def tiponly(
        self, 
        ctx,
        coin_list: str
    ):
        guild_setting_tiponly = await self.guild_setting_tiponly(ctx, coin_list)
        if guild_setting_tiponly and "error" in guild_setting_tiponly:
            await ctx.reply(guild_setting_tiponly['error'])


    # No permission needed
    @setting.sub_command(
        usage="setting info", 
        description="Get Guild's setting / informatin"
    )
    async def info(
        self, 
        ctx
    ):
        guild_setting_info = await self.guild_setting_info(ctx)
        if guild_setting_info and "error" in guild_setting_info:
            await ctx.reply(guild_setting_info['error'])


    @setting.sub_command(
        usage="setting trade", 
        description="Toggle trade enable ON/OFF in your guild"
    )
    @dislash.has_permissions(manage_channels=True)
    async def trade(
        self, 
        ctx,
    ):
        guild_setting_trade = await self.guild_setting_trade(ctx)
        if guild_setting_trade and "error" in guild_setting_trade:
            await ctx.reply(guild_setting_trade['error'])


    @setting.sub_command(
        usage="setting nsfw", 
        description="Toggle nsfw enable ON/OFF in your guild"
    )
    @dislash.has_permissions(manage_channels=True)
    async def nsfw(
        self, 
        ctx,
    ):
        guild_setting_nsfw = await self.guild_setting_nsfw(ctx)
        if guild_setting_nsfw and "error" in guild_setting_nsfw:
            await ctx.reply(guild_setting_nsfw['error'])


    @setting.sub_command(
        usage="setting game", 
        description="Toggle game enable ON/OFF in your guild"
    )
    @dislash.has_permissions(manage_channels=True)
    async def game(
        self, 
        ctx,
    ):
        guild_setting_game = await self.guild_setting_game(ctx)
        if guild_setting_game and "error" in guild_setting_game:
            await ctx.reply(guild_setting_game['error'])


    @setting.sub_command(
        usage="setting market", 
        description="Toggle market enable ON/OFF in your guild"
    )
    @dislash.has_permissions(manage_channels=True)
    async def market(
        self, 
        ctx,
    ):
        guild_setting_market = await self.guild_setting_market(ctx)
        if guild_setting_market and "error" in guild_setting_market:
            await ctx.reply(guild_setting_market['error'])


    @setting.sub_command(
        usage="setting faucet", 
        description="Toggle faucet enable ON/OFF in your guild"
    )
    @dislash.has_permissions(manage_channels=True)
    async def faucet(
        self, 
        ctx,
    ):
        guild_setting_faucet = await self.guild_setting_faucet(ctx)
        if guild_setting_faucet and "error" in guild_setting_faucet:
            await ctx.reply(guild_setting_faucet['error'])


    @setting.sub_command(
        usage="setting defaultcoin <coin>", 
        options=[
            Option('coin', 'coin', OptionType.STRING, required=True)
        ],
        description="Deposit from your balance to guild's balance"
    )
    @dislash.has_permissions(manage_channels=True)
    async def defaultcoin(
        self, 
        ctx,
        coin: str
    ):
        guild_setting_defaultcoin = await self.guild_setting_defaultcoin(ctx, coin)
        if guild_setting_defaultcoin and "error" in guild_setting_defaultcoin:
            await ctx.reply(guild_setting_defaultcoin['error'])


    @setting.sub_command(
        usage="setting mute", 
        description="Mute in your guild's said channel."
    )
    @dislash.has_permissions(manage_channels=True)
    async def mute(
        self, 
        ctx,
    ):
        guild_setting_mutechan = await self.guild_setting_mutechan(ctx)
        if guild_setting_mutechan and "error" in guild_setting_mutechan:
            await ctx.reply(guild_setting_mutechan['error'])


    @setting.sub_command(
        usage="setting unmute", 
        description="Unmute in your guild's said channel."
    )
    @dislash.has_permissions(manage_channels=True)
    async def unmute(
        self, 
        ctx,
    ):
        guild_setting_unmutechan = await self.guild_setting_unmutechan(ctx)
        if guild_setting_unmutechan and "error" in guild_setting_unmutechan:
            await ctx.reply(guild_setting_unmutechan['error'])


    @setting.sub_command(
        usage="setting reacttip", 
        description="Toggle reacttip enable ON/OFF in your guild"
    )
    @dislash.has_permissions(manage_channels=True)
    async def reacttip(
        self, 
        ctx,
    ):
        guild_setting_reacttip = await self.guild_setting_reacttip(ctx)
        if guild_setting_reacttip and "error" in guild_setting_reacttip:
            await ctx.reply(guild_setting_reacttip['error'])


    @setting.sub_command(
        usage="setting reactamount <amount> <coin>", 
        options=[
            Option('amount', 'amount', OptionType.NUMBER, required=True),
            Option('coin', 'coin', OptionType.STRING, required=True)
        ],
        description="Deposit from your balance to guild's balance"
    )
    @dislash.has_permissions(manage_channels=True)
    async def reactamount(
        self, 
        ctx,
        amount: float,
        coin: str
    ):
        guild_setting_reacttip_amount = await self.guild_setting_reacttip_amount(ctx, amount, coin)
        if guild_setting_reacttip_amount and "error" in guild_setting_reacttip_amount:
            await ctx.reply(guild_setting_reacttip_amount['error'])


    @inter_client.slash_command(description="Guild commands.")
    async def guild(
        self, 
        ctx
    ):
        pass


    @guild.sub_command(
        usage="guild createraffle <amount> <coin> <duration>", 
        options=[
            Option('amount', 'amount', OptionType.NUMBER, required=True),
            Option('coin', 'coin', OptionType.STRING, required=True),
            Option('duration', 'duration', OptionType.STRING, required=True)
        ],
        description="Create a raffle."
    )
    @dislash.has_permissions(manage_channels=True)
    async def createraffle(
        self, 
        ctx, 
        amount: float, 
        coin: str, 
        duration: str
    ):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.reply(f'{ctx.author.mention} This command can not be DM.')
            return
        guild_createraffle = await self.guild_createraffle(ctx, amount, coin, duration)
        if guild_createraffle and "error" in guild_createraffle:
            await ctx.reply(guild_createraffle['error'], ephemeral=False)


    @guild.sub_command(
        usage="guild raffle [info|join|check]", 
        options=[
            Option('subc', 'subc', OptionType.STRING, required=False, choices=[
                OptionChoice("Get Information", "INFO"),
                OptionChoice("Join opened raffle", "JOIN"),
                OptionChoice("Check raffle's status", "CHECK")
            ]
            )
        ],
        description="Create a raffle."
    )
    @dislash.has_permissions(manage_channels=True)
    async def raffle(
        self, 
        ctx, 
        subc: str=None
    ):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.reply(f'{ctx.author.mention} This command can not be DM.')
            return
        guild_raffle = await self.guild_raffle(ctx, subc)
        if guild_raffle and "error" in guild_raffle:
            await ctx.reply(guild_raffle['error'], ephemeral=False)


    @guild.sub_command(
        usage="guild deposit <amount> <coin>", 
        options=[
            Option('amount', 'amount', OptionType.NUMBER, required=True),
            Option('coin', 'coin', OptionType.STRING, required=True)
        ],
        description="Deposit from your balance to guild's balance"
    )
    async def deposit(
        self, 
        ctx,
        amount: float,
        coin: str
    ):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.reply(f'{ctx.author.mention} This command can not be DM.')
            return

        try:
            amount = Decimal(amount)
        except ValueError:
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
            return
        guild_deposit = await self.guild_deposit(ctx, amount, coin)
        if guild_deposit and "error" in guild_deposit:
            await ctx.reply(guild_deposit['error'], ephemeral=False)


    @guild.sub_command(
        usage="guild mdeposit <coin_name>", 
        options=[
            Option('coin_name', 'coin_name', OptionType.STRING, required=True)
        ],
        description="Get a deposit address for a guild."
    )
    async def mdeposit(
        self, 
        ctx,
        coin_name: str
    ):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.reply(f'{ctx.author.mention} This command can not be DM.')
            return

        guild_mdeposit = await self.guild_mdeposit(ctx, coin_name)
        if guild_mdeposit and "error" in guild_mdeposit:
            await ctx.reply(guild_mdeposit['error'], ephemeral=True)


    @guild.sub_command(
        usage="guild mbalance", 
        options=[
            Option('coin_name', 'coin_name', OptionType.STRING, required=False)
        ],
        description="Get guild's balance."
    )
    async def mbalance(
        self, 
        ctx,
        coin_name: str=None
    ):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.reply(f'{ctx.author.mention} This command can not be DM.')
            return
        guild_mbalance = await self.guild_mbalance(ctx, coin_name)
        if guild_mbalance and "error" in guild_mbalance:
            await ctx.reply(guild_mbalance['error'], ephemeral=True)


    @guild.sub_command(
        usage="guild info", 
        description="Get guild's info."
    )
    async def info(
        self, 
        ctx
    ):
        await self.guild_info(ctx)


    @guild.sub_command(
        usage="guild botchan", 
        description="Set Guild's bot channel."
    )
    @dislash.has_permissions(manage_channels=True)
    async def botchan(
        self, 
        ctx
    ):
        guild_botchan = await self.guild_botchan(ctx)
        if guild_botchan and "error" in guild_botchan:
            await ctx.reply(guild_botchan['error'])


    @guild.sub_command(
        usage="guild rafflechan", 
        description="Set Guild's raffle channel."
    )
    @dislash.has_permissions(manage_channels=True)
    async def rafflechan(
        self, 
        ctx
    ):
        guild_raffle_channel = await self.guild_raffle_channel(ctx)
        if guild_raffle_channel and "error" in guild_raffle_channel:
            await ctx.reply(guild_raffle_channel['error'])


    @guild.sub_command(
        usage="guild gamechan <game>", 
        options=[
            Option('game', 'game', OptionType.STRING, required=True, choices=[
                OptionChoice("2048", "2048"),
                OptionChoice("BLACKJACK", "BLACKJACK"),
                OptionChoice("DICE", "DICE"),
                OptionChoice("MAZE", "MAZE"),
                OptionChoice("SLOT", "SLOT"),
                OptionChoice("SNAIL", "SNAIL"),
                OptionChoice("SOKOBAN", "SOKOBAN")
            ]
            )
        ],
        description="Set Guild's game channel."
    )
    @dislash.has_permissions(manage_channels=True)
    async def gamechan(
        self, 
        ctx,
        game: str
    ):
        guild_gamechan = await self.guild_gamechan(ctx, game)
        if guild_gamechan and "error" in guild_gamechan:
            await ctx.reply(guild_gamechan['error'])


    ## Message commands
    @commands.command(
        usage="info", 
        description="Check guild's information"
    )
    async def info(
        self, 
        ctx
    ):
        await self.guild_info(ctx)


    @commands.group(
        usage="guild <subcommand>", 
        description="Various guild's command"
    )
    async def guild(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.reply(f'{ctx.author.mention} This command can not be DM.')
            return

        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)

        prefix = await get_guild_prefix(ctx)
        if ctx.invoked_subcommand is None:
            await ctx.reply(f'{ctx.author.mention} Invalid {prefix}guild command.\n Please use {prefix}help guild')
            return


    @guild.command(
        usage="guild deposit <amount> <coin>", 
        description="Deposit from your balance to guild's balance."
    )
    async def deposit(
        self, 
        ctx, 
        amount: str, 
        coin: str
    ):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.reply(f'{ctx.author.mention} This command can not be DM.')
            return

        amount = amount.replace(",", "")
        try:
            amount = Decimal(amount)
        except ValueError:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
            return
        await self.guild_deposit(ctx, amount, coin)


    @guild.command(
        usage="guild mdeposit <coin_name>", 
        description="Get a deposited address of a coin in the guild."
    )
    async def mdeposit(
        self, 
        ctx,
        coin_name: str,
        option: str=None
    ):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.reply(f'{ctx.author.mention} This command can not be DM.')
            return
        guild_mdeposit = await self.guild_mdeposit(ctx, coin_name, option)
        if guild_mdeposit and "error" in guild_mdeposit:
            await ctx.reply(guild_mdeposit['error'], ephemeral=False)


    ## message command
    @guild.command(
        usage="guild tipmsg <message>", 
        description="Set guild's tip's message."
    )
    @commands.has_permissions(manage_channels=True)
    async def tipmsg(
        self, 
        ctx, 
        *, 
        tipmessage
    ):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.reply(f'{ctx.author.mention} This command can not be DM.')
            return

        if 1000 <= len(tipmessage) <= 5:
            await ctx.reply(f'{ctx.author.mention} Tip message is too short or too long.')
            return
        else:
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'tip_message', tipmessage)
            changeinfo = await store.sql_changeinfo_by_server(str(ctx.guild.id), 'tip_message_by', "{}#{}".format(ctx.author.name, ctx.author.discriminator))
            try:
                await ctx.reply(f'{ctx.author.mention} Tip message for this guild is updated.')
            except Exception as e:
                await logchanbot(traceback.format_exc())
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} changed tipmessage in {str(ctx.guild.id)}/{ctx.guild.name}.')
            return


    @guild.command(
        usage="guild createraffle <amount> <coin> <duration>", 
        aliases=['crfl', 'create_raffle'], 
        description="Create a raffle."
    )
    @commands.has_permissions(manage_channels=True)
    async def createraffle(
        self, 
        ctx, 
        amount: str, 
        coin: str, 
        duration: str
    ):
        amount = amount.replace(",", "")
        guild_createraffle = await self.guild_createraffle(ctx, amount, coin, duration)
        if guild_createraffle and "error" in guild_createraffle:
            await ctx.reply(guild_createraffle['error'])


    @guild.command(
        usage="guild raffle [info|join|check]", 
        aliases=['rfl'], 
        description="Check current raffle."
    )
    async def raffle(
        self, 
        ctx, 
        subc: str=None
    ):
        guild_raffle = await self.guild_raffle(ctx, subc)
        if guild_raffle and "error" in guild_raffle:
            await ctx.reply(guild_raffle['error'])


    @guild.command(
        usage="guild botchan", 
        aliases=['botchannel', 'bot_chan'], 
        description="Set bot channel to the said channel."
    )
    @commands.has_permissions(manage_channels=True)
    async def botchan(self, ctx):
        guild_botchan = await self.guild_botchan(ctx)
        if guild_botchan and "error" in guild_botchan:
            await ctx.reply(guild_botchan['error'])


    @guild.command(
        usage="guild raffle_channel", 
        description="Set bot channel to the said channel."
    )
    @commands.has_permissions(manage_channels=True)
    async def raffle_channel(self, ctx):
        guild_raffle_channel = await self.guild_raffle_channel(ctx)
        if guild_raffle_channel and "error" in guild_raffle_channel:
            await ctx.reply(guild_raffle_channel['error'])


    @guild.command(
        usage="gamechan <game name>", 
        aliases=['gamechannel', 'game_chan'], 
        description="Set game channel to the said channel."
    )
    @commands.has_permissions(manage_channels=True)
    async def gamechan(
        self, 
        ctx, 
        *, 
        game: str=None
    ):
        guild_gamechan = await self.guild_gamechan(ctx, game)
        if guild_gamechan and "error" in guild_gamechan:
            await ctx.reply(guild_gamechan['error'])


    @guild.command(
        usage="guild prefix <prefix>", 
        description="Change prefix command in your guild."
    )
    @commands.has_permissions(manage_channels=True)
    async def prefix(
        self, 
        ctx, 
        prefix_char: str=None
    ):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.reply(f'{ctx.author.mention} This command can not be DM.')
            return
        await ctx.reply(f'{ctx.author.mention} Please use slash commands.')
        return


    @inter_client.slash_command(
        usage="mdeposit <coin_name>", 
        options=[
            Option('coin_name', 'coin_name', OptionType.STRING, required=True)
        ],
        description="Get a deposit address for a guild."
    )
    async def mdeposit(
        self, 
        ctx,
        coin_name: str
    ):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.reply(f'{ctx.author.mention} This command can not be DM.')
            return

        guild_mdeposit = await self.guild_mdeposit(ctx, coin_name)
        if guild_mdeposit and "error" in guild_mdeposit:
            await ctx.reply(guild_mdeposit['error'], ephemeral=True)


    @commands.command(
        usage='mdeposit [coin_name] <plain/embed>', 
        description="Get a deposit address for a guild."
    )
    async def mdeposit(
        self, 
        ctx, 
        coin_name: str, 
        option: str=None
    ):
        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'mdeposit')
        if account_lock:
            await ctx.message.add_reaction(EMOJI_LOCKED) 
            await ctx.reply(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
            return
        # end of check if account locked
        guild_mdeposit = await self.guild_mdeposit(ctx, coin_name, option)
        if guild_mdeposit and "error" in guild_mdeposit:
            await ctx.reply(guild_mdeposit['error'])


    @inter_client.slash_command(
        usage="mbalance", 
        options=[
            Option('coin_name', 'coin_name', OptionType.STRING, required=False)
        ],
        description="Get guild's balance."
    )
    async def mbalance(
        self, 
        ctx,
        coin_name: str=None
    ):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.reply(f'{ctx.author.mention} This command can not be DM.')
            return
        guild_mbalance = await self.guild_mbalance(ctx, coin_name)
        if guild_mbalance and "error" in guild_mbalance:
            await ctx.reply(guild_mbalance['error'], ephemeral=False)


    @commands.command(
        usage='mbalance [coin]', 
        aliases=['mbal'], 
        description="Get guild's balance."
    )
    async def mbalance(
        self, 
        ctx, 
        coin: str = None
    ):
        guild_mbalance = await self.guild_mbalance(ctx, coin)
        if guild_mbalance and "error" in guild_mbalance:
            await ctx.reply(guild_mbalance['error'])


def setup(bot):
    bot.add_cog(Guild(bot))