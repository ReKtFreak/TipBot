import sys
import traceback

import discord
from discord.ext import commands
from dislash import InteractionClient, ActionRow, Button, ButtonStyle, Option, OptionType

from Bot import *

from config import config

class CoinGecko(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def bot_log(self):
        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def paprika_coin(
        self, 
        coin: str
    ):
        COIN_NAME = coin.upper()
        target = coin.lower()
        if target == 'wow':
            target = 'wownero'
        elif target == 'wrkz':
            target = 'wrkzcoin'
        elif target == 'dego':
            target = 'derogold'
        key = config.redis_setting.prefix_paprika + coin.upper()
        # Get from redis
        try:
            openRedis()
            if redis_conn and redis_conn.exists(key):
                response_text = redis_conn.get(key).decode()
                return {"result": response_text, "cache": True}
        except Exception as e:
            traceback.format_exc()
            await logchanbot(traceback.format_exc())
            return {"error": "Internal error from cache."}

        try:
            if redis_conn and redis_conn.exists(config.redis_setting.prefix_paprika + "COINSLIST"):
                j = json.loads(redis_conn.get(config.redis_setting.prefix_paprika + "COINSLIST").decode())
            else:
                link = 'https://api.coinpaprika.com/v1/coins'
                async with aiohttp.ClientSession() as session:
                    async with session.get(link) as resp:
                        if resp.status == 200:
                            j = await resp.json()
                            # add to redis coins list
                            try:
                                openRedis()
                                redis_conn.set(config.redis_setting.prefix_paprika + "COINSLIST", json.dumps(j), ex=config.redis_setting.default_time_coinlist)
                            except Exception as e:
                                traceback.format_exc()
                            # end add to redis
            if target.isdigit():
                for i in j:
                    if int(target) == int(i['rank']):
                        id = i['id']
            else:
                if target == 'wow':
                    target = 'wownero'
                elif target == 'wrkz':
                    target = 'wrkzcoin'
                elif target == 'dego':
                    target = 'derogold'
                for i in j:
                    if target == i['name'].lower() or target == i['symbol'].lower():
                        id = i['id']
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get('https://api.coinpaprika.com/v1/tickers/{}'.format(id)) as resp:
                        if resp.status == 200:
                            j = await resp.json()
                            if 'error' in j and j['error'] == 'id not found':
                                return {"error": f"Can not get data **{coin.upper()}** from paprika."}
                            response_text = "{} ({}) is #{} by marketcap (${:,.2f}), trading at ${:.4f} with a 24h vol of ${:,.2f}. It's changed {}% over 24h, {}% over 7d, {}% over 30d, and {}% over 1y with an ath of ${} on {}.".format(j['name'], j['symbol'], j['rank'], float(j['quotes']['USD']['market_cap']), float(j['quotes']['USD']['price']), float(j['quotes']['USD']['volume_24h']), j['quotes']['USD']['percent_change_24h'], j['quotes']['USD']['percent_change_7d'], j['quotes']['USD']['percent_change_30d'], j['quotes']['USD']['percent_change_1y'], j['quotes']['USD']['ath_price'], j['quotes']['USD']['ath_date'])
                            
                            try:
                                openRedis()
                                redis_conn.set(key, response_text, ex=config.redis_setting.default_time_paprika)
                            except Exception as e:
                                traceback.format_exc()
                                await logchanbot(traceback.format_exc())
                            return {"result": response_text}
                        else:
                            return {"error": f"Can not get data **{coin.upper()}** from paprika."}
                        return
            except Exception as e:
                traceback.format_exc()
        except Exception as e:
            traceback.format_exc()
        return {"error": "No paprika only salt."}


    @commands.command(
        usage="cg", 
        aliases=['coingecko'], 
        description="Get coin information from CoinGecko."
    )
    async def cg(
        self, 
        ctx, 
        ticker: str
    ):
        await self.bot_log()
        if isinstance(ctx.message.channel, discord.DMChannel) == False and ctx.guild and ctx.guild.id == TRTL_DISCORD:
            return

        try:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if isinstance(ctx.message.channel, discord.DMChannel) == False and serverinfo \
            and 'enable_market' in serverinfo and serverinfo['enable_market'] == "NO":
                prefix = serverinfo['prefix']
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Market Command is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING MARKET`')
                await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}cg** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
                return
        except Exception as e:
            if isinstance(ctx.message.channel, discord.DMChannel) == False:
                return
            pass

        get_cg = await store.get_coingecko_coin(ticker)
        def format_amount(amount: float):
            if amount > 1:
                return '{:,.2f}'.format(amount)
            elif amount > 0.01:
                return '{:,.4f}'.format(amount)
            elif amount > 0.0001:
                return '{:,.6f}'.format(amount)
            elif amount > 0.000001:
                return '{:,.8f}'.format(amount)
            else:
                return '{:,.10f}'.format(amount)
        if get_cg and len(get_cg) > 0:
            rank = ''
            if 'name' in get_cg and 'mcap_ranking' in get_cg and get_cg['mcap_ranking']:
                rank = '{} Rank #{}'.format(get_cg['name'], get_cg['mcap_ranking'])
            embed = discord.Embed(title='{} at CoinGecko'.format(ticker.upper()), description='{}'.format(rank), timestamp=datetime.utcnow(), colour=7047495)
            if isinstance(get_cg['marketcap_USD'], float) and get_cg['marketcap_USD'] > 0:
                embed.add_field(name="MarketCap", value='{}USD'.format(format_amount(get_cg['marketcap_USD'])), inline=True)
            embed.add_field(name="High 24h", value='{}USD'.format(format_amount(get_cg['high24h_USD'])), inline=True)
            embed.add_field(name="Low 24h", value='{}USD'.format(format_amount(get_cg['low24h_USD'])), inline=True)
            embed.add_field(name="Market Price", value='{}USD'.format(format_amount(get_cg['marketprice_USD'])), inline=True)
            embed.add_field(name="Change (24h)", value='{:,.2f}%{}'.format(get_cg['price_change24h_percent'], EMOJI_CHART_DOWN if float(get_cg['price_change24h_percent']) < 0 else EMOJI_CHART_UP), inline=True)
            embed.add_field(name="Change (7d)", value='{:,.2f}%{}'.format(get_cg['price_change7d_percent'], EMOJI_CHART_DOWN if float(get_cg['price_change7d_percent']) < 0 else EMOJI_CHART_UP), inline=True)
            embed.add_field(name="Change (14d)", value='{:,.2f}%{}'.format(get_cg['price_change14d_percent'], EMOJI_CHART_DOWN if float(get_cg['price_change14d_percent']) < 0 else EMOJI_CHART_UP), inline=True)
            embed.add_field(name="Change (30d)", value='{:,.2f}%{}'.format(get_cg['price_change30d_percent'], EMOJI_CHART_DOWN if float(get_cg['price_change30d_percent']) < 0 else EMOJI_CHART_UP), inline=True)
            embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
            
            # Add image
            name_png = 'tmp_' + str(uuid.uuid4())
            random_file = config.cg_cmc_setting.static_file + name_png + '.png'
            url_png = config.cg_cmc_setting.url_file + name_png + '.png'
            graph_price = await store.cg_plot_price(ticker, 14, random_file)
            if graph_price:
                embed.set_image(url = url_png)
            try:
                embed.set_footer(text=f"Fetched from CoinGecko requested by {ctx.author.name}#{ctx.author.discriminator}")
            except Exception as e:
                await logchanbot(traceback.format_exc())
            try:
                msg = await ctx.send(embed=embed)
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                await msg.add_reaction(EMOJI_OK_BOX)
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                message_price = '{} at CoinGecko\n'.format(ticker.upper())
                if 'name' in get_cg and 'mcap_ranking' in get_cg and get_cg['mcap_ranking']:
                    message_price += '{} Rank #{}'.format(get_cg['name'], get_cg['mcap_ranking'])
                if isinstance(get_cg['marketcap_USD'], float) and get_cg['marketcap_USD'] > 0:
                    message_price += 'MarketCap:    {}USD\n'.format(format_amount(get_cg['marketcap_USD']))
                message_price += 'High 24h:     {}USD\n'.format(format_amount(get_cg['high24h_USD']))
                message_price += 'Low 24h:      {}USD\n'.format(format_amount(get_cg['low24h_USD']))
                message_price += 'Market Price: {}USD\n'.format(format_amount(get_cg['marketprice_USD']))
                message_price += 'Change 24h/7d/14d/30d:  {}%/{}%/{}%/{}%\n'.format(format_amount(get_cg['price_change24h_percent'], get_cg['price_change7d_percent'], get_cg['price_change14d_percent'], get_cg['price_change30d_percent']))
                try:
                    fetch = datetime.utcfromtimestamp(int(get_cg['fetch_date'])).strftime("%Y-%m-%d %H:%M:%S")
                    ago = str(timeago.format(fetch, datetime.utcnow()))
                    message_price += f"Fetched from CoinGecko {ago} requested by {ctx.author.name}#{ctx.author.discriminator}"
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                try:
                    msg = await ctx.send(f'{ctx.author.mention}```{message_price}```')
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                    await msg.add_reaction(EMOJI_OK_BOX)
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    await logchanbot(traceback.format_exc())
                    return
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} I can not find the ticker **{ticker}** in CoinGecko.')
        return


    @commands.command(
        usage="pricelist <coin1> <coin2> ...", 
        aliases=['pricetable', 'pt', 'pl'], 
        description="Get price list."
    )
    async def pricelist(
        self, 
        ctx, 
        *, 
        coin_list
    ):
        await self.bot_log()
        prefix = await get_guild_prefix(ctx)
        coin_list = ' '.join(coin_list.split())

        # disable game for TRTL discord
        if isinstance(ctx.message.channel, discord.DMChannel) == False and ctx.guild and ctx.guild.id == TRTL_DISCORD:
            return

        try:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if isinstance(ctx.message.channel, discord.DMChannel) == False and serverinfo \
            and 'enable_market' in serverinfo and serverinfo['enable_market'] == "NO":
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Market command is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING MARKET`')
                await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}price** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
                return
        except Exception as e:
            if isinstance(ctx.message.channel, discord.DMChannel) == False:
                return
            pass

        def format_amount(amount: float):
            if amount > 1:
                return '{:,.2f}'.format(amount)
            elif amount > 0.01:
                return '{:,.4f}'.format(amount)
            elif amount > 0.0001:
                return '{:,.6f}'.format(amount)
            else:
                return '{:,.8f}'.format(amount)

        has_none = True
        coin_list_call = coin_list.split(" ")
        if 10 >= len(coin_list_call) >= 1:
            table_data = [
                ["COIN", "CMC [USD]", "CG [USD]", "Remark"]
                ]
            for each_coin in coin_list_call:
                ticker = each_coin.upper()
                market_price = await store.market_value_in_usd(1, ticker)
                if market_price:
                    has_none = False
                    cmc_p = "N/A"
                    cg_p = "N/A"
                    cmc_ago = "N/A"
                    cg_ago = "N/A"
                    if 'cmc_price' in market_price and market_price['cmc_price'] > 0.00000001:
                        cmc_p = format_amount(market_price['cmc_price'])
                        update = datetime.strptime(market_price['cmc_update'].split(".")[0], '%Y-%m-%dT%H:%M:%S')
                        cmc_ago = timeago.format(update, datetime.utcnow())
                    if 'cg_price' in market_price and market_price['cg_price'] > 0.00000001:
                        cg_p = format_amount(market_price['cg_price'])
                        update = datetime.strptime(market_price['cg_update'].split(".")[0], '%Y-%m-%dT%H:%M:%S')
                        cg_ago = timeago.format(update, datetime.utcnow())
                    table_data.append([ticker, cmc_p, cg_p, ""])
            table = AsciiTable(table_data)
            table.padding_left = 0
            table.padding_right = 0
            try:
                embed = discord.Embed(title='Price List Command', description='Price Information', timestamp=datetime.utcnow(), colour=7047495)
                if has_none == True:
                    embed.add_field(name=coin_list.upper(), value='```N/A for {}```'.format(coin_list), inline=False)
                else:
                    embed.add_field(name=coin_list.upper(), value='```{}```'.format(table.table), inline=False)
                    embed.add_field(name="INFO", value='```CMC updated: {}\nCG updated: {}```'.format(cmc_ago, cg_ago), inline=False)
                embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
                embed.set_footer(text=f"Market command requested by {ctx.author.name}#{ctx.author.discriminator}. To disable Market Command, {prefix}setting market")
                try:
                    msg = await ctx.send(embed=embed)
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                    await msg.add_reaction(EMOJI_OK_BOX)
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                    await logchanbot(traceback.format_exc())
            except Exception as e:
                await logchanbot(traceback.format_exc())
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} Too many tickers.')
            return

    @commands.command(
        usage="gecko <coin>", 
        aliases=['gec'], 
        description="Get information of a coin in CoinGecko."
    )
    async def gecko(
        self, 
        ctx, 
        coin: str=None
    ):
        await self.bot_log()
        # disable game for TRTL discord
        if isinstance(ctx.message.channel, discord.DMChannel) == False and ctx.guild and ctx.guild.id == TRTL_DISCORD:
            return
        try:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if isinstance(ctx.message.channel, discord.DMChannel) == False and serverinfo \
            and 'enable_market' in serverinfo and serverinfo['enable_market'] == "NO":
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Market command is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING MARKET`')
                await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}gecko** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
                return
        except Exception as e:
            traceback.format_exc()
            if isinstance(ctx.message.channel, discord.DMChannel) == False:
                return
            pass
        if coin is None:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Missing coin name.')
            return
        else:
            coin = coin.lower()
            if coin == 'wow':
                coin = 'wownero'
            elif coin == 'wrkz':
                coin = 'wrkzcoin'
            elif coin == 'dego':
                coin = 'derogold'
            key = config.redis_setting.prefix_gecko + coin.upper()
            try:
                openRedis()
                if redis_conn and redis_conn.exists(key):
                    response_text = redis_conn.get(key).decode()
                    msg = await ctx.reply("{}#{}, {}".format(ctx.author.name, ctx.author.discriminator, response_text))
                    await msg.add_reaction(EMOJI_OK_BOX)
                    await ctx.message.add_reaction(EMOJI_FLOPPY)
                    return
            except Exception as e:
                traceback.format_exc()
                await logchanbot(traceback.format_exc())
        try:
            if redis_conn and redis_conn.exists(config.redis_setting.prefix_gecko + "COINSLIST"):
                j = json.loads(redis_conn.get(config.redis_setting.prefix_gecko + "COINSLIST").decode())
            else:
                link = 'https://api.coingecko.com/api/v3/coins/list'
                async with aiohttp.ClientSession() as session:
                    async with session.get(link) as resp:
                        if resp.status == 200:
                            j = await resp.json()
                            # add to redis coins list
                            try:
                                openRedis()
                                redis_conn.set(config.redis_setting.prefix_gecko + "COINSLIST", json.dumps(j), ex=config.redis_setting.default_time_coinlist)
                            except Exception as e:
                                traceback.format_exc()
                            # end add to redis
            for i in j:
                if coin == i['symbol'] or coin == i['name'].lower():
                    id = i['id']
        except Exception as e:
            traceback.format_exc()
            msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Can not get data for {coin}.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        try:
            if coin == 'wow':
                coin = 'wownero'
            elif coin == 'wrkz':
                coin = 'wrkzcoin'
            elif coin == 'dego':
                coin = 'derogold'
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.coingecko.com/api/v3/coins/{}'.format(id)) as resp:
                    if resp.status == 200:
                        j = await resp.json()
                        if 'error' in j and j['error'] == 'Could not find coin with the given id':
                            msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Can not get data **{coin.upper()}** from coingecko.')
                            await msg.add_reaction(EMOJI_OK_BOX)
                            return
                        name = j['name']
                        ticker = j['symbol'].upper()
                        mcaprank = j['market_cap_rank']
                        mcap = j['market_data']['market_cap']['usd']
                        geckorank = j['coingecko_rank']
                        btcprice = j['market_data']['current_price']['btc']
                        usdprice = j['market_data']['current_price']['usd']
                        athbtc = j['market_data']['ath']['btc']
                        athusd = j['market_data']['ath']['usd']
                        change_1d = j['market_data']['price_change_percentage_24h_in_currency']['usd']
                        change_1w = j['market_data']['price_change_percentage_7d_in_currency']['usd']
                        try:
                            change_1m = j['market_data']['price_change_percentage_30d_in_currency']['usd']
                        except: change_1m = 0
                        try:
                            change_1y = j['market_data']['price_change_percentage_1y_in_currency']['usd']
                        except: change_1y = 0
                        # add to redis
                        try:
                            openRedis()
                            response_text = "{} ({}) is #{:.0f} by mcap (${:,.2f}) and #{:.0f} by coingecko rank. Current price is {:.8f} BTC / ${:.3f}. ATH price is {:.8f} BTC / ${:.3f}. USD change: 1d {:.1f}%, 1w {:.1f}%, 1m {:.1f}%, 1y {:.1f}%.".format(name, ticker, mcaprank, mcap, geckorank, btcprice, usdprice, athbtc, athusd, change_1d, change_1w, change_1m, change_1y)
                            redis_conn.set(key, response_text, ex=config.redis_setting.default_time_gecko)
                        except Exception as e:
                            traceback.format_exc()
                            await logchanbot(traceback.format_exc())
                        msg = await ctx.reply("{}#{}, {}".format(ctx.author.name, ctx.author.discriminator, response_text))
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
        except:
            msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Can not get data for {coin}.')
            await msg.add_reaction(EMOJI_OK_BOX)
        return


    @commands.command(
        usage="price ...", 
        description="Check price with parameters."
    )
    async def price(
        self, 
        ctx, 
        *args
    ):
        await self.bot_log()
        prefix = await get_guild_prefix(ctx)
        PriceQ = (' '.join(args)).split()

        # disable game for TRTL discord
        if isinstance(ctx.message.channel, discord.DMChannel) == False and ctx.guild and ctx.guild.id == TRTL_DISCORD:
            return

        note = None
        try:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if isinstance(ctx.message.channel, discord.DMChannel) == False and serverinfo \
            and 'enable_market' in serverinfo and serverinfo['enable_market'] == "NO":
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Market command is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING MARKET`')
                await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}price** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
                return
        except Exception as e:
            if isinstance(ctx.message.channel, discord.DMChannel) == False:
                return
            pass

        def format_amount(amount: float):
            if amount > 1:
                return '{:,.2f}'.format(amount)
            elif amount > 0.01:
                return '{:,.4f}'.format(amount)
            elif amount > 0.0001:
                return '{:,.6f}'.format(amount)
            elif amount > 0.000001:
                return '{:,.8f}'.format(amount)
            else:
                return '{:,.10f}'.format(amount)

        if len(PriceQ) == 1:
            # Only ticker accepted
            if not re.match('^[a-zA-Z0-9]+$', PriceQ[0]):
                await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} Invalid **{ticker}**.')
                await ctx.message.add_reaction(EMOJI_ERROR)
                return
            
            ticker = PriceQ[0].upper()
            market_price = await store.market_value_in_usd(1, ticker)
            if market_price is None:
                await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} I can not find price information for **{ticker}** in CoinGecko and CMC.')
                await ctx.message.add_reaction(EMOJI_ERROR)
                return
            else:
                if ticker in SAME_TICKERS:
                    note = f'There are more than one ticker for {ticker}. Please check yourself in cmc or coingecko.'
                try:
                    embed = discord.Embed(title='{} Price'.format(ticker), description='Price Information', timestamp=datetime.utcnow(), colour=7047495)
                    if 'cmc_price' in market_price and market_price['cmc_price'] > 0.00000001:
                        update = datetime.strptime(market_price['cmc_update'].split(".")[0], '%Y-%m-%dT%H:%M:%S')
                        ago = timeago.format(update, datetime.utcnow())
                        if ticker in SAME_TICKERS:
                            embed.add_field(name="From CoinMarketCap", value='`1 {} = {}USD. Updated {} from CoinMarketCap`'.format(market_price['name_cmc'], format_amount(market_price['cmc_price']), ago), inline=False)
                        else:
                            embed.add_field(name="From CoinMarketCap", value='`1 {} = {}USD. Updated {} from CoinMarketCap`'.format(ticker, format_amount(market_price['cmc_price']), ago), inline=False)
                    if 'cg_price' in market_price and market_price['cg_price'] > 0.00000001:
                        update = datetime.strptime(market_price['cg_update'].split(".")[0], '%Y-%m-%dT%H:%M:%S')
                        ago = timeago.format(update, datetime.utcnow())
                        if ticker in SAME_TICKERS:
                            embed.add_field(name="From CoinGecko", value='`1 {} = {}USD. Updated {} from CoinGecko`'.format(market_price['name_cg'], format_amount(market_price['cg_price']), ago), inline=False)
                        else:
                            embed.add_field(name="From CoinGecko", value='`1 {} = {}USD. Updated {} from CoinGecko`'.format(ticker, format_amount(market_price['cg_price']), ago), inline=False)
                    if note:
                        embed.add_field(name="NOTE", value="`{}`".format(note), inline=False)
                    embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
                    embed.set_footer(text=f"Market command requested by {ctx.author.name}#{ctx.author.discriminator}. To disable Market Command, {prefix}setting market")
                    try:
                        msg = await ctx.send(embed=embed)
                        await ctx.message.add_reaction(EMOJI_OK_HAND)
                        await msg.add_reaction(EMOJI_OK_BOX)
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        await logchanbot(traceback.format_exc())
                    return
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                return
        elif len(PriceQ) == 2:
            # Only ticker accepted sample 10 btc, 15.2 btc
            # price 10.0 btc
            ticker = PriceQ[1].upper()
            if not re.match('^[a-zA-Z0-9]+$', ticker):
                await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} Invalid **{ticker}**.')
                await ctx.message.add_reaction(EMOJI_ERROR)
                return
            # check if valid number
            amount = None
            PriceQ[0] = PriceQ[0].replace(",", "")
            try:
                amount = int(PriceQ[0])
            except ValueError:
                pass
            try:
                amount = float(PriceQ[0])
            except ValueError:
                pass

            if amount is None:
                await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} Invalid amount **{PriceQ[0]}**.')
                await ctx.message.add_reaction(EMOJI_ERROR)
                return

            market_price = await store.market_value_in_usd(amount, ticker)
            if market_price is None:
                await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} I can not find price information for **{ticker}** in CoinGecko and CMC.')
                await ctx.message.add_reaction(EMOJI_ERROR)
                return
            else:
                if ticker in SAME_TICKERS:
                    note = f'There are more than one ticker for {ticker}. Please check yourself in cmc or coingecko.'
                try:
                    embed = discord.Embed(title='{}{} Price'.format(PriceQ[0], ticker), description='Price Information', timestamp=datetime.utcnow(), colour=7047495)
                    if 'cmc_price' in market_price and market_price['cmc_price'] > 0.00000001:
                        update = datetime.strptime(market_price['cmc_update'].split(".")[0], '%Y-%m-%dT%H:%M:%S')
                        ago = timeago.format(update, datetime.utcnow())
                        if note:
                            embed.add_field(name="From CoinMarketCap", value='`{} {} = {}USD. Updated {} from CoinMarketCap`'.format(PriceQ[0], PriceQ[1].upper(), format_amount(market_price['cmc_price'] * float(PriceQ[0])), ago), inline=False)
                        else:
                            embed.add_field(name="From CoinMarketCap", value='`{} {} = {}USD. Updated {} from CoinMarketCap`'.format(PriceQ[0], market_price['name_cmc'], format_amount(market_price['cmc_price'] * float(PriceQ[0])), ago), inline=False)
                    if 'cg_price' in market_price and market_price['cg_price'] > 0.00000001:
                        update = datetime.strptime(market_price['cg_update'].split(".")[0], '%Y-%m-%dT%H:%M:%S')
                        ago = timeago.format(update, datetime.utcnow())
                        if note:
                            embed.add_field(name="From CoinGecko", value='`{} {} = {}USD. Updated {} from CoinGecko`'.format(PriceQ[0], market_price['name_cg'], format_amount(market_price['cg_price'] * float(PriceQ[0])), ago), inline=False)
                        else:
                            embed.add_field(name="From CoinGecko", value='`{} {} = {}USD. Updated {} from CoinGecko`'.format(PriceQ[0], PriceQ[1].upper(), format_amount(market_price['cg_price'] * float(PriceQ[0])), ago), inline=False)
                    if note:
                        embed.add_field(name="NOTE", value="`{}`".format(note), inline=False)
                    embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
                    embed.set_footer(text=f"Market command requested by {ctx.author.name}#{ctx.author.discriminator}. To disable Market Command, {prefix}setting market")
                    try:
                        msg = await ctx.send(embed=embed)
                        await ctx.message.add_reaction(EMOJI_OK_HAND)
                        await msg.add_reaction(EMOJI_OK_BOX)
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        await logchanbot(traceback.format_exc())
                    return
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                return
        elif len(PriceQ) == 3:
            # .price xmr in btc
            if not re.match('^[a-zA-Z0-9]+$', PriceQ[0]) or not re.match('^[a-zA-Z0-9]+$', PriceQ[2]):
                await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} Invalid pairs **{PriceQ[0]}** and **{PriceQ[2]}**.')
                await ctx.message.add_reaction(EMOJI_ERROR)
                return

            if PriceQ[1].lower() == "in":
                ### A1 / B1 or A2 / B2
                tmpA1 = await store.market_value_cmc_usd(PriceQ[0])
                tmpA2 = await store.market_value_cg_usd(PriceQ[0])

                tmpB1 = await store.market_value_cmc_usd(PriceQ[2])
                tmpB2 = await store.market_value_cg_usd(PriceQ[2])

                if PriceQ[0].upper() in SAME_TICKERS:
                    note = f'There are more than one ticker for {PriceQ[0].upper()}. Please check yourself in cmc or coingecko.'
                if PriceQ[2].upper() in SAME_TICKERS:
                    if note:
                        note = f'There are more than one ticker for {PriceQ[0].upper()} and {PriceQ[2].upper()}. Please check yourself in cmc or coingecko.'
                    else:
                        note = f'There are more than one ticker for {PriceQ[2].upper()}. Please check yourself in cmc or coingecko.'
                try:
                    embed = discord.Embed(title='{} IN {}'.format(PriceQ[0].upper(), PriceQ[2].upper()), description='Price Information', timestamp=datetime.utcnow(), colour=7047495)
                    if any(x is None for x in [tmpA1, tmpB1]) and any(x is None for x in [tmpA2, tmpB2]):
                        embed.add_field(name="From CoinMarketCap", value='`No data from CoinMarketCap`', inline=True)
                        embed.add_field(name="From CoinGecko", value='`No data from Coingecko`', inline=True)
                    if tmpA1 and tmpB1:
                        totalValue = float(tmpA1 / tmpB1)
                        embed.add_field(name="From CoinMarketCap", value='`1 {} = {:,.8f}{} from CoinMarketCap`'.format(PriceQ[0].upper(), totalValue, PriceQ[2].upper()), inline=False)
                    if tmpA2 and tmpB2:
                        totalValue = float(tmpA2 / tmpB2)
                        embed.add_field(name="From CoinGecko", value='`1 {} = {:,.8f}{} from CoinGecko`'.format(PriceQ[0].upper(), totalValue, PriceQ[2].upper()), inline=False)
                    if note:
                        embed.add_field(name="NOTE", value="`{}`".format(note), inline=False)
                    embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
                    embed.set_footer(text=f"Market command requested by {ctx.author.name}#{ctx.author.discriminator}. To disable Market Command, {prefix}setting market")
                    try:
                        msg = await ctx.send(embed=embed)
                        await ctx.message.add_reaction(EMOJI_OK_HAND)
                        await msg.add_reaction(EMOJI_OK_BOX)
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        await logchanbot(traceback.format_exc())
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                return
        elif len(PriceQ) >= 4:
            # .price 10 xmr in btc
            if not re.match('^[a-zA-Z0-9]+$', PriceQ[1]) or not re.match('^[a-zA-Z0-9]+$', PriceQ[3]):
                await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} Invalid pairs **{PriceQ[1]}** and **{PriceQ[3]}**.')
                await ctx.message.add_reaction(EMOJI_ERROR)
                return

            if PriceQ[2].lower() != "in":
                await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} Invalid syntax.')
                await ctx.message.add_reaction(EMOJI_ERROR)
                return
            else:
                # check if valid number
                amount = None
                PriceQ[0] = PriceQ[0].replace(",", "")
                try:
                    amount = int(PriceQ[0])
                except ValueError:
                    message = 'Invalid given number.'
                    pass
                if amount is None:
                    try:
                        amount = float(PriceQ[0])
                    except ValueError:
                        message = 'Invalid given number.'

                if amount is None:
                    await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} Invalid amount **{PriceQ[0]}**.')
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    return

                ### A1 / B1 or A2 / B2
                tmpA1 = await store.market_value_cmc_usd(PriceQ[1])
                tmpA2 = await store.market_value_cg_usd(PriceQ[1])

                tmpB1 = await store.market_value_cmc_usd(PriceQ[3])
                tmpB2 = await store.market_value_cg_usd(PriceQ[3])

                if PriceQ[1].upper() in SAME_TICKERS:
                    note = f'There are more than one ticker for {PriceQ[1].upper()}. Please check yourself in cmc or coingecko.'
                if PriceQ[3].upper() in SAME_TICKERS:
                    if note:
                        note = f'There are more than one ticker for {PriceQ[1].upper()} and {PriceQ[3].upper()}. Please check yourself in cmc or coingecko.'
                    else:
                        note = f'There are more than one ticker for {PriceQ[3].upper()}. Please check yourself in cmc or coingecko.'
                try:
                    embed = discord.Embed(title='{}{} IN {}'.format(PriceQ[0], PriceQ[1].upper(), PriceQ[3].upper()), description='Price Information', timestamp=datetime.utcnow(), colour=7047495)
                    if any(x is None for x in [tmpA1, tmpB1]) and any(x is None for x in [tmpA2, tmpB2]):
                        embed.add_field(name="From CoinMarketCap", value='`No data from CoinMarketCap`', inline=True)
                        embed.add_field(name="From CoinGecko", value='`No data from Coingecko`', inline=True)
                    if tmpA1 and tmpB1:
                        totalValue = float(float(PriceQ[0]) * tmpA1 / tmpB1)
                        if tmpA1 == 0 or tmpB1 == 0:
                            embed.add_field(name="From CoinMarketCap", value='`Not sufficient data from CoinMarketCap`', inline=True)
                        else:
                            embed.add_field(name="From CoinMarketCap", value='`{} {} = {}{} from CoinMarketCap`'.format(PriceQ[0], PriceQ[1].upper(), format_amount(totalValue), PriceQ[3].upper()), inline=False)
                    if tmpA2 and tmpB2:
                        totalValue = float(float(PriceQ[0]) * tmpA2 / tmpB2)
                        if tmpA2 == 0 or tmpB2 == 0:
                            embed.add_field(name="From CoinGecko", value='`Not sufficient data from CoinGecko`', inline=True)
                        else:
                            embed.add_field(name="From CoinGecko", value='`{} {} = {}{} from CoinGecko`'.format(PriceQ[0], PriceQ[1].upper(), format_amount(totalValue), PriceQ[3].upper()), inline=False)
                    if note:
                        embed.add_field(name="NOTE", value="`{}`".format(note), inline=False)
                    embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
                    embed.set_footer(text=f"Market command requested by {ctx.author.name}#{ctx.author.discriminator}. To disable Market Command, {prefix}setting market")
                    try:
                        msg = await ctx.send(embed=embed)
                        await ctx.message.add_reaction(EMOJI_OK_HAND)
                        await msg.add_reaction(EMOJI_OK_BOX)
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        await logchanbot(traceback.format_exc())
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                return


    @inter_client.slash_command(usage="paprika [coin]",
                                aliases=['pap'],
                                options=[
                                    Option("coin", "Enter coin ticker/name", OptionType.STRING, required=True)
                                    # By default, Option is optional
                                    # Pass required=True to make it a required arg
                                ],
                                description="Check coin at Paprika.")
    async def paprika(
        self, 
        ctx, 
        coin: str
    ):
        prefix = await get_guild_prefix(ctx)
        get_pap = await self.paprika_coin(coin)
        if 'result' in get_pap:
            resp = get_pap['result']
            await ctx.reply(f"{ctx.author.name}#{ctx.author.discriminator}, {resp}", ephemeral=False)
        elif 'error' in get_pap:
            resp = get_pap['error']
            await ctx.reply(f"{EMOJI_RED_NO} {ctx.author.name}#{ctx.author.discriminator}, {resp}", ephemeral=False)


    @commands.command(
        usage="pap <coin>", 
        aliases=['paprika'], 
        description="Paprika."
    )
    async def pap(
        self, 
        ctx, 
        coin: str=None
    ):
        await self.bot_log()
        # disable game for TRTL discord
        if isinstance(ctx.message.channel, discord.DMChannel) == False and ctx.guild and ctx.guild.id == TRTL_DISCORD:
            return
        prefix = await get_guild_prefix(ctx)
        try:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if isinstance(ctx.message.channel, discord.DMChannel) == False and serverinfo \
            and 'enable_market' in serverinfo and serverinfo['enable_market'] == "NO":
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Market command is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING MARKET`')
                await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}pap** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
                return
        except Exception as e:
            traceback.format_exc()
            if isinstance(ctx.message.channel, discord.DMChannel) == False:
                return
            pass
        if coin is None:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Missing coin name.')
            return
        else:
            get_pap = await self.paprika_coin(coin)
            if 'result' in get_pap:
                resp = get_pap['result']
                msg = await ctx.reply(f"{ctx.author.name}#{ctx.author.discriminator}, {resp}")
                await msg.add_reaction(EMOJI_OK_BOX)
                if 'cache' in get_pap:
                    await ctx.message.add_reaction(EMOJI_FLOPPY)
            elif 'error' in get_pap:
                resp = get_pap['error']
                msg = await ctx.reply(f"{EMOJI_RED_NO} {ctx.author.name}#{ctx.author.discriminator}, {resp}")
                await msg.add_reaction(EMOJI_OK_BOX)


def setup(bot):
    bot.add_cog(CoinGecko(bot))