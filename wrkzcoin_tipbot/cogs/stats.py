import sys, traceback
import time, timeago
import disnake
from disnake.ext import commands

from config import config
from Bot import *

class Stats(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(
        usage="stats <coin|bot>", 
        aliases=['stat'], 
        description="Get Bot's statistic."
    )
    async def stats(
        self, 
        ctx, 
        coin: str = None
    ):
        COIN_NAME = None
        serverinfo = None
        if coin is None and isinstance(ctx.message.channel, disnake.DMChannel) == False:
            serverinfo = await get_info_pref_coin(ctx)
            COIN_NAME = serverinfo['default_coin'].upper()
        elif coin is None and isinstance(ctx.message.channel, disnake.DMChannel):
            COIN_NAME = "BOT"
        elif coin and isinstance(ctx.message.channel, disnake.DMChannel) == False:
            serverinfo = await get_info_pref_coin(ctx)
            COIN_NAME = coin.upper()
        elif coin:
            COIN_NAME = coin.upper()

        if COIN_NAME not in (ENABLE_COIN+ENABLE_XMR+ENABLE_COIN_ERC+ENABLE_COIN_TRC) and COIN_NAME != "BOT":
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} Unsupported or Unknown Ticker: **{COIN_NAME}**')
            return

        if is_maintenance_coin(COIN_NAME) and (ctx.author.id not in MAINTENANCE_OWNER):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            await ctx.reply(f'{EMOJI_RED_NO} {COIN_NAME} in maintenance.')
            return
        elif is_maintenance_coin(COIN_NAME) and (ctx.author.id in MAINTENANCE_OWNER):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)

        if COIN_NAME == "BOT":
            total_claimed = '{:,.0f}'.format(await store.sql_faucet_count_all())
            total_tx = await store.sql_count_tx_all()
            embed = disnake.Embed(title="[ TIPBOT ]", description="TipBot Stats", timestamp=datetime.utcnow(), color=0xDEADBF)
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)
            embed.add_field(name="Bot ID", value=str(self.bot.user.id), inline=True)
            embed.add_field(name="Guilds", value='{:,.0f}'.format(len(bot.guilds)), inline=True)
            embed.add_field(name="Shards", value='{:,.0f}'.format(self.bot.shard_count), inline=True)
            try:
                embed.add_field(name="Total Online", value='{:,.0f}'.format(sum(1 for m in self.bot.get_all_members() if m.status == disnake.Status.online)), inline=True)
                embed.add_field(name="Users", value='{:,.0f}'.format(sum(1 for m in self.bot.get_all_members() if m.bot == False)), inline=True)
                embed.add_field(name="Bots", value='{:,.0f}'.format(sum(1 for m in self.bot.get_all_members() if m.bot == True)), inline=True)
            except Exception as e:
                pass
            embed.add_field(name="Total faucet claims", value=total_claimed, inline=True)
            embed.add_field(name="Total tip operations", value='{:,.0f} off-chain, {:,.0f} on-chain'.format(total_tx['off_chain'], total_tx['on_chain']), inline=False)
            try:
                your_tip_count_10mn = await store.sql_get_countLastTip(str(ctx.author.id), 10*60)
                your_tip_count_24h = await store.sql_get_countLastTip(str(ctx.author.id), 24*3600)
                your_tip_count_7d = await store.sql_get_countLastTip(str(ctx.author.id), 7*24*3600)
                your_tip_count_30d = await store.sql_get_countLastTip(str(ctx.author.id), 30*24*3600)
                embed.add_field(name="You have tipped", value='Last 10mn: {:,.0f}, 24h: {:,.0f}, 7d: {:,.0f}, 30d: {:,.0f}'.format(your_tip_count_10mn, your_tip_count_24h, your_tip_count_7d, your_tip_count_30d), inline=False)
            except Exception as e:
                await logchanbot(traceback.format_exc())
            embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
            try:
                msg = await ctx.reply(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
            except (disnake.errors.NotFound, disnake.errors.Forbidden) as e:
                await logchanbot(traceback.format_exc())
                await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
            return

        gettopblock = None
        timeout = 60
        try:
            if COIN_NAME in ENABLE_COIN_ERC:
                gettopblock = await store.erc_get_block_number(COIN_NAME, timeout)
            elif COIN_NAME in ENABLE_COIN_TRC:
                gettopblock = await store.trx_get_block_number(COIN_NAME, timeout)
            else:
                gettopblock = await daemonrpc_client.gettopblock(COIN_NAME, time_out=timeout)
        except asyncio.TimeoutError:
            msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} connection to daemon timeout after {str(timeout)} seconds. I am checking info from wallet now.')
            await msg.add_reaction(EMOJI_OK_BOX)
        except Exception as e:
            await logchanbot(traceback.format_exc())

        walletStatus = None
        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
        if coin_family in ["TRTL", "BCN"]:
            try:
                walletStatus = await daemonrpc_client.getWalletStatus(COIN_NAME)
            except Exception as e:
                await logchanbot(traceback.format_exc())
        elif coin_family == "XMR":
            try:
                walletStatus = await daemonrpc_client.getWalletStatus(COIN_NAME)
            except Exception as e:
                await logchanbot(traceback.format_exc())

        prefix = await get_guild_prefix(ctx)
        if gettopblock and COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            COIN_DIFF = get_diff_target(COIN_NAME)
            if COIN_NAME != "TRTL":
                blockfound = datetime.utcfromtimestamp(int(gettopblock['block_header']['timestamp'])).strftime("%Y-%m-%d %H:%M:%S")
                ago = str(timeago.format(blockfound, datetime.utcnow()))
                difficulty = "{:,}".format(gettopblock['block_header']['difficulty'])
                hashrate = str(hhashes(int(gettopblock['block_header']['difficulty']) / int(COIN_DIFF)))
                height = "{:,}".format(gettopblock['block_header']['height'])
                reward = "{:,}".format(int(gettopblock['block_header']['reward'])/int(get_decimal(COIN_NAME)))
            else:
                # TRTL use daemon API
                blockfound = datetime.utcfromtimestamp(int(gettopblock['timestamp'])).strftime("%Y-%m-%d %H:%M:%S")
                ago = str(timeago.format(blockfound, datetime.utcnow()))
                difficulty = "{:,}".format(gettopblock['difficulty'])
                hashrate = str(hhashes(int(gettopblock['difficulty']) / int(COIN_DIFF)))
                height = "{:,}".format(gettopblock['height'])
                reward = "{:,}".format(int(gettopblock['reward'])/int(get_decimal(COIN_NAME)))
            if coin_family == "XMR":
                desc = f"Tip min/max: {num_format_coin(get_min_mv_amount(COIN_NAME), COIN_NAME)}-{num_format_coin(get_max_mv_amount(COIN_NAME), COIN_NAME)} {COIN_NAME}\n"
                desc += f"Tx min/max: {num_format_coin(get_min_tx_amount(COIN_NAME), COIN_NAME)}-{num_format_coin(get_max_tx_amount(COIN_NAME), COIN_NAME)} {COIN_NAME}\n"
                embed = disnake.Embed(title=f"[ {COIN_NAME} ]", 
                                      description=desc, 
                                      timestamp=datetime.utcnow(), color=0xDEADBF)
                embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)
                embed.add_field(name="NET HEIGHT", value=str(height), inline=True)
                embed.add_field(name="FOUND", value=ago, inline=True)
                embed.add_field(name="DIFFICULTY", value=difficulty, inline=True)
                embed.add_field(name="BLOCK REWARD", value=f'{reward} {COIN_NAME}', inline=True)
                if COIN_NAME not in ["XWP"]:
                    embed.add_field(name="NETWORK HASH", value=hashrate, inline=True)
                if walletStatus:
                    if COIN_NAME != "TRTL":
                        t_percent = '{:,.2f}'.format(truncate((walletStatus['height'] - 1)/gettopblock['block_header']['height']*100,2))
                    else:
                        t_percent = '{:,.2f}'.format(truncate((walletStatus['height'] - 1)/gettopblock['height']*100,2))
                    embed.add_field(name="WALLET SYNC %", value=t_percent + '% (' + '{:,.0f}'.format(walletStatus['height'] - 1) + ')', inline=True)
                if NOTICE_COIN[COIN_NAME]:
                    notice_txt = NOTICE_COIN[COIN_NAME]
                else:
                    notice_txt = NOTICE_COIN['default']
                embed.add_field(name='Related commands', value=f'`{prefix}coininfo {COIN_NAME}`, `{prefix}deposit {COIN_NAME}`, `{prefix}balance {COIN_NAME}`', inline=False)
                embed.set_footer(text=notice_txt)
                try:
                    msg = await ctx.reply(embed=embed)
                    await msg.add_reaction(EMOJI_OK_BOX)
                except (disnake.Forbidden, disnake.errors.Forbidden, disnake.errors.HTTPException) as e:
                    # if embedded denied
                    msg = await ctx.reply(f'**[ {COIN_NAME} ]**\n'
                                   f'```[NETWORK HEIGHT] {height}\n'
                                   f'[TIME]           {ago}\n'
                                   f'[DIFFICULTY]     {difficulty}\n'
                                   f'[BLOCK REWARD]   {reward} {COIN_NAME}\n'
                                   f'[TIP Min/Max]    {num_format_coin(get_min_mv_amount(COIN_NAME), COIN_NAME)}-{num_format_coin(get_max_mv_amount(COIN_NAME), COIN_NAME)} {COIN_NAME}\n'
                                   f'[TX Min/Max]     {num_format_coin(get_min_tx_amount(COIN_NAME), COIN_NAME)}-{num_format_coin(get_max_tx_amount(COIN_NAME), COIN_NAME)} {COIN_NAME}\n'
                                   '```')
                    await msg.add_reaction(EMOJI_OK_BOX)
                return
            else:
                walletBalance = None
                if walletStatus:
                    localDaemonBlockCount = int(walletStatus['blockCount'])
                    networkBlockCount = int(walletStatus['knownBlockCount'])
                    t_percent = '{:,.2f}'.format(truncate((localDaemonBlockCount - 1)/networkBlockCount*100,2))
                    t_localDaemonBlockCount = '{:,}'.format(localDaemonBlockCount)
                    t_networkBlockCount = '{:,}'.format(networkBlockCount)
                    if COIN_NAME in WALLET_API_COIN:
                        walletBalance = await walletapi.walletapi_get_sum_balances(COIN_NAME)    
                    else:
                        walletBalance = await get_sum_balances(COIN_NAME)
                desc = f"Tip min/max: {num_format_coin(get_min_mv_amount(COIN_NAME), COIN_NAME)}-{num_format_coin(get_max_mv_amount(COIN_NAME), COIN_NAME)} {COIN_NAME}\n"
                desc += f"Tx min/max: {num_format_coin(get_min_tx_amount(COIN_NAME), COIN_NAME)}-{num_format_coin(get_max_tx_amount(COIN_NAME), COIN_NAME)} {COIN_NAME}\n"
                embed = disnake.Embed(title=f"[ {COIN_NAME} ]", 
                                      description=desc, 
                                      timestamp=datetime.utcnow(), color=0xDEADBF)
                embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)
                embed.add_field(name="NET HEIGHT", value=str(height), inline=True)
                embed.add_field(name="FOUND", value=ago, inline=True)
                embed.add_field(name="DIFFICULTY", value=difficulty, inline=True)
                embed.add_field(name="BLOCK REWARD", value=f'{reward} {COIN_NAME}', inline=True)
                embed.add_field(name="NETWORK HASH", value=hashrate, inline=True)
                if walletStatus:
                    embed.add_field(name="WALLET SYNC %", value=t_percent + '% (' + '{:,.0f}'.format(localDaemonBlockCount - 1) + ')', inline=True)
                    embed.add_field(name="TOTAL UNLOCKED", value=num_format_coin(walletBalance['unlocked'], COIN_NAME) + COIN_NAME, inline=True)
                    embed.add_field(name="TOTAL LOCKED", value=num_format_coin(walletBalance['locked'], COIN_NAME) + COIN_NAME, inline=True)
                if NOTICE_COIN[COIN_NAME]:
                    notice_txt = NOTICE_COIN[COIN_NAME]
                else:
                    notice_txt = NOTICE_COIN['default']
                embed.add_field(name='Related commands', value=f'`{prefix}coininfo {COIN_NAME}`, `{prefix}deposit {COIN_NAME}`, `{prefix}balance {COIN_NAME}`', inline=False)
                embed.set_footer(text=notice_txt)
                try:
                    msg = await ctx.reply(embed=embed)
                    await msg.add_reaction(EMOJI_OK_BOX)
                except (disnake.Forbidden, disnake.errors.Forbidden, disnake.errors.HTTPException) as e:
                    # if embedded denied
                    balance_str = ''
                    if walletBalance and ('unlocked' in walletBalance) and ('locked' in walletBalance) and walletStatus:
                        balance_actual = num_format_coin(walletBalance['unlocked'], COIN_NAME)
                        balance_locked = num_format_coin(walletBalance['locked'], COIN_NAME)
                        balance_str = f'[TOTAL UNLOCKED] {balance_actual} {COIN_NAME}\n'
                        balance_str = balance_str + f'[TOTAL LOCKED]   {balance_locked} {COIN_NAME}'
                        msg = await ctx.reply(f'**[ {COIN_NAME} ]**\n'
                                       f'```[NETWORK HEIGHT] {height}\n'
                                       f'[TIME]           {ago}\n'
                                       f'[DIFFICULTY]     {difficulty}\n'
                                       f'[BLOCK REWARD]   {reward} {COIN_NAME}\n'
                                       f'[NETWORK HASH]   {hashrate}\n'
                                       f'[TIP Min/Max]    {num_format_coin(get_min_mv_amount(COIN_NAME), COIN_NAME)}-{num_format_coin(get_max_mv_amount(COIN_NAME), COIN_NAME)} {COIN_NAME}\n'
                                       f'[TX Min/Max]     {num_format_coin(get_min_tx_amount(COIN_NAME), COIN_NAME)}-{num_format_coin(get_max_tx_amount(COIN_NAME), COIN_NAME)} {COIN_NAME}\n'
                                       f'[WALLET SYNC %]: {t_percent}' + '% (' + '{:,.0f}'.format(localDaemonBlockCount - 1) + ')\n'
                                       f'{balance_str}'
                                       '```')
                    else:
                        msg = await ctx.reply(f'**[ {COIN_NAME} ]**\n'
                                       f'```[NETWORK HEIGHT] {height}\n'
                                       f'[TIME]           {ago}\n'
                                       f'[DIFFICULTY]     {difficulty}\n'
                                       f'[BLOCK REWARD]   {reward} {COIN_NAME}\n'
                                       f'[NETWORK HASH]   {hashrate}\n'
                                       f'[TIP Min/Max]    {num_format_coin(get_min_mv_amount(COIN_NAME), COIN_NAME)}-{num_format_coin(get_max_mv_amount(COIN_NAME), COIN_NAME)} {COIN_NAME}\n'
                                       f'[TX Min/Max]     {num_format_coin(get_min_tx_amount(COIN_NAME), COIN_NAME)}-{num_format_coin(get_max_tx_amount(COIN_NAME), COIN_NAME)} {COIN_NAME}\n'
                                       '```')
                    await msg.add_reaction(EMOJI_OK_BOX)
                return
        elif COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            if gettopblock is None and coin_family in ["TRTL", "BCN"] and walletStatus:
                localDaemonBlockCount = int(walletStatus['blockCount'])
                networkBlockCount = int(walletStatus['knownBlockCount'])
                t_percent = '{:,.2f}'.format(truncate((localDaemonBlockCount - 1)/networkBlockCount*100,2))
                t_localDaemonBlockCount = '{:,}'.format(localDaemonBlockCount)
                t_networkBlockCount = '{:,}'.format(networkBlockCount)
                if COIN_NAME in WALLET_API_COIN:
                    walletBalance = await walletapi.walletapi_get_sum_balances(COIN_NAME)    
                else:
                    walletBalance = await get_sum_balances(COIN_NAME)     
                desc = f"Tip min/max: {num_format_coin(get_min_mv_amount(COIN_NAME), COIN_NAME)}-{num_format_coin(get_max_mv_amount(COIN_NAME), COIN_NAME)} {COIN_NAME}\n"
                desc += f"Tx min/max: {num_format_coin(get_min_tx_amount(COIN_NAME), COIN_NAME)}-{num_format_coin(get_max_tx_amount(COIN_NAME), COIN_NAME)} {COIN_NAME}\n"
                embed = disnake.Embed(title=f"[ {COIN_NAME} ]", 
                                      description=desc, 
                                      timestamp=datetime.utcnow(), color=0xDEADBF)
                embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)
                embed.add_field(name="LOCAL DAEMON", value=str(t_localDaemonBlockCount), inline=True)
                embed.add_field(name="NETWORK", value=str(t_networkBlockCount), inline=True)
                embed.add_field(name="WALLET SYNC %", value=t_percent + '% (' + '{:,.0f}'.format(localDaemonBlockCount - 1) + ')', inline=True)
                embed.add_field(name="TOTAL UNLOCKED", value=num_format_coin(walletBalance['unlocked'], COIN_NAME) + COIN_NAME, inline=True)
                embed.add_field(name="TOTAL LOCKED", value=num_format_coin(walletBalance['locked'], COIN_NAME) + COIN_NAME, inline=True)
                embed.add_field(name='Related commands', value=f'`{prefix}coininfo {COIN_NAME}`, `{prefix}deposit {COIN_NAME}`, `{prefix}balance {COIN_NAME}`', inline=False)
                if NOTICE_COIN[COIN_NAME]:
                    notice_txt = NOTICE_COIN[COIN_NAME] + " | Daemon RPC not available"
                else:
                    notice_txt = NOTICE_COIN['default'] + " | Daemon RPC not available"
                embed.set_footer(text=notice_txt)
                try:
                    msg = await ctx.reply(embed=embed)
                    await msg.add_reaction(EMOJI_OK_BOX)
                except (disnake.Forbidden, disnake.errors.Forbidden, disnake.errors.HTTPException) as e:
                    # if embedded denied
                    balance_str = ''
                    if ('unlocked' in walletBalance) and ('locked' in walletBalance):
                        balance_actual = num_format_coin(walletBalance['unlocked'], COIN_NAME)
                        balance_locked = num_format_coin(walletBalance['locked'], COIN_NAME)
                        balance_str = f'[TOTAL UNLOCKED] {balance_actual} {COIN_NAME}\n'
                        balance_str = balance_str + f'[TOTAL LOCKED]   {balance_locked} {COIN_NAME}'
                        msg = await ctx.reply(f'**[ {COIN_NAME} ]**\n'
                                       f'```[LOCAL DAEMON]   {t_localDaemonBlockCount}\n'
                                       f'[NETWORK]        {t_networkBlockCount}\n'
                                       f'[WALLET SYNC %]: {t_percent}' + '% (' + '{:,.0f}'.format(localDaemonBlockCount - 1) + ')\n'
                                       f'[TIP Min/Max]    {num_format_coin(get_min_mv_amount(COIN_NAME), COIN_NAME)}-{num_format_coin(get_max_mv_amount(COIN_NAME), COIN_NAME)} {COIN_NAME}\n'
                                       f'[TX Min/Max]     {num_format_coin(get_min_tx_amount(COIN_NAME), COIN_NAME)}-{num_format_coin(get_max_tx_amount(COIN_NAME), COIN_NAME)} {COIN_NAME}\n'
                                       f'{balance_str}'
                                       '```'
                                       )
                    await msg.add_reaction(EMOJI_OK_BOX)
                return
            else:
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME}\'s status unavailable.')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
        elif COIN_NAME in ENABLE_COIN_ERC:
            try:
                token_info = await store.get_token_info(COIN_NAME)
                desc = f"Tip min/max: {num_format_coin(token_info['real_min_tip'], COIN_NAME)}-{num_format_coin(token_info['real_max_tip'], COIN_NAME)} {COIN_NAME}\n"
                desc += f"Tx min/max: {num_format_coin(token_info['real_min_tx'], COIN_NAME)}-{num_format_coin(token_info['real_max_tx'], COIN_NAME)} {COIN_NAME}\n"
                embed = disnake.Embed(title=f"[ {COIN_NAME} ]", 
                                      description=desc, 
                                      timestamp=datetime.utcnow(), color=0xDEADBF)
                embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)
                topBlock = await store.erc_get_block_number(COIN_NAME)
                embed.add_field(name="NETWORK", value='{:,}'.format(topBlock), inline=True)
                try:
                    get_main_balance = await store.http_wallet_getbalance(token_info['withdraw_address'], COIN_NAME, True)
                    if get_main_balance:
                        embed.add_field(name="MAIN BALANCE", value=num_format_coin(get_main_balance / 10**token_info['token_decimal'], COIN_NAME) + COIN_NAME, inline=True)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                try:
                    embed.add_field(name="COININFO", value=token_info['coininfo_note'], inline=True)
                    embed.add_field(name="EXPLORER", value=token_info['explorer_link'], inline=True)
                    embed.add_field(name='Related commands', value=f'`{prefix}coininfo {COIN_NAME}`, `{prefix}deposit {COIN_NAME}`, `{prefix}balance {COIN_NAME}`', inline=False)
                except Exception as e:
                    pass
                embed.set_footer(text=f"{token_info['deposit_note']}")
                try:
                    msg = await ctx.reply(embed=embed)
                    await msg.add_reaction(EMOJI_OK_BOX)
                except (disnake.Forbidden, disnake.errors.Forbidden, disnake.errors.HTTPException) as e:
                    pass
            except Exception as e:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await logchanbot(traceback.format_exc())
                print(traceback.format_exc())
        elif COIN_NAME in ENABLE_COIN_TRC:
            try:
                token_info = await store.get_token_info(COIN_NAME)
                desc = f"Tip min/max: {num_format_coin(token_info['real_min_tip'], COIN_NAME)}-{num_format_coin(token_info['real_max_tip'], COIN_NAME)} {COIN_NAME}\n"
                desc += f"Tx min/max: {num_format_coin(token_info['real_min_tx'], COIN_NAME)}-{num_format_coin(token_info['real_max_tx'], COIN_NAME)} {COIN_NAME}\n"
                embed = disnake.Embed(title=f"[ {COIN_NAME} ]", 
                                      description=desc, 
                                      timestamp=datetime.utcnow(), color=0xDEADBF)
                embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)
                topBlock = await store.trx_get_block_number(COIN_NAME)
                embed.add_field(name="NETWORK", value='{:,}'.format(topBlock), inline=True)
                try:
                    get_main_balance = await store.trx_wallet_getbalance(token_info['withdraw_address'], COIN_NAME)
                    embed.add_field(name="MAIN BALANCE", value=num_format_coin(get_main_balance, COIN_NAME) + COIN_NAME, inline=True)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                try:
                    embed.add_field(name="COININFO", value=token_info['coininfo_note'], inline=True)
                    embed.add_field(name="EXPLORER", value=token_info['explorer_link'], inline=True)
                    embed.add_field(name='Related commands', value=f'`{prefix}coininfo {COIN_NAME}`, `{prefix}deposit {COIN_NAME}`, `{prefix}balance {COIN_NAME}`', inline=False)
                except Exception as e:
                    pass
                embed.set_footer(text=f"{token_info['deposit_note']}")
                try:
                    msg = await ctx.reply(embed=embed)
                    await msg.add_reaction(EMOJI_OK_BOX)
                except (disnake.Forbidden, disnake.errors.Forbidden, disnake.errors.HTTPException) as e:
                    pass
            except Exception as e:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await logchanbot(traceback.format_exc())
                print(traceback.format_exc())


def setup(bot):
    bot.add_cog(Stats(bot))