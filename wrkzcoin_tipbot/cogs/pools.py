import sys, traceback
import time, timeago
import discord
from discord.ext import commands
import json

from config import config
from Bot import *

class Pools(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(usage="pools <coin>", aliases=['pool'], description="Check hashrate of a coin.")
    async def pools(self, ctx, coin: str):
        async def get_miningpoolstat_coin(coin: str):
            global redis_conn, redis_expired
            COIN_NAME = coin.upper()
            key = "TIPBOT:MININGPOOLDATA:" + COIN_NAME
            if redis_conn and redis_conn.exists(key):
                return json.loads(redis_conn.get(key).decode())
            else:
                try:
                    openRedis()
                    try:
                        link = config.miningpoolstat.coinapi.replace("COIN_NAME", coin.lower())
                        print(f"Fetching {link}")
                        async with aiohttp.ClientSession() as cs:
                            async with cs.get(link, timeout=config.miningpoolstat.timeout) as r:
                                if r.status == 200:
                                    res_data = await r.read()
                                    res_data = res_data.decode('utf-8')
                                    decoded_data = json.loads(res_data)
                                    await cs.close()
                                    if decoded_data and len(decoded_data) > 0 and 'data' in decoded_data:
                                        redis_conn.set(key, json.dumps(decoded_data), ex=config.miningpoolstat.expired)
                                        return decoded_data
                                    else:
                                        print(f'MININGPOOLSTAT: Error {link} Fetching from miningpoolstats')
                                        return None
                    except asyncio.TimeoutError:
                        print(f'TIMEOUT: Fetching from miningpoolstats {COIN_NAME}')
                    except Exception:
                        await logchanbot(traceback.format_exc())
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                return None

        try:
            requested_date = int(time.time())
            COIN_NAME = coin.upper()
            if config.miningpoolstat.enable != 1:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{ctx.author.mention} Command temporarily disable')
                return
            if isinstance(ctx.message.channel, discord.DMChannel) == False and ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TURTLECOIN":
                await ctx.message.add_reaction(EMOJI_ERROR)
                return
            key = "TIPBOT:MININGPOOL:" + COIN_NAME
            key_hint = "TIPBOT:MININGPOOL:SHORTNAME:" + COIN_NAME
            if redis_conn and not redis_conn.exists(key):
                if redis_conn.exists(key_hint):
                    await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
                    await ctx.send(f'{ctx.author.mention} Did you mean **{redis_conn.get(key_hint).decode().lower()}**.')
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{ctx.author.mention} Unknown coin **{COIN_NAME}**.')
                return
            elif redis_conn and redis_conn.exists(key):
                # check if already in redis
                key_p = key + ":POOLS" # TIPBOT:MININGPOOL:COIN_NAME:POOLS
                key_data = "TIPBOT:MININGPOOLDATA:" + COIN_NAME
                get_pool_data = None
                is_cache = 'NO'
                if redis_conn and redis_conn.exists(key_data):
                    await ctx.message.add_reaction(EMOJI_FLOPPY)
                    get_pool_data = json.loads(redis_conn.get(key_data).decode())
                    is_cache = 'YES'
                else:
                    if ctx.author.id not in MINGPOOLSTAT_IN_PROCESS:
                        MINGPOOLSTAT_IN_PROCESS.append(ctx.author.id)
                    else:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{ctx.author.mention} You have another check of pools stats in progress.')
                        return
                    try:
                        async with ctx.typing():
                            await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
                            get_pool_data = await get_miningpoolstat_coin(COIN_NAME)
                    except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                        await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                        return
                if get_pool_data and 'data' in get_pool_data:
                    try:
                        embed = discord.Embed(title='Mining Pools for {}'.format(COIN_NAME), description='', timestamp=datetime.utcnow(), colour=7047495)
                        if 'symbol' in get_pool_data:
                            embed.add_field(name="Ticker", value=get_pool_data['symbol'], inline=True)
                        if 'algo' in get_pool_data:
                            embed.add_field(name="Algo", value=get_pool_data['algo'], inline=True)
                        if 'hashrate' in get_pool_data:
                            embed.add_field(name="Hashrate", value=hhashes(get_pool_data['hashrate']), inline=True)
                        i = 1
                        if len(get_pool_data['data']) > 0:
                            async def sorted_pools(pool_list):
                                # https://web.archive.org/web/20150222160237/stygianvision.net/updates/python-sort-list-object-dictionary-multiple-key/
                                mylist = sorted(pool_list, key=lambda k: -k['hashrate'])
                                return mylist
                            pool_links = ''
                            pool_list = await sorted_pools(get_pool_data['data'])

                            for each_pool in pool_list:
                                if i <= 15:
                                    try:
                                        hash_rate = hhashes(each_pool['hashrate'])
                                    except Exception as e:
                                        pass
                                    pool_name = None
                                    if 'pool_id' in each_pool:
                                        pool_name = each_pool['pool_id']
                                    elif 'text' in each_pool:
                                        pool_name = each_pool['text']
                                    if pool_name is None:
                                        pool_name = each_pool['url'].replace("https://", "").replace("http://", "").replace("www", "")
                                    pool_links += "#{}. [{}]({}) - {}\n".format(i, pool_name, each_pool['url'], hash_rate if hash_rate else '0H/s')
                                    i += 1
                            try:
                                embed.add_field(name="Pool List", value=pool_links)
                            except Exception as e:
                                await logchanbot(traceback.format_exc())
                        embed.add_field(name="OTHER LINKS", value="{} / {} / {} / {}".format("[More pools](https://miningpoolstats.stream/{})".format(COIN_NAME.lower()), "[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
                        embed.set_footer(text="Data from https://miningpoolstats.stream")
                        try:
                            msg = await ctx.send(embed=embed)
                            respond_date = int(time.time())
                            await store.sql_miningpoolstat_fetch(COIN_NAME, str(ctx.author.id), 
                                                                '{}#{}'.format(ctx.author.name, ctx.author.discriminator), 
                                                                requested_date, respond_date, json.dumps(get_pool_data), str(ctx.guild.id) if isinstance(ctx.channel, discord.DMChannel) == False else 'DM', 
                                                                ctx.guild.name if isinstance(ctx.channel, discord.DMChannel) == False else 'DM', 
                                                                str(ctx.message.channel.id), is_cache, SERVER_BOT, 'NO')
                            # sleep 3s
                            await asyncio.sleep(3)
                            await msg.add_reaction(EMOJI_OK_BOX)
                        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                            await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                            await logchanbot(traceback.format_exc())
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                    if ctx.author.id in MINGPOOLSTAT_IN_PROCESS:
                        MINGPOOLSTAT_IN_PROCESS.remove(ctx.author.id)
                else:
                    # Try old way
                    # if not exist, add to queue in redis
                    key_queue = "TIPBOT:MININGPOOL2:QUEUE"
                    if redis_conn and redis_conn.llen(key_queue) > 0:
                        list_coin_queue = redis_conn.lrange(key_queue, 0, -1)
                        if COIN_NAME not in list_coin_queue:
                            redis_conn.lpush(key_queue, COIN_NAME)
                    elif redis_conn and redis_conn.llen(key_queue) == 0:
                        redis_conn.lpush(key_queue, COIN_NAME)
                    try:
                        async with ctx.typing():
                            # loop and waiting for another fetch
                            retry = 0
                            await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
                            while True:
                                key = "TIPBOT:MININGPOOL2:" + COIN_NAME
                                key_p = key + ":POOLS" # TIPBOT:MININGPOOL2:COIN_NAME:POOLS
                                await asyncio.sleep(5)
                                if redis_conn and redis_conn.exists(key_p):
                                    result = json.loads(redis_conn.get(key_p).decode())
                                    is_cache = 'NO'
                                    try:
                                        embed = discord.Embed(title='Mining Pools for {}'.format(COIN_NAME), description='', timestamp=datetime.utcnow(), colour=7047495)
                                        i = 0
                                        if result and len(result) > 0:
                                            pool_links = ''
                                            hash_rate = ''
                                            for each in result:
                                                if i < 15 and i < len(result):
                                                    if len(each) >= 4:
                                                        hash_list = ['H/s', 'KH/s', 'MH/s', 'GH/s', 'TH/s', 'PH/s', 'EH/s']
                                                        if [ele for ele in hash_list if((ele in each[2]) and ('Hashrate' not in each[2]))]:
                                                            hash_rate = each[2]
                                                        elif [ele for ele in hash_list if((ele in each[3]) and ('Hashrate' not in each[3]))]:
                                                            hash_rate = each[3]
                                                        else:
                                                            hash_rate = ''
                                                        if hash_rate == '' and len(each) >= 5 and [ele for ele in hash_list if((ele in each[4]) and ('Hashrate' not in each[4]))]:
                                                            hash_rate = each[4]
                                                        elif hash_rate == '' and len(each) >= 6 and [ele for ele in hash_list if((ele in each[5]) and ('Hashrate' not in each[5]))]:
                                                            hash_rate = each[5]
                                                        elif hash_rate == '' and len(each) >= 7 and [ele for ele in hash_list if((ele in each[6]) and ('Hashrate' not in each[6]))]:
                                                            hash_rate = each[6]
                                                        pool_links += each[0] + ' ' + each[1] + ' ' + hash_rate + '\n'
                                                    else:
                                                        pool_links += each[0] + ' ' + each[1] + '\n'
                                                    i += 1
                                            try:
                                                embed.add_field(name="List", value=pool_links)
                                            except Exception as e:
                                                await logchanbot(traceback.format_exc())
                                        embed.add_field(name="OTHER LINKS", value="{} / {} / {} / {}".format("[More pools](https://miningpoolstats.stream/{})".format(COIN_NAME.lower()), "[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
                                        embed.set_footer(text="Data from https://miningpoolstats.stream")
                                        msg = await ctx.send(embed=embed)
                                        respond_date = int(time.time())
                                        await store.sql_miningpoolstat_fetch(COIN_NAME, str(ctx.author.id), 
                                                                            '{}#{}'.format(ctx.author.name, ctx.author.discriminator), 
                                                                            requested_date, respond_date, json.dumps(result), str(ctx.guild.id) if isinstance(ctx.channel, discord.DMChannel) == False else 'DM', 
                                                                            ctx.guild.name if isinstance(ctx.channel, discord.DMChannel) == False else 'DM', 
                                                                            str(ctx.message.channel.id), is_cache, SERVER_BOT, 'YES')
                                        # sleep 3s
                                        await msg.add_reaction(EMOJI_OK_BOX)
                                        await ctx.message.add_reaction(EMOJI_OK_HAND)
                                        break
                                        if ctx.author.id in MINGPOOLSTAT_IN_PROCESS:
                                            MINGPOOLSTAT_IN_PROCESS.remove(ctx.author.id)
                                        return
                                    except Exception as e:
                                        await ctx.message.add_reaction(EMOJI_ERROR)
                                        await logchanbot(traceback.format_exc())
                                        if ctx.author.id in MINGPOOLSTAT_IN_PROCESS:
                                            MINGPOOLSTAT_IN_PROCESS.remove(ctx.author.id)
                                        return
                                elif redis_conn and not redis_conn.exists(key_p):
                                    retry += 1
                                if retry >= 5:
                                    redis_conn.lrem(key_queue, 0, COIN_NAME)
                                    await ctx.message.add_reaction(EMOJI_ERROR)
                                    await ctx.send(f'{ctx.author.mention} We can not fetch data for **{COIN_NAME}**.')
                                    break
                                    if ctx.author.id in MINGPOOLSTAT_IN_PROCESS:
                                        MINGPOOLSTAT_IN_PROCESS.remove(ctx.author.id)
                                    return
                    except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                        if ctx.author.id in MINGPOOLSTAT_IN_PROCESS:
                            MINGPOOLSTAT_IN_PROCESS.remove(ctx.author.id)
                        await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                        return
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
            if ctx.author.id in MINGPOOLSTAT_IN_PROCESS:
                MINGPOOLSTAT_IN_PROCESS.remove(ctx.author.id)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)


def setup(bot):
    bot.add_cog(Pools(bot))