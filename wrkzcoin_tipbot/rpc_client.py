from discord_webhook import DiscordWebhook
import discord

from typing import Dict
from uuid import uuid4

import aiohttp
import asyncio
import json

from config import config

import sys, traceback
sys.path.append("..")
ENABLE_COIN_DOGE = config.Enable_Coin_Doge.split(",")
ENABLE_COIN_NANO = config.Enable_Coin_Nano.split(",")
ENABLE_XCH = config.Enable_Coin_XCH.split(",")

class RPCException(Exception):
    def __init__(self, message):
        super(RPCException, self).__init__(message)


async def logchanbot(content: str):
    filterword = config.discord.logfilterword.split(",")
    for each in filterword:
        content = content.replace(each, config.discord.filteredwith)
    if len(content) > 1500: content = content[:1500]
    try:
        webhook = DiscordWebhook(url=config.discord.botdbghook, content=f'```{discord.utils.escape_markdown(content)}```')
        webhook.execute()
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


async def call_aiohttp_wallet(method_name: str, coin: str, time_out: int = None, payload: Dict = None) -> Dict:
    coin_family = getattr(getattr(config,"daemon"+coin),"coin_family","TRTL")
    full_payload = {
        'params': payload or {},
        'jsonrpc': '2.0',
        'id': str(uuid4()),
        'method': f'{method_name}'
    }
    url = get_wallet_rpc_url(coin.upper())
    timeout = time_out or 60
    if method_name == "save" or method_name == "store":
        timeout = 300
    elif method_name == "sendTransaction":
        timeout = 180
    elif method_name == "createAddress" or method_name == "getSpendKeys":
        timeout = 60
    try:
        if coin.upper() == "LTHN":
            # Copied from XMR below
            try:
                async with aiohttp.ClientSession(headers={'Content-Type': 'application/json'}) as session:
                    async with session.post(url, json=full_payload, timeout=timeout) as response:
                        # sometimes => "message": "Not enough unlocked money" for checking fee
                        if method_name == "split_integrated_address":
                            # we return all data including error
                            if response.status == 200:
                                res_data = await response.read()
                                res_data = res_data.decode('utf-8')
                                decoded_data = json.loads(res_data)
                                return decoded_data
                        elif method_name == "transfer":
                            print('{} - transfer'.format(coin.upper()))
                            print(full_payload)

                        if response.status == 200:
                            res_data = await response.read()
                            res_data = res_data.decode('utf-8')
                            if method_name == "transfer":
                                print(res_data)
                            await session.close()
                            decoded_data = json.loads(res_data)
                            if 'result' in decoded_data:
                                return decoded_data['result']
                            else:
                                print(decoded_data)
                                return None
            except asyncio.TimeoutError:
                await logchanbot('call_aiohttp_wallet: method_name: {} COIN_NAME {} - timeout {}\nfull_payload:\n{}'.format(method_name, coin.upper(), timeout, json.dumps(payload)))
                print('TIMEOUT: {} COIN_NAME {} - timeout {}'.format(method_name, coin.upper(), timeout))
                return None
            except Exception:
                traceback.print_exc(file=sys.stdout)
                return None
        elif coin_family == "XMR":
            try:
                async with aiohttp.ClientSession(headers={'Content-Type': 'application/json'}) as session:
                    async with session.post(url, json=full_payload, timeout=timeout) as response:
                        # sometimes => "message": "Not enough unlocked money" for checking fee
                        if method_name == "transfer":
                            print('{} - transfer'.format(coin.upper()))
                            print(full_payload)
                        if response.status == 200:
                            res_data = await response.read()
                            res_data = res_data.decode('utf-8')
                            if method_name == "transfer":
                                print(res_data)
                            await session.close()
                            decoded_data = json.loads(res_data)
                            if 'result' in decoded_data:
                                return decoded_data['result']
                            else:
                                return None
            except asyncio.TimeoutError:
                await logchanbot('call_aiohttp_wallet: method_name: {} COIN_NAME {} - timeout {}\nfull_payload:\n{}'.format(method_name, coin.upper(), timeout, json.dumps(payload)))
                print('TIMEOUT: {} COIN_NAME {} - timeout {}'.format(method_name, coin.upper(), timeout))
                return None
            except Exception:
                traceback.print_exc(file=sys.stdout)
                return None
        elif coin_family in ["TRTL", "BCN"]:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=full_payload, timeout=timeout) as response:
                        if response.status == 200 or response.status == 201:
                            res_data = await response.read()
                            res_data = res_data.decode('utf-8')
                            await session.close()
                            decoded_data = json.loads(res_data)
                            if 'result' in decoded_data:
                                return decoded_data['result']
                            else:
                                await logchanbot(str(res_data))
                                return None
                        else:
                            await logchanbot(str(response))
                            return None
            except asyncio.TimeoutError:
                await logchanbot('call_aiohttp_wallet: {} COIN_NAME {} - timeout {}\nfull_payload:\n{}'.format(method_name, coin.upper(), timeout, json.dumps(payload)))
                print('TIMEOUT: {} COIN_NAME {} - timeout {}'.format(method_name, coin.upper(), timeout))
                return None
            except Exception:
                traceback.print_exc(file=sys.stdout)
                return None
    except asyncio.TimeoutError:
        print('TIMEOUT: method_name: {} - coin_family: {} - timeout {}'.format(method_name, coin_family, timeout))
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


async def call_doge(method_name: str, coin: str, payload: str = None) -> Dict:
    global ENABLE_COIN_DOGE
    timeout = 100
    COIN_NAME = coin.upper()
    headers = {
        'content-type': 'text/plain;',
    }
    if payload is None:
        data = '{"jsonrpc": "1.0", "id":"'+str(uuid4())+'", "method": "'+method_name+'", "params": [] }'
    else:
        data = '{"jsonrpc": "1.0", "id":"'+str(uuid4())+'", "method": "'+method_name+'", "params": ['+payload+'] }'
    url = None
    if COIN_NAME in ENABLE_COIN_DOGE:
        url = 'http://'+getattr(config,"daemon"+COIN_NAME).username+':'+getattr(config,"daemon"+COIN_NAME).password+'@'+getattr(config,"daemon"+COIN_NAME).rpchost+'/'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, timeout=timeout) as response:
                if response.status == 200:
                    res_data = await response.read()
                    res_data = res_data.decode('utf-8')
                    await session.close()
                    decoded_data = json.loads(res_data)
                    return decoded_data['result']
                else:
                    await logchanbot(f'Call {COIN_NAME} returns {str(response.status)} with method {method_name}')
    except asyncio.TimeoutError:
        print('TIMEOUT: method_name: {} - COIN: {} - timeout {}'.format(method_name, coin.upper(), timeout))
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


async def call_nano(coin: str, payload: str) -> Dict:
    global ENABLE_COIN_NANO
    timeout = 100
    COIN_NAME = coin.upper()
    url = None
    if COIN_NAME in ENABLE_COIN_NANO:
        url = 'http://'+getattr(config,"daemon"+COIN_NAME).rpchost
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload, timeout=timeout) as response:
                if response.status == 200:
                    res_data = await response.read()
                    res_data = res_data.decode('utf-8')
                    await session.close()
                    decoded_data = json.loads(res_data)
                    return decoded_data
    except asyncio.TimeoutError:
        print('TIMEOUT: COIN: {} - timeout {}'.format(coin.upper(), timeout))
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
    return None


async def call_xch(method_name: str, coin: str, payload: Dict=None) -> Dict:
    import ssl
    global ENABLE_XCH
    timeout = 100
    COIN_NAME = coin.upper()
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(getattr(config,"daemon"+COIN_NAME).cert, getattr(config,"daemon"+COIN_NAME).key)

    headers = {
        'Content-Type': 'application/json',
    }
    if payload is None:
        data = '{}'
    else:
        data = payload
    url = None
    if COIN_NAME in ENABLE_XCH:
        url = 'https://'+getattr(config,"daemon"+COIN_NAME).rpchost+'/'+method_name.lower()
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            async with session.post(url, json=data, headers=headers, timeout=timeout, ssl=ssl_context) as response:
                if response.status == 200:
                    res_data = await response.read()
                    res_data = res_data.decode('utf-8')
                    await session.close()
                    decoded_data = json.loads(res_data)
                    return decoded_data
                else:
                    await logchanbot(f'Call {COIN_NAME} returns {str(response.status)} with method {method_name}')
    except asyncio.TimeoutError:
        print('TIMEOUT: method_name: {} - COIN: {} - timeout {}'.format(method_name, coin.upper(), timeout))
        await logchanbot('call_doge: method_name: {} - COIN: {} - timeout {}'.format(method_name, coin.upper(), timeout))
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def get_wallet_rpc_url(coin: str = None):
    coin_family = getattr(getattr(config,"daemon"+coin),"coin_family","TRTL")
    if coin_family == "TRTL" or coin_family == "BCN" :
        return "http://"+getattr(config,"daemon"+coin,config.daemonWRKZ).wallethost + ":" + \
            str(getattr(config,"daemon"+coin,config.daemonWRKZ).walletport) \
            + '/json_rpc'
    elif coin_family == "XMR":
        return "http://"+getattr(config,"daemon"+coin,config.daemonWRKZ).wallethost + ":" + \
            str(getattr(config,"daemon"+coin,config.daemonWRKZ).walletport) \
            + '/json_rpc'
