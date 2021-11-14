import click
from discord_webhook import DiscordWebhook

import discord
from discord.ext import commands
from discord.ext.commands import Bot, AutoShardedBot, when_mentioned_or, CheckFailure

from discord.utils import get

import time, timeago
import simplejson as json
import pyotp

import store, daemonrpc_client, addressvalidation, addressvalidation_xch, walletapi, coin360, chart_pair_snapshot

from generic_xmr.address_msr import address_msr as address_msr
from generic_xmr.address_xmr import address_xmr as address_xmr
from generic_xmr.address_upx import address_upx as address_upx
from generic_xmr.address_wow import address_wow as address_wow
from generic_xmr.address_xol import address_xol as address_xol

# games.bagels
from games.bagels import getSecretNum as bagels_getSecretNum
from games.bagels import getClues as bagels_getClues
from games.hangman import drawHangman as hm_drawHangman
from games.hangman import load_words as hm_load_words

from games.maze2d import displayMaze as maze_displayMaze
from games.maze2d import createMazeDump as maze_createMazeDump

from games.blackjack import getDeck as blackjack_getDeck
from games.blackjack import displayHands as blackjack_displayHands
from games.blackjack import getCardValue as blackjack_getCardValue

from games.twentyfortyeight import getNewBoard as g2048_getNewBoard
from games.twentyfortyeight import drawBoard as g2048_drawBoard
from games.twentyfortyeight import getScore as g2048_getScore
from games.twentyfortyeight import addTwoToBoard as g2048_addTwoToBoard
from games.twentyfortyeight import isFull as g2048_isFull
from games.twentyfortyeight import makeMove as g2048_makeMove

# eth erc
from eth_account import Account

# linedraw
from linedraw.linedraw import *
from cairosvg import svg2png
import functools

from decimal import Decimal

from dislash import InteractionClient

# tb
from tb.tbfun import action as tb_action
# byte-oriented StringIO was moved to io.BytesIO in py3k
try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

# For eval
import contextlib
import io

# For hash file in case already have
import hashlib

import cv2
import numpy as np

from config import config
from wallet import *

# regex
import re
# reaction
from discord.utils import get
from datetime import datetime
import math, random
import os.path
import uuid
from PIL import Image, ImageDraw, ImageFont

# ascii table
from terminaltables import AsciiTable

import sys, traceback
import asyncio
import aiohttp

# numexpr
import numexpr

import binascii

# add logging
# CRITICAL, ERROR, WARNING, INFO, and DEBUG and if not specified defaults to WARNING.
import logging

# redis
import redis

# gTTs
from gtts import gTTS
from googletrans import Translator

bot_start_time = time.time()

redis_pool = None
redis_conn = None
redis_expired = 120

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

sys.path.append("..")

MAINTENANCE_OWNER = [386761001808166912]  # list owner
OWNER_ID_TIPBOT = 386761001808166912
TESTER = [ 288403695878537218 ]
# bingo and duckhunt
BOT_IGNORECHAN = [558173489194991626, 524572420468899860]  # list ignore chan
LOG_CHAN = 905302454365741066 # TODO: use config later
NOTIFY_TRADE_CHAN = config.discord.channelNotify

WALLET_SERVICE = None
LIST_IGNORECHAN = None
MUTE_CHANNEL = None

# param introduce by @bobbieltd
TX_IN_PROCESS = []

# tip-react temp storage
REACT_TIP_STORE = []

# faucet enabled coin. The faucet balance is taken from TipBot's own balance
FAUCET_COINS = config.Enable_Faucet_Coin.split(",")

# Coin using wallet-api
WALLET_API_COIN = config.Enable_Coin_WalletApi.split(",")

# Coin allowed to trade
ENABLE_TRADE_COIN = config.trade.enable_coin.split(",")
MIN_TRADE_RATIO = float(config.trade.Min_Ratio)
TRADE_PERCENT = config.trade.Trade_Margin

# coin or token same tickers
SAME_TICKERS = config.price.multiple_same_tickers.split(",")

# Fee per byte coin
FEE_PER_BYTE_COIN = config.Fee_Per_Byte_Coin.split(",")

# Bot invitation link
BOT_INVITELINK = "[Invite TipBot](http://invite.discord.bot.tips)"
BOT_INVITELINK_PLAIN = "http://invite.discord.bot.tips"

# DOGE will divide by 10 after random
FAUCET_MINMAX = {
    "WRKZ": [config.Faucet_min_max.wrkz_min, config.Faucet_min_max.wrkz_max],
    "DEGO": [config.Faucet_min_max.dego_min, config.Faucet_min_max.dego_max],
    "TRTL": [config.Faucet_min_max.trtl_min, config.Faucet_min_max.trtl_max],
    "DOGE": [config.Faucet_min_max.doge_min, config.Faucet_min_max.doge_max],
    "PGO": [config.Faucet_min_max.pgo_min, config.Faucet_min_max.pgo_max],
    "KVA": [config.Faucet_min_max.kva_min, config.Faucet_min_max.kva_max],
    "BTCMZ": [config.Faucet_min_max.btcmz_min, config.Faucet_min_max.btcmz_max],
    "NBXC": [config.Faucet_min_max.nbxc_min, config.Faucet_min_max.nbxc_max],
    "XFG": [config.Faucet_min_max.xfg_min, config.Faucet_min_max.xfg_max],
    "WOW": [config.Faucet_min_max.wow_min, config.Faucet_min_max.wow_max],
    "GNTL": [config.Faucet_min_max.gntl_min, config.Faucet_min_max.gntl_max],
    "BAN": [config.Faucet_min_max.ban_min, config.Faucet_min_max.ban_max],
    "NANO": [config.Faucet_min_max.nano_min, config.Faucet_min_max.nano_max],
    "BTIPZ": [config.Faucet_min_max.btipz_min, config.Faucet_min_max.btipz_max],
    "XFX": [config.Faucet_min_max.xfx_min, config.Faucet_min_max.xfx_max]
}


GAME_COIN = config.game.coin_game.split(",")
# This will multiplied in result
GAME_SLOT_REWARD = {
    "WRKZ": config.game_reward.wrkz,
    "DEGO": config.game_reward.dego,
    "TRTL": config.game_reward.trtl,
    "BTCMZ": config.game_reward.btcmz,
    "NBXC": config.game_reward.nbxc,
    "XFG": config.game_reward.xfg,
    "DOGE": config.game_reward.doge,
    "PGO": config.game_reward.pgo,
    "KVA": config.game_reward.kva,
    "WOW": config.game_reward.wow,
    "GNTL": config.game_reward.gntl,
    "BAN": config.game_reward.ban,
    "NANO": config.game_reward.nano,
    "BTIPZ": config.game_reward.btipz
}

SWAP_PAIR = {
    "WRKZ-BWRKZ": 1,
    "BWRKZ-WRKZ": 1,
    "WRKZ-XWRKZ": 1,
    "XWRKZ-WRKZ": 1
}

GAME_INTERACTIVE_PRGORESS = []
GAME_SLOT_IN_PRGORESS = []
GAME_DICE_IN_PRGORESS = []
GAME_MAZE_IN_PROCESS = []
CHART_TRADEVIEW_IN_PROCESS = []
GAME_INTERACTIVE_ECO = []
# miningpoolstat_progress
MINGPOOLSTAT_IN_PROCESS = []
# raffle queue join
GAME_RAFFLE_QUEUE = []


GUILD_ID_SLASH = [int(each) for each in config.discord.guild_id.split(",")]

# save all temporary
SAVING_ALL = None

# disclaimer message
DISCLAIM_MSG = """Disclaimer: No warranty or guarantee is provided, expressed, or implied \
when using this bot and any funds lost, mis-used or stolen in using this bot \
are not the responsibility of the bot creator or hoster."""

DISCLAIM_MSG_LONG = """```
Disclaimer: TipBot, its owners, service providers or any other parties providing services, \
are not in any way responsible or liable for any lost, mis-used, stolen funds, or any coin \
network's issues. TipBot's purpose is to be fun, do testing, and share tips between \
user to user, and its use is on each user’s own risks.

We operate the bot on our own rented servers. \
Feel free to donate if you like the TipBot and the service it provides. \
Your donations will help to fund the development & maintenance. 

We commit to make it as secure as possible to the best of our expertise, \
however we accept no liability and responsibility for any loss or damage \
caused to you. Additionally, the purpose of the TipBot is to spread awareness \
of cryptocurrency through tips, which is one of our project’s main commitments.

Updated July 1st, 2021
* We implemented a flat fee for each coin (tx/node). \
You can check by a command COININFO COINNAME
```
"""

IS_MAINTENANCE = config.maintenance
IS_RESTARTING = False
IS_DEBUG = False

# Get them from https://emojipedia.org
EMOJI_MONEYFACE = "\U0001F911"
EMOJI_ERROR = "\u274C"
EMOJI_OK_BOX = "\U0001F197"
EMOJI_OK_HAND = "\U0001F44C"
EMOJI_WARNING = "\u26A1"
EMOJI_ALARMCLOCK = "\u23F0"
EMOJI_HOURGLASS_NOT_DONE = "\u23F3"
EMOJI_CHECK = "\u2705"
EMOJI_MONEYBAG = "\U0001F4B0"
EMOJI_SCALE = "\u2696"
EMOJI_INFORMATION = "\u2139"
EMOJI_100 = "\U0001F4AF"
EMOJI_99 = "<:almost100:405478443028054036>"
EMOJI_TIP = "<:tip:424333592102043649>"
EMOJI_MAINTENANCE = "\U0001F527"
EMOJI_QUESTEXCLAIM = "\u2049"
EMOJI_CHECKMARK = "\u2714"
EMOJI_PARTY = "\U0001F389"

TOKEN_EMOJI = "\U0001F3CC"

EMOJI_UP = "\u2B06"
EMOJI_LEFT = "\u2B05"
EMOJI_RIGHT = "\u27A1"
EMOJI_DOWN = "\u2B07"
EMOJI_FIRE = "\U0001F525"
EMOJI_BOMB = "\U0001F4A3"
EMPTY_DISPLAY = '⬛' # ⬛ :black_large_square:

EMOJI_UP_RIGHT = "\u2197"
EMOJI_DOWN_RIGHT = "\u2198"
EMOJI_CHART_DOWN = "\U0001F4C9"
EMOJI_CHART_UP = "\U0001F4C8"

EMOJI_LETTER_S = "\U0001F1F8"
EMOJI_LETTER_H = "\U0001F1ED"

EMOJI_FLOPPY = "\U0001F4BE"

EMOJI_RED_NO = "\u26D4"
EMOJI_SPEAK = "\U0001F4AC"
EMOJI_ARROW_RIGHTHOOK = "\u21AA"
EMOJI_FORWARD = "\u23E9"
EMOJI_REFRESH = "\U0001F504"
EMOJI_ZIPPED_MOUTH = "\U0001F910"
EMOJI_LOCKED = "\U0001F512"

EMOJI_HELP_HOUSE = "\U0001F3E0" # :house:
EMOJI_HELP_GUILD = "\U0001F9D9" # :mage_man:
EMOJI_HELP_TIP = "\U0001F4B8" # :money_with_wings:
EMOJI_HELP_GAME = "\U0001F3B2" # :game_die:
EMOJI_HELP_TOOL = "\U0001F6E0" # :hammer_and_wrench:
EMOJI_HELP_NOTE = "\U0001F4DD" # :memo:
EMOJI_HELP_CG = "\U0001F4C8" # :chart_with_upwards_trend: :chart_increasing:

ENABLE_COIN = config.Enable_Coin.split(",")
ENABLE_COIN_DOGE = config.Enable_Coin_Doge.split(",")
ENABLE_XMR = config.Enable_Coin_XMR.split(",")
ENABLE_XCH = config.Enable_Coin_XCH.split(",")
ENABLE_COIN_NANO = config.Enable_Coin_Nano.split(",")
ENABLE_COIN_ERC = config.Enable_Coin_ERC.split(",")
ENABLE_COIN_TRC = config.Enable_Coin_TRC.split(",")
ENABLE_TIPTO = config.Enabe_TipTo_Coin.split(",")
ENABLE_RAFFLE_COIN = config.raffle.enable_coin.split(",")
MAINTENANCE_COIN = config.Maintenance_Coin.split(",")

COIN_REPR = "COIN"
DEFAULT_TICKER = "WRKZ"
ENABLE_COIN_VOUCHER = config.Enable_Coin_Voucher.split(",")
HIGH_DECIMAL_COIN = config.ManyDecimalCoin.split(",")

NOTICE_COIN = {}
for each in ENABLE_COIN+ENABLE_XMR+ENABLE_XCH+ENABLE_COIN_DOGE+ENABLE_COIN_NANO:
    try:
        NOTICE_COIN[each.upper()] = getattr(getattr(config,"daemon"+each.upper()),"coin_notice", None)
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
NOTICE_COIN['default'] = "Thank you for using."


EMOJI_COIN = {}
for each in ENABLE_COIN+ENABLE_XMR+ENABLE_COIN_DOGE+ENABLE_COIN_NANO+ENABLE_XCH:
    try:
        EMOJI_COIN[each.upper()] = getattr(getattr(config,"daemon"+each.upper()),"emoji", '\U0001F4B0')
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
for each in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
    try:
        EMOJI_COIN[each.upper()] = TOKEN_EMOJI
    except Exception as e:
        traceback.print_exc(file=sys.stdout)

# atomic Amount
ROUND_AMOUNT_COIN = {
    "DEGO" : 4 # 10^4
    }


# TRTL discord. Need for some specific tasks later.
TRTL_DISCORD = 388915017187328002

NOTIFICATION_OFF_CMD = 'Type: `.notifytip off` to turn off this notification or mention.'
MSG_LOCKED_ACCOUNT = "Your account is locked. Please contact Pluton#4425 in WrkzCoin discord. Check `.about` for more info."

bot_description = f"Tip {COIN_REPR} to other users on your server."
bot_help_info = "Get discord server's info for TipBot."

bot_help_stats = f"Show summary {COIN_REPR}: height, difficulty, etc."
bot_help_height = f"Show {COIN_REPR}'s current height"
bot_help_feedback = "Share your feedback or inquiry about TipBot to dev team"
bot_help_view_feedback = "View feedback submit by you"
bot_help_view_feedback_list = "List of your recent feedback."

SERVER_BOT = "DISCORD"

def init():
    global redis_pool
    print("PID %d: initializing redis pool..." % os.getpid())
    redis_pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True, db=8)


def openRedis():
    global redis_pool, redis_conn
    if redis_conn is None:
        try:
            redis_conn = redis.Redis(connection_pool=redis_pool)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)


def get_round_amount(coin: str, amount: int):
    COIN_NAME = coin.upper()
    if COIN_NAME in ROUND_AMOUNT_COIN:
        if amount > 10**ROUND_AMOUNT_COIN[COIN_NAME]:
            n = 10**ROUND_AMOUNT_COIN[COIN_NAME]
            return amount // n * n
        else:
            # less than define, cut only decimal
            return amount // get_decimal(COIN_NAME) * get_decimal(COIN_NAME)
    else:
        return amount


def get_emoji(coin: str):
    COIN_NAME = coin.upper()
    if COIN_NAME in EMOJI_COIN:
        return EMOJI_COIN[COIN_NAME]
    else:
        return EMOJI_ERROR


def get_notice_txt(coin: str):
    COIN_NAME = coin.upper()
    if COIN_NAME in NOTICE_COIN:
        if NOTICE_COIN[COIN_NAME] is None:
            return ""
        else:
            return "`" + NOTICE_COIN[COIN_NAME] + "`"
    else:
        return "Any support for this TipBot, please join https://chat.wrkz.work"


# Steal from https://github.com/cree-py/RemixBot/blob/master/bot.py#L49
async def get_prefix(bot, message):
    """Gets the prefix for the guild"""
    pre_cmd = config.discord.prefixCmd
    if isinstance(message.channel, discord.DMChannel):
        pre_cmd = config.discord.prefixCmd
        extras = [pre_cmd, 'tb!', 'tipbot!', '?', '.', '+', '!', '-']
        return when_mentioned_or(*extras)(bot, message)

    serverinfo = await store.sql_info_by_server(str(message.guild.id))
    if serverinfo is None:
        # Let's add some info if guild return None
        add_server_info = await store.sql_addinfo_by_server(str(message.guild.id), message.guild.name,
                                                            config.discord.prefixCmd, "WRKZ")
        pre_cmd = config.discord.prefixCmd
        serverinfo = await store.sql_info_by_server(str(message.guild.id))
    if serverinfo and ('prefix' in serverinfo):
        pre_cmd = serverinfo['prefix']
    else:
        pre_cmd =  config.discord.prefixCmd
    extras = [pre_cmd, 'tb!', 'tipbot!']
    return when_mentioned_or(*extras)(bot, message)


# Create ETH
def create_eth_wallet():
    Account.enable_unaudited_hdwallet_features()
    acct, mnemonic = Account.create_with_mnemonic()
    return {'address': acct.address, 'seed': mnemonic, 'private_key': acct.privateKey.hex()}

async def create_address_eth():
    wallet_eth = functools.partial(create_eth_wallet)
    create_wallet = await bot.loop.run_in_executor(None, wallet_eth)
    return create_wallet


intents = discord.Intents.default()
intents.members = True
intents.presences = True

bot = AutoShardedBot(command_prefix = get_prefix, case_insensitive=True, owner_id = OWNER_ID_TIPBOT, pm_help = True, intents=discord.Intents.all())
inter_client = InteractionClient(bot, test_guilds=GUILD_ID_SLASH)

bot.remove_command('help')


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


@bot.event
async def on_ready():
    global LIST_IGNORECHAN, MUTE_CHANNEL, IS_RESTARTING, BOT_INVITELINK, HANGMAN_WORDS
    HANGMAN_WORDS = hm_load_words()
    print('Ready!')
    print("Hello, I am TipBot Bot!")
    LIST_IGNORECHAN = await store.sql_listignorechan()
    MUTE_CHANNEL = await store.sql_list_mutechan()
    print("Loaded ignore and mute channel list.")
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    print("Guilds: {}".format(len(bot.guilds)))
    print("Bot invitation link: " + BOT_INVITELINK)
    if HANGMAN_WORDS and len(HANGMAN_WORDS) > 0: print('Loaded {} words for hangman.'.format(len(HANGMAN_WORDS)))
    game = discord.Game(name="making crypto fun!")
    await bot.change_presence(status=discord.Status.online, activity=game)
    botLogChan = bot.get_channel(LOG_CHAN)
    await botLogChan.send(f'{EMOJI_REFRESH} I am back :)')
    IS_RESTARTING = False


@bot.event
async def on_shard_ready(shard_id):
    print(f'Shard {shard_id} connected')


@bot.event
async def on_raw_reaction_add(payload):
    global EMOJI_OK_BOX
    if payload.guild_id is None:
        return  # Reaction is on a private message
    """Handle a reaction add."""
    try:
        emoji_partial = str(payload.emoji)
        message_id = payload.message_id
        channel_id = payload.channel_id
        user_id = payload.user_id
        guild = bot.get_guild(payload.guild_id)
        channel = bot.get_channel(channel_id)
        if not channel:
            return
        if isinstance(channel, discord.DMChannel):
            return
    except Exception as e:
        await logchanbot(traceback.format_exc())
        return
    message = None
    author = None
    if message_id:
        try:
            message = await channel.fetch_message(message_id)
            author = message.author
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            # No message found
            return
        member = bot.get_user(user_id)
        if emoji_partial in [EMOJI_OK_BOX] and message.author.id == bot.user.id \
            and author != member and message:
            # Delete message
            try:
                # do not delete maze or blackjack message
                if 'MAZE' in message.content.upper() or 'BLACKJACK' in message.content.upper() or 'YOUR SCORE' in message.content.upper() \
                or 'SOKOBAN ' in message.content.upper() or 'GAME 2048' in message.content.upper():
                    return
                try:
                    await message.delete()
                except Exception as e:
                    pass
                return
            except discord.errors.NotFound as e:
                # No message found
                return


@bot.event
async def on_reaction_add(reaction, user):
    global REACT_TIP_STORE, TRTL_DISCORD, EMOJI_99, EMOJI_TIP, TX_IN_PROCESS
    # If bot re-act, ignore.
    if user.id == bot.user.id:
        return
    # If other people beside bot react.
    else:
        # If re-action is OK box and message author is bot itself
        if reaction.emoji == EMOJI_OK_BOX and reaction.message.author.id == bot.user.id:
            # do not delete maze or blackjack message
            if 'MAZE' in reaction.message.content.upper() or 'BLACKJACK' in reaction.message.content.upper():
                return
            # do not delete some embed message
            if reaction.message.embeds and len(reaction.message.embeds) > 0:
                title = reaction.message.embeds[0].title
                try:
                    if title and ('SOKOBAN' in str(title.upper()) or 'FREE TIP' in str(title.upper())):
                        return
                except Exception as e:
                    pass
            try:
                await reaction.message.delete()
            except Exception as e:
                pass
        # EMOJI_100
        elif reaction.emoji == EMOJI_100 \
            and user.bot == False and reaction.message.author != user and reaction.message.author.bot == False:
            # check if react_tip_100 is ON in the server
            serverinfo = await store.sql_info_by_server(str(reaction.message.guild.id))
            if serverinfo['react_tip'] == "ON":
                if (str(reaction.message.id) + '.' + str(user.id)) not in REACT_TIP_STORE:
                    # OK add new message to array                  
                    pass
                else:
                    # he already re-acted and tipped once
                    return
                # get the amount of 100 from defined
                COIN_NAME = serverinfo['default_coin']
                real_amount = int(serverinfo['react_tip_100']) * get_decimal(COIN_NAME)
                MinTx = get_min_mv_amount(COIN_NAME)
                MaxTX = get_max_mv_amount(COIN_NAME)

                user_from = await store.sql_get_userwallet(str(user.id), COIN_NAME)
                if user_from is None:
                    userregister = await store.sql_register_user(str(user.id), COIN_NAME, SERVER_BOT, 0)
                user_to = await store.sql_get_userwallet(str(reaction.message.author.id), COIN_NAME)
                if user_to is None:
                    userregister = await store.sql_register_user(str(reaction.message.author.id), COIN_NAME, SERVER_BOT, 0)
                userdata_balance = await store.sql_user_balance(str(user.id), COIN_NAME)
                xfer_in = 0
                if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    xfer_in = await store.sql_user_balance_get_xfer_in(str(user.id), COIN_NAME)
                if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
                elif COIN_NAME in ENABLE_COIN_NANO:
                    actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
                    actual_balance = round(actual_balance / get_decimal(COIN_NAME), 6) * get_decimal(COIN_NAME)
                else:
                    actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])

                coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                # Negative check
                try:
                    if actual_balance < 0:
                        msg_negative = 'Negative balance detected:\nUser: '+str(user.id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
                        await logchanbot(msg_negative)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                # process other check balance
                if real_amount > actual_balance or \
                    real_amount > MaxTX or real_amount < MinTx:
                    return
                else:
                    # add queue also react-tip
                    if user.id not in TX_IN_PROCESS:
                        TX_IN_PROCESS.append(user.id)
                    else:
                        try:
                            msg = await user.send(f'{EMOJI_ERROR} You have another tx in progress. Re-act tip not proceed.')
                        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                            pass
                        return
                    tip = None
                    try:
                        tip = await store.sql_mv_cn_single(str(user.id), str(reaction.message.author.id), real_amount, 'REACTTIP', COIN_NAME)
                    except Exception as e:
                        await logchanbot(traceback.format_exc())

                    # remove queue from react-tip
                    if user.id in TX_IN_PROCESS:
                        TX_IN_PROCESS.remove(user.id)

                    if tip:
                        notifyList = await store.sql_get_tipnotify()
                        REACT_TIP_STORE.append((str(reaction.message.id) + '.' + str(user.id)))
                        if get_emoji(COIN_NAME) not in reaction.message.reactions:
                            await reaction.message.add_reaction(get_emoji(COIN_NAME))
                        # tipper shall always get DM. Ignore notifyList
                        try:
                            await user.send(
                                f'{EMOJI_ARROW_RIGHTHOOK} Tip of {num_format_coin(real_amount, COIN_NAME)} '
                                f'{COIN_NAME} '
                                f'was sent to {reaction.message.author.name}#{reaction.message.author.discriminator} in server `{reaction.message.guild.name}` by your re-acting {EMOJI_100}')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            await store.sql_toggle_tipnotify(str(user.id), "OFF")
                        if str(reaction.message.author.id) not in notifyList:
                            try:
                                await reaction.message.author.send(
                                    f'{EMOJI_MONEYFACE} You got a tip of {num_format_coin(real_amount, COIN_NAME)} '
                                    f'{COIN_NAME} from {user.name}#{user.discriminator} in server `{reaction.message.guild.name}` #{reaction.message.channel.name} from their re-acting {EMOJI_100}\n'
                                    f'{NOTIFICATION_OFF_CMD}')
                            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                await store.sql_toggle_tipnotify(str(reaction.message.author.id), "OFF")
                        return
                    else:
                        try:
                            await user.send(f'{user.mention} Can not deliver TX for {COIN_NAME} right now with {EMOJI_100}.')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            await store.sql_toggle_tipnotify(str(user.id), "OFF")
                        # add to failed tx table
                        await store.sql_add_failed_tx(COIN_NAME, str(user.id), user.name, real_amount, "REACTTIP")
                        return
        # EMOJI_99 TRTL_DISCORD Only
        elif str(reaction.emoji) == EMOJI_99 and reaction.message.guild.id == TRTL_DISCORD \
            and user.bot == False and reaction.message.author != user and reaction.message.author.bot == False:
            # check if react_tip_100 is ON in the server
            serverinfo = await store.sql_info_by_server(str(reaction.message.guild.id))
            if serverinfo['react_tip'] == "ON":
                if (str(reaction.message.id) + '.' + str(user.id)) not in REACT_TIP_STORE:
                    # OK add new message to array                  
                    pass
                else:
                    # he already re-acted and tipped once
                    return
                # get the amount of 100 from defined
                COIN_NAME = "TRTL"
                real_amount = 99 * get_decimal(COIN_NAME)
                MinTx = get_min_mv_amount(COIN_NAME)
                MaxTX = get_max_mv_amount(COIN_NAME)

                user_from = await store.sql_get_userwallet(str(user.id), COIN_NAME)
                if user_from is None:
                    userregister = await store.sql_register_user(str(user.id), COIN_NAME, SERVER_BOT, 0)

                userdata_balance = await store.sql_user_balance(str(user.id), COIN_NAME)
                xfer_in = 0
                if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    xfer_in = await store.sql_user_balance_get_xfer_in(str(user.id), COIN_NAME)
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
                        msg_negative = 'Negative balance detected:\nUser: '+str(user.id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
                        await logchanbot(msg_negative)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                user_to = await store.sql_get_userwallet(str(reaction.message.author.id), COIN_NAME)
                if user_to is None:
                    userregister = await store.sql_register_user(str(reaction.message.author.id), COIN_NAME, SERVER_BOT, 0)
                # process other check balance
                if real_amount > actual_balance or \
                    real_amount > MaxTX or real_amount < MinTx:
                    return
                else:
                    # add queue also react-tip
                    if user.id not in TX_IN_PROCESS:
                        TX_IN_PROCESS.append(user.id)
                    else:
                        try:
                            msg = await user.send(f'{EMOJI_ERROR} You have another tx in progress. Re-act tip not proceed.')
                        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                            pass
                        return

                    tip = None
                    try:
                        tip = await store.sql_mv_cn_single(str(user.id), str(reaction.message.author.id), real_amount, 'REACTTIP', COIN_NAME)
                    except Exception as e:
                        await logchanbot(traceback.format_exc())

                    # remove queue from react-tip
                    if user.id in TX_IN_PROCESS:
                        TX_IN_PROCESS.remove(user.id)

                    if tip:
                        notifyList = await store.sql_get_tipnotify()
                        REACT_TIP_STORE.append((str(reaction.message.id) + '.' + str(user.id)))
                        if get_emoji(COIN_NAME) not in reaction.message.reactions:
                            await reaction.message.add_reaction(get_emoji(COIN_NAME))
                        # tipper shall always get DM. Ignore notifyList
                        try:
                            await user.send(
                                f'{EMOJI_ARROW_RIGHTHOOK} Tip of {num_format_coin(real_amount, COIN_NAME)} '
                                f'{COIN_NAME} '
                                f'was sent to {reaction.message.author.name}#{reaction.message.author.discriminator} in server `{reaction.message.guild.name}` by your re-acting {EMOJI_99}')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            await store.sql_toggle_tipnotify(str(user.id), "OFF")
                        if str(reaction.message.author.id) not in notifyList:
                            try:
                                await reaction.message.author.send(
                                    f'{EMOJI_MONEYFACE} You got a tip of {num_format_coin(real_amount, COIN_NAME)} '
                                    f'{COIN_NAME} from {user.name}#{user.discriminator} in server `{reaction.message.guild.name}` #{reaction.message.channel.name} from their re-acting {EMOJI_99}\n'
                                    f'{NOTIFICATION_OFF_CMD}')
                            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                await store.sql_toggle_tipnotify(str(reaction.message.author.id), "OFF")
                        return
                    else:
                        try:
                            await user.send(f'{user.mention} Can not deliver TX for {COIN_NAME} right now with {EMOJI_99}.')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            await store.sql_toggle_tipnotify(str(user.id), "OFF")
                        # add to failed tx table
                        await store.sql_add_failed_tx(COIN_NAME, str(user.id), user.name, real_amount, "REACTTIP")
                        return
            else:
                return
        # EMOJI_TIP Only
        elif str(reaction.emoji) == EMOJI_TIP \
            and user.bot == False and reaction.message.author != user and reaction.message.author.bot == False:
            # They re-act TIP emoji
            # check if react_tip_100 is ON in the server
            serverinfo = await store.sql_info_by_server(str(reaction.message.guild.id))
            if serverinfo['react_tip'] == "ON":
                if (str(reaction.message.id) + '.' + str(user.id)) not in REACT_TIP_STORE:
                    # OK add new message to array                  
                    pass
                else:
                    # he already re-acted and tipped once
                    return
                # get the amount of 100 from defined
                msg = reaction.message.content
                # Check if bot re-act TIP also
                if EMOJI_TIP in reaction.message.reactions:
                    # bot in re-act list
                    users_reacted = reaction.message.reactions[reaction.message.reactions.index(EMOJI_TIP)].users()
                    if users_reacted:
                        if bot.user in users_reacted:
                            print('yes, bot also in TIP react')
                        else:
                            return
                args = reaction.message.content.split(" ")
                try:
                    amount = float(args[1].replace(",", ""))
                except ValueError:
                    return

                COIN_NAME = None
                try:
                    COIN_NAME = args[2].upper()
                    if COIN_NAME in ENABLE_XMR+ENABLE_XCH:
                        pass
                    elif COIN_NAME not in ENABLE_COIN:
                        if COIN_NAME in ENABLE_COIN_DOGE:
                            pass
                        elif 'default_coin' in serverinfo:
                            COIN_NAME = serverinfo['default_coin'].upper()
                except:
                    if 'default_coin' in serverinfo:
                        COIN_NAME = serverinfo['default_coin'].upper()
                print("TIP REACT COIN_NAME: " + COIN_NAME)
                await _tip_react(reaction, user, amount, COIN_NAME)
        return


@bot.command(hidden = True, pass_context=True, name='prefix')
async def prefix(ctx):
    prefix = await get_guild_prefix(ctx)
    try:
        msg = await ctx.send(f'{EMOJI_INFORMATION} {ctx.author.mention}, the prefix here is **{prefix}**')
        await msg.add_reaction(EMOJI_OK_BOX)
    except (discord.errors.NotFound, discord.errors.Forbidden) as e:
        await msg.add_reaction(EMOJI_ERROR)
        await logchanbot(traceback.format_exc())
    return


def hhashes(num) -> str:
    for x in ['H/s', 'KH/s', 'MH/s', 'GH/s', 'TH/s', 'PH/s', 'EH/s']:
        if num < 1000.0:
            return "%3.1f%s" % (num, x)
        num /= 1000.0
    return "%3.1f%s" % (num, 'TH/s')


async def alert_if_userlock(ctx, cmd: str):
    botLogChan = bot.get_channel(LOG_CHAN)
    get_discord_userinfo = None
    try:
        get_discord_userinfo = await store.sql_discord_userinfo_get(str(ctx.author.id))
    except Exception as e:
        await logchanbot(traceback.format_exc())
    if get_discord_userinfo is None:
        return None
    else:
        if get_discord_userinfo['locked'].upper() == "YES":
            await botLogChan.send(f'{ctx.author.name}#{ctx.author.discriminator} locked but is commanding `{cmd}`')
            return True
        else:
            return None


async def get_info_pref_coin(ctx):
    if isinstance(ctx.channel, discord.DMChannel):
        prefixChar = '.'
        return {'server_prefix': prefixChar}
    else:
        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo is None:
            # Let's add some info if server return None
            add_server_info = await store.sql_addinfo_by_server(str(ctx.guild.id),
                                                                ctx.message.guild.name, config.discord.prefixCmd, "WRKZ")
            server_id = str(ctx.guild.id)
            server_prefix = config.discord.prefixCmd
            server_coin = DEFAULT_TICKER
        else:
            server_id = str(ctx.guild.id)
            server_prefix = serverinfo['prefix']
            server_coin = serverinfo['default_coin'].upper()
            botchan = serverinfo['botchan'] or None
        return {'server_prefix': server_prefix, 'default_coin': server_coin, 'server_id': server_id, 'servername': ctx.guild.name, 'botchan': botchan}


def get_cn_coin_from_address(CoinAddress: str):
    COIN_NAME = None
    if CoinAddress.startswith("Wrkz"):
        COIN_NAME = "WRKZ"
    elif CoinAddress.startswith("dg"):
        COIN_NAME = "DEGO"
    elif CoinAddress.startswith("Nimb"):
        COIN_NAME = "NIMB"
    elif CoinAddress.startswith("cat1"):
        COIN_NAME = "CX"
    elif CoinAddress.startswith("XCR"):
        COIN_NAME = "NBXC"
    elif CoinAddress.startswith("ccx7"):
        COIN_NAME = "CCX"
    elif CoinAddress.startswith("fango"):
        COIN_NAME = "XFG"
    elif CoinAddress.startswith("btcm"):
        COIN_NAME = "BTCMZ"
    elif CoinAddress.startswith("PLe"):
        COIN_NAME = "PLE"
    elif CoinAddress.startswith("TRTL"):
        COIN_NAME = "TRTL"
    elif CoinAddress.startswith("bit") and (len(CoinAddress) == 98 or len(CoinAddress) == 109):
        COIN_NAME = "XTOR"
    elif (CoinAddress.startswith("4") or CoinAddress.startswith("8") or CoinAddress.startswith("5") or CoinAddress.startswith("9")) \
        and (len(CoinAddress) == 95 or len(CoinAddress) == 106):
        # XMR / MSR
        # 5, 9: MSR
        # 4, 8: XMR
        addr = None
        # Try MSR
        try:
            addr = address_msr(CoinAddress)
            COIN_NAME = "MSR"
            return COIN_NAME
        except Exception as e:
            # await logchanbot(traceback.format_exc())
            pass
        # Try XMR
        try:
            addr = address_xmr(CoinAddress)
            COIN_NAME = "XMR"
            return COIN_NAME
        except Exception as e:
            # await logchanbot(traceback.format_exc())
            pass
        # Try UPX	
        try:	
            addr = address_upx(CoinAddress)	
            COIN_NAME = "UPX"	
            return COIN_NAME	
        except Exception as e:	
            # traceback.print_exc(file=sys.stdout)	
            pass
    elif CoinAddress.startswith("L") and (len(CoinAddress) == 95 or len(CoinAddress) == 106):
        COIN_NAME = "LOKI"
    elif CoinAddress.startswith("cms") and (len(CoinAddress) == 98 or len(CoinAddress) == 109):
        COIN_NAME = "BLOG"
    elif (CoinAddress.startswith("WW") and len(CoinAddress) == 97) or \
    (CoinAddress.startswith("Wo") and len(CoinAddress) == 97) or \
    (CoinAddress.startswith("So") and len(CoinAddress) == 108):
        COIN_NAME = "WOW"
    elif (CoinAddress.startswith("Xw") and len(CoinAddress) == 97) or \
    (CoinAddress.startswith("iz") and len(CoinAddress) == 108):
        COIN_NAME = "XOL"
    elif CoinAddress.startswith("gnt") and (len(CoinAddress) == 98 or len(CoinAddress) == 99 or len(CoinAddress) == 109):
        COIN_NAME = "GNTL"
    elif ((CoinAddress.startswith("NV") or CoinAddress.startswith("NS")) and len(CoinAddress) == 97) or (CoinAddress.startswith("Ni") and len(CoinAddress) == 109):
        COIN_NAME = "XNV"
    elif ((CoinAddress.startswith("UPX") and len(CoinAddress) == 98) or (CoinAddress.startswith("UPi") and len(CoinAddress) == 109) or (CoinAddress.startswith("Um") and len(CoinAddress) == 97)):
        COIN_NAME = "UPX"
    elif (CoinAddress.startswith("5") or CoinAddress.startswith("9")) and (len(CoinAddress) == 95 or len(CoinAddress) == 106):
        COIN_NAME = "MSR"
    elif (CoinAddress.startswith("fh") and len(CoinAddress) == 97) or \
    (CoinAddress.startswith("fi") and len(CoinAddress) == 108) or \
    (CoinAddress.startswith("fs") and len(CoinAddress) == 97):
        COIN_NAME = "XWP"
    elif (CoinAddress[0] in ["T"]) and len(CoinAddress) == 34:
        COIN_NAME = "TRON_TOKEN"
    elif CoinAddress.startswith("D") and len(CoinAddress) == 34:
        COIN_NAME = "DOGE"
    elif CoinAddress.startswith("V") and len(CoinAddress) == 34:
        COIN_NAME = "KVA"
    elif (CoinAddress[0] in ["M", "L", "4", "5"]) and len(CoinAddress) == 34:
        COIN_NAME = None
    elif (CoinAddress[0] in ["P", "Q"]) and len(CoinAddress) == 34:
        COIN_NAME = "PGO"
    elif (CoinAddress[0] in ["3", "1"]) and len(CoinAddress) == 34:
        COIN_NAME = "BTC"
    elif (CoinAddress[0] in ["X"]) and len(CoinAddress) == 34:
        COIN_NAME = "DASH"
    elif CoinAddress.startswith("ban_") and len(CoinAddress) == 64:
        COIN_NAME = "BAN"
    elif CoinAddress.startswith("nano_") and len(CoinAddress) == 65:
        COIN_NAME = "NANO"
    elif CoinAddress.startswith("xch") and len(CoinAddress) == 62:
        COIN_NAME = "XCH"
    elif CoinAddress.startswith("xfx") and len(CoinAddress) == 62:
        COIN_NAME = "XFX"
    elif (CoinAddress.startswith("iz") and len(CoinAddress) == 97) or (CoinAddress.startswith("NaX") and len(CoinAddress) == 108):
        COIN_NAME = "LTHN"
    print('get_cn_coin_from_address return {}: {}'.format(CoinAddress, COIN_NAME))
    return COIN_NAME


async def check_guild_permissions(ctx, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    if ctx.guild is None:
        return False

    resolved = ctx.author.guild_permissions
    return check(getattr(resolved, name, None) == value for name, value in perms.items())


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send('This command cannot be used in private messages.')
    elif isinstance(error, commands.DisabledCommand):
        await ctx.send('Sorry. This command is disabled and cannot be used.')
    elif isinstance(error, commands.MissingRequiredArgument):
        #command = ctx.message.content.split()[0].strip('.')
        #await ctx.send('Missing an argument: try `.help` or `.help ' + command + '`')
        pass
    elif isinstance(error, commands.CommandNotFound):
        pass


# Update number of user, bot, channel
async def update_user_guild():
    while not bot.is_closed():
        for g in bot.guilds:
            num_channel = sum(1 for _ in g.channels)
            num_user = sum(1 for _ in g.members)
            num_bot = sum(1 for member in g.members if member.bot == True)
            num_online = sum(1 for member in g.members if member.status != "offline")
            await store.sql_updatestat_by_server(str(g.id), num_user, num_bot, num_channel, num_online, g.name)
        await asyncio.sleep(300)



async def update_block_height():
    sleep_time = 5
    while True:
        for coinItem in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_XCH:
            if is_maintenance_coin(coinItem) or not is_coin_depositable(coinItem):
                continue
            else:
                start = time.time()
                try:
                    await store.sql_block_height(coinItem)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                end = time.time()
            if end - start > config.interval.log_longduration:
                await logchanbot('update_block_height {} longer than {}s. Took {}s.'.format(coinItem, config.interval.log_longduration,  int(end - start)))
        for coinItem in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            if is_maintenance_coin(coinItem) or not is_coin_depositable(coinItem):
                continue
            else:
                start = time.time()
                try:
                    if coinItem in ENABLE_COIN_ERC:
                        await store.erc_get_block_number(coinItem)
                    elif coinItem in ENABLE_COIN_TRC:
                        await store.trx_get_block_number(coinItem)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                end = time.time()
            if end - start > config.interval.log_longduration:
                await logchanbot('update_block_height {} longer than {}s. Took {}s.'.format(coinItem, config.interval.log_longduration, int(end - start)))
        await asyncio.sleep(sleep_time)


async def unlocked_move_pending_erc_trx():
    while True:
        await asyncio.sleep(config.interval.update_balance)
        for coinItem in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            if is_maintenance_coin(coinItem) or not is_coin_depositable(coinItem):
                continue
            start = time.time()
            try:
                if coinItem in ENABLE_COIN_ERC:
                    await store.erc_check_pending_move_deposit(coinItem, 'ALL')
                    check_min = await store.erc_check_minimum_deposit(coinItem, 1800) # who inquire balance last 30mn
                elif coinItem in ENABLE_COIN_TRC:
                    await store.trx_check_pending_move_deposit(coinItem, 'ALL')
                    check_min = await store.trx_check_minimum_deposit(coinItem, 1800) # who inquire balance last 30mn
            except Exception as e:
                print(traceback.format_exc())
                await logchanbot(traceback.format_exc())
            end = time.time()
            if end - start > config.interval.log_longduration_token:
                await logchanbot('unlocked_move_pending_erc_trx {} longer than {}s. Took {}s.'.format(coinItem, config.interval.log_longduration_token, int(end - start)))
        await asyncio.sleep(config.interval.update_balance)


async def erc_trx_notify_new_confirmed_spendable():
    while True:
        await asyncio.sleep(config.interval.update_balance)
        for coinItem in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            if is_maintenance_coin(coinItem) or not is_coin_depositable(coinItem):
                continue
            start = time.time()
            try:
                notify_list = None
                if coinItem in ENABLE_COIN_ERC:
                    notify_list = await store.erc_get_pending_notification_users(coinItem)
                elif coinItem in ENABLE_COIN_TRC:
                    notify_list = await store.trx_get_pending_notification_users(coinItem)
                if notify_list and len(notify_list) > 0:
                    for each_notify in notify_list:
                        is_notify_failed = False
                        member = bot.get_user(int(each_notify['user_id']))
                        if member and int(each_notify['user_id']) != bot.user.id:
                            msg = "You got a new deposit confirmed: ```" + "Amount: {}{}".format(each_notify['real_amount'], coinItem) + "```"
                            try:
                                await member.send(msg)
                            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                is_notify_failed = True
                            except Exception as e:
                                traceback.print_exc(file=sys.stdout)
                                await logchanbot(traceback.format_exc())
                            if coinItem in ENABLE_COIN_ERC:
                                update_status = await store.erc_updating_pending_move_deposit(True, is_notify_failed, each_notify['txn'])
                            elif coinItem in ENABLE_COIN_TRC:
                                update_status = await store.trx_updating_pending_move_deposit(True, is_notify_failed, each_notify['txn'])
            except Exception as e:
                await logchanbot(traceback.format_exc())
            end = time.time()
        await asyncio.sleep(config.interval.update_balance)


# Let's run balance update by a separate process
async def update_balance():
    while True:
        for coinItem in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_XCH:
            if is_maintenance_coin(coinItem) or not is_coin_depositable(coinItem):
                continue
            start = time.time()
            try:
                await store.sql_update_balances(coinItem)
            except Exception as e:
                await logchanbot(traceback.format_exc())
            end = time.time()
            if end - start > config.interval.log_longduration:
                await logchanbot('update_balance {} longer than {}s. Took {}s'.format(coinItem, config.interval.log_longduration, int(end - start)))
        await asyncio.sleep(config.interval.update_balance)


# notify_new_tx_user_noconfirmation
async def notify_new_tx_user_noconfirmation():
    global redis_conn
    INTERVAL_EACH = config.interval.notify_tx
    while not bot.is_closed():
        await asyncio.sleep(INTERVAL_EACH)
        if config.notify_new_tx.enable_new_no_confirm == 1:
            key_tx_new = config.redis_setting.prefix_new_tx + 'NOCONFIRM'
            key_tx_no_confirmed_sent = config.redis_setting.prefix_new_tx + 'NOCONFIRM:SENT'
            try:
                openRedis()
                if redis_conn and redis_conn.llen(key_tx_new) > 0:
                    list_new_tx = redis_conn.lrange(key_tx_new, 0, -1)
                    list_new_tx_sent = redis_conn.lrange(key_tx_no_confirmed_sent, 0, -1) # byte list with b'xxx'
                    # Unique the list
                    list_new_tx = np.unique(list_new_tx).tolist()
                    list_new_tx_sent = np.unique(list_new_tx_sent).tolist()
                    for tx in list_new_tx:
                        try:
                            if tx not in list_new_tx_sent:
                                tx = tx.decode() # decode byte from b'xxx to xxx
                                key_tx_json = config.redis_setting.prefix_new_tx + tx
                                eachTx = None
                                try:
                                    if redis_conn.exists(key_tx_json): eachTx = json.loads(redis_conn.get(key_tx_json).decode())
                                except Exception as e:
                                    await logchanbot(traceback.format_exc())
                                if eachTx and eachTx['coin_name'] in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_XCH:
                                    user_tx = await store.sql_get_userwallet_by_paymentid(eachTx['payment_id'], eachTx['coin_name'], SERVER_BOT)
                                    if user_tx and eachTx['coin_name'] in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_XCH:
                                        user_found = bot.get_user(int(user_tx['user_id']))
                                        if user_found:
                                            try:
                                                msg = None
                                                confirmation_number_txt = "{} needs {} confirmations.".format(eachTx['coin_name'], get_confirm_depth(eachTx['coin_name']))
                                                if eachTx['coin_name'] not in ENABLE_COIN_DOGE:
                                                    msg = "You got a new **pending** deposit: ```" + "Coin: {}\nTx: {}\nAmount: {}\nHeight: {:,.0f}\n{}".format(eachTx['coin_name'], eachTx['txid'], num_format_coin(eachTx['amount'], eachTx['coin_name']), eachTx['height'], confirmation_number_txt) + "```"
                                                else:
                                                    msg = "You got a new **pending** deposit: ```" + "Coin: {}\nTx: {}\nAmount: {}\nBlock Hash: {}\n{}".format(eachTx['coin_name'], eachTx['txid'], num_format_coin(eachTx['amount'], eachTx['coin_name']), eachTx['blockhash'], confirmation_number_txt) + "```"
                                                await user_found.send(msg)
                                            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                                pass
                                            # TODO:
                                            redis_conn.lpush(key_tx_no_confirmed_sent, tx)
                                        else:
                                            # try to find if it is guild
                                            guild_found = bot.get_guild(id=int(user_tx['user_id']))
                                            if guild_found: user_found = bot.get_user(guild_found.owner.id)
                                            if guild_found and user_found:
                                                try:
                                                    msg = None
                                                    confirmation_number_txt = "{} needs {} confirmations.".format(eachTx['coin_name'], get_confirm_depth(eachTx['coin_name']))
                                                    if eachTx['coin_name'] not in ENABLE_COIN_DOGE:
                                                        msg = "Your guild got a new **pending** deposit: ```" + "Coin: {}\nTx: {}\nAmount: {}\nHeight: {:,.0f}\n{}".format(eachTx['coin_name'], eachTx['txid'], num_format_coin(eachTx['amount'], eachTx['coin_name']), eachTx['height'], confirmation_number_txt) + "```"
                                                    else:
                                                        msg = "Your guild got a new **pending** deposit: ```" + "Coin: {}\nTx: {}\nAmount: {}\nBlock Hash: {}\n{}".format(eachTx['coin_name'], eachTx['txid'], num_format_coin(eachTx['amount'], eachTx['coin_name']), eachTx['blockhash'], confirmation_number_txt) + "```"
                                                    await user_found.send(msg)
                                                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                                    pass
                                                except Exception as e:
                                                    await logchanbot(traceback.format_exc())
                                                redis_conn.lpush(key_tx_no_confirmed_sent, tx)
                                            else:
                                                #print('Can not find user id {} to notification **pending** tx: {}'.format(user_tx['user_id'], eachTx['txid']))
                                                pass
                                    # TODO: if no user
                                    # elif eachTx['coin_name'] in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR:
                                    #    redis_conn.lpush(key_tx_no_confirmed_sent, tx)
                                # if disable coin
                                else:
                                    redis_conn.lpush(key_tx_no_confirmed_sent, tx)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
            except Exception as e:
                await logchanbot(traceback.format_exc())
        await asyncio.sleep(INTERVAL_EACH)


# Notify user
async def notify_new_tx_user():
    INTERVAL_EACH = config.interval.notify_tx
    while not bot.is_closed():
        await asyncio.sleep(INTERVAL_EACH)
        pending_tx = await store.sql_get_new_tx_table('NO', 'NO')
        if pending_tx and len(pending_tx) > 0:
            # let's notify_new_tx_user
            for eachTx in pending_tx:
                try:
                    if eachTx['coin_name'] in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_XCH:
                        user_tx = await store.sql_get_userwallet_by_paymentid(eachTx['payment_id'], eachTx['coin_name'], SERVER_BOT)
                        if user_tx and user_tx['user_id']:
                            user_found = bot.get_user(int(user_tx['user_id']))
                            if user_found:
                                is_notify_failed = False
                                try:
                                    msg = None
                                    if eachTx['coin_name'] in ENABLE_COIN_NANO:
                                        msg = "You got a new deposit: ```" + "Coin: {}\nAmount: {}".format(eachTx['coin_name'], num_format_coin(eachTx['amount'], eachTx['coin_name'])) + "```"   
                                    elif eachTx['coin_name'] not in ENABLE_COIN_DOGE:
                                        msg = "You got a new deposit confirmed: ```" + "Coin: {}\nTx: {}\nAmount: {}\nHeight: {:,.0f}".format(eachTx['coin_name'], eachTx['txid'], num_format_coin(eachTx['amount'], eachTx['coin_name']), eachTx['height']) + "```"                         
                                    else:
                                        msg = "You got a new deposit confirmed: ```" + "Coin: {}\nTx: {}\nAmount: {}\nBlock Hash: {}".format(eachTx['coin_name'], eachTx['txid'], num_format_coin(eachTx['amount'], eachTx['coin_name']), eachTx['blockhash']) + "```"
                                    await user_found.send(msg)
                                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                    is_notify_failed = True
                                    pass
                                except Exception as e:
                                    await logchanbot(traceback.format_exc())
                                update_notify_tx = await store.sql_update_notify_tx_table(eachTx['payment_id'], user_tx['user_id'], user_found.name, 'YES', 'NO' if is_notify_failed == False else 'YES')
                            else:
                                # try to find if it is guild
                                guild_found = bot.get_guild(id=int(user_tx['user_id']))
                                if guild_found: user_found = bot.get_user(guild_found.owner.id)
                                if guild_found and user_found:
                                    is_notify_failed = False
                                    try:
                                        msg = None
                                        if eachTx['coin_name'] in ENABLE_COIN_NANO:
                                            msg = "Your guild got a new deposit: ```" + "Coin: {}\nAmount: {}".format(eachTx['coin_name'], num_format_coin(eachTx['amount'], eachTx['coin_name'])) + "```"   
                                        elif eachTx['coin_name'] not in ENABLE_COIN_DOGE:
                                            msg = "Your guild got a new deposit confirmed: ```" + "Coin: {}\nTx: {}\nAmount: {}\nHeight: {:,.0f}".format(eachTx['coin_name'], eachTx['txid'], num_format_coin(eachTx['amount'], eachTx['coin_name']), eachTx['height']) + "```"                         
                                        else:
                                            msg = "Your guild got a new deposit confirmed: ```" + "Coin: {}\nTx: {}\nAmount: {}\nBlock Hash: {}".format(eachTx['coin_name'], eachTx['txid'], num_format_coin(eachTx['amount'], eachTx['coin_name']), eachTx['blockhash']) + "```"
                                        await user_found.send(msg)
                                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                        is_notify_failed = True
                                        pass
                                    except Exception as e:
                                        await logchanbot(traceback.format_exc())
                                    update_notify_tx = await store.sql_update_notify_tx_table(eachTx['payment_id'], user_tx['user_id'], guild_found.name, 'YES', 'NO' if is_notify_failed == False else 'YES')
                                else:
                                    #print('Can not find user id {} to notification tx: {}'.format(user_tx['user_id'], eachTx['txid']))
                                    pass
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
                    await logchanbot(traceback.format_exc())
        await asyncio.sleep(INTERVAL_EACH)


# Notify user
async def notify_new_move_balance_user():
    time_lap = 5
    while not bot.is_closed():
        await asyncio.sleep(time_lap)
        pending_tx = await store.sql_get_move_balance_table('NO', 'NO')
        if pending_tx and len(pending_tx) > 0:
            # let's notify_new_tx_user
            for eachTx in pending_tx:
                try:
                    if eachTx['coin_name'] in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO:
                        if eachTx['to_server'] == SERVER_BOT:
                            user_found = bot.get_user(int(eachTx['to_userid']))
                            if user_found:
                                is_notify_failed = False
                                try:
                                    msg = "You got a new tip: ```" + "Coin: {}\nAmount: {}\nFrom: {}@{}".format(eachTx['coin_name'], num_format_coin(eachTx['amount'], eachTx['coin_name']), eachTx['from_name'], eachTx['from_server']) + "```"   
                                    await user_found.send(msg)
                                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                    is_notify_failed = True
                                except Exception as e:
                                    await logchanbot(traceback.format_exc())
                                update_receiver = await store.sql_update_move_balance_table(eachTx['id'], 'RECEIVER')
                            else:
                                await asyncio.sleep(time_lap)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
        await asyncio.sleep(time_lap)


async def trade_complete_sale_notify():
    while True:
        await asyncio.sleep(30.0)
        # get list of people to notify
        list_complete_sale_notify = await store.sql_get_completed_sale_notify(SERVER_BOT)
        if list_complete_sale_notify and len(list_complete_sale_notify) > 0:
            for each_notify in list_complete_sale_notify:
                is_notify_failed = False
                member = bot.get_user(int(each_notify['userid_sell']))
                if member and int(each_notify['userid_sell']) != bot.user.id:
                    msg = "**#{}** Order completed!".format(each_notify['order_id'])
                    try:
                        await member.send(msg)
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        is_notify_failed = True
                    except Exception as e:
                        traceback.print_exc(file=sys.stdout)
                        await logchanbot(traceback.format_exc())
                    update_status = await store.trade_sale_notify_update(each_notify['order_id'], "YES", "YES" if is_notify_failed == True else "NO")
        await asyncio.sleep(30.0)


async def saving_wallet():
    global LOG_CHAN
    saving = False
    botLogChan = bot.get_channel(LOG_CHAN)
    while not bot.is_closed():
        while botLogChan is None:
            botLogChan = bot.get_channel(LOG_CHAN)
            await asyncio.sleep(10)
        COIN_SAVING = ENABLE_COIN + ENABLE_XMR
        for COIN_NAME in COIN_SAVING:
            if is_maintenance_coin(COIN_NAME) or (COIN_NAME in ["BCN"]):
                continue
            if (COIN_NAME in ENABLE_COIN + ENABLE_XMR) and saving == False:
                duration = None
                saving = True
                try:
                    if COIN_NAME in WALLET_API_COIN:
                        duration = await walletapi.save_walletapi(COIN_NAME)
                    else:
                        duration = await rpc_cn_wallet_save(COIN_NAME)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                if duration:
                    if duration > 30:
                        await botLogChan.send(f'INFO: AUTOSAVE FOR **{COIN_NAME}** TOOK **{round(duration, 3)}s**.')
                    elif duration > 5:
                        print(f'INFO: AUTOSAVE FOR **{COIN_NAME}** TOOK **{round(duration, 3)}s**.')
                else:
                    await botLogChan.send(f'WARNING: AUTOSAVE FOR **{COIN_NAME}** FAILED.')
                saving = False
            await asyncio.sleep(config.interval.saving_wallet_sleep)
        await asyncio.sleep(config.interval.wallet_balance_update_interval)


# Multiple tip
async def _tip(ctx, amount, coin: str, if_guild: bool=False):
    global TX_IN_PROCESS
    guild_name = '**{}**'.format(ctx.guild.name) if if_guild == True else ''
    tip_type_text = 'guild tip' if if_guild == True else 'tip'
    guild_or_tip = 'GUILDTIP' if if_guild == True else 'TIPS'
    id_tipper = str(ctx.guild.id) if if_guild == True else str(ctx.author.id)
    serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
    tipmsg = ""
    if if_guild:
        try:
            if serverinfo['tip_message']: tipmsg = "**Guild Message:**\n" + serverinfo['tip_message']
        except Exception as e:
            pass
    botLogChan = bot.get_channel(LOG_CHAN)

    COIN_NAME = coin.upper()
    notifyList = await store.sql_get_tipnotify()
    if COIN_NAME in ENABLE_COIN_ERC:
        coin_family = "ERC-20"
    elif COIN_NAME in ENABLE_COIN_TRC:
        coin_family = "TRC-20"
    else:
        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")

    if coin_family == "ERC-20" or coin_family == "TRC-20":
        real_amount = float(amount)
        token_info = await store.get_token_info(COIN_NAME)
        MinTx = token_info['real_min_tip']
        MaxTX = token_info['real_max_tip']
    else:
        real_amount = int(Decimal(amount) * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
        MinTx = get_min_mv_amount(COIN_NAME)
        MaxTX = get_max_mv_amount(COIN_NAME)

    user_from = await store.sql_get_userwallet(id_tipper, COIN_NAME)
    if user_from is None:
        if coin_family == "ERC-20":
            w = await create_address_eth()
            user_from = await store.sql_register_user(id_tipper, COIN_NAME, SERVER_BOT, 0, w)
        elif coin_family == "TRC-20":
            result = await store.create_address_trx()
            user_from = await store.sql_register_user(id_tipper, COIN_NAME, SERVER_BOT, 0, result)
        else:
            user_from = await store.sql_register_user(id_tipper, COIN_NAME, SERVER_BOT, 0)

    userdata_balance = await store.sql_user_balance(id_tipper, COIN_NAME)
    xfer_in = 0
    if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
        xfer_in = await store.sql_user_balance_get_xfer_in(id_tipper, COIN_NAME)
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
            msg_negative = 'Negative balance detected:\nUser: '+id_tipper+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
            await logchanbot(msg_negative)
    except Exception as e:
        await logchanbot(traceback.format_exc())

    if real_amount > MaxTX:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than '
                                f'{num_format_coin(MaxTX, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return
    elif real_amount < MinTx:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than '
                                f'{num_format_coin(MinTx, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return

    listMembers = []

    guild_members = ctx.guild.members
    if ctx.message.role_mentions and len(ctx.message.role_mentions) >= 1:
        mention_roles = ctx.message.role_mentions
        if "@everyone" in mention_roles:
            mention_roles.remove("@everyone")
        if len(mention_roles) >= 1:
            for each_role in mention_roles:
                role_listMember = [member for member in guild_members if member.bot == False and each_role in member.roles]
                if len(role_listMember) >= 1:
                    for each_member in role_listMember:
                        if each_member not in listMembers:
                            listMembers.append(each_member)
    else:
        listMembers = ctx.message.mentions
    list_receivers = []

    for member in listMembers:
        # print(member.name) # you'll just print out Member objects your way.
        if ctx.author.id != member.id and member in guild_members:
            user_to = await store.sql_get_userwallet(str(member.id), COIN_NAME)
            if user_to is None:
                if coin_family == "ERC-20":
                    w = await create_address_eth()
                    userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0, w)
                elif coin_family == "TRC-20":
                    result = await store.create_address_trx()
                    userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0, result)
                else:
                    userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0)
                user_to = await store.sql_get_userwallet(str(member.id), COIN_NAME)
            if len(list_receivers) == 0 or str(member.id) not in list_receivers:
                list_receivers.append(str(member.id))
            

    TotalAmount = real_amount * len(list_receivers)
    if TotalAmount > MaxTX:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Total transactions cannot be bigger than '
                                f'{num_format_coin(MaxTX, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return
    elif real_amount < MinTx:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Total transactions cannot be smaller than '
                                f'{num_format_coin(MinTx, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return
    elif TotalAmount > actual_balance:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to send total {tip_type_text} of '
                                f'{num_format_coin(TotalAmount, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return

    # add queue also tip
    if int(id_tipper) not in TX_IN_PROCESS:
        TX_IN_PROCESS.append(int(id_tipper))
    else:
        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    tip = None
    if len(list_receivers) < 1:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} There is no one to {tip_type_text} to.')
        if int(id_tipper) in TX_IN_PROCESS:
            TX_IN_PROCESS.remove(int(id_tipper))
        return
    try:
        if coin_family in ["TRTL", "BCN"]:
            tip = await store.sql_mv_cn_multiple(id_tipper, real_amount, list_receivers, guild_or_tip, COIN_NAME)
        elif coin_family == "XMR":
            tip = await store.sql_mv_xmr_multiple(id_tipper, list_receivers, real_amount, COIN_NAME, guild_or_tip)
        elif coin_family == "XCH":
            tip = await store.sql_mv_xch_multiple(id_tipper, list_receivers, real_amount, COIN_NAME, guild_or_tip)
        elif coin_family == "NANO":
            tip = await store.sql_mv_nano_multiple(id_tipper, list_receivers, real_amount, COIN_NAME, guild_or_tip)
        elif coin_family == "DOGE":
            tip = await store.sql_mv_doge_multiple(id_tipper, list_receivers, real_amount, COIN_NAME, guild_or_tip)
        elif coin_family == "ERC-20":
            tip = await store.sql_mv_erc_multiple(id_tipper, list_receivers, real_amount, COIN_NAME, "TIPS", token_info['contract'])
        elif coin_family == "TRC-20":
            tip = await store.sql_mv_trx_multiple(id_tipper, list_receivers, real_amount, COIN_NAME, "TIPS", token_info['contract'])
        if ctx.author.bot == False and serverinfo['react_tip'] == "ON":
            try:
                await ctx.message.add_reaction(EMOJI_TIP)
            except Exception as e:
                pass
    except Exception as e:
        await logchanbot(traceback.format_exc())

    # remove queue from tip
    if int(id_tipper) in TX_IN_PROCESS:
        TX_IN_PROCESS.remove(int(id_tipper))
 
    if tip:
        # Update tipstat
        try:
            update_tipstat = await store.sql_user_get_tipstat(id_tipper, COIN_NAME, True, SERVER_BOT)
        except Exception as e:
            await logchanbot(traceback.format_exc())
        try:
            for member in listMembers:
                if ctx.author.id != member.id and bot.user.id != member.id and len(listMembers) < 15 and str(member.id) not in notifyList:
                    try:
                        await member.send(f'{EMOJI_MONEYFACE} You got a {tip_type_text} of  {num_format_coin(real_amount, COIN_NAME)} '
                                          f'{COIN_NAME} from {ctx.author.name}#{ctx.author.discriminator} in server `{ctx.guild.name} #{ctx.channel.name}`\n'
                                          f'{NOTIFICATION_OFF_CMD}\n{tipmsg}')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        await logchanbot(traceback.format_exc())
                        await store.sql_toggle_tipnotify(str(member.id), "OFF")
        except Exception as e:
            await logchanbot(traceback.format_exc())
        await ctx.message.add_reaction(get_emoji(COIN_NAME))
        # tipper shall always get DM. Ignore notifyList
        try:
            if if_guild == True:
                await ctx.send(f'{EMOJI_ARROW_RIGHTHOOK} Total {tip_type_text} of {num_format_coin(TotalAmount, COIN_NAME)} '
                               f'{COIN_NAME} '
                               f'was sent to ({len(list_receivers)}) members in server `{ctx.guild.name}`.\n'
                               f'Each: `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`'
                               f'Total spending: `{num_format_coin(TotalAmount, COIN_NAME)} {COIN_NAME}`')
            else:
                await ctx.author.send(f'{EMOJI_ARROW_RIGHTHOOK} Total {tip_type_text} of {num_format_coin(TotalAmount, COIN_NAME)} '
                                        f'{COIN_NAME} '
                                        f'was sent to ({len(list_receivers)}) members in server `{ctx.guild.name}`.\n'
                                        f'Each: `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`'
                                        f'Total spending: `{num_format_coin(TotalAmount, COIN_NAME)} {COIN_NAME}`')
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            try:
                if if_guild == True:
                    await ctx.author.send(f'{EMOJI_ARROW_RIGHTHOOK} Total {tip_type_text} of {num_format_coin(TotalAmount, COIN_NAME)} '
                                            f'{COIN_NAME} '
                                            f'was sent to ({len(list_receivers)}) members in server `{ctx.guild.name}`.\n'
                                            f'Each: `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`'
                                            f'Total spending: `{num_format_coin(TotalAmount, COIN_NAME)} {COIN_NAME}`')
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                pass
        return
    else:
        await ctx.message.add_reaction(EMOJI_ERROR)
        msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Tipping failed, try again.')
        await botLogChan.send(f'A user failed to _tip `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
        await msg.add_reaction(EMOJI_OK_BOX)
        # add to failed tx table
        await store.sql_add_failed_tx(COIN_NAME, str(ctx.author.id), ctx.author.name, real_amount, guild_or_tip)
        return


# Multiple tip
async def _tip_talker(ctx, amount, list_talker, if_guild: bool=False, coin: str = None):
    global TX_IN_PROCESS
    guild_or_tip = 'GUILDTIP' if if_guild == True else 'TIPS'
    guild_name = '**{}**'.format(ctx.guild.name) if if_guild == True else ''
    tip_type_text = 'guild tip' if if_guild == True else 'tip'
    id_tipper = str(ctx.guild.id) if if_guild == True else str(ctx.author.id)

    botLogChan = bot.get_channel(LOG_CHAN)
    serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
    tipmsg = ""
    if if_guild:
        try:
            if serverinfo['tip_message']: tipmsg = "**Guild Message:**\n" + serverinfo['tip_message']
        except Exception as e:
            pass
    COIN_NAME = coin.upper()
    if COIN_NAME in ENABLE_COIN_ERC:
        coin_family = "ERC-20"
    elif COIN_NAME in ENABLE_COIN_TRC:
        coin_family = "TRC-20"
    else:
        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
    try:
        amount = Decimal(amount)
    except ValueError:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
        return

    notifyList = await store.sql_get_tipnotify()
    if coin_family not in ["BCN", "TRTL", "DOGE", "XMR", "NANO", "ERC-20", "TRC-20", "XCH"]:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} is restricted with this command.')
        return

    if coin_family == "ERC-20" or coin_family == "TRC-20":
        real_amount = float(amount)
        token_info = await store.get_token_info(COIN_NAME)
        MinTx = token_info['real_min_tip']
        MaxTX = token_info['real_max_tip']
    else:
        real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["XMR", "TRTL", "BCN", "NANO", "XCH"] else float(amount)
        MinTx = get_min_mv_amount(COIN_NAME)
        MaxTX = get_max_mv_amount(COIN_NAME)

    user_from = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
    if user_from is None:
        if coin_family == "ERC-20":
            w = await create_address_eth()
            user_from = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
        elif coin_family == "TRC-20":
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
        if actual_balance <= 0:
            msg_negative = 'Negative or zero balance detected:\nUser: '+str(ctx.author.id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
            await logchanbot(msg_negative)
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to send {tip_type_text} of '
                                    f'{num_format_coin(real_amount, COIN_NAME)} '
                                    f'{COIN_NAME}.')
            return
    except Exception as e:
        await logchanbot(traceback.format_exc())

    if real_amount > MaxTX:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than '
                                f'{num_format_coin(MaxTX, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return
    elif real_amount < MinTx:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than '
                                f'{num_format_coin(MinTx, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return
    elif real_amount > actual_balance:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to send {tip_type_text} of '
                                f'{num_format_coin(real_amount, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return

    list_receivers = []
    addresses = []
    guild_members = ctx.guild.members
    for member_id in list_talker:
        try:
            member = bot.get_user(int(member_id))
            if member and member in guild_members and ctx.author.id != member.id:
                user_to = await store.sql_get_userwallet(str(member_id), COIN_NAME)
                if user_to is None:
                    if coin_family == "ERC-20":
                        w = await create_address_eth()
                        userregister = await store.sql_register_user(str(member_id), COIN_NAME, SERVER_BOT, 0, w)
                    elif coin_family == "TRC-20":
                        result = await store.create_address_trx()
                        userregister = await store.sql_register_user(str(member_id), COIN_NAME, SERVER_BOT, 0, result)
                    else:
                        userregister = await store.sql_register_user(str(member_id), COIN_NAME, SERVER_BOT, 0)
                    user_to = await store.sql_get_userwallet(str(member_id), COIN_NAME)
                try:
                    list_receivers.append(str(member_id))
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                    print('Failed creating wallet for tip talk for userid: {}'.format(member_id))
        except Exception as e:
            await logchanbot(traceback.format_exc())

    # Check number of receivers.
    if len(list_receivers) > config.tipallMax:
        await ctx.message.add_reaction(EMOJI_ERROR)
        try:
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} The number of receivers are too many.')
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            await ctx.author.send(f'{EMOJI_RED_NO} The number of receivers are too many in `{ctx.guild.name}`.')
        return
    # End of checking receivers numbers.

    TotalAmount = real_amount * len(list_receivers)

    if TotalAmount > MaxTX:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Total transactions cannot be bigger than '
                                f'{num_format_coin(MaxTX, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return
    elif real_amount < MinTx:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Total transactions cannot be smaller than '
                                f'{num_format_coin(MinTx, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return
    elif TotalAmount > actual_balance:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {guild_name} Insufficient balance to send total {tip_type_text} of '
                                f'{num_format_coin(TotalAmount, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return

    if len(list_receivers) < 1:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} There is no active talker in such period. Please increase more duration or tip directly!')
        return

    # add queue also tip
    if int(id_tipper) not in TX_IN_PROCESS:
        TX_IN_PROCESS.append(int(id_tipper))
    else:
        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    tip = None
    try:
        if coin_family in ["TRTL", "BCN"]:
            tip = await store.sql_mv_cn_multiple(id_tipper, real_amount, list_receivers, guild_or_tip, COIN_NAME)
        elif coin_family == "XMR":
            tip = await store.sql_mv_xmr_multiple(id_tipper, list_receivers, real_amount, COIN_NAME, guild_or_tip)
        elif coin_family == "XCH":
            tip = await store.sql_mv_xch_multiple(id_tipper, list_receivers, real_amount, COIN_NAME, guild_or_tip)
        elif coin_family == "NANO":
            tip = await store.sql_mv_nano_multiple(id_tipper, list_receivers, real_amount, COIN_NAME, guild_or_tip)
        elif coin_family == "DOGE":
            tip = await store.sql_mv_doge_multiple(id_tipper, list_receivers, real_amount, COIN_NAME, guild_or_tip)
        elif coin_family == "ERC-20":
            tip = await store.sql_mv_erc_multiple(id_tipper, list_receivers, real_amount, COIN_NAME, "TIPS", token_info['contract'])
        elif coin_family == "TRC-20":
            tip = await store.sql_mv_trx_multiple(id_tipper, list_receivers, real_amount, COIN_NAME, "TIPS", token_info['contract'])
    except Exception as e:
        await logchanbot(traceback.format_exc())

    # remove queue from tip
    if int(id_tipper) in TX_IN_PROCESS:
        TX_IN_PROCESS.remove(int(id_tipper))

    if tip:
        # Update tipstat
        try:
            update_tipstat = await store.sql_user_get_tipstat(id_tipper, COIN_NAME, True, SERVER_BOT)
        except Exception as e:
            await logchanbot(traceback.format_exc())

        mention_list_name = ''
        guild_members = ctx.guild.members
        tip_public = False
        max_mention = 40
        numb_mention = 0
        total_found = 0
        if len(list_talker) < max_mention:
            for member_id in list_talker:
                # print(member.name) # you'll just print out Member objects your way.
                if ctx.author.id != int(member_id):
                    member = bot.get_user(int(member_id))
                    if member and member.bot == False and member in guild_members:
                        mention_list_name += '{}#{} '.format(member.name, member.discriminator)
                        total_found += 1
                        if str(member_id) not in notifyList:
                            try:
                                await member.send(
                                    f'{EMOJI_MONEYFACE} You got a {tip_type_text} of `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}` '
                                    f'from {ctx.author.name}#{ctx.author.discriminator} in server `{ctx.guild.name}` #{ctx.channel.name} for active talking.\n'
                                    f'{NOTIFICATION_OFF_CMD}\n{tipmsg}')
                            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                await store.sql_toggle_tipnotify(str(member.id), "OFF")
        else:
            send_tipped_ping = 0
            list_user_mention = []
            list_user_mention_str = ""
            list_user_not_mention = []
            list_user_not_mention_str = ""
            # shuffle list_talker
            random.shuffle(list_talker)
            for member_id in list_talker:
                member = bot.get_user(int(member_id))
                if ctx.author.id != int(member_id) and member and member.bot == False and member in guild_members:
                    if send_tipped_ping < config.maxTipMessage:
                        if str(member_id) not in notifyList:
                            list_user_mention.append("{}".format(member.mention))
                        else:
                            list_user_not_mention.append("{}".format(member.name))
                        numb_mention += 1
                        total_found += 1
                        # Check if a batch meets
                        if numb_mention > 0 and numb_mention % max_mention == 0:
                                # send the batch
                            if len(list_user_mention) >= 1:
                                list_user_mention_str = ", ".join(list_user_mention)
                            if len(list_user_not_mention) >= 1:
                                list_user_not_mention_str = ", ".join(list_user_not_mention)
                            try:
                                if len(list_user_mention_str) > 5 or len(list_user_not_mention_str) > 5:
                                    await ctx.send(
                                        f'{EMOJI_MONEYFACE} {list_user_mention_str} {list_user_not_mention_str}, You got a {tip_type_text} of {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME} '
                                        f'from {ctx.author.name}#{ctx.author.discriminator} for active talking.\n'
                                        f'{NOTIFICATION_OFF_CMD}\n{tipmsg}')
                                    send_tipped_ping += 1
                                tip_public = True
                            except Exception as e:
                                pass
                            # reset
                            list_user_mention = []
                            list_user_mention_str = ""
                            list_user_not_mention = []
                            list_user_not_mention_str = ""
                    else:
                        total_found += 1
            # If there is still in record.
            if len(list_user_mention) + len(list_user_not_mention) > 1:
                if len(list_user_mention) >= 1:
                    list_user_mention_str = ", ".join(list_user_mention)
                if len(list_user_not_mention) >= 1:
                    list_user_not_mention_str = ", ".join(list_user_not_mention)
                try:
                    remaining_str = ""
                    if numb_mention < total_found:
                        remaining_str = " and other {} members".format(total_found-numb_mention)
                    await ctx.message.reply(
                        f'{EMOJI_MONEYFACE} {list_user_mention_str} {list_user_not_mention_str} {remaining_str}, You got a {tip_type_text} of `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}` '
                        f'from {ctx.author.name}#{ctx.author.discriminator} for active talking.\n'
                        f'{NOTIFICATION_OFF_CMD}\n{tipmsg}')
                    tip_public = True
                except Exception as e:
                    pass

        # tipper shall always get DM. Ignore notifyList
        try:
            await ctx.author.send(
                f'{EMOJI_ARROW_RIGHTHOOK} {tip_type_text} of {num_format_coin(TotalAmount, COIN_NAME)} '
                f'{COIN_NAME} '
                f'was sent to ({total_found}) members in server `{ctx.guild.name}` for active talking.\n'
                f'Each member got: `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`\n')
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            await store.sql_toggle_tipnotify(str(ctx.author.id), "OFF")

        await ctx.message.add_reaction(get_emoji(COIN_NAME))
        if tip_public == False:
            try:
                await ctx.message.reply(f'{discord.utils.escape_markdown(mention_list_name)}\n\n**({total_found})** members got {tip_type_text} :) for active talking in `{ctx.guild.name}` {ctx.channel.mention} :)')
                await ctx.message.add_reaction(EMOJI_SPEAK)
            except discord.errors.Forbidden:
                serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                if serverinfo and 'botchan' in serverinfo and serverinfo['botchan']:
                    bot_channel = bot.get_channel(int(serverinfo['botchan']))
                    try:
                        msg = await bot_channel.send(f'{discord.utils.escape_markdown(mention_list_name)}\n\n**({total_found})** members got {tip_type_text} :) for active talking in `{ctx.guild.name}` {ctx.channel.mention} :)')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        await ctx.message.add_reaction(EMOJI_SPEAK)
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                        await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                    except discord.errors.HTTPException:
                        msg = await bot_channel.send(f'**({total_found})** members got {tip_type_text} :) for active talking in `{ctx.guild.name}` {ctx.channel.mention} :)')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        await ctx.message.add_reaction(EMOJI_SPEAK)
                else:
                    await ctx.message.add_reaction(EMOJI_SPEAK)
                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
            except discord.errors.HTTPException:
                await ctx.message.add_reaction(EMOJI_SPEAK)
                await ctx.send(f'**({total_found})** members got {tip_type_text} :) for active talking in `{ctx.guild.name}` {ctx.channel.mention} :)')
            return
    else:
        await ctx.message.add_reaction(EMOJI_ERROR)
        return


# Multiple tip_react
async def _tip_react(reaction, user, amount, coin: str):
    global REACT_TIP_STORE
    botLogChan = bot.get_channel(LOG_CHAN)
    serverinfo = await store.sql_info_by_server(str(reaction.message.guild.id))
    COIN_NAME = coin.upper()

    # If only one user and he re-act
    if len(reaction.message.mentions) == 1 and user in (reaction.message.mentions):
        return
        
    notifyList = await store.sql_get_tipnotify()
    if COIN_NAME in ENABLE_COIN_ERC:
        coin_family = "ERC-20"
    elif COIN_NAME in ENABLE_COIN_TRC:
        coin_family = "TRC-20"
    else:
        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")

    if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
        token_info = await store.get_token_info(COIN_NAME)
        real_amount = float(amount)
        MinTx = token_info['real_min_tip']
        MaxTX = token_info['real_max_tip']
    else:
        real_amount = int(Decimal(amount) * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
        MinTx = get_min_mv_amount(COIN_NAME)
        MaxTX = get_max_mv_amount(COIN_NAME)

    user_from = await store.sql_get_userwallet(str(user.id), COIN_NAME)
    if user_from is None:
        if COIN_NAME in ENABLE_COIN_ERC:
            w = await create_address_eth()
            user_from = await store.sql_register_user(str(user.id), COIN_NAME, SERVER_BOT, 0, w)
        elif COIN_NAME in ENABLE_COIN_TRC:
            result = await store.create_address_trx()
            user_from = await store.sql_register_user(str(user.id), COIN_NAME, SERVER_BOT, 0, result)
        else:
            user_from = await store.sql_register_user(str(user.id), COIN_NAME, SERVER_BOT, 0)

    # get user balance
    userdata_balance = await store.sql_user_balance(str(user.id), COIN_NAME)
    xfer_in = 0
    if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
        xfer_in = await store.sql_user_balance_get_xfer_in(str(user.id), COIN_NAME)
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
            msg_negative = 'Negative balance detected:\nUser: '+str(user.id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
            await logchanbot(msg_negative)
    except Exception as e:
        await logchanbot(traceback.format_exc())

    listMembers = reaction.message.mentions
    list_receivers = []
    addresses = []

    for member in listMembers:
        # print(member.name) # you'll just print out Member objects your way.
        if user.id != member.id and reaction.message.author.id != member.id:
            user_to = await store.sql_get_userwallet(str(member.id), COIN_NAME)
            if user_to is None:
                if COIN_NAME in ENABLE_COIN_ERC:
                    coin_family = "ERC-20"
                    w = await create_address_eth()
                    userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0, w)
                elif COIN_NAME in ENABLE_COIN_TRC:
                    coin_family = "TRC-20"
                    result = await store.create_address_trx()
                    userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0, result)
                else:
                    coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                    userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0)
                user_to = await store.sql_get_userwallet(str(member.id), COIN_NAME)

            list_receivers.append(str(member.id))

    TotalAmount = real_amount * len(list_receivers)
    if TotalAmount >= actual_balance:
        try:
            await user.send(f'{EMOJI_RED_NO} {user.mention} Insufficient balance {EMOJI_TIP} total of '
                            f'{num_format_coin(TotalAmount, COIN_NAME)} '
                            f'{COIN_NAME}.')
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            print(f"_tip_react Can not send DM to {user.id}")
        return

    tip = None
    if len(list_receivers) < 1:
        await reaction.message.add_reaction(EMOJI_ERROR)
        return
    try:
        if coin_family in ["TRTL", "BCN"]:
            tip = await store.sql_mv_cn_multiple(str(user.id), real_amount, list_receivers, 'TIPS', COIN_NAME)
        elif coin_family == "XMR":
            tip = await store.sql_mv_xmr_multiple(str(user.id), list_receivers, real_amount, COIN_NAME, "TIPS")
        elif coin_family == "XCH":
            tip = await store.sql_mv_xch_multiple(str(user.id), list_receivers, real_amount, COIN_NAME, "TIPS")
        elif coin_family == "NANO":
            tip = await store.sql_mv_nano_multiple(str(user.id), list_receivers, real_amount, COIN_NAME, "TIPS")
        elif coin_family == "DOGE":
            tip = await store.sql_mv_doge_multiple(user.id, list_receivers, real_amount, COIN_NAME, "TIPS")
        REACT_TIP_STORE.append((str(reaction.message.id) + '.' + str(user.id)))
    except Exception as e:
        await logchanbot(traceback.format_exc())
    if tip:
        # tipper shall always get DM. Ignore notifyList
        try:
            await user.send(f'{EMOJI_ARROW_RIGHTHOOK} Total {EMOJI_TIP} of {num_format_coin(TotalAmount, COIN_NAME)} '
                            f'{COIN_NAME} '
                            f'was sent to ({len(list_receivers)}) members in server `{reaction.message.guild.name}`.\n'
                            f'Each: `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`'
                            f'Total spending: `{num_format_coin(TotalAmount, COIN_NAME)} {COIN_NAME}`')
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            await store.sql_toggle_tipnotify(str(user.id), "OFF")
        for member in reaction.message.mentions:
            if user.id != member.id and reaction.message.author.id != member.id and member.bot == False:
                if str(member.id) not in notifyList:
                    try:
                        await member.send(f'{EMOJI_MONEYFACE} You got a {EMOJI_TIP} of  {num_format_coin(real_amount, COIN_NAME)} '
                                          f'{COIN_NAME} from {user.name}#{user.discriminator} in server `{reaction.message.guild.name}`\n'
                                          f'{NOTIFICATION_OFF_CMD}')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        await store.sql_toggle_tipnotify(str(member.id), "OFF")
        return
    else:
        msg = await user.send(f'{EMOJI_RED_NO} {user.mention} Try again for {EMOJI_TIP}.')
        await botLogChan.send(f'A user failed to _tip_react `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
        await msg.add_reaction(EMOJI_OK_BOX)
        # add to failed tx table
        await store.sql_add_failed_tx(COIN_NAME, str(user.id), user.name, real_amount, "REACTTIP")
        return


def truncate(number, digits) -> float:
    stepper = pow(10.0, digits)
    return math.trunc(stepper * number) / stepper


def seconds_str_days(time: float):
    day = time // (24 * 3600)
    time = time % (24 * 3600)
    hour = time // 3600
    time %= 3600
    minutes = time // 60
    time %= 60
    seconds = time
    return "{:02d} day(s) {:02d}:{:02d}:{:02d}".format(day, hour, minutes, seconds)


def seconds_str(time: float):
    # day = time // (24 * 3600)
    # time = time % (24 * 3600)
    hour = time // 3600
    time %= 3600
    minutes = time // 60
    time %= 60
    seconds = time
    return "{:02d}:{:02d}:{:02d}".format(hour, minutes, seconds)


def is_maintenance_coin(coin: str):
    global redis_conn, redis_expired, MAINTENANCE_COIN
    COIN_NAME = coin.upper()
    if COIN_NAME in MAINTENANCE_COIN:
        return True
    # Check if exist in redis
    try:
        openRedis()
        key = config.redis_setting.prefix_coin_setting + COIN_NAME + '_MAINT'
        if redis_conn and redis_conn.exists(key):
            return True
        else:
            return False
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def set_maintenance_coin(coin: str, set_maint: bool = True):
    global redis_conn, redis_expired, MAINTENANCE_COIN
    COIN_NAME = coin.upper()
    if COIN_NAME in MAINTENANCE_COIN:
        return True

    # Check if exist in redis
    try:
        openRedis()
        key = config.redis_setting.prefix_coin_setting + COIN_NAME + '_MAINT'
        if set_maint == True:
            if redis_conn and redis_conn.exists(key):
                return True
            else:
                redis_conn.set(key, "ON")
                return True
        else:
            if redis_conn and redis_conn.exists(key):
                redis_conn.delete(key)
            return True
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def is_coin_txable(coin: str):
    global redis_conn, redis_expired, MAINTENANCE_COIN
    COIN_NAME = coin.upper()
    if is_maintenance_coin(COIN_NAME):
        return False
    # Check if exist in redis
    try:
        openRedis()
        key = config.redis_setting.prefix_coin_setting + COIN_NAME + '_TX'
        if redis_conn and redis_conn.exists(key):
            return False
        else:
            return True
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def set_coin_txable(coin: str, set_txable: bool = True):
    global redis_conn, redis_expired, MAINTENANCE_COIN
    COIN_NAME = coin.upper()
    if COIN_NAME in MAINTENANCE_COIN:
        return False

    # Check if exist in redis
    try:
        openRedis()
        key = config.redis_setting.prefix_coin_setting + COIN_NAME + '_TX'
        if set_txable == True:
            if redis_conn and redis_conn.exists(key):
                redis_conn.delete(key)
                return True
        else:
            if redis_conn and not redis_conn.exists(key):
                redis_conn.set(key, "ON")                
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def is_coin_depositable(coin: str):
    global redis_conn, redis_expired
    COIN_NAME = coin.upper()
    if is_maintenance_coin(COIN_NAME):
        return False
    # Check if exist in redis
    try:
        openRedis()
        key = config.redis_setting.prefix_coin_setting + COIN_NAME + '_DEPOSIT'
        if redis_conn and redis_conn.exists(key):
            return False
        else:
            return True
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def set_coin_depositable(coin: str, set_deposit: bool = True):
    global redis_conn, redis_expired
    COIN_NAME = coin.upper()
    if is_maintenance_coin(COIN_NAME):
        return False

    # Check if exist in redis
    try:
        openRedis()
        key = config.redis_setting.prefix_coin_setting + COIN_NAME + '_DEPOSIT'
        if set_deposit == True:
            if redis_conn and redis_conn.exists(key):
                redis_conn.delete(key)
                return True
        else:
            if redis_conn and not redis_conn.exists(key):
                redis_conn.set(key, "ON")                
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def is_coin_tipable(coin: str):
    global redis_conn, redis_expired
    COIN_NAME = coin.upper()
    if is_maintenance_coin(COIN_NAME):
        return False
    # Check if exist in redis
    try:
        openRedis()
        key = config.redis_setting.prefix_coin_setting + COIN_NAME + '_TIP'
        if redis_conn and redis_conn.exists(key):
            return False
        else:
            return True
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def set_coin_tipable(coin: str, set_tipable: bool = True):
    global redis_conn, redis_expired
    COIN_NAME = coin.upper()
    if is_maintenance_coin(COIN_NAME):
        return False

    # Check if exist in redis
    try:
        openRedis()
        key = config.redis_setting.prefix_coin_setting + COIN_NAME + '_TIP'
        if set_tipable == True:
            if redis_conn and redis_conn.exists(key):
                redis_conn.delete(key)
                return True
        else:
            if redis_conn and not redis_conn.exists(key):
                redis_conn.set(key, "ON")                
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def is_tradeable_coin(coin: str):
    global redis_conn, redis_expired
    COIN_NAME = coin.upper()

    # Check if exist in redis
    try:
        openRedis()
        key = config.redis_setting.prefix_coin_setting + COIN_NAME + '_TRADEABLE'
        if redis_conn and redis_conn.exists(key):
            return True
        else:
            return False
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def set_tradeable_coin(coin: str, set_trade: bool = True):
    global redis_conn, redis_expired 
    COIN_NAME = coin.upper()

    # Check if exist in redis
    try:
        openRedis()
        key = config.redis_setting.prefix_coin_setting + COIN_NAME + '_TRADEABLE'
        if set_trade == True:
            if redis_conn and redis_conn.exists(key):
                return True
            else:
                redis_conn.set(key, "ON")
                return True
        else:
            if redis_conn and redis_conn.exists(key):
                redis_conn.delete(key)
            return True
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


async def store_action_list():
    while True:
        interval_action_list = 60
        try:
            openRedis()
            key = config.redis_setting.prefix_action_tx
            if redis_conn and redis_conn.llen(key) > 0:
                temp_action_list = []
                for each in redis_conn.lrange(key, 0, -1):
                    temp_action_list.append(tuple(json.loads(each)))
                num_add = await store.sql_add_logs_tx(temp_action_list)
                if num_add > 0:
                    redis_conn.delete(key)
                else:
                    print(f"Failed delete {key}")
        except Exception as e:
            await logchanbot(traceback.format_exc())
        await asyncio.sleep(interval_action_list)


async def add_tx_action_redis(action: str, delete_temp: bool = False):
    try:
        openRedis()
        key = config.redis_setting.prefix_action_tx
        if redis_conn:
            if delete_temp:
                redis_conn.delete(key)
            else:
                redis_conn.lpush(key, action)
    except Exception as e:
        await logchanbot(traceback.format_exc())


async def get_guild_prefix(ctx):
    if isinstance(ctx.channel, discord.DMChannel) == True: return "."
    serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
    if serverinfo is None:
        return "."
    else:
        return serverinfo['prefix']


async def get_guild_prefix_msg(message):
    if isinstance(message.channel, discord.DMChannel) == True: return "."
    serverinfo = await store.sql_info_by_server(str(message.guild.id))
    if serverinfo is None:
        return "."
    else:
        return serverinfo['prefix']


async def add_msg_redis(msg: str, delete_temp: bool = False):
    try:
        openRedis()
        key = config.redis_setting.prefix_discord_msg
        if redis_conn:
            if delete_temp:
                redis_conn.delete(key)
            else:
                redis_conn.lpush(key, msg)
    except Exception as e:
        await logchanbot(traceback.format_exc())


async def store_message_list():
    while True:
        interval_msg_list = 30 # in second
        try:
            openRedis()
            key = config.redis_setting.prefix_discord_msg
            if redis_conn and redis_conn.llen(key) > 0 :
                temp_msg_list = []
                for each in redis_conn.lrange(key, 0, -1):
                    temp_msg_list.append(tuple(json.loads(each)))
                try:
                    num_add = await store.sql_add_messages(temp_msg_list)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                if num_add and num_add > 0:
                    redis_conn.delete(key)
                else:
                    redis_conn.delete(key)
                    print(f"Failed delete {key}")
        except Exception as e:
            await logchanbot(traceback.format_exc())
        await asyncio.sleep(interval_msg_list)


async def get_miningpool_coinlist():
    global redis_conn, redis_expired
    while True:
        interval_msg_list = 1800 # in second
        try:
            openRedis()
            try:
                async with aiohttp.ClientSession() as cs:
                    async with cs.get(config.miningpoolstat.coinlist_link, timeout=config.miningpoolstat.timeout) as r:
                        if r.status == 200:
                            res_data = await r.read()
                            res_data = res_data.decode('utf-8')
                            res_data = res_data.replace("var coin_list = ", "").replace(";", "")
                            decoded_data = json.loads(res_data)
                            await cs.close()
                            key = "TIPBOT:MININGPOOL:"
                            key_hint = "TIPBOT:MININGPOOL:SHORTNAME:"
                            if decoded_data and len(decoded_data) > 0:
                                # print(decoded_data)
                                for kc, cat in decoded_data.items():
                                    if not isinstance(cat, int) and not isinstance(cat, str):
                                        for k, v in cat.items():
                                            # Should have no expire.
                                            redis_conn.set((key+k).upper(), json.dumps(v))
                                            redis_conn.set((key_hint+v['s']).upper(), k.upper())
            except asyncio.TimeoutError:
                print('TIMEOUT: Fetching from miningpoolstats')
            except Exception:
                await logchanbot(traceback.format_exc())
        except Exception as e:
            await logchanbot(traceback.format_exc())
        await asyncio.sleep(interval_msg_list)



# function to return if input string is ascii
def is_ascii(s):
    return all(ord(c) < 128 for c in s)


# json.dumps for turple
def remap_keys(mapping):
    return [{'key':k, 'value': v} for k, v in mapping.items()]


# -*- coding: utf-8 -*-
def isEnglish(s):
    try:
        s.encode(encoding='utf-8').decode('ascii')
    except UnicodeDecodeError:
        return False
    else:
        return True

def isKhmer(s):
    def strip_ascii(string):
        ''' Returns the string without ASCII characters'''
        stripped = (c for c in string if ord(c) >= 127)
        return ''.join(stripped)
    s = strip_ascii(s)
    s = s.replace(" ", "")
    s = s.replace("?", "")
    s = s.replace("!", "")
    s = s.replace(".", "")
    s = s.replace("​", "")
    s = s.replace(":", "")
    try:
        return all(u'\u1780' <= c <= u'\u17F9' for c in s.encode().decode('utf-8'))
    except Exception as e:
        return False
    else:
        return False


def isChinese(s):
    def strip_ascii(string):
        ''' Returns the string without ASCII characters'''
        stripped = (c for c in string if ord(c) >= 127)
        return ''.join(stripped)
    s = strip_ascii(s)
    s = s.replace(" ", "")
    s = s.replace("?", "")
    s = s.replace("!", "")
    s = s.replace(".", "")
    s = s.replace(":", "")
    try:
        return all(u'\u4e00' <= c <= u'\u9fff' for c in s.encode().decode('utf-8'))
    except Exception as e:
        return False
    else:
        return False


## https://github.com/MrJacob12/StringProgressBar
def createBox(value, maxValue, size, show_percentage: bool=False):
    percentage = value / maxValue
    progress = round((size * percentage))
    emptyProgress = size - progress
        
    progressText = '█'
    emptyProgressText = '—'
    percentageText = str(round(percentage * 100)) + '%'

    if show_percentage:
        bar = '[' + progressText*progress + emptyProgressText*emptyProgress + ']' + percentageText
    else:
        bar = '[' + progressText*progress + emptyProgressText*emptyProgress + ']'
    return bar


def get_roach_level(takes: int):
    if takes > 2000:
        return "Great Ultimate Master"
    elif takes > 1500:
        return "Great Supreme Master"
    elif takes > 1000:
        return "Great Grand Master"
    elif takes > 750:
        return "Great Master"
    elif takes > 500:
        return "Ultimate Master"
    elif takes > 250:
        return "Grand Master"
    elif takes > 100:
        return "Master"
    elif takes > 50:
        return "Specialist"
    elif takes > 25:
        return "Licensed"
    elif takes > 10:
        return "Learning"
    elif takes > 0:
        return "Baby"
    else:
        return None


def get_min_sell(coin: str, token_info = None):
    COIN_NAME = coin.upper()
    if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
        return token_info['min_buysell']
    else:
        return getattr(config,"daemon"+coin,config.daemonWRKZ).min_buysell

def get_max_sell(coin: str, token_info = None):
    COIN_NAME = coin.upper()
    if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
        return token_info['max_buysell']
    else:
        return getattr(config,"daemon"+coin,config.daemonWRKZ).max_buysell


async def get_balance_coin_user(user_id, coin: str):
    COIN_NAME = coin.upper()
    wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
    real_deposit_balance = 0
    token_info = None
    if wallet is None:
        if COIN_NAME in ENABLE_COIN_ERC:
            w = await create_address_eth()
            userregister = await store.sql_register_user(str(user_id), COIN_NAME, SERVER_BOT, 0, w)
        elif COIN_NAME in ENABLE_COIN_TRC:
            result = await store.create_address_trx()
            userregister = await store.sql_register_user(str(user_id), COIN_NAME, SERVER_BOT, 0, result)
        else:
            userregister = await store.sql_register_user(str(user_id), COIN_NAME, SERVER_BOT, 0)
        wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
    if COIN_NAME in ENABLE_COIN_ERC:
        token_info = await store.get_token_info(COIN_NAME)
        deposit_balance = await store.http_wallet_getbalance(wallet['balance_wallet_address'], COIN_NAME, True)
        real_deposit_balance = round(deposit_balance / 10**token_info['token_decimal'], 6)
    elif COIN_NAME in ENABLE_COIN_TRC:
        token_info = await store.get_token_info(COIN_NAME)
        deposit_balance = await store.trx_wallet_getbalance(wallet['balance_wallet_address'], COIN_NAME)
        real_deposit_balance = round(deposit_balance, 6)
    userdata_balance = await store.sql_user_balance(str(user_id), COIN_NAME, SERVER_BOT)
    xfer_in = 0
    if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
        xfer_in = await store.sql_user_balance_get_xfer_in(str(user_id), COIN_NAME)
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
            msg_negative = 'Negative balance detected:\nUser: '+str(user_id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
            await logchanbot(msg_negative)
    except Exception as e:
        await logchanbot(traceback.format_exc())
    
    min_deposit_txt = ""
    deposit_note = ""
    if token_info:
        min_deposit_txt = " Min. deposit for moving to spendable: " + num_format_coin(token_info['min_move_deposit'], COIN_NAME) + " "+ COIN_NAME
        deposit_note = token_info['deposit_note']
        
    return {
        'balance_wallet_address': wallet['balance_wallet_address'],
        'user_wallet_address': wallet['user_wallet_address'] if wallet['user_wallet_address'] else None,
        'real_deposit_balance': real_deposit_balance,
        'balance_actual': num_format_coin(actual_balance, COIN_NAME),
        'locked_openorder': userdata_balance['OpenOrder'],
        'raffle_spent': userdata_balance['raffle_fee'],
        'raffle_reward': userdata_balance['raffle_reward'],
        'economy_balance': userdata_balance['economy_balance'],
        'min_deposit_txt': min_deposit_txt,
        'deposit_note': deposit_note
        }



async def get_balance_list_user(user_id):
    user_coins = {}
    for COIN_NAME in [coinItem.upper() for coinItem in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH]:
        actual_balance = 0
        if not is_maintenance_coin(COIN_NAME):
            wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
            if wallet is None:
                if COIN_NAME in ENABLE_COIN_ERC:
                    w = await create_address_eth()
                    userregister = await store.sql_register_user(str(user_id), COIN_NAME, SERVER_BOT, 0, w)
                elif COIN_NAME in ENABLE_COIN_TRC:
                    result = await store.create_address_trx()
                    userregister = await store.sql_register_user(str(user_id), COIN_NAME, SERVER_BOT, 0, result)
                else:
                    userregister = await store.sql_register_user(str(user_id), COIN_NAME, SERVER_BOT, 0)
                wallet = await store.sql_get_userwallet(str(user_id), COIN_NAME)
            if wallet is None:
                await botLogChan.send(f'A user call `{prefix}balance` failed with {COIN_NAME}')
            else:
                userdata_balance = await store.sql_user_balance(str(user_id), COIN_NAME)
                xfer_in = 0
                if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    xfer_in = await store.sql_user_balance_get_xfer_in(str(user_id), COIN_NAME)
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
                        msg_negative = 'Negative balance detected:\nUser: '+str(user_id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
                        await logchanbot(msg_negative)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
            if actual_balance > 0:
                balance_actual = num_format_coin(actual_balance, COIN_NAME)
                user_coins[COIN_NAME] = {'actual_balance': actual_balance, 'balance_actual': balance_actual}
    return user_coins


@bot.command(usage="load <cog>")
@commands.is_owner()
async def load(ctx, extension):
    try:
        """Load specified cog"""
        extension = extension.lower()
        bot.load_extension(f'cogs.{extension}')
        await ctx.send('{} has been loaded.'.format(extension.capitalize()))
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


@bot.command(usage="unload <cog name>")
@commands.is_owner()
async def unload(ctx, extension):
    try:
        """Unload specified cog"""
        extension = extension.lower()
        bot.unload_extension(f'cogs.{extension}')
        await ctx.send('{} has been unloaded.'.format(extension.capitalize()))
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


@bot.command(usage="reload <cog name>")
@commands.is_owner()
async def reload(ctx, extension):
    """Reload specified cog"""
    try:
        extension = extension.lower()
        bot.reload_extension(f'cogs.{extension}')
        await ctx.send('{} has been reloaded.'.format(extension.capitalize()))
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


@click.command()
def main():
    #bot.loop.create_task(saving_wallet())
    #bot.loop.create_task(update_user_guild())
    #bot.loop.create_task(update_balance())
    #bot.loop.create_task(update_block_height())
    #bot.loop.create_task(notify_new_tx_user())
    #bot.loop.create_task(notify_new_tx_user_noconfirmation())
    #bot.loop.create_task(store_action_list())
    #bot.loop.create_task(store_message_list())
    #bot.loop.create_task(get_miningpool_coinlist())

    #bot.loop.create_task(unlocked_move_pending_erc_trx())
    #bot.loop.create_task(erc_trx_notify_new_confirmed_spendable())

    #bot.loop.create_task(notify_new_move_balance_user())
    #bot.loop.create_task(check_raffle_status())

    #bot.loop.create_task(trade_complete_sale_notify())

    for filename in os.listdir('./cogs/'):
        if filename.endswith('.py'):
            bot.load_extension(f'cogs.{filename[:-3]}')

    bot.run(config.discord.token, reconnect=True)


if __name__ == '__main__':
    main()
