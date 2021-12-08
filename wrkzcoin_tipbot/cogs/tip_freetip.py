import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class TipFreeTip(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def bot_log(self):
        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def process_freetip(
        self,
        ctx,
        amount: str, 
        coin: str, 
        duration: str='60s', 
        comment: str=None
    ):
        await self.bot_log()
        # check if bot is going to restart
        if IS_RESTARTING: return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this."}
        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'tip')
        if account_lock:
            return {"error": f"{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}"}
        # end of check if account locked

        # Check if tx in progress
        if ctx.author.id in TX_IN_PROCESS:
            return {"error": f"{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress."}

        def hms_to_seconds(time_string):
            duration_in_second = 0
            try:
                time_string = time_string.replace("hours", "h")
                time_string = time_string.replace("hour", "h")
                time_string = time_string.replace("hrs", "h")
                time_string = time_string.replace("hr", "h")

                time_string = time_string.replace("minutes", "mn")
                time_string = time_string.replace("mns", "mn")
                time_string = time_string.replace("mins", "mn")
                time_string = time_string.replace("min", "mn")
                time_string = time_string.replace("m", "mn")
                mult = {'h': 60*60, 'mn': 60}
                duration_in_second = sum(int(num) * mult.get(val, 1) for num, val in re.findall('(\d+)(\w+)', time_string))
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
            return duration_in_second

        duration_s = 0
        try:
            duration_s = hms_to_seconds(duration)
        except Exception as e:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Invalid duration."}

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{EMOJI_RED_NO} This command can not be in private."}

        if duration_s == 0:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Invalid time given. Please use time format: XXs"}
        elif duration_s < config.freetip.duration_min or duration_s > config.freetip.duration_max:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Invalid duration. Please use between {str(config.freetip.duration_min)}s to {str(config.freetip.duration_max)}s."}

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        COIN_NAME = coin.upper()

        # TRTL discord
        if ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention}, Not in this guild with this coin."}

        if COIN_NAME not in ENABLE_COIN + ENABLE_XMR + ENABLE_COIN_DOGE + ENABLE_COIN_NANO + ENABLE_COIN_ERC + ENABLE_COIN_TRC + ENABLE_XCH:
            return {"error": f"{EMOJI_ERROR} {ctx.author.mention} **{COIN_NAME}** is not in our supported coins."}

        if not is_coin_tipable(COIN_NAME):
            return {"error": f"{EMOJI_ERROR} {ctx.author.mention} TIPPING is currently disable for {COIN_NAME}."}

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
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} not in allowed coins set by server manager."}
        # End of checking allowed coins

        if is_maintenance_coin(COIN_NAME):
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance."}

        notifyList = await store.sql_get_tipnotify()
        if coin_family == "ERC-20" or coin_family == "TRC-20":
            token_info = await store.get_token_info(COIN_NAME)
            real_amount = float(amount)
            MinTx = token_info['real_min_tip']
            MaxTx = token_info['real_max_tip']
        else:
            real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["XMR", "TRTL", "BCN", "NANO", "XCH"] else float(amount)
            MinTx = get_min_mv_amount(COIN_NAME)
            MaxTx = get_max_mv_amount(COIN_NAME)
        if comment and len(comment) > 0:
            MinTx = MinTx * config.freetip.with_comment_x_amount
            MaxTx = MaxTx * config.freetip.with_comment_x_amount

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
        get_user_balance = await get_balance_coin_user(str(ctx.author.id), COIN_NAME, discord_guild=False, server__bot=SERVER_BOT)
        if real_amount > MaxTx:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than {num_format_coin(MaxTx, COIN_NAME)} {COIN_NAME}."}
        elif real_amount < MinTx:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than {num_format_coin(MinTx, COIN_NAME)} {COIN_NAME}."}
        elif real_amount > get_user_balance['actual_balance']:
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to do a free tip of {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}."}


        if ctx.author.id not in TX_IN_PROCESS:
            TX_IN_PROCESS.append(ctx.author.id)
        attend_list = []
        ts = datetime.utcnow()
        embed = discord.Embed(title=f"Free Tip appears {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}", description=f"React {EMOJI_PARTY} to collect", timestamp=ts)
        add_index = 0
        try:
            if comment and len(comment) > 0:
                add_index = 1
                embed.add_field(name="Comment", value=comment, inline=True)
            embed.add_field(name="Attendees", value="React below to join!", inline=False)
            embed.add_field(name="Individual Tip Amount", value=f"{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}", inline=True)
            embed.add_field(name="Num. Attendees", value="**0** members", inline=True)
            embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, Time Left: {seconds_str(duration_s)}")
            msg: discord.Message = await ctx.send(embed=embed)
            await msg.add_reaction(EMOJI_PARTY)
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            if ctx.author.id in TX_IN_PROCESS:
                TX_IN_PROCESS.remove(ctx.author.id)
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention}, I got no permission."}
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
            if ctx.author.id in TX_IN_PROCESS:
                TX_IN_PROCESS.remove(ctx.author.id)
            return

        prev = []
        start_time = time.time()
        time_left = duration_s
        while time_left > 0:
            # Retrieve new reactions
            try:
                _msg: discord.Message = await self.bot.get_channel(ctx.channel.id).fetch_message(msg.id)

                # Find reaction we're looking for
                r = discord.utils.get(_msg.reactions, emoji=EMOJI_PARTY)
                if r:
                    # Get list of Users that reacted & filter bots out
                    attend_list = [i for i in await r.users().flatten() if not i.bot and i != ctx.author]

                    # Check if there's been a change, otherwise delay & recheck
                    if set(attend_list) == set(prev) or len(attend_list) == 0:
                        time_left = duration_s - (time.time() - start_time)
                        if int(time_left) % 3 == 0:  # Update embed every 3s with current time left
                            time_left = 0 if time_left <= 0 else time_left
                            embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, Time Left: {seconds_str(int(time_left))}")
                            await _msg.edit(embed=embed)
                        if time_left <= 0:
                            break
                        await asyncio.sleep(1)
                        continue

                    attend_list_names = " | ".join([str(u.name) + "#" + str(u.discriminator) for u in attend_list])
                    if len(attend_list_names) >= 1000:
                        attend_list_names = attend_list_names[:1000]
                    try:
                        embed.set_field_at(index=add_index, name='Attendees', value=attend_list_names, inline=False)
                        embed.set_field_at(index=1 + add_index, name='Each Member Receives:', value=f"{num_format_coin(real_amount / len(attend_list), COIN_NAME)} {COIN_NAME}", inline=True)
                        embed.set_field_at(index=2 + add_index, name="Num. Attendees", value=f"**{len(attend_list)}** members", inline=True)
                    except Exception as e:
                        traceback.print_exc(file=sys.stdout)

                    embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, Time Left: {seconds_str(int(time_left))}")
                    await msg.edit(embed=embed)
                    prev = attend_list

                time_left = duration_s - (time.time() - start_time)
                await asyncio.sleep(1)
            except Exception as e:
                if ctx.author.id in TX_IN_PROCESS:
                    TX_IN_PROCESS.remove(ctx.author.id)
                traceback.print_exc(file=sys.stdout)
                await logchanbot('Can not fetch message ID: {} in guild {}/{} channel #'.format(msg.id, msg.guild.id, msg.guild.name, msg.channel.name))
                return

        try:
            _msg: discord.Message = await self.bot.get_channel(ctx.channel.id).fetch_message(msg.id)
            # Find reaction we're looking for
            r = discord.utils.get(_msg.reactions, emoji=EMOJI_PARTY)
            if r:
                # Get list of Users that reacted & filter bots out
                tmp_attend_list = [i for i in await r.users().flatten() if not i.bot and i != ctx.author]
                if len(tmp_attend_list) > len(attend_list):
                    attend_list = tmp_attend_list
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())

        try:
            await msg.clear_reactions()
        except Exception as e:
            pass

        # re-check balance
        get_user_balance = await get_balance_coin_user(str(ctx.author.id), COIN_NAME, discord_guild=False, server__bot=SERVER_BOT)
        if real_amount > get_user_balance['actual_balance']:
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to do a free tip of {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}.')
            return
        # end of re-check balance

        # Multiple tip here
        notifyList = await store.sql_get_tipnotify()

        if len(attend_list) == 0:
            embed = discord.Embed(title=f"Free Tip appears {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}", description=f"Already expired", timestamp=ts)
            if comment and len(comment) > 0:
                embed.add_field(name="Comment", value=comment, inline=False)
            embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, and no one collected!")
            try:
                await msg.edit(embed=embed, components=[row_close_message])
                await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, discord.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
            if ctx.author.id in TX_IN_PROCESS:
                TX_IN_PROCESS.remove(ctx.author.id)
            return

        amountDiv = int(round(real_amount / len(attend_list), 2))  # cut 2 decimal only
        if coin_family == "DOGE" or coin_family == "ERC-20" or coin_family == "TRC-20":
            amountDiv = round(real_amount / len(attend_list), 4)

        attend_list_id = [member.id for member in attend_list]
        tip = None
        try:
            if coin_family in ["TRTL", "BCN"]:
                tip = await store.sql_mv_cn_multiple(str(ctx.author.id), amountDiv, attend_list_id, 'TIPALL', COIN_NAME)
            elif coin_family == "XMR":
                tip = await store.sql_mv_xmr_multiple(str(ctx.author.id), attend_list_id, amountDiv, COIN_NAME, "TIPALL")
            elif coin_family == "XCH":
                tip = await store.sql_mv_xch_multiple(str(ctx.author.id), attend_list_id, amountDiv, COIN_NAME, "TIPALL")
            elif coin_family == "NANO":
                tip = await store.sql_mv_nano_multiple(str(ctx.author.id), attend_list_id, amountDiv, COIN_NAME, "TIPALL")
            elif coin_family == "DOGE":
                tip = await store.sql_mv_doge_multiple(str(ctx.author.id), attend_list_id, amountDiv, COIN_NAME, "TIPALL")
            elif coin_family == "ERC-20":
                tip = await store.sql_mv_erc_multiple(str(ctx.author.id), attend_list_id, amountDiv, COIN_NAME, "TIPALL", token_info['contract'])
            elif coin_family == "TRC-20":
                tip = await store.sql_mv_trx_multiple(str(ctx.author.id), attend_list_id, amountDiv, COIN_NAME, "TIPALL", token_info['contract'])
        except Exception as e:
            await logchanbot(traceback.format_exc())

        # remove queue from tipall
        if ctx.author.id in TX_IN_PROCESS:
            TX_IN_PROCESS.remove(ctx.author.id)
        if tip:
            tipAmount = num_format_coin(real_amount, COIN_NAME)
            ActualSpend_str = num_format_coin(amountDiv * len(attend_list_id), COIN_NAME)
            amountDiv_str = num_format_coin(amountDiv, COIN_NAME)
            if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                await ctx.message.add_reaction(TOKEN_EMOJI)
            else:
                await ctx.message.add_reaction(get_emoji(COIN_NAME))
            # tipper shall always get DM. Ignore notifyList
            try:
                await ctx.author.send(
                    f'{EMOJI_ARROW_RIGHTHOOK} Free Tip of {tipAmount} '
                    f'{COIN_NAME} '
                    f'was collected by ({len(attend_list_id)}) members in server `{ctx.guild.name}`.\n'
                    f'Each member got: `{amountDiv_str} {COIN_NAME}`\n'
                    f'Actual spending: `{ActualSpend_str} {COIN_NAME}`')
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                await store.sql_toggle_tipnotify(str(ctx.author.id), "OFF")
            numMsg = 0
            for member_id in attend_list_id:
                member = self.bot.get_user(member_id)
                if ctx.author.id != member.id and member.id != self.bot.user.id:
                    if str(member.id) not in notifyList:
                        # random user to DM
                        dm_user = bool(random.getrandbits(1)) if len(attend_list_id) > config.tipallMax_LimitDM else True
                        if dm_user:
                            try:
                                await member.send(
                                    f'{EMOJI_MONEYFACE} You collected a free tip of {amountDiv_str} '
                                    f'{COIN_NAME} from {ctx.author.name}#{ctx.author.discriminator} in server `{ctx.guild.name}` #{ctx.channel.name}\n'
                                    f'{NOTIFICATION_OFF_CMD}')
                                numMsg += 1
                            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                await store.sql_toggle_tipnotify(str(member.id), "OFF")
                if numMsg >= config.tipallMax_LimitDM:
                    # stop DM if reaches
                    break


    @dislash.guild_only()
    @inter_client.slash_command(
        usage="freetip <amount> <coin> <duration> <comment here>", 
        options=[
            Option('amount', 'amount', OptionType.STRING, required=True),
            Option('coin', 'coin', OptionType.STRING, required=True),
            Option('duration', 'duration', OptionType.STRING, required=True),
            Option('comment', 'comment', OptionType.STRING, required=False)
        ],
        description="Distribute free tips to re-actors."
    )
    async def freetip(
        self, 
        ctx, 
        amount: str, 
        coin: str, 
        duration: str='60s', 
        comment: str=None
    ):
        amount = amount.replace(",", "")
        try:
            amount = Decimal(amount)
        except ValueError:
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
            return

        process_freetip = await self.process_freetip(ctx, amount, coin.upper(), duration, comment)
        if process_freetip and "error" in process_freetip:
            await ctx.reply(process_freetip['error'])


    @commands.guild_only()
    @commands.command(
        usage="freetip <amount> <coin> <duration> <comment here>", 
        description="Distribute free tips to re-actors."
    )
    async def freetip(
        self, 
        ctx, 
        amount: str, 
        coin: str, 
        duration: str='60s', 
        *, 
        comment: str=None
    ):
        amount = amount.replace(",", "")
        try:
            amount = Decimal(amount)
        except ValueError:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
            return

        process_freetip = await self.process_freetip(ctx, amount, coin.upper(), duration, comment)
        if process_freetip and "error" in process_freetip:
            await ctx.reply(process_freetip['error'])


def setup(bot):
    bot.add_cog(TipFreeTip(bot))