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
import qrcode
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
bot_help_about = "About TipBot"
bot_help_register = "Register or change your deposit address."
bot_help_info = "Get discord server's info for TipBot."
bot_help_deposit = "Get your wallet's deposit address."
bot_help_userinfo = "Get user info in discord server."
bot_help_withdraw = f"Withdraw {COIN_REPR} from your balance."
bot_help_balance = f"Check your {COIN_REPR} balance."
bot_help_botbalance = f"Check (only) bot {COIN_REPR} balance."
bot_help_donate = f"Donate {COIN_REPR} to a Bot Owner."
bot_help_tip = f"Give {COIN_REPR} to a user from your balance."
bot_help_freetip = f"Give {COIN_REPR} to a re-acted user from your balance."
bot_help_randomtip = "Tip to random user in the guild"

bot_help_forwardtip = f"Forward all your received tip of {COIN_REPR} to registered wallet."
bot_help_tipall = f"Spread a tip amount of {COIN_REPR} to all online members."
bot_help_send = f"Send {COIN_REPR} to a {COIN_REPR} address from your balance (supported integrated address)."
bot_help_address = f"Check {COIN_REPR} address | Generate {COIN_REPR} integrated address."
bot_help_paymentid = "Make a random payment ID with 64 chars length."
bot_help_tag = "Display a description or a link about what it is. (-add|-del) requires permission manage_channels"
bot_help_itag = "Upload image (gif|png|jpeg|mp4) and add tag."
bot_help_stats = f"Show summary {COIN_REPR}: height, difficulty, etc."
bot_help_height = f"Show {COIN_REPR}'s current height"
bot_help_notifytip = "Toggle notify tip notification from bot ON|OFF"
bot_help_invite = "Invite link of bot to your server."
bot_help_random_number = "Get random number. Example .rand 1-100"
bot_help_disclaimer = "Show disclaimer."
bot_help_voucher = "Make a voucher image and your friend can claim via QR code."
bot_help_take = "Get random faucet tip."
bot_help_cal = "Use built-in calculator."
bot_help_coininfo = "List of coin status."
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

bot = AutoShardedBot(command_prefix = get_prefix, case_insensitive=True, owner_id = OWNER_ID_TIPBOT, pm_help = True, intents=intents)
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


@bot.command(pass_context=True, name='info', help=bot_help_info)
async def info(ctx, coin: str = None):
    global LIST_IGNORECHAN, MUTE_CHANNEL
    # check if account locked
    account_lock = await alert_if_userlock(ctx, 'info')
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

    wallet = None
    COIN_NAME = None
    if coin is None:
        if len(ctx.message.mentions) == 0:
            cmdName = ctx.message.content
        else:
            cmdName = ctx.message.content.split(" ")[0]
        cmdName = cmdName[1:]

        if cmdName.lower() not in ['wallet', 'info']:
            cmdName = ctx.message.content.split(" ")[1]
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} This command can not be in DM. If you want to deposit, use **DEPOSIT** command instead.')
            return
        else:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            prefix = config.discord.prefixCmd
            server_coin = DEFAULT_TICKER
            server_tiponly = "ALLCOIN"
            react_tip_value = "N/A"
            if serverinfo is None:
                # Let's add some info if server return None
                add_server_info = await store.sql_addinfo_by_server(str(ctx.guild.id),
                                                                    ctx.message.guild.name, config.discord.prefixCmd, "WRKZ")
            else:
                prefix = serverinfo['prefix']
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
                msg = await ctx.send(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
                await ctx.message.add_reaction(EMOJI_OK_HAND)
            except (discord.errors.NotFound, discord.errors.Forbidden, Exception) as e:
                msg = await ctx.send(
                    '\n```'
                    f'Server ID:      {ctx.guild.id}\n'
                    f'Server Name:    {ctx.message.guild.name}\n'
                    f'Default Ticker: {server_coin}\n'
                    f'Default Prefix: {prefix}\n'
                    f'TipOnly Coins:  {server_tiponly}\n'
                    f'Re-act Tip:     {react_tip_value}\n'
                    f'Ignored Tip in: {chanel_ignore_list}\n'
                    f'Mute in:        {chanel_mute_list}\n'
                    f'```{extra_text}')
                await msg.add_reaction(EMOJI_OK_BOX)
                await ctx.message.add_reaction(EMOJI_OK_HAND)
            return
    else:
        COIN_NAME = coin.upper()
        pass

    if COIN_NAME:
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please use **DEPOSIT** command instead.')
        return



@bot.command(pass_context=True, name='coininfo', aliases=['coinf_info', 'coin'], help=bot_help_coininfo)
async def coininfo(ctx, coin: str = None):
    global TRTL_DISCORD, ENABLE_COIN, ENABLE_COIN_DOGE, ENABLE_XMR, ENABLE_COIN_NANO, ENABLE_COIN_ERC, ENABLE_COIN_TRC, ENABLE_XCH
    if coin is None:
        if isinstance(ctx.channel, discord.DMChannel) == False and ctx.guild.id == TRTL_DISCORD:
            return
        table_data = [
            ["TICKER", "Height", "Tip", "Wdraw", "Depth"]
            ]
        for COIN_NAME in [coinItem.upper() for coinItem in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH]:
            height = None
            if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                token_info = await store.get_token_info(COIN_NAME)
                confim_depth = token_info['deposit_confirm_depth']
            else:
                confim_depth = get_confirm_depth(COIN_NAME)
            try:
                openRedis()
                if redis_conn and redis_conn.exists(f'{config.redis_setting.prefix_daemon_height}{COIN_NAME}'):
                    height = int(redis_conn.get(f'{config.redis_setting.prefix_daemon_height}{COIN_NAME}'))
                    if not is_maintenance_coin(COIN_NAME):
                        table_data.append([COIN_NAME,  '{:,.0f}'.format(height), "ON" if is_coin_tipable(COIN_NAME) else "OFF"\
                        , "ON" if is_coin_txable(COIN_NAME) else "OFF"\
                        , confim_depth])
                    else:
                        table_data.append([COIN_NAME, "***", "***", "***", confim_depth])
            except Exception as e:
                await logchanbot(traceback.format_exc())

        table = AsciiTable(table_data)
        table.padding_left = 0
        table.padding_right = 0
        msg = await ctx.send('**[ TIPBOT COIN LIST ]**\n'
                             f'```{table.table}```')
        
        return
    else:
        COIN_NAME = coin.upper()
        if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            token_info = await store.get_token_info(COIN_NAME)
            confim_depth = token_info['deposit_confirm_depth']
            Min_Tip = token_info['real_min_tip']
            Max_Tip = token_info['real_max_tip']
            Min_Tx = token_info['real_min_tx']
            Max_Tx = token_info['real_max_tx']
        elif COIN_NAME in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_XCH:
            confim_depth = get_confirm_depth(COIN_NAME)
            Min_Tip = get_min_mv_amount(COIN_NAME)
            Max_Tip = get_max_mv_amount(COIN_NAME)
            Min_Tx = get_min_tx_amount(COIN_NAME)
            Max_Tx = get_max_tx_amount(COIN_NAME)
            token_info = None
        if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
            await ctx.author.send(f'{ctx.author.mention} **{COIN_NAME}** is not in our list.')
            return
        else:
            response_text = "**[ COIN INFO {} ]**".format(COIN_NAME)
            response_text += "```"
            try:
                openRedis()
                if redis_conn and redis_conn.exists(f'{config.redis_setting.prefix_daemon_height}{COIN_NAME}'):
                    height = int(redis_conn.get(f'{config.redis_setting.prefix_daemon_height}{COIN_NAME}'))
                    response_text += "Height: {:,.0f}".format(height) + "\n"
                response_text += "Confirmation: {} Blocks".format(confim_depth) + "\n"
                tip_deposit_withdraw_stat = ["ON", "ON", "ON"]
                if not is_coin_tipable(COIN_NAME):
                    tip_deposit_withdraw_stat[0] = "OFF"
                if not is_coin_depositable(COIN_NAME):
                    tip_deposit_withdraw_stat[1] = "OFF"
                if not is_coin_txable(COIN_NAME):
                    tip_deposit_withdraw_stat[2] = "OFF"
                response_text += "Tipping / Depositing / Withdraw:\n   {} / {} / {}\n".format(tip_deposit_withdraw_stat[0], tip_deposit_withdraw_stat[1], tip_deposit_withdraw_stat[2])

                get_tip_min_max = "Tip Min/Max:\n   " + num_format_coin(Min_Tip, COIN_NAME) + " / " + num_format_coin(Max_Tip, COIN_NAME) + " " + COIN_NAME
                response_text += get_tip_min_max + "\n"
                get_tx_min_max = "Withdraw Min/Max:\n   " + num_format_coin(Min_Tx, COIN_NAME) + " / " + num_format_coin(Max_Tx, COIN_NAME) + " " + COIN_NAME
                response_text += get_tx_min_max + "\n"

                if COIN_NAME in FEE_PER_BYTE_COIN + ENABLE_COIN_DOGE + ENABLE_XCH + ENABLE_XMR:
                    response_text += "Withdraw Tx Node Fee: {} {}\n".format(num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
                elif COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    if token_info['contract'] and len(token_info['contract']) == 42:
                        response_text += "Contract:\n   {}\n".format(token_info['contract'])
                    elif COIN_NAME in ENABLE_COIN_TRC and token_info['contract'] and len(token_info['contract']) > 4:
                        response_text += "Contract/Token ID:\n   {}\n".format(token_info['contract'])
                    response_text += "Withdraw Tx Fee: {} {}\n".format(num_format_coin(token_info['real_withdraw_fee'], COIN_NAME), COIN_NAME)
                    if token_info['real_deposit_fee'] and token_info['real_deposit_fee'] > 0:
                        response_text += "Deposit Tx Fee: {} {}\n".format(num_format_coin(token_info['real_deposit_fee'], COIN_NAME), COIN_NAME)
                elif COIN_NAME in ENABLE_COIN_NANO:
                    # nothing
                    response_text += "Withdraw Tx Fee: Zero\n"
                else:
                    response_text += "Withdraw Tx Fee: {} {}\n".format(num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)

                if isinstance(ctx.channel, discord.DMChannel) == True:
                    if COIN_NAME in ENABLE_TRADE_COIN and is_tradeable_coin(COIN_NAME): 
                        response_text += f"Trade Min/Max: {num_format_coin(get_min_sell(COIN_NAME, token_info), COIN_NAME)} {COIN_NAME} / {num_format_coin(get_max_sell(COIN_NAME, token_info), COIN_NAME)} {COIN_NAME}\n"
                        
                elif isinstance(ctx.channel, discord.DMChannel) == False and COIN_NAME in ENABLE_TRADE_COIN and is_tradeable_coin(COIN_NAME):
                    serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                    if 'enable_trade' in serverinfo and serverinfo['enable_trade'] == "YES":
                        response_text += f"Trade Min/Max: {num_format_coin(get_min_sell(COIN_NAME, token_info), COIN_NAME)} {COIN_NAME} / {num_format_coin(get_max_sell(COIN_NAME, token_info), COIN_NAME)} {COIN_NAME}\n"
                        # If there is volume
                        try:
                            get_trade = await store.sql_get_coin_trade_stat(COIN_NAME)
                            if get_trade:
                                response_text += "Trade volume:\n   24h: {} {}\n".format(num_format_coin(get_trade['trade_24h'], COIN_NAME), COIN_NAME)
                                response_text += "   7d: {} {}\n".format(num_format_coin(get_trade['trade_7d'], COIN_NAME), COIN_NAME)
                                response_text += "   30d: {} {}\n".format(num_format_coin(get_trade['trade_30d'], COIN_NAME), COIN_NAME)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC and token_info['coininfo_note']:
                    response_text += "\nNote:\n   {}\n".format(token_info['coininfo_note'])
            except Exception as e:
                await logchanbot(traceback.format_exc())
            response_text += "```"
            await ctx.message.reply(response_text)
            return


@bot.command(pass_context=True, name='balance', aliases=['bal'], help=bot_help_balance)
async def balance(ctx, coin: str = None):
    prefix = await get_guild_prefix(ctx)
    botLogChan = bot.get_channel(LOG_CHAN)
    # check if account locked
    account_lock = await alert_if_userlock(ctx, 'balance')
    if account_lock:
        await ctx.message.add_reaction(EMOJI_LOCKED) 
        await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
        return
    # end of check if account locked

    PUBMSG = ctx.message.content.strip().split(" ")[-1].upper()

    # Get wallet status
    walletStatus = None
    COIN_NAME = None
    embed = discord.Embed(title='[ YOUR BALANCE LIST ]', timestamp=datetime.utcnow())
    num_coins = 0
    per_page = 25
    if (coin is None) or (PUBMSG == "PUB") or (PUBMSG == "PUBLIC") or (PUBMSG == "LIST"):
        table_data = [
            ['TICKER', 'Available', 'Tx']
        ]
        table_data_str = []
        for COIN_NAME in [coinItem.upper() for coinItem in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH]:
            if not is_maintenance_coin(COIN_NAME):
                wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                if wallet is None:
                    if COIN_NAME in ENABLE_COIN_ERC:
                        w = await create_address_eth()
                        userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
                    elif COIN_NAME in ENABLE_COIN_TRC:
                        result = await store.create_address_trx()
                        userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, result)
                    else:
                        userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
                    wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
                if wallet is None:
                    if coin: table_data.append([COIN_NAME, "N/A", "N/A"])
                    await botLogChan.send(f'A user call `{prefix}balance` failed with {COIN_NAME}')
                else:
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
                    balance_actual = num_format_coin(actual_balance, COIN_NAME)
                    coinName = COIN_NAME
                    if actual_balance != 0:
                        if coin:
                            table_data.append([coinName, balance_actual, "YES" if is_coin_txable(COIN_NAME) else "NO"])
                        else:
                            if actual_balance > 0:
                                table_data_str.append("{} {}".format(balance_actual, coinName))
                                embed.add_field(name=COIN_NAME, value=balance_actual+" "+COIN_NAME, inline=True)
                                num_coins += 1
                                if num_coins > 0 and num_coins % per_page == 0:
                                    embed.set_footer(text="Continue... Page {}".format(int(num_coins/per_page)))
                                    try:
                                        msg = await ctx.author.send(embed=embed)
                                        await msg.add_reaction(EMOJI_OK_BOX)
                                        ## New embed
                                        embed = discord.Embed(title='[ YOUR BALANCE LIST CONTINUE - {}]'.format(int(num_coins/per_page+1)), timestamp=datetime.utcnow())
                                    except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                        await ctx.add_reaction(EMOJI_ZIPPED_MOUTH)
                                        break
                                        return
                                
                    pass
            else:
                if coin: table_data.append([COIN_NAME, "***", "***"])
        table = AsciiTable(table_data)
        # table.inner_column_border = False
        # table.outer_border = False
        table.padding_left = 0
        table.padding_right = 0
        await ctx.message.add_reaction(EMOJI_OK_HAND)
        if coin is None:
            # table_data_str = ", ".join(table_data_str)
            embed.add_field(name='Related commands', value=f'`{prefix}balance TICKER` or `{prefix}deposit TICKER` or `{prefix}balance LIST`', inline=False)
            if num_coins > 0 and num_coins / per_page > 1:
                embed.set_footer(text="Last Page {}".format(int(np.ceil(num_coins/per_page))))
            try:
                msg = await ctx.author.send(embed=embed)
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                return
        else:
            if PUBMSG.upper() == "PUB" or PUBMSG.upper() == "PUBLIC":
                msg = await ctx.message.reply('**[ BALANCE LIST ]**\n'
                                f'```{table.table}```'
                                f'Related command: `{prefix}balance TICKER` or `{prefix}deposit TICKER`\n`***`: On Maintenance\n')
            else:
                msg = await ctx.author.send('**[ BALANCE LIST ]**\n'
                                f'```{table.table}```'
                                f'Related command: `{prefix}balance TICKER` or `{prefix}deposit TICKER`\n`***`: On Maintenance\n'
                                f'{get_notice_txt(COIN_NAME)}')
        await msg.add_reaction(EMOJI_OK_BOX)
        return
    else:
        COIN_NAME = coin.upper()

    if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**!')
        return

    if is_maintenance_coin(COIN_NAME) and ctx.author.id not in MAINTENANCE_OWNER:
        await ctx.message.add_reaction(EMOJI_MAINTENANCE)
        msg = await ctx.message.reply(f'{EMOJI_RED_NO} {COIN_NAME} in maintenance.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return
    if COIN_NAME in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
        wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
        if wallet is None:
            if COIN_NAME in ENABLE_COIN_ERC:
                w = await create_address_eth()
                userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
            elif COIN_NAME in ENABLE_COIN_TRC:
                result = await store.create_address_trx()
                userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, result)
            else:
                userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
            wallet = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
        if COIN_NAME in ENABLE_COIN_ERC:
            token_info = await store.get_token_info(COIN_NAME)
            deposit_balance = await store.http_wallet_getbalance(wallet['balance_wallet_address'], COIN_NAME, True)
            real_deposit_balance = round(deposit_balance / 10**token_info['token_decimal'], 6)
        elif COIN_NAME in ENABLE_COIN_TRC:
            token_info = await store.get_token_info(COIN_NAME)
            deposit_balance = await store.trx_wallet_getbalance(wallet['balance_wallet_address'], COIN_NAME)
            real_deposit_balance = round(deposit_balance, 6)
        userdata_balance = await store.sql_user_balance(str(ctx.author.id), COIN_NAME, SERVER_BOT)
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

        balance_actual = num_format_coin(actual_balance, COIN_NAME)
        locked_openorder = userdata_balance['OpenOrder']
        raffle_spent = userdata_balance['raffle_fee']
        raffle_reward = userdata_balance['raffle_reward']
        economy_amount = userdata_balance['economy_balance']
        embed = discord.Embed(title=f'[ {ctx.author.name}#{ctx.author.discriminator}\'s {COIN_NAME} balance ]', timestamp=datetime.utcnow())
        try:
            if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                embed.add_field(name="Deposited", value="`{} {}`".format(num_format_coin(float(real_deposit_balance), COIN_NAME), COIN_NAME), inline=True)
            embed.add_field(name="Spendable", value=balance_actual+COIN_NAME, inline=True)
            if locked_openorder > 0 and COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                embed.add_field(name="Opened Order", value=num_format_coin(locked_openorder, COIN_NAME)+" "+COIN_NAME, inline=True)
                embed.add_field(name="Total", value=num_format_coin(actual_balance+locked_openorder, COIN_NAME)+" "+COIN_NAME, inline=True)
            elif locked_openorder > 0 and COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                embed.add_field(name="Opened Order", value=num_format_coin(locked_openorder, COIN_NAME)+" "+COIN_NAME, inline=True)
                embed.add_field(name="Total", value=num_format_coin(actual_balance+locked_openorder+float(real_deposit_balance), COIN_NAME)+" "+COIN_NAME, inline=True)
            elif locked_openorder == 0 and COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                embed.add_field(name="Total", value=num_format_coin(actual_balance+float(real_deposit_balance), COIN_NAME)+" "+COIN_NAME, inline=True)
            if raffle_spent and raffle_spent > 0:
                embed.add_field(name="Raffle Spent / Won", value="{} / {} {}".format(num_format_coin(raffle_spent, COIN_NAME), num_format_coin(raffle_reward, COIN_NAME), COIN_NAME), inline=False)
        except Exception as e:
            print(traceback.format_exc())
        if userdata_balance['economy_balance'] and userdata_balance['economy_balance'] != 0:
            embed.add_field(name="Economy Expense (+/-)", value=num_format_coin(userdata_balance['economy_balance'], COIN_NAME)+ " " + COIN_NAME, inline=True)
        embed.add_field(name='Related commands', value=f'`{prefix}balance` or `{prefix}deposit {COIN_NAME}` or `{prefix}balance LIST`', inline=False)
        if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            min_deposit_txt = " Min. deposit for moving to spendable: " + num_format_coin(token_info['min_move_deposit'], COIN_NAME) + " "+ COIN_NAME
            embed.set_footer(text=f"{token_info['deposit_note'] + min_deposit_txt}")
        else:
            embed.set_footer(text=f"{get_notice_txt(COIN_NAME)}")
        try:
            msg = await ctx.author.send(embed=embed)
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            await msg.add_reaction(EMOJI_OK_BOX)
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            try:
                msg = await ctx.message.reply(embed=embed)
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                await msg.add_reaction(EMOJI_OK_BOX)
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
            return
    else:
        msg = await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} There is no such ticker {COIN_NAME}.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return



@bot.command(pass_context=True, aliases=['botbal'], help=bot_help_botbalance)
async def botbalance(ctx, member: discord.Member, coin: str):
    global TRTL_DISCORD

    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} This command can not be in DM.')
        return
        
    # if public and there is a bot channel
    if isinstance(ctx.channel, discord.DMChannel) == False:
        serverinfo = await get_info_pref_coin(ctx)
        server_prefix = serverinfo['server_prefix']
        # check if bot channel is set:
        if serverinfo and serverinfo['botchan']:
            try: 
                if ctx.channel.id != int(serverinfo['botchan']):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    botChan = bot.get_channel(int(serverinfo['botchan']))
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, {botChan.mention} is the bot channel!!!')
                    return
            except ValueError:
                pass
        # end of bot channel check

    if member.bot == False:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Only for bot!!')
        return

    COIN_NAME = coin.upper()
    if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER {COIN_NAME}**!')
        return

    # TRTL discord
    if ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
        return

    if is_maintenance_coin(COIN_NAME):
        await ctx.message.add_reaction(EMOJI_MAINTENANCE)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
        return


    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    if COIN_NAME in ENABLE_COIN_ERC:
        coin_family = "ERC-20"
    elif COIN_NAME in ENABLE_COIN_TRC:
        coin_family = "TRC-20"
    else:
        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
    if COIN_NAME in ENABLE_COIN+ENABLE_XMR+ENABLE_COIN_DOGE+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
        try:
            userwallet = await store.sql_get_userwallet(str(member.id), COIN_NAME)
            if userwallet is None:
                if coin_family == "ERC-20":
                    w = await create_address_eth()
                    userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0, w)
                elif coin_family == "TRC-20":
                    result = await store.create_address_trx()
                    userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0, result)
                else:
                    userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0)
                userwallet = await store.sql_get_userwallet(str(member.id), COIN_NAME)
            depositAddress = userwallet['balance_wallet_address']
        except Exception as e:
            await logchanbot(traceback.format_exc())

        balance_actual = "0.00"

        userdata_balance = await store.sql_user_balance(str(member.id), COIN_NAME)
        xfer_in = 0
        if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            xfer_in = await store.sql_user_balance_get_xfer_in(str(member.id), COIN_NAME)
        if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
        elif COIN_NAME in ENABLE_COIN_NANO:
            actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
            actual_balance = round(actual_balance / get_decimal(COIN_NAME), 6) * get_decimal(COIN_NAME)
        else:
            actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
        balance_actual = num_format_coin(actual_balance, COIN_NAME)

        # Negative check
        try:
            if actual_balance < 0:
                msg_negative = 'Negative balance detected:\nBot User: '+str(member.id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
                await logchanbot(msg_negative)
        except Exception as e:
            await logchanbot(traceback.format_exc())

        embed = discord.Embed(title=f'Deposit for {member.name}#{member.discriminator}', description='`This is bot\'s tipjar address. Do not deposit here unless you want to deposit to this bot`', timestamp=datetime.utcnow(), colour=7047495)
        embed.set_author(name=member.name, icon_url=member.display_avatar)
        embed.add_field(name="{} Deposit Address".format(COIN_NAME), value="`{}`".format(userwallet['balance_wallet_address']), inline=False)
        if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            token_info = await store.get_token_info(COIN_NAME)
            if token_info and COIN_NAME in ENABLE_COIN_ERC and token_info['contract'] and len(token_info['contract']) == 42:
                embed.add_field(name="{} Contract".format(COIN_NAME), value="`{}`".format(token_info['contract']), inline=False)
            elif token_info and COIN_NAME in ENABLE_COIN_TRC and token_info['contract'] and len(token_info['contract']) >= 6:
                embed.add_field(name="{} Contract/Token ID".format(COIN_NAME), value="`{}`".format(token_info['contract']), inline=False)
            if token_info and token_info['deposit_note']:
                embed.add_field(name="{} Deposit Note".format(COIN_NAME), value="`{}`".format(token_info['deposit_note']), inline=False)
        embed.add_field(name=f"Balance {COIN_NAME}", value="`{} {}`".format(balance_actual, COIN_NAME), inline=False)
        try:
            msg = await ctx.send(embed=embed)
            await msg.add_reaction(EMOJI_OK_BOX)
            await ctx.message.add_reaction(EMOJI_OK_HAND)
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            msg = await ctx.send(
                    f'**[ <@{member.id}> BALANCE]**\n'
                    f' Deposit Address: `{depositAddress}`\n'
                    f'{EMOJI_MONEYBAG} Available: {balance_actual} '
                    f'{COIN_NAME}\n'
                    '**This is bot\'s tipjar address. Do not deposit here unless you want to deposit to this bot.**')
            await msg.add_reaction(EMOJI_OK_BOX)
            await ctx.message.add_reaction(EMOJI_OK_HAND)
        return


@bot.command(pass_context=True, name='register', aliases=['registerwallet', 'reg', 'updatewallet'],
             help=bot_help_register)
async def register(ctx, wallet_address: str, coin: str=None):
    global IS_RESTARTING
    # check if bot is going to restart
    if IS_RESTARTING:
        await ctx.message.add_reaction(EMOJI_REFRESH)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
        return

    # check if account locked
    account_lock = await alert_if_userlock(ctx, 'register')
    if account_lock:
        await ctx.message.add_reaction(EMOJI_LOCKED) 
        await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
        return
    # end of check if account locked

    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    # if public and there is a bot channel
    if isinstance(ctx.channel, discord.DMChannel) == False:
        serverinfo = await get_info_pref_coin(ctx)
        server_prefix = serverinfo['server_prefix']
        # check if bot channel is set:
        if serverinfo and serverinfo['botchan']:
            try: 
                if ctx.channel.id != int(serverinfo['botchan']):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    botChan = bot.get_channel(int(serverinfo['botchan']))
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, {botChan.mention} is the bot channel!!!')
                    return
            except ValueError:
                pass
        # end of bot channel check

    if not re.match(r'^[A-Za-z0-9_]+$', wallet_address):
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                       f'`{wallet_address}`')
        return

    COIN_NAME = get_cn_coin_from_address(wallet_address)
    if COIN_NAME:
        if COIN_NAME == "TRON_TOKEN":
            if coin is None:
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} you need to add **TOKEN NAME** address.')
                return
            else:
                valid_address = await store.trx_validate_address(wallet_address)
                if not valid_address:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token address:\n'
                                         f'`{wallet_address}`')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                else:
                    COIN_NAME = coin.upper()
                    valid_address = wallet_address
        else:
            pass
    else:
        if wallet_address.startswith("0x"):
            if wallet_address.upper().startswith("0X00000000000000000000000000000"):
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token:\n'
                                     f'`{wallet_address}`')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            if coin is None:
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} you need to add **TOKEN NAME** address.')
                return
            else:
                COIN_NAME = coin.upper()
                if COIN_NAME not in ENABLE_COIN_ERC:
                    await ctx.message.add_reaction(EMOJI_WARNING)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Unsupported Token.')
                    return
                else:
                    # validate
                    valid_address = await store.erc_validate_address(wallet_address, COIN_NAME)
                    valid = False
                    if valid_address and valid_address.upper() == wallet_address.upper():
                        valid = True
                    else:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token address:\n'
                                             f'`{wallet_address}`')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
        else:
            if coin is None:
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} you need to add **COIN NAME** after address.')
                return
            else:
                COIN_NAME = coin.upper()
                if COIN_NAME not in ENABLE_COIN_DOGE:
                    await ctx.message.add_reaction(EMOJI_WARNING)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Unsupported coin **{COIN_NAME}**.')
                    return

    if COIN_NAME in ENABLE_COIN_ERC:
        coin_family = "ERC-20"
    elif COIN_NAME in ENABLE_COIN_TRC:
        coin_family = "TRC-20"
    elif COIN_NAME in ENABLE_XCH:
        coin_family = "XCH"
    else:
        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")

    if is_maintenance_coin(COIN_NAME):
        await ctx.message.add_reaction(EMOJI_MAINTENANCE)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
        return

    if coin_family in ["TRTL", "BCN", "XMR", "NANO"]:
        main_address = getattr(getattr(config,"daemon"+COIN_NAME),"MainAddress")
        if wallet_address == main_address:
            await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} do not register with main address. You could lose your coin when withdraw.')
            return
    elif coin_family == "ERC-20":
        # Check if register address in any of user balance address
        check_in_balance_users = await store.erc_check_balance_address_in_users(wallet_address, COIN_NAME)
        if check_in_balance_users:
            await ctx.message.add_reaction(EMOJI_ERROR)
            msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You can not register with any of user\'s tipjar\'s token address.\n'
                                 f'`{wallet_address}`')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
    elif coin_family == "XCH":
        # Check if register address in any of user balance address
        check_in_balance_users = await store.coin_check_balance_address_in_users(wallet_address, COIN_NAME)
        if check_in_balance_users:
            await ctx.message.add_reaction(EMOJI_ERROR)
            msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You can not register with any of user\'s tipjar\'s address.\n'
                                 f'`{wallet_address}`')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
    elif coin_family == "TRC-20":
        # Check if register address in any of user balance address
        check_in_balance_users = await store.trx_check_balance_address_in_users(wallet_address, COIN_NAME)
        if check_in_balance_users:
            await ctx.message.add_reaction(EMOJI_ERROR)
            msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You can not register with any of user\'s tipjar\'s token address.\n'
                                 f'`{wallet_address}`')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

    user = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
    if user is None:
        if coin_family == "ERC-20":
            w = await create_address_eth()
            userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
        elif coin_family == "TRC-20":
            result = await store.create_address_trx()
            userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, result)
        else:
            userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
        user = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)

    existing_user = user

    valid_address = None
    if COIN_NAME in ENABLE_COIN_DOGE:
        user_from = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
        if user_from is None:
            user_from = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
            user_from = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
        user_from['address'] = user_from['balance_wallet_address']
        if COIN_NAME in ENABLE_COIN_DOGE:
            valid_address = await doge_validaddress(str(wallet_address), COIN_NAME)
            if ('isvalid' in valid_address):
                if str(valid_address['isvalid']) == "True":
                    valid_address = wallet_address
                else:
                    valid_address = None
                pass
            pass
    elif COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
        # already validated above
        pass
    else:
        if coin_family in ["TRTL", "BCN"]:
            valid_address = addressvalidation.validate_address_cn(wallet_address, COIN_NAME)
        elif coin_family in ["NANO"]:
            valid_address = await nano_validate_address(COIN_NAME, wallet_address)
            if valid_address == True:
                valid_address = wallet_address
        elif coin_family in ["XCH"]:
            try:
                valid_address = addressvalidation_xch.validate_address(wallet_address, COIN_NAME)
                if valid_address == True:
                    valid_address = wallet_address
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid {COIN_NAME} address.')
                    return
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
        elif coin_family == "XMR":
            if COIN_NAME not in ["MSR", "UPX", "XAM"]:
                valid_address = await validate_address_xmr(str(wallet_address), COIN_NAME)
                if valid_address is None:
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                   f'`{wallet_address}`')
                if valid_address['valid'] == True and valid_address['integrated'] == False \
                    and valid_address['subaddress'] == False and valid_address['nettype'] == 'mainnet':
                    # re-value valid_address
                    valid_address = str(wallet_address)
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please use {COIN_NAME} main address.')
                    return
            else:
                if COIN_NAME == "MSR":
                    valid_address = address_msr(wallet_address)
                    if type(valid_address).__name__ != "Address":
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please use {COIN_NAME} main address.')
                        return
                elif COIN_NAME == "WOW":
                    valid_address = address_wow(wallet_address)
                    if type(valid_address).__name__ != "Address":
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please use {COIN_NAME} main address.')
                        return
                elif COIN_NAME == "XOL":
                    valid_address = address_xol(wallet_address)
                    if type(valid_address).__name__ != "Address":
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please use {COIN_NAME} main address.')
                        return
                elif COIN_NAME == "UPX":
                    #
                    valid_address = None
                    try:	
                        valid_address = address_upx(wallet_address)
                        print(valid_address)
                        if type(valid_address).__name__ != "Address":	
                            await ctx.message.add_reaction(EMOJI_ERROR)	
                            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please use {COIN_NAME} main address.')	
                            return
                    except Exception as e:	
                        traceback.print_exc(file=sys.stdout)	
                        pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Unknown Ticker.')
            return
    # correct print(valid_address)
    if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
        if valid_address is None: 
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid {COIN_NAME} address:\n'
                           f'`{wallet_address}`')
            return

        if valid_address != wallet_address:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid {COIN_NAME} address:\n'
                           f'`{wallet_address}`')
            return

    # if they want to register with tipjar address
    try:
        if user['balance_wallet_address'] == wallet_address:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You can not register with your {COIN_NAME} tipjar\'s address.\n'
                           f'`{wallet_address}`')
            return
        else:
            pass
    except Exception as e:
        await ctx.message.add_reaction(EMOJI_ERROR)
        print('Error during register user address:' + str(e))
        return

    serverinfo = await get_info_pref_coin(ctx)
    server_prefix = serverinfo['server_prefix']
    if existing_user['user_wallet_address']:
        prev_address = existing_user['user_wallet_address']
        if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            if prev_address.upper() != wallet_address.upper():
                await store.sql_update_user(str(ctx.author.id), wallet_address, COIN_NAME)
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                await ctx.send(f'Your {COIN_NAME} {ctx.author.mention} withdraw address has changed from:\n'
                               f'`{prev_address}`\n to\n '
                               f'`{wallet_address}`')
                try:
                    await store.redis_delete_userwallet(str(ctx.author.id), COIN_NAME, SERVER_BOT)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
            else:
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.send(f'{ctx.author.mention} Your {COIN_NAME} previous and new address is the same.')
            return

        else:
            if prev_address != valid_address:
                await store.sql_update_user(str(ctx.author.id), wallet_address, COIN_NAME)
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                await ctx.send(f'Your {COIN_NAME} {ctx.author.mention} withdraw address has changed from:\n'
                               f'`{prev_address}`\n to\n '
                               f'`{wallet_address}`')
                try:
                    await store.redis_delete_userwallet(str(ctx.author.id), COIN_NAME, SERVER_BOT)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
            else:
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.send(f'{ctx.author.mention} Your {COIN_NAME} previous and new address is the same.')
            return
    else:
        await store.sql_update_user(str(ctx.author.id), wallet_address, COIN_NAME)
        await ctx.message.add_reaction(EMOJI_OK_HAND)
        await ctx.send(f'{ctx.author.mention} You have registered {COIN_NAME} withdraw address.\n'
                       f'You can use `{server_prefix}withdraw AMOUNT {COIN_NAME}` anytime.')
        try:
            await store.redis_delete_userwallet(str(ctx.author.id), COIN_NAME, SERVER_BOT)
        except Exception as e:
            await logchanbot(traceback.format_exc())
        return


@bot.command(pass_context=True, help=bot_help_withdraw)
async def withdraw(ctx, amount: str, coin: str = None):
    global TX_IN_PROCESS, IS_RESTARTING
    # check if bot is going to restart
    if IS_RESTARTING:
        await ctx.message.add_reaction(EMOJI_REFRESH)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
        return

    # check if account locked
    account_lock = await alert_if_userlock(ctx, 'withdraw')
    if account_lock:
        await ctx.message.add_reaction(EMOJI_LOCKED) 
        await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
        return
    # end of check if account locked

    # Check if tx in progress
    if ctx.author.id in TX_IN_PROCESS:
        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    botLogChan = bot.get_channel(LOG_CHAN)
    amount = amount.replace(",", "")

    # Check flood of tip
    floodTip = await store.sql_get_countLastTip(str(ctx.author.id), config.floodTipDuration)
    if floodTip >= config.floodTip:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Cool down your tip or TX. or increase your amount next time.')
        await botLogChan.send('A user reached max. TX threshold. Currently halted: `.withdraw`')
        return
    # End of Check flood of tip

    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    if isinstance(ctx.channel, discord.DMChannel):
        server_prefix = '.'
    else:
        serverinfo = await get_info_pref_coin(ctx)
        server_prefix = serverinfo['server_prefix']
        # check if bot channel is set:
        if serverinfo and serverinfo['botchan']:
            try: 
                if ctx.channel.id != int(serverinfo['botchan']):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    botChan = bot.get_channel(int(serverinfo['botchan']))
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, {botChan.mention} is the bot channel!!!')
                    return
            except ValueError:
                pass
        # end of bot channel check
    try:
        amount = Decimal(amount)
    except ValueError:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid given amount for `withdraw`.')
        return

    if coin is None:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please have **ticker** (coin name) after amount for `withdraw`.')
        return

    COIN_NAME = coin.upper()
    if not is_coin_txable(COIN_NAME):
        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} TX is currently disable for {COIN_NAME}.')
        await msg.add_reaction(EMOJI_OK_BOX)
        await logchanbot(f'User {ctx.author.id} tried to withdraw {amount} {COIN_NAME} while it tx not enable.')
        return

    if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
        await ctx.message.add_reaction(EMOJI_WARNING)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Unknown Ticker.')
        return

    if COIN_NAME in ENABLE_COIN_ERC:
        coin_family = "ERC-20"
        real_amount = float(amount)
    elif COIN_NAME in ENABLE_COIN_TRC:
        coin_family = "TRC-20"
        real_amount = float(amount)
    else:
        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
        real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
        MinTx = get_min_tx_amount(COIN_NAME)
        MaxTX = get_max_tx_amount(COIN_NAME)
    if is_maintenance_coin(COIN_NAME):
        await ctx.message.add_reaction(EMOJI_MAINTENANCE)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
        return

    try:
        user = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
        if user is None:
            if COIN_NAME in ENABLE_COIN_ERC:
                w = await create_address_eth()
                user = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
            elif COIN_NAME in ENABLE_COIN_TRC:
                result = await store.create_address_trx()
                user = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, result)
            else:
                user = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
            user = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)

        if user['user_wallet_address'] is None:
            extra_txt = ""
            if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                extra_txt = " " + COIN_NAME
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You do not have a withdrawal address for **{COIN_NAME}**, please use '
                           f'`{server_prefix}register wallet_address{extra_txt}` to register. Alternatively, please use `{server_prefix}send <amount> <coin_address>`')
            return

        NetFee = 0
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

        if coin_family == "ERC-20" or coin_family == "TRC-20":
            token_info = await store.get_token_info(COIN_NAME)
            NetFee = token_info['real_withdraw_fee']
            MinTx = token_info['real_min_tx']
            MaxTX = token_info['real_max_tx']
        else:
            NetFee = get_tx_node_fee(coin = COIN_NAME)
        # Negative check
        try:
            if actual_balance < 0:
                msg_negative = 'Negative balance detected:\nUser: '+str(ctx.author.id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
                await logchanbot(msg_negative)
        except Exception as e:
            await logchanbot(traceback.format_exc())

        # add redis action
        random_string = str(uuid.uuid4())
        await add_tx_action_redis(json.dumps([random_string, "WITHDRAW", str(ctx.author.id), ctx.author.name, float("%.3f" % time.time()), ctx.message.content, SERVER_BOT, "START"]), False)

        # If balance 0, no need to check anything
        if actual_balance <= 0:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please check your **{COIN_NAME}** balance.')
            return
        elif real_amount + NetFee > actual_balance:
            extra_fee_txt = ''
            if NetFee > 0:
                extra_fee_txt = f'You need to leave a node/tx fee: {num_format_coin(NetFee, COIN_NAME)} {COIN_NAME}'
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to withdraw '
                           f'{num_format_coin(real_amount, COIN_NAME)} '
                           f'{COIN_NAME}. {extra_fee_txt}')
            return
        elif real_amount > MaxTX:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than '
                           f'{num_format_coin(MaxTX, COIN_NAME)} '
                           f'{COIN_NAME}')
            return
        elif real_amount < MinTx:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be lower than '
                           f'{num_format_coin(MinTx, COIN_NAME)} '
                           f'{COIN_NAME}')
            return
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        await logchanbot(traceback.format_exc())
        return
    withdrawTx = None
    withdraw_txt = ''
    # add to queue withdraw
    if ctx.author.id not in TX_IN_PROCESS:
        TX_IN_PROCESS.append(ctx.author.id)
    else:
        # reject and tell to wait
        await botLogChan.send(f'A user tried to executed `.withdraw {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}` while there is in queue of **TX_IN_PROCESS**.')
        try:
            msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You have another tx in process. Please wait it to finish. ')
        except Exception as e:
            pass
        await msg.add_reaction(EMOJI_OK_BOX)
        return
    try:
        if coin_family in ["TRTL", "BCN"]:
            withdrawTx = await store.sql_external_cn_single(str(ctx.author.id), user['user_wallet_address'], real_amount, COIN_NAME, SERVER_BOT, 'WITHDRAW')
            if withdrawTx:
                withdraw_txt = "Transaction hash: `{}`\nA node/tx fee `{} {}` deducted from your balance.".format(withdrawTx['transactionHash'], num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
        elif coin_family == "XMR":
            withdrawTx = await store.sql_external_xmr_single(str(ctx.author.id),
                                                            real_amount,
                                                            user['user_wallet_address'],
                                                            COIN_NAME, "WITHDRAW", NetFee)
            if withdrawTx:
                withdraw_txt = "Transaction hash: `{}`\nA node/tx fee `{} {}` deducted from your balance.".format(withdrawTx['tx_hash'], num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
        elif coin_family == "XCH":
            withdrawTx = await store.sql_external_xch_single(str(ctx.author.id),
                                                            real_amount,
                                                            user['user_wallet_address'],
                                                            COIN_NAME, "WITHDRAW")
            if withdrawTx:
                withdraw_txt = "Transaction hash: `{}`\nA node/tx fee `{} {}` deducted from your balance.".format(withdrawTx['tx_hash']['name'], num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
        elif coin_family == "NANO":
            withdrawTx = await store.sql_external_nano_single(str(ctx.author.id), real_amount,
                                                            user['user_wallet_address'],
                                                            COIN_NAME, "WITHDRAW")
            if withdrawTx:
                withdraw_txt = "Block: `{}`".format(withdrawTx['block'])
        elif coin_family == "DOGE": 
            withdrawTx = await store.sql_external_doge_single(str(ctx.author.id), real_amount,
                                                            NetFee, user['user_wallet_address'],
                                                            COIN_NAME, "WITHDRAW")
            if withdrawTx:
                withdraw_txt = 'Transaction hash: `{}`\nA node/tx fee `{} {}` deducted from your balance.'.format(withdrawTx, num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
        elif coin_family == "ERC-20": 
            withdrawTx = await store.sql_external_erc_single(str(ctx.author.id), user['user_wallet_address'], real_amount, COIN_NAME, 'WITHDRAW', SERVER_BOT)
            if withdrawTx:
                withdraw_txt = f'Transaction hash: `{withdrawTx}`\nFee `{NetFee} {COIN_NAME}` deducted from your balance.'
        elif coin_family == "TRC-20": 
            withdrawTx = await store.sql_external_trx_single(str(ctx.author.id), user['user_wallet_address'], real_amount, COIN_NAME, 'WITHDRAW', SERVER_BOT)
            if withdrawTx:
                withdraw_txt = f'Transaction hash: `{withdrawTx}`\nFee `{NetFee} {COIN_NAME}` deducted from your balance.'
        # add redis action
        await add_tx_action_redis(json.dumps([random_string, "WITHDRAW", str(ctx.author.id), ctx.author.name, float("%.3f" % time.time()), ctx.message.content, SERVER_BOT, "COMPLETE"]), False)
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        await logchanbot(traceback.format_exc())
    # remove to queue withdraw
    if ctx.author.id in TX_IN_PROCESS:
        TX_IN_PROCESS.remove(ctx.author.id)

    if withdrawTx:
        withdrawAddress = user['user_wallet_address']
        if coin_family == "ERC-20" or coin_family == "TRC-20":
            await ctx.message.add_reaction(TOKEN_EMOJI)
        else:
            await ctx.message.add_reaction(get_emoji(COIN_NAME))
        try:
            await ctx.author.send(
                                f'{EMOJI_ARROW_RIGHTHOOK} You have withdrawn {num_format_coin(real_amount, COIN_NAME)} '
                                f'{COIN_NAME} to `{withdrawAddress}`.\n'
                                f'{withdraw_txt}')
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            try:
                await ctx.send(f'{EMOJI_ARROW_RIGHTHOOK} You have withdrawn {num_format_coin(real_amount, COIN_NAME)} '
                               f'{COIN_NAME} to `{withdrawAddress}`.\n'
                               f'{withdraw_txt}')
            except Exception as e:
                pass
        await botLogChan.send(f'A user successfully executed `.withdraw {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`')
        return
    else:
        msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Internal error during your withdraw, please report or try again later.')
        await botLogChan.send(f'A user failed to executed `.withdraw {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`')
        await ctx.message.add_reaction(EMOJI_ERROR)
        return


@bot.command(pass_context=True, help=bot_help_donate)
async def donate(ctx, amount: str, coin: str=None):
    global IS_RESTARTING, TX_IN_PROCESS
    # check if bot is going to restart
    if IS_RESTARTING:
        await ctx.message.add_reaction(EMOJI_REFRESH)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
        return
    # check if account locked
    account_lock = await alert_if_userlock(ctx, 'donate')
    if account_lock:
        await ctx.message.add_reaction(EMOJI_LOCKED) 
        await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
        return
    # end of check if account locked

    # Check if tx in progress
    if ctx.author.id in TX_IN_PROCESS:
        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    botLogChan = bot.get_channel(LOG_CHAN)
    donate_msg = ''
    if amount.upper() == "LIST":
        # if .donate list
        donate_list = await store.sql_get_donate_list()
        item_list = []
        embed = discord.Embed(title='Donation List', timestamp=datetime.utcnow())
        for key, value in donate_list.items():
            if value:
                coin_value = num_format_coin(value, key.upper())+key.upper()
                item_list.append(coin_value)
                embed.add_field(name=key.upper(), value=num_format_coin(value, key.upper())+key.upper(), inline=True)
        embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
        if len(item_list) > 0:
            try:
                await ctx.send(embed=embed)
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                msg_coins = ', '.join(item_list)
                try:
                    await ctx.send(f'Thank you for checking. So far, we got donations:\n```{msg_coins}```')
                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                    return
        return

    amount = amount.replace(",", "")

    # Check flood of tip
    floodTip = await store.sql_get_countLastTip(str(ctx.author.id), config.floodTipDuration)
    if floodTip >= config.floodTip:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Cool down your tip or TX. or increase your amount next time.')
        await botLogChan.send('A user reached max. TX threshold. Currently halted: `.donate`')
        return
    # End of Check flood of tip

    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    try:
        amount = Decimal(amount)
    except ValueError:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
        return

    COIN_NAME = coin.upper()
    if COIN_NAME in ENABLE_COIN_ERC:
        coin_family = "ERC-20"
        real_amount = float(amount)
    elif COIN_NAME in ENABLE_COIN_TRC:
        coin_family = "TRC-20"
        real_amount = float(amount)
    else:
        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
        real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else Decimal(amount)
    if is_maintenance_coin(COIN_NAME):
        await ctx.message.add_reaction(EMOJI_MAINTENANCE)
        await ctx.send(f'{EMOJI_RED_NO} {COIN_NAME} in maintenance.')
        return
 
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
        await logchanbot(traceback.format_exc())

    if real_amount > actual_balance:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to donate '
                       f'{num_format_coin(real_amount, COIN_NAME)} '
                       f'{COIN_NAME}.')
        return

    donateTx = None
    try:
        if coin_family in ["TRTL", "BCN"]:
            donateTx = await store.sql_donate(str(ctx.author.id), get_donate_address(COIN_NAME), real_amount, COIN_NAME)
        elif coin_family == "XMR":
            donateTx = await store.sql_mv_xmr_single(str(ctx.author.id), 
                                                    get_donate_account_name(COIN_NAME), 
                                                    real_amount, COIN_NAME, "DONATE")
        elif coin_family == "XCH":
            donateTx = await store.sql_mv_xch_single(str(ctx.author.id), 
                                                    get_donate_account_name(COIN_NAME), 
                                                    real_amount, COIN_NAME, "DONATE")
        elif coin_family == "NANO":
            donateTx = await store.sql_mv_nano_single(str(ctx.author.id), 
                                                      get_donate_account_name(COIN_NAME), 
                                                      real_amount, COIN_NAME, "DONATE")
        elif coin_family == "DOGE":
            donateTx = await store.sql_mv_doge_single(str(ctx.author.id), get_donate_account_name(COIN_NAME), real_amount,
                                                      COIN_NAME, "DONATE")
        elif coin_family == "ERC-20":
            token_info = await store.get_token_info(COIN_NAME)
            donateTx = await store.sql_mv_erc_single(str(ctx.author.id), token_info['donate_name'], real_amount, COIN_NAME, "DONATE", token_info['contract'])
        elif coin_family == "TRC-20":
            token_info = await store.get_token_info(COIN_NAME)
            donateTx = await store.sql_mv_trx_single(str(ctx.author.id), token_info['donate_name'], real_amount, COIN_NAME, "DONATE", token_info['contract'])
    except Exception as e:
        await logchanbot(traceback.format_exc())
    if donateTx:
        # Update tipstat
        try:
            update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
        except Exception as e:
            await logchanbot(traceback.format_exc())

        await ctx.message.add_reaction(get_emoji(COIN_NAME))
        await botLogChan.send(f'{EMOJI_MONEYFACE} TipBot got donation: {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}')
        await ctx.author.send(
                                f'{EMOJI_MONEYFACE} TipBot got donation: {num_format_coin(real_amount, COIN_NAME)} '
                                f'{COIN_NAME} '
                                f'\n'
                                f'Thank you.')
        return
    else:
        await ctx.message.add_reaction(EMOJI_ERROR)
        msg = await ctx.send(f'{ctx.author.mention} Donating failed, try again. Thank you.')
        await botLogChan.send(f'A user failed to donate `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
        await msg.add_reaction(EMOJI_OK_BOX)
        # add to failed tx table
        await store.sql_add_failed_tx(COIN_NAME, str(ctx.author.id), ctx.author.name, real_amount, "DONATE")
        return


@bot.command(pass_context=True, help=bot_help_notifytip)
async def notifytip(ctx, onoff: str):
    # check if account locked
    account_lock = await alert_if_userlock(ctx, 'forwardtip')
    if account_lock:
        await ctx.message.add_reaction(EMOJI_LOCKED) 
        await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
        return
    # end of check if account locked

    if onoff.upper() not in ["ON", "OFF"]:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{ctx.author.mention} You need to use only `ON` or `OFF`.')
        return

    onoff = onoff.upper()
    notifyList = await store.sql_get_tipnotify()
    if onoff == "ON":
        if str(ctx.author.id) in notifyList:
            await store.sql_toggle_tipnotify(str(ctx.author.id), "ON")
            await ctx.send(f'{ctx.author.mention} OK, you will get all notification when tip.')
            return
        else:
            await ctx.send(f'{ctx.author.mention} You already have notification ON by default.')
            return
    elif onoff == "OFF":
        if str(ctx.author.id) in notifyList:
            await ctx.send(f'{ctx.author.mention} You already have notification OFF.')
            return
        else:
            await store.sql_toggle_tipnotify(str(ctx.author.id), "OFF")
            await ctx.send(f'{ctx.author.mention} OK, you will not get any notification when anyone tips.')
            return


@bot.command(pass_context=True)	
async def swap(ctx, amount: str, coin_from: str, coin_to: str):	
    global IS_RESTARTING, TRTL_DISCORD, TX_IN_PROCESS	

    # check if account locked
    account_lock = await alert_if_userlock(ctx, 'swap')
    if account_lock:
        await ctx.message.add_reaction(EMOJI_LOCKED) 
        await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
        return
    # end of check if account locked

    # disable swap for TRTL discord	
    if ctx.guild and ctx.guild.id == TRTL_DISCORD:	
        await ctx.message.add_reaction(EMOJI_LOCKED)	
        return

    # Check if tx in progress
    if ctx.author.id in TX_IN_PROCESS:
        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    # check if bot is going to restart
    if IS_RESTARTING:
        await ctx.message.add_reaction(EMOJI_REFRESH)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
        return

    COIN_NAME_FROM = coin_from.upper()
    COIN_NAME_TO = coin_to.upper()
    if is_maintenance_coin(COIN_NAME_FROM):	
        await ctx.message.add_reaction(EMOJI_MAINTENANCE)	
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME_FROM} in maintenance.')	
        return

    if is_maintenance_coin(COIN_NAME_TO):	
        await ctx.message.add_reaction(EMOJI_MAINTENANCE)	
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME_TO} in maintenance.')	
        return
    
    PAIR_NAME = COIN_NAME_FROM + "-" + COIN_NAME_TO
    if PAIR_NAME not in SWAP_PAIR:
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {PAIR_NAME} is not available.')	
        return

    amount = amount.replace(",", "")	
    try:
        if COIN_NAME_FROM == "WRKZ" or COIN_NAME_TO == "WRKZ":
            amount = float("%.2f" % float(amount))
        else:
            amount = float("%.4f" % float(amount))
    except ValueError:	
        await ctx.message.add_reaction(EMOJI_ERROR)	
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')	
        return

    try:
        SwapCount = await store.sql_swap_count_user(str(ctx.author.id), config.swap_token_setting.allow_second)
        if SwapCount >= config.swap_token_setting.allow_for:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Reduce your swapping in the last **{seconds_str(config.swap_token_setting.allow_second)}**.')
            await logchanbot(f'A user {ctx.author.name}#{ctx.author.discriminator} reached max. swap threshold.')
            return
        # End of Check swap of tip

        real_from_amount = amount
        real_to_amount = amount * SWAP_PAIR[PAIR_NAME]

        if COIN_NAME_FROM in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
            token_info = await store.get_token_info(COIN_NAME_FROM)
            from_decimal = token_info['token_decimal']
            Min_Tip = token_info['real_min_tip']
            Max_Tip = token_info['real_max_tip']
        elif COIN_NAME_FROM in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
            token_info = await store.get_token_info(COIN_NAME_FROM)
            from_decimal = token_info['token_decimal']
            Min_Tip = token_info['real_min_tip']
            Max_Tip = token_info['real_max_tip']
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME_FROM),"coin_family","TRTL")
            from_decimal = int(math.log10(get_decimal(COIN_NAME_FROM)))
            Min_Tip = get_min_mv_amount(COIN_NAME_FROM) / 10**from_decimal
            Max_Tip = get_max_mv_amount(COIN_NAME_FROM) / 10**from_decimal * 5 # Increase x5 for swap

        if COIN_NAME_FROM == "WRKZ" or COIN_NAME_TO == "WRKZ":
            Min_Tip_str = "{:,.2f}".format(Min_Tip)
            Max_Tip_str = "{:,.2f}".format(Max_Tip)
        else:
            Min_Tip_str = "{:,.4f}".format(Min_Tip)
            Max_Tip_str = "{:,.4f}".format(Max_Tip)
        if COIN_NAME_TO in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
            token_info = await store.get_token_info(COIN_NAME_TO)
            to_decimal = token_info['token_decimal']
        elif COIN_NAME_TO in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
            token_info = await store.get_token_info(COIN_NAME_TO)
            to_decimal = token_info['token_decimal']
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME_TO),"coin_family","TRTL")
            to_decimal = int(math.log10(get_decimal(COIN_NAME_TO)))
            

        userdata_balance = await store.sql_user_balance(str(ctx.author.id), COIN_NAME_FROM)
        xfer_in = 0
        if COIN_NAME_FROM not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            xfer_in = await store.sql_user_balance_get_xfer_in(str(ctx.author.id), COIN_NAME_FROM)
        if COIN_NAME_FROM in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
        elif COIN_NAME_FROM in ENABLE_COIN_NANO:
            actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
            actual_balance = round(actual_balance / get_decimal(COIN_NAME_FROM), 6) * get_decimal(COIN_NAME_FROM)
        else:
            actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
        
        if COIN_NAME_FROM in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            real_actual_balance = actual_balance
        else:
            real_actual_balance = actual_balance / 10**from_decimal

        if real_from_amount > Max_Tip:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Swap cannot be bigger than '
                           f'{Max_Tip_str} {COIN_NAME_FROM}.')
            return
        elif real_from_amount < Min_Tip:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Swap cannot be smaller than '
                           f'{Min_Tip_str} {COIN_NAME_FROM}.')
            return
        elif real_from_amount > real_actual_balance:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to do a swap of '
                           f'{num_format_coin(real_from_amount if COIN_NAME_FROM in ENABLE_COIN_ERC+ENABLE_COIN_TRC else real_from_amount*10**from_decimal, COIN_NAME_FROM)} '
                           f'{COIN_NAME_FROM}. Having {num_format_coin(real_actual_balance if COIN_NAME_FROM in ENABLE_COIN_ERC+ENABLE_COIN_TRC else real_from_amount*10**from_decimal, COIN_NAME_FROM)}{COIN_NAME_FROM}.')
            return

        swapit = None	
        try:	
            if ctx.author.id not in TX_IN_PROCESS:	
                TX_IN_PROCESS.append(ctx.author.id)	
                swapit = await store.sql_swap_balance_token(COIN_NAME_FROM, real_from_amount, from_decimal, COIN_NAME_TO,
                                                            real_to_amount, to_decimal, str(ctx.author.id), "{}#{}".format(ctx.author.name, ctx.author.discriminator),
                                                            SERVER_BOT)
                TX_IN_PROCESS.remove(ctx.author.id)	
            else:	
                await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)	
                msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')	
                await msg.add_reaction(EMOJI_OK_BOX)	
                return	
        except Exception as e:	
            await logchanbot(traceback.format_exc())	
        if swapit:
            real_from_str = "{:,.4f}".format(real_from_amount)
            real_to_str = "{:,.4f}".format(real_to_amount)
            await ctx.message.add_reaction(EMOJI_OK_BOX)	
            await ctx.author.send(
                    f'{EMOJI_ARROW_RIGHTHOOK} You swapped {real_from_amount} '	
                    f'{COIN_NAME_FROM} to **{real_to_amount} {COIN_NAME_TO}**.')
            await logchanbot(f'[Discord] User {ctx.author.name}#{ctx.author.discriminator} swapped {real_from_amount} '	
                             f'{COIN_NAME_FROM} to **{real_to_amount} {COIN_NAME_TO}**.')
            return	
        else:	
            await ctx.message.add_reaction(EMOJI_ERROR)	
            await botLogChan.send(f'A user call failed to swap {COIN_NAME_FROM} to {COIN_NAME_TO}')	
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Internal error during swap.')	
            return
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


@bot.command(pass_context=True, aliases=['randomtip'], help=bot_help_randomtip)
async def randtip(ctx, amount: str, coin: str, *, rand_option: str=None):
    global TRTL_DISCORD, IS_RESTARTING
    # check if bot is going to restart
    if IS_RESTARTING:
        await ctx.message.add_reaction(EMOJI_REFRESH)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
        return
    # check if account locked
    account_lock = await alert_if_userlock(ctx, 'tip')
    if account_lock:
        await ctx.message.add_reaction(EMOJI_LOCKED) 
        await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
        return
    # end of check if account locked

    # Check if tx in progress
    if ctx.author.id in TX_IN_PROCESS:
        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    botLogChan = bot.get_channel(LOG_CHAN)
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
    print("COIN_NAME: " + COIN_NAME)

    # TRTL discord
    if ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
        return

    if COIN_NAME not in (ENABLE_COIN_ERC + ENABLE_COIN_TRC + ENABLE_COIN + ENABLE_XMR + ENABLE_COIN_DOGE + ENABLE_COIN_NANO + ENABLE_XCH):
        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} **{COIN_NAME}** is not in our supported coins.')
        await msg.add_reaction(EMOJI_OK_BOX)
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
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} not in allowed coins set by server manager.')
        return
    # End of checking allowed coins

    if is_maintenance_coin(COIN_NAME):
        await ctx.message.add_reaction(EMOJI_MAINTENANCE)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
        return

    # Check flood of tip
    floodTip = await store.sql_get_countLastTip(str(ctx.author.id), config.floodTipDuration)
    if floodTip >= config.floodTip:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Cool down your tip or TX. or increase your amount next time.')
        await botLogChan.send('A user reached max. TX threshold. Currently halted: `.tip`')
        return
    # End of Check flood of tip

    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}')
            return
    # End Check if maintenance

    # Get a random user in the guild, except bots. At least 3 members for random.
    has_last = False
    message_talker = None
    listMembers = None
    minimum_users = 3
    try:
        # Check random option
        if rand_option is None or rand_option.upper().startswith("ALL"):
            listMembers = [member for member in ctx.guild.members if member.bot == False]
        elif rand_option and rand_option.upper().startswith("ONLINE"):
            listMembers = [member for member in ctx.guild.members if member.bot == False and member.status != discord.Status.offline]
        elif rand_option and rand_option.upper().strip().startswith("LAST "):
            argument = rand_option.strip().split(" ")            
            if len(argument) == 2:
                # try if the param is 1111u
                num_user = argument[1].lower()
                if 'u' in num_user or 'user' in num_user or 'users' in num_user or 'person' in num_user or 'people' in num_user:
                    num_user = num_user.replace("people", "")
                    num_user = num_user.replace("person", "")
                    num_user = num_user.replace("users", "")
                    num_user = num_user.replace("user", "")
                    num_user = num_user.replace("u", "")
                    try:
                        num_user = int(num_user)
                        if num_user < minimum_users:
                            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Number of random users cannot below **{minimum_users}**.')
                            return
                        elif num_user >= minimum_users:
                            message_talker = await store.sql_get_messages(str(ctx.message.guild.id), str(ctx.message.channel.id), 0, num_user + 1)
                            if ctx.author.id in message_talker:
                                message_talker.remove(ctx.author.id)
                            else:
                                # remove the last one
                                message_talker.pop()
                            if len(message_talker) < minimum_users:
                                await ctx.message.add_reaction(EMOJI_ERROR)
                                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} There is not sufficient user to count for random tip.')
                                return
                            elif len(message_talker) < num_user:
                                try:
                                    await ctx.message.add_reaction(EMOJI_INFORMATION)
                                    await ctx.send(f'{EMOJI_INFORMATION} {ctx.author.mention} I could not find sufficient talkers up to **{num_user}**. I found only **{len(message_talker)}**'
                                                   f' and will random to one of those **{len(message_talker)}** users.')
                                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                    # No need to tip if failed to message
                                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                    # Let it still go through
                                    #return
                        has_last = True
                    except ValueError:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid param after **LAST** for random tip. Support only *LAST* **X**u right now.')
                        return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid param after **LAST** for random tip. Support only *LAST* **X**u right now.')
                    return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid param after **LAST** for random tip. Support only *LAST* **X**u right now.')
                return
        if has_last == False and listMembers and len(listMembers) >= minimum_users:
            rand_user = random.choice(listMembers)
            max_loop = 0
            while True:
                if rand_user != ctx.author and rand_user.bot == False:
                    break
                else:
                    rand_user = random.choice(listMembers)
                max_loop += 1
                if max_loop >= 5:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} Please try again, maybe guild doesnot have so many users.')
                    return
                    break
        elif has_last == True and message_talker and len(message_talker) >= minimum_users:
            rand_user_id = random.choice(message_talker)
            max_loop = 0
            while True:
                rand_user = bot.get_user(rand_user_id)
                if rand_user and rand_user != ctx.author and rand_user.bot == False and rand_user in ctx.guild.members:
                    break
                else:
                    rand_user_id = random.choice(message_talker)
                    rand_user = bot.get_user(rand_user_id)
                max_loop += 1
                if max_loop >= 10:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} Please try again, maybe guild doesnot have so many users.')
                    return
                    break
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} not enough member for random tip.')
            return
    except Exception as e:
        await logchanbot(traceback.format_exc())
        return
        
    notifyList = await store.sql_get_tipnotify()

    if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
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
        await logchanbot(traceback.format_exc())

    if real_amount > MaxTX:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than '
                       f'{num_format_coin(MaxTX, COIN_NAME)} '
                       f'{COIN_NAME}.')
        return
    elif real_amount < MinTx:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than '
                       f'{num_format_coin(MinTx, COIN_NAME)} '
                       f'{COIN_NAME}.')
        return
    elif real_amount > actual_balance:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to do a random tip of '
                       f'{num_format_coin(real_amount, COIN_NAME)} '
                       f'{COIN_NAME}.')
        return

    # add queue also randtip
    if ctx.author.id not in TX_IN_PROCESS:
        TX_IN_PROCESS.append(ctx.author.id)
    else:
        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    print('random get user: {}/{}'.format(rand_user.name, rand_user.id))

    tip = None
    user_to = await store.sql_get_userwallet(str(rand_user.id), COIN_NAME)
    if user_to is None:
        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
            w = await create_address_eth()
            wallet = await store.sql_register_user(str(rand_user.id), COIN_NAME, SERVER_BOT, 0, w)
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
            result = await store.create_address_trx()
            wallet = await store.sql_register_user(str(rand_user.id), COIN_NAME, SERVER_BOT, 0, result)
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
            wallet = await store.sql_register_user(str(rand_user.id), COIN_NAME, SERVER_BOT, 0)
        user_to = await store.sql_get_userwallet(str(rand_user.id), COIN_NAME)

    if coin_family in ["TRTL", "BCN"]:
        tip = await store.sql_mv_cn_single(str(ctx.author.id), str(rand_user.id), real_amount, 'RANDTIP', COIN_NAME)
    elif coin_family == "XMR":
        tip = await store.sql_mv_xmr_single(str(ctx.author.id), str(rand_user.id), real_amount, COIN_NAME, "RANDTIP")
    elif coin_family == "XCH":
        tip = await store.sql_mv_xch_single(str(ctx.author.id), str(rand_user.id), real_amount, COIN_NAME, "RANDTIP")
    elif coin_family == "NANO":
        tip = await store.sql_mv_nano_single(str(ctx.author.id), str(rand_user.id), real_amount, COIN_NAME, "RANDTIP")
    elif coin_family == "DOGE":
        tip = await store.sql_mv_doge_single(str(ctx.author.id), str(rand_user.id), real_amount, COIN_NAME, "RANDTIP")
    elif coin_family == "ERC-20":
        tip = await store.sql_mv_erc_single(str(ctx.author.id), str(rand_user.id), real_amount, COIN_NAME, "RANDTIP", token_info['contract'])
    elif coin_family == "TRC-20":
        tip = await store.sql_mv_trx_single(str(ctx.author.id), str(rand_user.id), real_amount, COIN_NAME, "RANDTIP", token_info['contract'])
    # remove queue from randtip
    if ctx.author.id in TX_IN_PROCESS:
        TX_IN_PROCESS.remove(ctx.author.id)

    if tip:
        # Update tipstat
        try:
            update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
            update_tipstat = await store.sql_user_get_tipstat(str(rand_user.id), COIN_NAME, True, SERVER_BOT)
        except Exception as e:
            await logchanbot(traceback.format_exc())

        randtip_public_respond = False
        # tipper shall always get DM. Ignore notifyList
        try:
            await ctx.author.send(
                f'{EMOJI_ARROW_RIGHTHOOK} {rand_user.name}#{rand_user.discriminator} got your random tip of {num_format_coin(real_amount, COIN_NAME)} '
                f'{COIN_NAME} in server `{ctx.guild.name}`')
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            await store.sql_toggle_tipnotify(str(ctx.author.id), "OFF")
        if str(rand_user.id) not in notifyList:
            try:
                await rand_user.send(
                    f'{EMOJI_MONEYFACE} You got a random tip of {num_format_coin(real_amount, COIN_NAME)} '
                    f'{COIN_NAME} from {ctx.author.name}#{ctx.author.discriminator} in server `{ctx.guild.name}`\n'
                    f'{NOTIFICATION_OFF_CMD}')
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                await store.sql_toggle_tipnotify(str(user.id), "OFF")
        try:
            # try message in public also
            msg = await ctx.message.reply(
                            f'{rand_user.name}#{rand_user.discriminator} got a random tip of {num_format_coin(real_amount, COIN_NAME)} '
                            f'{COIN_NAME} from {ctx.author.name}#{ctx.author.discriminator}')
            await msg.add_reaction(EMOJI_OK_BOX)
            randtip_public_respond = True
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            pass
        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if randtip_public_respond == False and serverinfo and 'botchan' in serverinfo and serverinfo['botchan']:
            # It has bot channel, let it post in bot channel
            try:
                bot_channel = bot.get_channel(int(serverinfo['botchan']))
                msg = await bot_channel.send(
                            f'{rand_user.name}#{rand_user.discriminator} got a random tip of {num_format_coin(real_amount, COIN_NAME)} '
                            f'{COIN_NAME} from {ctx.author.name}#{ctx.author.discriminator} in {ctx.channel.mention}')
                await msg.add_reaction(EMOJI_OK_BOX)
            except Exception as e:
                await logchanbot(traceback.format_exc())
        await ctx.message.add_reaction(EMOJI_OK_BOX)
        return


@bot.command(pass_context=True, help=bot_help_freetip)
async def freetip(ctx, amount: str, coin: str, duration: str='60s', *, comment: str=None):
    global TRTL_DISCORD, IS_RESTARTING
    # check if bot is going to restart
    if IS_RESTARTING:
        await ctx.message.add_reaction(EMOJI_REFRESH)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
        return
    # check if account locked
    account_lock = await alert_if_userlock(ctx, 'tip')
    if account_lock:
        await ctx.message.add_reaction(EMOJI_LOCKED) 
        await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
        return
    # end of check if account locked

    # Check if tx in progress
    if ctx.author.id in TX_IN_PROCESS:
        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    botLogChan = bot.get_channel(LOG_CHAN)
    amount = amount.replace(",", "")

    try:
        amount = Decimal(amount)
    except ValueError:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
        return

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
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid duration.')
        return

    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.send(f'{EMOJI_RED_NO} This command can not be in private.')
        return

    if duration_s == 0:
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid time given. Please use time format: XXs')
        return
    elif duration_s < config.freetip.duration_min or duration_s > config.freetip.duration_max:
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid duration. Please use between {str(config.freetip.duration_min)}s to {str(config.freetip.duration_max)}s.')
        return

    serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
    COIN_NAME = coin.upper()
    print("COIN_NAME: " + COIN_NAME)

    # TRTL discord
    if ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
        return

    if COIN_NAME not in (ENABLE_COIN + ENABLE_XMR + ENABLE_COIN_DOGE + ENABLE_COIN_NANO + ENABLE_COIN_ERC + ENABLE_COIN_TRC + ENABLE_XCH):
        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} **{COIN_NAME}** is not in our supported coins.')
        await msg.add_reaction(EMOJI_OK_BOX)
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
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} not in allowed coins set by server manager.')
        return
    # End of checking allowed coins

    if is_maintenance_coin(COIN_NAME):
        await ctx.message.add_reaction(EMOJI_MAINTENANCE)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
        return

    # Check flood of tip
    floodTip = await store.sql_get_countLastTip(str(ctx.author.id), config.floodTipDuration)
    if floodTip >= config.floodTip:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Cool down your tip or TX. or increase your amount next time.')
        await botLogChan.send('A user reached max. TX threshold. Currently halted: `.tip`')
        return
    # End of Check flood of tip

    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}')
            return
    # End Check if maintenance

    notifyList = await store.sql_get_tipnotify()
    if coin_family == "ERC-20" or coin_family == "TRC-20":
        token_info = await store.get_token_info(COIN_NAME)
        real_amount = float(amount)
        MinTx = token_info['real_min_tip']
        MaxTX = token_info['real_max_tip']
    else:
        real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["XMR", "TRTL", "BCN", "NANO", "XCH"] else float(amount)
        MinTx = get_min_mv_amount(COIN_NAME)
        MaxTX = get_max_mv_amount(COIN_NAME)
    if comment and len(comment) > 0:
        MinTx = MinTx * config.freetip.with_comment_x_amount
        MaxTX = MaxTX * config.freetip.with_comment_x_amount

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
        await logchanbot(traceback.format_exc())

    if real_amount > MaxTX:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than '
                       f'{num_format_coin(MaxTX, COIN_NAME)} '
                       f'{COIN_NAME}.')
        return
    elif real_amount < MinTx:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than '
                       f'{num_format_coin(MinTx, COIN_NAME)} '
                       f'{COIN_NAME}.')
        return
    elif real_amount > actual_balance:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to do a free tip of '
                       f'{num_format_coin(real_amount, COIN_NAME)} '
                       f'{COIN_NAME}.')
        return

    attend_list_id = []
    attend_list_names = []
    ts = timestamp=datetime.utcnow()

    if ctx.author.id not in TX_IN_PROCESS:
        TX_IN_PROCESS.append(ctx.author.id)
    try:
        embed = discord.Embed(title=f"Free Tip appears {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}", description=f"Re-act {EMOJI_PARTY} to collect", timestamp=ts, color=0x00ff00)
        msg = await ctx.message.reply(embed=embed)
        await msg.add_reaction(EMOJI_PARTY)
        if comment and len(comment) > 0:
            embed.add_field(name="Comment", value=comment, inline=False)
        embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, timeout: {seconds_str(duration_s)}")
        await msg.edit(embed=embed)
        await ctx.message.add_reaction(EMOJI_OK_HAND)
    except (discord.errors.NotFound, discord.errors.Forbidden) as e:
        if ctx.author.id in TX_IN_PROCESS:
            TX_IN_PROCESS.remove(ctx.author.id)
        await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
        return
    def check(reaction, user):
        return user != ctx.author and user.bot == False and reaction.message.author == bot.user \
and reaction.message.id == msg.id and str(reaction.emoji) == EMOJI_PARTY
    
    if comment and len(comment) > 0:
        # multiple free tip
        while True:
            start_time = int(time.time())
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=duration_s, check=check)
            except asyncio.TimeoutError:
                if ctx.author.id in TX_IN_PROCESS:
                    TX_IN_PROCESS.remove(ctx.author.id)
                if len(attend_list_id) == 0:
                    embed = discord.Embed(title=f"Free Tip appears {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}", description=f"Already expired", timestamp=ts, color=0x00ff00)
                    embed.add_field(name="Comment", value=comment, inline=False)
                    embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, and no one collected!")
                    await msg.edit(embed=embed)
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                break

            if str(reaction.emoji) == EMOJI_PARTY and user.id not in attend_list_id:
                attend_list_id.append(user.id)
                attend_list_names.append('{}#{}'.format(user.name, user.discriminator))
                embed = discord.Embed(title=f"Free Tip appears {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}", description=f"Re-act {EMOJI_PARTY} to collect", timestamp=ts, color=0x00ff00)
                embed.add_field(name="Comment", value=comment, inline=False)
                embed.add_field(name="Attendees", value=", ".join(attend_list_names), inline=False)
                embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, timeout: {seconds_str(duration_s)}")
                await msg.edit(embed=embed)
                duration_s -= int(time.time()) - start_time
                if duration_s <= 1:
                    break

        # re-check balance
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

        if real_amount > actual_balance:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to do a free tip of '
                           f'{num_format_coin(real_amount, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return
        # end of re-check balance

        # Multiple tip here
        notifyList = await store.sql_get_tipnotify()

        if len(attend_list_id) == 0:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} divided by 0!!!')
            return

        amountDiv = int(round(real_amount / len(attend_list_id), 2))  # cut 2 decimal only
        if coin_family == "DOGE" or coin_family == "ERC-20" or coin_family == "TRC-20":
            amountDiv = round(real_amount / len(attend_list_id), 4)

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
            # Update tipstat
            try:
                update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
            except Exception as e:
                await logchanbot(traceback.format_exc())
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
                member = bot.get_user(member_id)
                if ctx.author.id != member.id and member.id != bot.user.id:
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
            # Edit embed
            try:
                embed = discord.Embed(title=f"Free Tip appears {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}", description=f"Re-act {EMOJI_PARTY} to collect", timestamp=ts, color=0x00ff00)
                embed.add_field(name="Comment", value=comment, inline=False)
                embed.add_field(name="Attendees", value=", ".join(attend_list_names), inline=False)
                embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, completed! Collected by {len(attend_list_id)} member(s)")
                await msg.edit(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            return
    else:
        # single free tip
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=duration_s, check=check)
        except asyncio.TimeoutError:
            if ctx.author.id in TX_IN_PROCESS:
                TX_IN_PROCESS.remove(ctx.author.id)
            embed = discord.Embed(title=f"Free Tip appears {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}", description=f"Already expired", timestamp=ts, color=0x00ff00)
            embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, and no one collected!")
            await msg.edit(embed=embed)
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        if str(reaction.emoji) == EMOJI_PARTY:
            # re-check balance
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

            if real_amount > actual_balance:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to do a free tip of '
                               f'{num_format_coin(real_amount, COIN_NAME)} '
                               f'{COIN_NAME}.')
                return
            # end of re-check balance

            tip = None
            user_to = await store.sql_get_userwallet(str(user.id), COIN_NAME)
            if user_to is None:
                if COIN_NAME in ENABLE_COIN_ERC:
                    w = await create_address_eth()
                    userregister = await store.sql_register_user(str(user.id), COIN_NAME, SERVER_BOT, 0, w)
                elif COIN_NAME in ENABLE_COIN_TRC:
                    result = await store.create_address_trx()
                    userregister = await store.sql_register_user(str(user.id), COIN_NAME, SERVER_BOT, 0, result)
                else:
                    userregister = await store.sql_register_user(str(user.id), COIN_NAME, SERVER_BOT, 0)
                user_to = await store.sql_get_userwallet(str(user.id), COIN_NAME)
            if coin_family in ["TRTL", "BCN"]:
                tip = await store.sql_mv_cn_single(str(ctx.author.id), str(user.id), real_amount, 'FREETIP', COIN_NAME)
            elif coin_family == "XMR":
                tip = await store.sql_mv_xmr_single(str(ctx.author.id), str(user.id), real_amount, COIN_NAME, "FREETIP")
            elif coin_family == "XCH":
                tip = await store.sql_mv_xch_single(str(ctx.author.id), str(user.id), real_amount, COIN_NAME, "FREETIP")
            elif coin_family == "NANO":
                tip = await store.sql_mv_nano_single(str(ctx.author.id), str(user.id), real_amount, COIN_NAME, "FREETIP")
            elif coin_family == "DOGE":
                tip = await store.sql_mv_doge_single(str(ctx.author.id), str(user.id), real_amount, COIN_NAME, "FREETIP")
            elif coin_family == "ERC-20":
                tip = await store.sql_mv_erc_single(str(ctx.author.id), str(user.id), real_amount, COIN_NAME, "FREETIP", token_info['contract'])
            elif coin_family == "TRC-20":
                tip = await store.sql_mv_trx_single(str(ctx.author.id), str(user.id), real_amount, COIN_NAME, "FREETIP", token_info['contract'])
            # remove queue from freetip
            if ctx.author.id in TX_IN_PROCESS:
                TX_IN_PROCESS.remove(ctx.author.id)

            if tip:
                # Update tipstat
                try:
                    update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
                    update_tipstat = await store.sql_user_get_tipstat(str(user.id), COIN_NAME, True, SERVER_BOT)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                embed = discord.Embed(title=f"Free Tip appeared {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}", description=f"Already collected", color=0x00ff00)
                embed.set_footer(text=f"Free tip by {ctx.author.name}#{ctx.author.discriminator}, collected by: {user.name}#{user.discriminator}")
                await msg.edit(embed=embed)
                # tipper shall always get DM. Ignore notifyList
                try:
                    await ctx.author.send(
                        f'{EMOJI_ARROW_RIGHTHOOK} Tip of {num_format_coin(real_amount, COIN_NAME)} '
                        f'{COIN_NAME} '
                        f'has been collected by {user.name}#{user.discriminator} in server `{ctx.guild.name}`')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    await store.sql_toggle_tipnotify(str(ctx.author.id), "OFF")
                if str(user.id) not in notifyList:
                    try:
                        await user.send(
                            f'{EMOJI_MONEYFACE} You had collected a tip of {num_format_coin(real_amount, COIN_NAME)} '
                            f'{COIN_NAME} from {ctx.author.name}#{ctx.author.discriminator} in server `{ctx.guild.name}`\n'
                            f'{NOTIFICATION_OFF_CMD}')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        await store.sql_toggle_tipnotify(str(user.id), "OFF")
                await msg.add_reaction(EMOJI_OK_BOX)
                return
        

@bot.command(pass_context=True)	
async def tipto(ctx, amount: str, coin: str, to_user: str):
    global TRTL_DISCORD, IS_RESTARTING, TX_IN_PROCESS, LOG_CHAN
    # check if bot is going to restart
    if IS_RESTARTING:
        await ctx.message.add_reaction(EMOJI_REFRESH)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
        return
    # check if account locked
    account_lock = await alert_if_userlock(ctx, 'tipto')
    if account_lock:
        await ctx.message.add_reaction(EMOJI_LOCKED) 
        await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
        return
    # end of check if account locked

    # Check if tx in progress
    if ctx.author.id in TX_IN_PROCESS:
        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    botLogChan = bot.get_channel(LOG_CHAN)
    amount = amount.replace(",", "")
    try:
        amount = Decimal(amount)
    except Exception as e:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
        return

    COIN_NAME = coin.upper()
    if COIN_NAME not in (ENABLE_COIN + ENABLE_XMR + ENABLE_COIN_DOGE + ENABLE_COIN_NANO + ENABLE_COIN_ERC + ENABLE_COIN_TRC + ENABLE_XCH):
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.author.send(f'{COIN_NAME} is not in TipBot.')
        return
    if COIN_NAME not in ENABLE_TIPTO:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.author.send(f'{COIN_NAME} is not in this function of TipTo.')
        return

    # TRTL discord
    if ctx.guild and ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
        return

    # offline can not tipto
    try:
        if ctx.author.status == discord.Status.offline:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Offline status cannot use this.')
            return
    except Exception as e:
        traceback.print_exc(file=sys.stdout)

    try:
        if not is_coin_tipable(COIN_NAME):
            msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} TIPPING is currently disable for {COIN_NAME}.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

        if is_maintenance_coin(COIN_NAME):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
            return

        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")

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

        if coin_family == "ERC-20" or coin_family == "TRC-20":
            real_amount = float(amount)
            token_info = await store.get_token_info(COIN_NAME)
            MinTx = token_info['real_min_tip']
            MaxTX = token_info['real_max_tip']
            decimal_pts = token_info['token_decimal']
        else:
            real_amount = int(Decimal(amount) * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
            MinTx = get_min_mv_amount(COIN_NAME)
            MaxTX = get_max_mv_amount(COIN_NAME)
            decimal_pts = int(math.log10(get_decimal(COIN_NAME)))
        if real_amount > MaxTX:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than '
                           f'{num_format_coin(MaxTX, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return
        elif real_amount > actual_balance:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to transfer tip of '
                           f'{num_format_coin(real_amount, COIN_NAME)} '
                           f'{COIN_NAME} to {to_user}.')
            return
        elif real_amount < MinTx:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than '
                           f'{num_format_coin(MinTx, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return

        if '@' not in to_user:
            msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You need to have a correct format to send to. Example: username@telegram')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        else:
            userid = to_user.split("@")[0]
            serverto = to_user.split("@")[1].upper()
            if serverto not in ["TELEGRAM", "REDDIT"]:
                msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} Unsupported or unknown **{serverto}**')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            else:
                # Find user in DB
                try:
                    to_teleuser = await store.sql_get_userwallet(userid, COIN_NAME, serverto)
                    if to_teleuser is None:
                        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} User **{userid}** is not in our DB for **{serverto}**')
                        await msg.add_reaction(EMOJI_OK_BOX)
                        return
                    else:
                        # We found it
                        # Let's send
                        tipto = await store.sql_tipto_crossing(COIN_NAME, str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator), 
                                                               SERVER_BOT, userid, userid, serverto, real_amount, decimal_pts)
                        if tipto:
                            await logchanbot('[Discord] {}#{} tipto {}{} to **{}**'.format(ctx.author.name, ctx.author.discriminator, num_format_coin(real_amount, COIN_NAME), COIN_NAME, to_user))
                            msg = await ctx.send(f'{EMOJI_CHECK} {ctx.author.mention} Successfully transfer {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME} to **{to_user}**.')
                            await msg.add_reaction(EMOJI_OK_BOX)
                            # Update tipstat
                            try:
                                update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
                                update_tipstat = await store.sql_user_get_tipstat(userid, COIN_NAME, True, serverto)
                            except Exception as e:
                                await logchanbot(traceback.format_exc())
                        else:
                            msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} Internal error for tipto {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME} to **{to_user}**.')
                            await msg.add_reaction(EMOJI_OK_BOX)
                            await logchanbot(f'{EMOJI_ERROR} {ctx.author.name}#{ctx.author.discriminator} Internal error for tipto {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME} to **{to_user}**.')
                        return
                except Exception as e:
                    print(traceback.format_exc())
                    await logchanbot(traceback.format_exc())
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


@bot.command(pass_context=True, help=bot_help_tip)
async def tip(ctx, amount: str, *args):
    global TRTL_DISCORD, IS_RESTARTING, TX_IN_PROCESS
    secrettip = False
    fromDM = False
    # check if bot is going to restart
    if IS_RESTARTING:
        await ctx.message.add_reaction(EMOJI_REFRESH)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
        return
    # check if account locked
    account_lock = await alert_if_userlock(ctx, 'tip')
    if account_lock:
        await ctx.message.add_reaction(EMOJI_LOCKED) 
        await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
        return
    # end of check if account locked

    # Check if tx in progress
    if ctx.author.id in TX_IN_PROCESS:
        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
        msg = await ctx.message.reply(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    botLogChan = bot.get_channel(LOG_CHAN)
    amount = amount.replace(",", "")

    try:
        amount = Decimal(amount)
    except ValueError:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
        return

    if isinstance(ctx.channel, discord.DMChannel) and args[-1].isdigit() == False and config.discord.enable_secrettip != 1:
        await ctx.message.reply(f'{EMOJI_RED_NO} This command can not be in private.')
        return

    if isinstance(ctx.channel, discord.DMChannel):
        if len(args) != 2:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You are using a secret tip. Please tip in public!')
            return
        else:
            COIN_NAME = args[0].upper()
            if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_COIN_NANO+ENABLE_XCH:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You are using a secret tip command. Please tip in public! **{COIN_NAME}** not available!')
                return
            try:
                member = bot.get_user(int(args[1]))
                if member:
                    secrettip = True
                    fromDM = True
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {args[1]} not found!')
                    return
            except Exception as e:
                await ctx.message.add_reaction(EMOJI_ERROR)
                try:
                    await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You are using a secret tip command. Please tip in public!')
                except Exception as e:
                    return
    else:
        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        COIN_NAME = None
        try:
            COIN_NAME = args[0].upper()
            if COIN_NAME in ENABLE_XMR+ENABLE_XCH+ENABLE_COIN_NANO:
                pass
            elif COIN_NAME not in ENABLE_COIN:
                if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                    pass
                elif 'default_coin' in serverinfo:
                    COIN_NAME = serverinfo['default_coin'].upper()
        except:
            if 'default_coin' in serverinfo:
                COIN_NAME = serverinfo['default_coin'].upper()
    print("COIN_NAME: " + COIN_NAME)

    # TRTL discord
    if isinstance(ctx.channel, discord.DMChannel) == False and ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
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
    if fromDM == False:
        # Check allowed coins
        tiponly_coins = serverinfo['tiponly'].split(",")
        if COIN_NAME == serverinfo['default_coin'].upper() or serverinfo['tiponly'].upper() == "ALLCOIN":
            pass
        elif COIN_NAME not in tiponly_coins:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} not in allowed coins set by server manager.')
            return
        # End of checking allowed coins

    if is_maintenance_coin(COIN_NAME):
        await ctx.message.add_reaction(EMOJI_MAINTENANCE)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
        return

    if len(ctx.message.mentions) == 0 and len(ctx.message.role_mentions) == 0 and fromDM == False:
        # Use how time.
        if len(args) >= 2:
            time_given = None
            if args[0].upper() == "LAST" or args[1].upper() == "LAST":
                # try if the param is 1111u
                num_user = None
                if args[0].upper() == "LAST":
                    num_user = args[1].lower()
                elif args[1].upper() == "LAST":
                    num_user = args[2].lower()
                if 'u' in num_user or 'user' in num_user or 'users' in num_user or 'person' in num_user or 'people' in num_user:
                    num_user = num_user.replace("people", "")
                    num_user = num_user.replace("person", "")
                    num_user = num_user.replace("users", "")
                    num_user = num_user.replace("user", "")
                    num_user = num_user.replace("u", "")
                    try:
                        num_user = int(num_user)
                        if len(ctx.guild.members) <= 10:
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please use normal tip command. There are only few users.')
                            return
                        # Check if we really have that many user in the guild 20%
                        elif num_user >= len(ctx.guild.members):
                            try:
                                await ctx.message.add_reaction(EMOJI_INFORMATION)
                                await ctx.message.reply(f'{ctx.author.mention} Boss, you want to tip more than the number of people in this guild!?.'
                                                        ' Can be done :). Wait a while.... I am doing it. (**counting..**)')
                            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                # No need to tip if failed to message
                                await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                return
                            message_talker = await store.sql_get_messages(str(ctx.message.guild.id), str(ctx.message.channel.id), 0, len(ctx.guild.members))
                            if ctx.author.id in message_talker:
                                message_talker.remove(ctx.author.id)
                            if len(message_talker) == 0:
                                await ctx.message.add_reaction(EMOJI_ERROR)
                                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} There is not sufficient user to count.')
                            elif len(message_talker) < len(ctx.guild.members) - 1: # minus bot
                                await ctx.message.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} I could not find sufficient talkers up to **{num_user}**. I found only **{len(message_talker)}**'
                                                        f' and tip to those **{len(message_talker)}** users if they are still here.')
                                # tip all user who are in the list
                                try:
                                    async with ctx.typing():
                                        await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                    # zipped mouth but still need to do tip talker
                                    await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                                except Exception as e:
                                    await logchanbot(traceback.format_exc())
                            return
                        elif num_user > 0:
                            message_talker = await store.sql_get_messages(str(ctx.message.guild.id), str(ctx.message.channel.id), 0, num_user + 1)
                            if ctx.author.id in message_talker:
                                message_talker.remove(ctx.author.id)
                            else:
                                # remove the last one
                                message_talker.pop()
                            if len(message_talker) == 0:
                                await ctx.message.add_reaction(EMOJI_ERROR)
                                await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} There is not sufficient user to count.')
                            elif len(message_talker) < num_user:
                                try:
                                    await ctx.message.add_reaction(EMOJI_INFORMATION)
                                    await ctx.message.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} I could not find sufficient talkers up to **{num_user}**. I found only **{len(message_talker)}**'
                                                            f' and tip to those **{len(message_talker)}** users if they are still here.')
                                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                    # No need to tip if failed to message
                                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                    return
                                # tip all user who are in the list
                                try:
                                    async with ctx.typing():
                                        await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                    # zipped mouth but still need to do tip talker
                                    await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                                except Exception as e:
                                    await logchanbot(traceback.format_exc())
                            else:
                                try:
                                    async with ctx.typing():
                                        await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                    # zipped mouth but still need to do tip talker
                                    await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                                except Exception as e:
                                    await logchanbot(traceback.format_exc())
                                return
                            return
                        else:
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} What is this **{num_user}** number? Please give a number bigger than 0 :) ')
                            return
                    except ValueError:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid param after **LAST**.')
                    return
                time_string = ctx.message.content.lower().split("last", 1)[1].strip()
                time_second = None
                try:
                    time_string = time_string.replace("years", "y")
                    time_string = time_string.replace("yrs", "y")
                    time_string = time_string.replace("yr", "y")
                    time_string = time_string.replace("year", "y")
                    time_string = time_string.replace("months", "mon")
                    time_string = time_string.replace("month", "mon")
                    time_string = time_string.replace("mons", "mon")
                    time_string = time_string.replace("weeks", "w")
                    time_string = time_string.replace("week", "w")

                    time_string = time_string.replace("day", "d")
                    time_string = time_string.replace("days", "d")

                    time_string = time_string.replace("hours", "h")
                    time_string = time_string.replace("hour", "h")
                    time_string = time_string.replace("hrs", "h")
                    time_string = time_string.replace("hr", "h")

                    time_string = time_string.replace("minutes", "mn")
                    time_string = time_string.replace("mns", "mn")
                    time_string = time_string.replace("mins", "mn")
                    time_string = time_string.replace("min", "mn")
                    time_string = time_string.replace("m", "mn")

                    mult = {'y': 12*30*24*60*60, 'mon': 30*24*60*60, 'w': 7*24*60*60, 'd': 24*60*60, 'h': 60*60, 'mn': 60}
                    time_second = sum(int(num) * mult.get(val, 1) for num, val in re.findall('(\d+)(\w+)', time_string))
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                    await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid time given. Please use this example: `.tip 1,000 last 5h 12mn`')
                    return
                try:
                    time_given = int(time_second)
                except ValueError:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid time given check.')
                    return
                if time_given:
                    if time_given < 5*60 or time_given > 60*24*60*60:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Please try time interval between 5minutes to 24hours.')
                        return
                    else:
                        message_talker = await store.sql_get_messages(str(ctx.message.guild.id), str(ctx.message.channel.id), time_given, None)
                        if len(message_talker) == 0:
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} There is no active talker in such period.')
                            return
                        else:
                            try:
                                async with ctx.typing():
                                    await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                # zipped mouth but still need to do tip talker
                                await _tip_talker(ctx, amount, message_talker, False, COIN_NAME)
                            except Exception as e:
                                await logchanbot(traceback.format_exc())
                            return
            else:
                if len(args) == 2 and args[1].isdigit():
                    try:
                        member = bot.get_user(int(args[1]))
                        secrettip = True
                    except Exception as e:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        try:
                            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            try:
                                await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                return
                        return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    try:
                        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        try:
                            await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            return
                    return
        elif len(args) == 1 and args[0].isdigit():
            try:
                member = bot.get_user(int(args[0]))
                secrettip = True
            except Exception as e:
                await ctx.message.add_reaction(EMOJI_ERROR)
                try:
                    await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    try:
                        await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        return
                return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            try:
                await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                try:
                    await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    return
            return
    elif len(ctx.message.mentions) == 1 and (bot.user in ctx.message.mentions) and fromDM == False:
        # Tip to TipBot
        member = ctx.message.mentions[0]
    elif len(ctx.message.mentions) == 1 and (bot.user not in ctx.message.mentions) and fromDM == False:
        member = ctx.message.mentions[0]
        if ctx.author.id == member.id:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Tip me if you want.')
            return
        pass
    elif len(ctx.message.role_mentions) >= 1 and fromDM == False:
        mention_roles = ctx.message.role_mentions
        if "@everyone" in mention_roles:
            mention_roles.remove("@everyone")
            if len(mention_roles) < 1:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Can not find user to tip to.')
                return
        try:
            await _tip(ctx, amount, COIN_NAME)
        except Exception as e:
            await logchanbot(traceback.format_exc())
        return
    elif len(ctx.message.mentions) > 1 and fromDM == False:
        try:
            await _tip(ctx, amount, COIN_NAME)
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            pass
        except Exception as e:
            await logchanbot(traceback.format_exc())
        return


    # Check flood of tip
    floodTip = await store.sql_get_countLastTip(str(ctx.author.id), config.floodTipDuration)
    if floodTip >= config.floodTip:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Cool down your tip or TX. or increase your amount next time.')
        await botLogChan.send('A user reached max. TX threshold. Currently halted: `.tip`')
        return
    # End of Check flood of tip

    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}')
            return
    # End Check if maintenance

    notifyList = await store.sql_get_tipnotify()

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
        await logchanbot(traceback.format_exc())

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
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than '
                                f'{num_format_coin(MaxTX, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return
    elif real_amount > actual_balance:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to send tip of '
                                f'{num_format_coin(real_amount, COIN_NAME)} '
                                f'{COIN_NAME} to {member.name}#{member.discriminator}.')
        return
    elif real_amount < MinTx:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than '
                                f'{num_format_coin(MinTx, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return

    # add queue also tip
    if ctx.author.id not in TX_IN_PROCESS:
        TX_IN_PROCESS.append(ctx.author.id)
    else:
        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
        msg = await ctx.message.reply(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    tip = None
    try:
        if coin_family in ["TRTL", "BCN"]:
            tip = await store.sql_mv_cn_single(str(ctx.author.id), str(member.id), real_amount, 'TIP', COIN_NAME)
        elif coin_family == "XMR":
            tip = await store.sql_mv_xmr_single(str(ctx.author.id), str(member.id), real_amount, COIN_NAME, "TIP")
        elif coin_family == "XCH":
            tip = await store.sql_mv_xch_single(str(ctx.author.id), str(member.id), real_amount, COIN_NAME, "TIP")
        elif coin_family == "DOGE":
            tip = await store.sql_mv_doge_single(str(ctx.author.id), str(member.id), real_amount, COIN_NAME, "TIP")
        elif coin_family == "NANO":
            tip = await store.sql_mv_nano_single(str(ctx.author.id), str(member.id), real_amount, COIN_NAME, "TIP")
        elif coin_family == "ERC-20":
            tip = await store.sql_mv_erc_single(str(ctx.author.id), str(member.id), real_amount, COIN_NAME, "TIP", token_info['contract'])
        elif coin_family == "TRC-20":
            tip = await store.sql_mv_trx_single(str(ctx.author.id), str(member.id), real_amount, COIN_NAME, "TIP", token_info['contract'])
        if ctx.author.bot == False and fromDM == False and serverinfo['react_tip'] == "ON":
            await ctx.message.add_reaction(EMOJI_TIP)
    except Exception as e:
        await logchanbot(traceback.format_exc())

    # remove queue from tip
    if ctx.author.id in TX_IN_PROCESS:
        TX_IN_PROCESS.remove(ctx.author.id)

    if tip:
        # Update tipstat
        try:
            update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
            update_tipstat = await store.sql_user_get_tipstat(str(member.id), COIN_NAME, True, SERVER_BOT)
        except Exception as e:
            await logchanbot(traceback.format_exc())

        await ctx.message.add_reaction(get_emoji(COIN_NAME))
        # tipper shall always get DM. Ignore notifyList
        try:
            if fromDM == True:
                in_server = ""
            else:
                in_server = f" in server `{ctx.guild.name}`"
            await ctx.author.send(
                f'{EMOJI_ARROW_RIGHTHOOK} Tip of {num_format_coin(real_amount, COIN_NAME)} '
                f'{COIN_NAME} '
                f'was sent to {member.name}#{member.discriminator}{in_server}')
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            await store.sql_toggle_tipnotify(str(ctx.author.id), "OFF")
        if bot.user.id != member.id and str(member.id) not in notifyList:
            try:
                fromtipper = f"{ctx.author.name}#{ctx.author.discriminator}"
                if fromDM == True:
                    from_server = ""
                else:
                    from_server = f" in server `{ctx.guild.name}` #{ctx.channel.name}"
                if secrettip:
                    fromtipper = "someone"
                await member.send(
                    f'{EMOJI_MONEYFACE} You got a tip of {num_format_coin(real_amount, COIN_NAME)} '
                    f'{COIN_NAME} from {fromtipper}{from_server}\n'
                    f'{NOTIFICATION_OFF_CMD}\n')
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                await store.sql_toggle_tipnotify(str(member.id), "OFF")
        if secrettip:
            await botLogChan.send(f'{ctx.author.name} / {ctx.author.id} using a secret tip command {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}.')
        return
    else:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{ctx.author.mention} Can not deliver TX for {COIN_NAME} right now. Try again soon.')
        # add to failed tx table
        await store.sql_add_failed_tx(COIN_NAME, str(ctx.author.id), ctx.author.name, real_amount, "TIP")
        return


@bot.command(pass_context=True, aliases=['gtip', 'modtip', 'guildtip'])
@commands.has_permissions(manage_channels=True)
async def mtip(ctx, amount: str, *args):
    global TRTL_DISCORD, IS_RESTARTING, TX_IN_PROCESS
    # check if bot is going to restart
    if IS_RESTARTING:
        await ctx.message.add_reaction(EMOJI_REFRESH)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
        return
    # check if account locked
    account_lock = await alert_if_userlock(ctx, 'tip')
    if account_lock:
        await ctx.message.add_reaction(EMOJI_LOCKED) 
        await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
        return
    # end of check if account locked

    # disable guild tip for TRTL discord
    if ctx.guild and ctx.guild.id == TRTL_DISCORD:
        await ctx.message.add_reaction(EMOJI_LOCKED)
        return

    # Check if tx in progress
    if ctx.guild.id in TX_IN_PROCESS:
        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
        msg = await ctx.message.reply(f'{EMOJI_ERROR} {ctx.author.mention} This guild have another tx in progress.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    botLogChan = bot.get_channel(LOG_CHAN)
    amount = amount.replace(",", "")

    try:
        amount = Decimal(amount)
    except ValueError:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
        return

    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.message.reply(f'{EMOJI_RED_NO} This command can not be in private.')
        return

    serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
    COIN_NAME = None
    try:
        COIN_NAME = args[0].upper()
        if COIN_NAME in ENABLE_XMR+ENABLE_XCH+ENABLE_COIN_NANO:
            pass
        elif COIN_NAME not in ENABLE_COIN:
            if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                pass
            elif 'default_coin' in serverinfo:
                COIN_NAME = serverinfo['default_coin'].upper()
    except:
        if 'default_coin' in serverinfo:
            COIN_NAME = serverinfo['default_coin'].upper()
    print("COIN_NAME: " + COIN_NAME)

    # TRTL discord
    if ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
        return

    if not is_coin_tipable(COIN_NAME):
        msg = await ctx.message.reply(f'{EMOJI_ERROR} {ctx.author.mention} TIPPING is currently disable for {COIN_NAME}.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    if COIN_NAME in ENABLE_COIN_ERC:
        coin_family = "ERC-20"
        token_info = await store.get_token_info(COIN_NAME)
    elif COIN_NAME in ENABLE_COIN_TRC:
        coin_family = "TRC-20"
        token_info = await store.get_token_info(COIN_NAME)
    else:
        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
    # Check allowed coins
    tiponly_coins = serverinfo['tiponly'].split(",")
    if COIN_NAME == serverinfo['default_coin'].upper() or serverinfo['tiponly'].upper() == "ALLCOIN":
        pass
    elif COIN_NAME not in tiponly_coins:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} not in allowed coins set by server manager.')
        return
    # End of checking allowed coins

    if is_maintenance_coin(COIN_NAME):
        await ctx.message.add_reaction(EMOJI_MAINTENANCE)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
        return

    if len(ctx.message.mentions) == 0 and len(ctx.message.role_mentions) == 0:
        # Use how time.
        if len(args) >= 2:
            time_given = None
            if args[0].upper() == "LAST" or args[1].upper() == "LAST":
                # try if the param is 1111u
                num_user = None
                if args[0].upper() == "LAST":
                    num_user = args[1].lower()
                elif args[1].upper() == "LAST":
                    num_user = args[2].lower()
                if 'u' in num_user or 'user' in num_user or 'users' in num_user or 'person' in num_user or 'people' in num_user:
                    num_user = num_user.replace("people", "")
                    num_user = num_user.replace("person", "")
                    num_user = num_user.replace("users", "")
                    num_user = num_user.replace("user", "")
                    num_user = num_user.replace("u", "")
                    try:
                        num_user = int(num_user)
                        if len(ctx.guild.members) <= 10:
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please use normal tip command. There are only few users.')
                            return
                        # Check if we really have that many user in the guild 20%
                        elif num_user >= len(ctx.guild.members):
                            try:
                                await ctx.message.add_reaction(EMOJI_INFORMATION)
                                await ctx.message.reply(f'{ctx.author.mention} Boss, you want to tip more than the number of people in this guild!?.'
                                                        ' Can be done :). Wait a while.... I am doing it. (**counting..**)')
                            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                # No need to tip if failed to message
                                await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                return
                            message_talker = await store.sql_get_messages(str(ctx.message.guild.id), str(ctx.message.channel.id), 0, len(ctx.guild.members))
                            if ctx.author.id in message_talker:
                                message_talker.remove(ctx.author.id)
                            if len(message_talker) == 0:
                                await ctx.message.add_reaction(EMOJI_ERROR)
                                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} There is not sufficient user to count.')
                            elif len(message_talker) < len(ctx.guild.members) - 1: # minus bot
                                await ctx.message.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} I could not find sufficient talkers up to **{num_user}**. I found only **{len(message_talker)}**'
                                                        f' and tip to those **{len(message_talker)}** users if they are still here.')
                                # tip all user who are in the list
                                try:
                                    async with ctx.typing():
                                        await _tip_talker(ctx, amount, message_talker, True, COIN_NAME)
                                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                    # zipped mouth but still need to do tip talker
                                    await _tip_talker(ctx, amount, message_talker, True, COIN_NAME)
                                except Exception as e:
                                    await logchanbot(traceback.format_exc())
                            return
                        elif num_user > 0:
                            message_talker = await store.sql_get_messages(str(ctx.message.guild.id), str(ctx.message.channel.id), 0, num_user + 1)
                            if ctx.author.id in message_talker:
                                message_talker.remove(ctx.author.id)
                            else:
                                # remove the last one
                                message_talker.pop()
                            if len(message_talker) == 0:
                                await ctx.message.add_reaction(EMOJI_ERROR)
                                await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} There is not sufficient user to count.')
                            elif len(message_talker) < num_user:
                                try:
                                    await ctx.message.add_reaction(EMOJI_INFORMATION)
                                    await ctx.message.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} I could not find sufficient talkers up to **{num_user}**. I found only **{len(message_talker)}**'
                                                            f' and tip to those **{len(message_talker)}** users if they are still here.')
                                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                    # No need to tip if failed to message
                                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                    return
                                # tip all user who are in the list
                                try:
                                    async with ctx.typing():
                                        await _tip_talker(ctx, amount, message_talker, True, COIN_NAME)
                                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                    # zipped mouth but still need to do tip talker
                                    await _tip_talker(ctx, amount, message_talker, True, COIN_NAME)
                                except Exception as e:
                                    await logchanbot(traceback.format_exc())
                            else:
                                try:
                                    async with ctx.typing():
                                        await _tip_talker(ctx, amount, message_talker, True, COIN_NAME)
                                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                    # zipped mouth but still need to do tip talker
                                    await _tip_talker(ctx, amount, message_talker, True, COIN_NAME)
                                except Exception as e:
                                    await logchanbot(traceback.format_exc())
                                return
                            return
                        else:
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} What is this **{num_user}** number? Please give a number bigger than 0 :) ')
                            return
                    except ValueError:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid param after **LAST**.')
                    return
                time_string = ctx.message.content.lower().split("last", 1)[1].strip()
                time_second = None
                try:
                    time_string = time_string.replace("years", "y")
                    time_string = time_string.replace("yrs", "y")
                    time_string = time_string.replace("yr", "y")
                    time_string = time_string.replace("year", "y")
                    time_string = time_string.replace("months", "mon")
                    time_string = time_string.replace("month", "mon")
                    time_string = time_string.replace("mons", "mon")
                    time_string = time_string.replace("weeks", "w")
                    time_string = time_string.replace("week", "w")

                    time_string = time_string.replace("day", "d")
                    time_string = time_string.replace("days", "d")

                    time_string = time_string.replace("hours", "h")
                    time_string = time_string.replace("hour", "h")
                    time_string = time_string.replace("hrs", "h")
                    time_string = time_string.replace("hr", "h")

                    time_string = time_string.replace("minutes", "mn")
                    time_string = time_string.replace("mns", "mn")
                    time_string = time_string.replace("mins", "mn")
                    time_string = time_string.replace("min", "mn")
                    time_string = time_string.replace("m", "mn")

                    mult = {'y': 12*30*24*60*60, 'mon': 30*24*60*60, 'w': 7*24*60*60, 'd': 24*60*60, 'h': 60*60, 'mn': 60}
                    time_second = sum(int(num) * mult.get(val, 1) for num, val in re.findall('(\d+)(\w+)', time_string))
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                    await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid time given. Please use this example: `.tip 1,000 last 5h 12mn`')
                    return
                try:
                    time_given = int(time_second)
                except ValueError:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid time given check.')
                    return
                if time_given:
                    if time_given < 5*60 or time_given > 60*24*60*60:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Please try time interval between 5minutes to 24hours.')
                        return
                    else:
                        message_talker = await store.sql_get_messages(str(ctx.message.guild.id), str(ctx.message.channel.id), time_given, None)
                        if len(message_talker) == 0:
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} There is no active talker in such period.')
                            return
                        else:
                            try:
                                async with ctx.typing():
                                    await _tip_talker(ctx, amount, message_talker, True, COIN_NAME)
                            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                # zipped mouth but still need to do tip talker
                                await _tip_talker(ctx, amount, message_talker, True, COIN_NAME)
                            except Exception as e:
                                await logchanbot(traceback.format_exc())
                            return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                try:
                    await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    try:
                        await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        return
                return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            try:
                await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                try:
                    await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} You need at least one person to tip to.')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    return
            return
    elif len(ctx.message.mentions) == 1 and (bot.user in ctx.message.mentions):
        # Tip to TipBot
        member = ctx.message.mentions[0]
        print('TipBot is receiving tip from {} amount: {}{}'.format(ctx.author.name, amount, COIN_NAME))
    elif len(ctx.message.mentions) == 1 and (bot.user not in ctx.message.mentions):
        member = ctx.message.mentions[0]
        if ctx.author.id == member.id:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Tip me if you want.')
            return
    elif len(ctx.message.role_mentions) >= 1:
        mention_roles = ctx.message.role_mentions
        if "@everyone" in mention_roles:
            mention_roles.remove("@everyone")
            if len(mention_roles) < 1:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Can not find user to tip to.')
                return
        try:
            await _tip(ctx, amount, COIN_NAME, True)
        except Exception as e:
            await logchanbot(traceback.format_exc())
        return
    elif len(ctx.message.mentions) > 1:
        try:
            await _tip(ctx, amount, COIN_NAME, True)
        except Exception as e:
            await logchanbot(traceback.format_exc())
        return

    # Check flood of tip
    floodTip = await store.sql_get_countLastTip(str(ctx.guild.id), config.floodTipDuration)
    if floodTip >= config.floodTip:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Cool down your tip or TX. or increase your amount next time.')
        await botLogChan.send('A guild reached max. TX threshold. Currently halted: `.tip`')
        return
    # End of Check flood of tip

    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}')
            return
    # End Check if maintenance

    notifyList = await store.sql_get_tipnotify()
    address_to = None

    user_from = await store.sql_get_userwallet(str(ctx.guild.id), COIN_NAME)
    if user_from is None:
        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
            w = await create_address_eth()
            wallet = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0, w)
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
            result = await store.create_address_trx()
            wallet = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0, result)
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
            wallet = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0)

        user_from = await store.sql_register_user(str(ctx.guild.id), COIN_NAME, SERVER_BOT, 0)
    # get user balance
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

    user_to = await store.sql_get_userwallet(str(member.id), COIN_NAME)
    if user_to is None:
        if COIN_NAME in ENABLE_COIN_ERC:
            w = await create_address_eth()
            userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0, w)
        elif COIN_NAME in ENABLE_COIN_TRC:
            result = await store.create_address_trx()
            userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0, result)
        else:
            userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0)
        user_to = await store.sql_get_userwallet(str(member.id), COIN_NAME)
 
    real_amount = int(Decimal(amount) * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
    if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
        MinTx = token_info['real_min_tip']
        MaxTX = token_info['real_max_tip']
    else:
        MinTx = get_min_mv_amount(COIN_NAME)
        MaxTX = get_max_mv_amount(COIN_NAME)

    if real_amount > MaxTX:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than '
                                f'{num_format_coin(MaxTX, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return
    elif real_amount > actual_balance:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to send tip of '
                                f'{num_format_coin(real_amount, COIN_NAME)} '
                                f'{COIN_NAME} to {member.name}#{member.discriminator}.')
        return
    elif real_amount < MinTx:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than '
                                f'{num_format_coin(MinTx, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return

    tipmsg = ""
    try:
        if serverinfo['tip_message']: tipmsg = "**Guild Message:**\n" + serverinfo['tip_message']
    except Exception as e:
        pass

    tip = None
    try:
        if coin_family in ["TRTL", "BCN"]:
            tip = await store.sql_mv_cn_single(str(ctx.guild.id), str(member.id), real_amount, 'TIP', COIN_NAME)
        elif coin_family == "XMR":
            tip = await store.sql_mv_xmr_single(str(ctx.guild.id), str(member.id), real_amount, COIN_NAME, "TIP")
        elif coin_family == "XCH":
            tip = await store.sql_mv_xch_single(str(ctx.guild.id), str(member.id), real_amount, COIN_NAME, "TIP")
        elif coin_family == "DOGE":
            tip = await store.sql_mv_doge_single(str(ctx.guild.id), str(member.id), real_amount, COIN_NAME, "TIP")
        elif coin_family == "NANO":
            tip = await store.sql_mv_nano_single(str(ctx.guild.id), str(member.id), real_amount, COIN_NAME, "TIP")
        elif coin_family == "ERC-20":
            token_info = await store.get_token_info(COIN_NAME)
            tip = await store.sql_mv_erc_single(str(ctx.guild.id), str(member.id), real_amount, COIN_NAME, "TIP", token_info['contract'])
        elif coin_family == "TRC-20":
            token_info = await store.get_token_info(COIN_NAME)
            tip = await store.sql_mv_trx_single(str(ctx.guild.id), str(member.id), real_amount, COIN_NAME, "TIP", token_info['contract'])
        if ctx.author.bot == False and serverinfo['react_tip'] == "ON":
            await ctx.message.add_reaction(EMOJI_TIP)
    except Exception as e:
        await logchanbot(traceback.format_exc())
    if tip:
        # Update tipstat
        try:
            update_tipstat = await store.sql_user_get_tipstat(str(ctx.guild.id), COIN_NAME, True, SERVER_BOT)
            update_tipstat = await store.sql_user_get_tipstat(str(member.id), COIN_NAME, True, SERVER_BOT)
        except Exception as e:
            await logchanbot(traceback.format_exc())

        if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            await ctx.message.add_reaction(TOKEN_EMOJI)
        else:
            await ctx.message.add_reaction(get_emoji(COIN_NAME))
        # tipper shall always get DM. Ignore notifyList
        try:
            await ctx.author.send(
                f'{EMOJI_ARROW_RIGHTHOOK} Guild tip of {num_format_coin(real_amount, COIN_NAME)} '
                f'{COIN_NAME} '
                f'was sent to {member.name}#{member.discriminator} in server `{ctx.guild.name}`\n')
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            await store.sql_toggle_tipnotify(str(ctx.author.id), "OFF")
        if bot.user.id != member.id and str(member.id) not in notifyList:
            try:
                await member.send(
                    f'{EMOJI_MONEYFACE} You got a guild tip of {num_format_coin(real_amount, COIN_NAME)} '
                    f'{COIN_NAME} from {ctx.author.name}#{ctx.author.discriminator} in server `{ctx.guild.name}` #{ctx.channel.name}\n'
                    f'{NOTIFICATION_OFF_CMD}\n{tipmsg}')
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                await store.sql_toggle_tipnotify(str(member.id), "OFF")
        return
    else:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{ctx.author.mention} Can not deliver TX for {COIN_NAME} right now. Try again soon.')
        # add to failed tx table
        await store.sql_add_failed_tx(COIN_NAME, str(ctx.author.id), ctx.author.name, real_amount, "TIP")
        return


@bot.command(pass_context=True, name='tipall', aliases=['share'], help=bot_help_tipall, hidden = True)
async def tipall(ctx, amount: str, coin: str, option: str=None):
    global IS_RESTARTING, TX_IN_PROCESS
    # check if bot is going to restart
    if IS_RESTARTING:
        await ctx.message.add_reaction(EMOJI_REFRESH)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
        return
    # check if account locked
    account_lock = await alert_if_userlock(ctx, 'tipall')
    if account_lock:
        await ctx.message.add_reaction(EMOJI_LOCKED) 
        await ctx.message.reply(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
        return
    # end of check if account locked

    # Check if tx in progress
    if ctx.author.id in TX_IN_PROCESS:
        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
        msg = await ctx.message.reply(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    botLogChan = bot.get_channel(LOG_CHAN)
    amount = amount.replace(",", "")

    try:
        amount = Decimal(amount)
    except ValueError:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
        return

    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.message.reply(f'{EMOJI_RED_NO} This command can not be in private.')
        return

    COIN_NAME = coin.upper()

    # TRTL discord
    if ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
        return

    if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**!')
        return

    serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
    if COIN_NAME in ENABLE_COIN_ERC:
        coin_family = "ERC-20"
    elif COIN_NAME in ENABLE_COIN_TRC:
        coin_family = "TRC-20"
    else:
        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")

    option = option.upper() if option else "ONLINE"
    option_list = ["ALL", "ONLINE"]
    if option not in option_list:
        allow_option = ", ".join(option_list)
        await ctx.message.add_reaction(EMOJI_ERROR)
        msg = await ctx.message.reply(f'{EMOJI_ERROR} {ctx.author.mention} TIPALL is currently support only option **{allow_option}**.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return
    print('TIPALL COIN_NAME:' + COIN_NAME)
    if not is_coin_tipable(COIN_NAME):
        msg = await ctx.message.reply(f'{EMOJI_ERROR} {ctx.author.mention} TIPPING is currently disable for {COIN_NAME}.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return
    if is_maintenance_coin(COIN_NAME):
        await ctx.message.add_reaction(EMOJI_MAINTENANCE)
        await ctx.send(f'{EMOJI_RED_NO} {COIN_NAME} in maintenance.')
        return

    # Check allowed coins
    tiponly_coins = serverinfo['tiponly'].split(",")
    if COIN_NAME == serverinfo['default_coin'].upper() or serverinfo['tiponly'].upper() == "ALLCOIN":
        pass
    elif COIN_NAME not in tiponly_coins:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} not in allowed coins set by server manager.')
        return
    # End of checking allowed coins

    # Check flood of tip
    floodTip = await store.sql_get_countLastTip(str(ctx.author.id), config.floodTipDuration)
    if floodTip >= config.floodTip:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Cool down your tip or TX. or increase your amount next time.')
        await botLogChan.send('A user reached max. TX threshold. Currently halted: `.tipall`')
        return
    # End of Check flood of tip

    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    notifyList = await store.sql_get_tipnotify()
    if coin_family == "ERC-20" or coin_family == "TRC-20":
        real_amount = float(amount)
        token_info = await store.get_token_info(COIN_NAME)
        MinTx = token_info['real_min_tip']
        MaxTX = token_info['real_max_tip']
    else:
        real_amount = int(Decimal(amount) * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
        MinTx = get_min_mv_amount(COIN_NAME)
        MaxTX = get_max_mv_amount(COIN_NAME)

    # [x.guild for x in [g.members for g in bot.guilds] if x.id = useridyourelookingfor]
    if option == "ONLINE":
        listMembers = [member for member in ctx.guild.members if member.status != discord.Status.offline and member.bot == False]
    elif option == "ALL":
        listMembers = [member for member in ctx.guild.members if member.bot == False]
    print("Number of tip-all in {}: {}".format(ctx.guild.name, len(listMembers)))
    # Check number of receivers.
    if len(listMembers) > config.tipallMax_Offchain:
        await ctx.message.add_reaction(EMOJI_ERROR)
        try:
            await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} The number of receivers are too many. This command isn\'t available here.')
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            await ctx.author.send(f'{EMOJI_RED_NO} The number of receivers are too many in `{ctx.guild.name}`. This command isn\'t available here.')
        return
    # End of checking receivers numbers.
    await logchanbot("{}#{} issuing TIPALL {}{} in {}/{} with {} users.".format(ctx.author.name, ctx.author.discriminator, 
                                                                                num_format_coin(real_amount, COIN_NAME), COIN_NAME,
                                                                                ctx.guild.id, ctx.guild.name, len(listMembers)))
    list_receivers = []
    addresses = []
    for member in listMembers:
        # print(member.name) # you'll just print out Member objects your way.
        if ctx.author.id != member.id and member.id != bot.user.id:
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
            list_receivers.append(str(member.id))

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

    # get user balance
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
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to spread tip of '
                                f'{num_format_coin(real_amount, COIN_NAME)} '
                                f'{COIN_NAME}.')
        return
    elif (real_amount / len(list_receivers)) < MinTx:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than '
                                f'{num_format_coin(MinTx, COIN_NAME)} '
                                f'{COIN_NAME} for each member. You need at least {num_format_coin(len(list_receivers) * MinTx, COIN_NAME)} {COIN_NAME}.')
        return

    amountDiv = int(round(real_amount / len(list_receivers), 2))  # cut 2 decimal only
    if coin_family == "DOGE" or coin_family == "ERC-20" or coin_family == "TRC-20":
        amountDiv = round(real_amount / len(list_receivers), 4)
        if (real_amount / len(list_receivers)) < MinTx:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than '
                           f'{num_format_coin(MinTx, COIN_NAME)} '
                           f'{COIN_NAME} for each member. You need at least {num_format_coin(len(list_receivers) * MinTx, COIN_NAME)} {COIN_NAME}.')
            return

    if len(list_receivers) < 1:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} There is no one to tip to.')
        return

    # add queue also tipall
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
            tip = await store.sql_mv_cn_multiple(str(ctx.author.id), amountDiv, list_receivers, 'TIPALL', COIN_NAME)
        elif coin_family == "XMR":
            tip = await store.sql_mv_xmr_multiple(str(ctx.author.id), list_receivers, amountDiv, COIN_NAME, "TIPALL")
        elif coin_family == "XCH":
            tip = await store.sql_mv_xch_multiple(str(ctx.author.id), list_receivers, amountDiv, COIN_NAME, "TIPALL")
        elif coin_family == "NANO":
            tip = await store.sql_mv_nano_multiple(str(ctx.author.id), list_receivers, amountDiv, COIN_NAME, "TIPALL")
        elif coin_family == "DOGE":
            tip = await store.sql_mv_doge_multiple(str(ctx.author.id), list_receivers, amountDiv, COIN_NAME, "TIPALL")
        elif coin_family == "ERC-20":
            tip = await store.sql_mv_erc_multiple(str(ctx.author.id), list_receivers, amountDiv, COIN_NAME, "TIPALL", token_info['contract'])
        elif coin_family == "TRC-20":
            tip = await store.sql_mv_trx_multiple(str(ctx.author.id), list_receivers, amountDiv, COIN_NAME, "TIPALL", token_info['contract'])
    except Exception as e:
        await logchanbot(traceback.format_exc())
    await asyncio.sleep(config.interval.tx_lap_each)

    # remove queue from tipall
    if ctx.author.id in TX_IN_PROCESS:
        TX_IN_PROCESS.remove(ctx.author.id)

    if tip:
        # Update tipstat
        try:
            update_tipstat = await store.sql_user_get_tipstat(str(ctx.author.id), COIN_NAME, True, SERVER_BOT)
        except Exception as e:
            await logchanbot(traceback.format_exc())
        tipAmount = num_format_coin(real_amount, COIN_NAME)
        ActualSpend_str = num_format_coin(amountDiv * len(list_receivers), COIN_NAME)
        amountDiv_str = num_format_coin(amountDiv, COIN_NAME)
        await ctx.message.add_reaction(get_emoji(COIN_NAME))
        numMsg = 0
        total_found = 0
        max_mention = 40
        numb_mention = 0
        if len(listMembers) < max_mention:
            # DM all user
            for member in listMembers:
                if ctx.author.id != member.id and member.id != bot.user.id:
                    total_found += 1
                    if str(member.id) not in notifyList:
                        # random user to DM
                        # dm_user = bool(random.getrandbits(1)) if len(listMembers) > config.tipallMax_LimitDM else True
                        try:
                            await member.send(
                                f'{EMOJI_MONEYFACE} You got a tip of {amountDiv_str} '
                                f'{COIN_NAME} from {ctx.author.name}#{ctx.author.discriminator} `.tipall` in server `{ctx.guild.name}` #{ctx.channel.name}\n'
                                f'{NOTIFICATION_OFF_CMD}')
                            numMsg += 1
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            await store.sql_toggle_tipnotify(str(member.id), "OFF")
        else:
            # mention all user
            send_tipped_ping = 0
            list_user_mention = []
            list_user_mention_str = ""
            list_user_not_mention = []
            list_user_not_mention_str = ""
            random.shuffle(listMembers)
            for member in listMembers:
                if send_tipped_ping >= config.maxTipMessage:
                    total_found += 1
                else:
                    if ctx.author.id != member.id and member.id != bot.user.id:
                        if str(member.id) not in notifyList:
                            list_user_mention.append("{}".format(member.mention))
                        else:
                            list_user_not_mention.append("{}#{}".format(member.name, member.discriminator))
                    total_found += 1
                    numb_mention += 1

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
                                    f'{EMOJI_MONEYFACE} {list_user_mention_str} {list_user_not_mention_str}, You got a tip of {amountDiv_str} {COIN_NAME} '
                                    f'from {ctx.author.name}#{ctx.author.discriminator}'
                                    f'{NOTIFICATION_OFF_CMD}')
                                send_tipped_ping += 1
                        except Exception as e:
                            pass
                        # reset
                        list_user_mention = []
                        list_user_mention_str = ""
                        list_user_not_mention = []
                        list_user_not_mention_str = ""
            # if there is still here
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
                            f'{EMOJI_MONEYFACE} {list_user_mention_str} {list_user_not_mention_str} {remaining_str}, You got a tip of {amountDiv_str} '
                            f'{COIN_NAME} from {ctx.author.name}#{ctx.author.discriminator}'
                            f'{NOTIFICATION_OFF_CMD}')
                except Exception as e:
                    try:
                        await ctx.message.reply(f'**({total_found})** members got {amountDiv_str} {COIN_NAME} :) Too many to mention :) Phew!!!')
                    except Exception as e:
                        await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
        # tipper shall always get DM. Ignore notifyList
        try:
            await ctx.author.send(
                f'{EMOJI_ARROW_RIGHTHOOK} Tip of {tipAmount} '
                f'{COIN_NAME} '
                f'was sent spread to ({total_found}) members in server `{ctx.guild.name}`.\n'
                f'Each member got: `{amountDiv_str} {COIN_NAME}`\n'
                f'Actual spending: `{ActualSpend_str} {COIN_NAME}`')
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            await store.sql_toggle_tipnotify(str(ctx.author.id), "OFF")
        return


@bot.command(pass_context=True, help=bot_help_send)
async def send(ctx, amount: str, CoinAddress: str, coin: str=None):
    global TX_IN_PROCESS, IS_RESTARTING
    # check if bot is going to restart
    if IS_RESTARTING:
        await ctx.message.add_reaction(EMOJI_REFRESH)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
        return
    # check if account locked
    account_lock = await alert_if_userlock(ctx, 'send')
    if account_lock:
        await ctx.message.add_reaction(EMOJI_LOCKED) 
        await ctx.send(f'{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}')
        return
    # end of check if account locked

    botLogChan = bot.get_channel(LOG_CHAN)
    amount = amount.replace(",", "")

    # Check if tx in progress
    if ctx.author.id in TX_IN_PROCESS:
        await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    # if public and there is a bot channel
    if isinstance(ctx.channel, discord.DMChannel) == False:
        serverinfo = await get_info_pref_coin(ctx)
        server_prefix = serverinfo['server_prefix']
        # check if bot channel is set:
        if serverinfo and serverinfo['botchan']:
            try: 
                if ctx.channel.id != int(serverinfo['botchan']):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    botChan = bot.get_channel(int(serverinfo['botchan']))
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, {botChan.mention} is the bot channel!!!')
                    return
            except ValueError:
                pass
        # end of bot channel check

    # Check flood of tip
    floodTip = await store.sql_get_countLastTip(str(ctx.author.id), config.floodTipDuration)
    if floodTip >= config.floodTip:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO}{ctx.author.mention} Cool down your tip or TX. or increase your amount next time.')
        await botLogChan.send('A user reached max. TX threshold. Currently halted: `.send`')
        return
    # End of Check flood of tip

    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    try:
        amount = Decimal(amount)
    except ValueError:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
        return

    # Check which coinname is it.
    COIN_NAME = get_cn_coin_from_address(CoinAddress)
    if COIN_NAME is None and CoinAddress.startswith("0x"):
        if coin is None:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} you need to add **TOKEN NAME** after address.')
            return
        else:
            COIN_NAME = coin.upper()
            if COIN_NAME not in ENABLE_COIN_ERC:
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Unsupported Token.')
                return
        if CoinAddress.upper().startswith("0X00000000000000000000000000000"):
            await ctx.message.add_reaction(EMOJI_ERROR)
            msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token address:\n'
                                 f'`{CoinAddress}`')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        else:
            try:
                valid_address = await store.erc_validate_address(CoinAddress, COIN_NAME)
                if valid_address and valid_address.upper() == CoinAddress.upper():
                    valid = True
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token address:\n'
                                         f'`{CoinAddress}`')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
            except Exception as e:
                print(traceback.format_exc())
                await logchanbot(traceback.format_exc())
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} internal error checking address:\n'
                                     f'`{CoinAddress}`')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
    elif COIN_NAME is None:
        if coin is None:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} you need to add **COIN NAME** after address.')
            return
        else:
            COIN_NAME = coin.upper()
            if COIN_NAME not in ENABLE_COIN_DOGE:
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Unsupported coin **{COIN_NAME}**.')
                return
    elif COIN_NAME == "TRON_TOKEN":
        if coin is None:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} you need to add **COIN NAME** after address.')
            return
        else:
            COIN_NAME = coin.upper()
            if COIN_NAME not in ENABLE_COIN_TRC:
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Unsupported token **{COIN_NAME}**.')
                return

    coin_family = None
    if not is_coin_txable(COIN_NAME):
        msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} TX is currently disable for {COIN_NAME}.')
        await msg.add_reaction(EMOJI_OK_BOX)
        await logchanbot(f'User {ctx.author.id} tried to send {amount} {COIN_NAME} while it tx not enable.')
        return
    if COIN_NAME:
        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
    else:
        await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
        try:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} could not find what address it is.')
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            try:
                await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} could not find what address it is.')
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                return
        return

    # add redis action
    random_string = str(uuid.uuid4())
    await add_tx_action_redis(json.dumps([random_string, "SEND", str(ctx.author.id), ctx.author.name, float("%.3f" % time.time()), ctx.message.content, SERVER_BOT, "START"]), False)

    if coin_family in ["TRTL", "BCN"]:
        MinTx = get_min_tx_amount(COIN_NAME)
        MaxTX = get_max_tx_amount(COIN_NAME)
        real_amount = int(amount * get_decimal(COIN_NAME))
        addressLength = get_addrlen(COIN_NAME)
        IntaddressLength = get_intaddrlen(COIN_NAME)
        NetFee = get_tx_node_fee(coin = COIN_NAME)
        if is_maintenance_coin(COIN_NAME):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            try:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                try:
                    await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    return
            return

        print('{} - {} - {}'.format(COIN_NAME, addressLength, IntaddressLength))
        if len(CoinAddress) == int(addressLength):
            valid_address = addressvalidation.validate_address_cn(CoinAddress, COIN_NAME)
            # print(valid_address)
            if valid_address != CoinAddress:
                valid_address = None

            if valid_address is None:
                await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
                try:
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                   f'`{CoinAddress}`')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    try:
                        await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                                      f'`{CoinAddress}`')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        return
                return
        elif len(CoinAddress) == int(IntaddressLength):
            valid_address = addressvalidation.validate_integrated_cn(CoinAddress, COIN_NAME)
            # print(valid_address)
            if valid_address == 'invalid':
                await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
                try:
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid integrated address:\n'
                                   f'`{CoinAddress}`')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    try:
                        await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid integrated address:\n'
                                                      f'`{CoinAddress}`')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        return
                return
            if len(valid_address) == 2:
                iCoinAddress = CoinAddress
                CoinAddress = valid_address['address']
                paymentid = valid_address['integrated_id']
        elif len(CoinAddress) == int(addressLength) + 64 + 1:
            valid_address = {}
            check_address = CoinAddress.split(".")
            if len(check_address) != 2:
                await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
                try:
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid {COIN_NAME} address + paymentid')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    try:
                        await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid {COIN_NAME} address + paymentid')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        return
                return
            else:
                valid_address_str = addressvalidation.validate_address_cn(check_address[0], COIN_NAME)
                paymentid = check_address[1].strip()
                if valid_address_str is None:
                    await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
                    try:
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                       f'`{check_address[0]}`')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        try:
                            await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                                          f'`{check_address[0]}`')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            return
                    return
                else:
                    valid_address['address'] = valid_address_str
            # Check payment ID
                if len(paymentid) == 64:
                    if not re.match(r'[a-zA-Z0-9]{64,}', paymentid.strip()):
                        await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
                        try:
                            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} PaymentID: `{paymentid}`\n'
                                            'Should be in 64 correct format.')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            try:
                                await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} PaymentID: `{paymentid}`\n'
                                                              'Should be in 64 correct format.')
                            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                                return
                        return
                    else:
                        CoinAddress = valid_address['address']
                        valid_address['paymentid'] = paymentid
                        iCoinAddress = addressvalidation.make_integrated_cn(valid_address['address'], COIN_NAME, paymentid)['integrated_address']
                        pass
                else:
                    await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
                    try:
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} PaymentID: `{paymentid}`\n'
                                        'Incorrect length')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        try:
                            await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} PaymentID: `{paymentid}`\n'
                                                         'Incorrect length')
                        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                            return
                    return
        else:
            await ctx.message.add_reaction(EMOJI_QUESTEXCLAIM)
            try:
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                               f'`{CoinAddress}`')
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                try:
                    await ctx.author.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                                  f'`{CoinAddress}`')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    return
            return

        user_from = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
        if user_from is None:
            user_from = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
        if user_from['balance_wallet_address'] == CoinAddress:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You can not send to your own deposit address.')
            return

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

        if real_amount + NetFee > actual_balance:
            extra_fee_txt = ''
            if NetFee > 0:
                extra_fee_txt = f'You need to leave a node/tx fee: {num_format_coin(NetFee, COIN_NAME)} {COIN_NAME}'
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to send tx of '
                           f'{num_format_coin(real_amount, COIN_NAME)} '
                           f'{COIN_NAME} to {CoinAddress}. {extra_fee_txt}')

            return

        if real_amount > MaxTX:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be bigger than '
                           f'{num_format_coin(MaxTX, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return
        elif real_amount < MinTx:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transactions cannot be smaller than '
                           f'{num_format_coin(MinTx, COIN_NAME)} '
                           f'{COIN_NAME}.')

            return

        # Get wallet status
        walletStatus = await daemonrpc_client.getWalletStatus(COIN_NAME)
        if walletStatus is None:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} I can not connect to wallet service or daemon.')
            return
        else:
            localDaemonBlockCount = int(walletStatus['blockCount'])
            networkBlockCount = int(walletStatus['knownBlockCount'])
            if networkBlockCount - localDaemonBlockCount >= 20:
                # if height is different by 20
                t_percent = '{:,.2f}'.format(truncate(localDaemonBlockCount / networkBlockCount * 100, 2))
                t_localDaemonBlockCount = '{:,}'.format(localDaemonBlockCount)
                t_networkBlockCount = '{:,}'.format(networkBlockCount)
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} Wallet service hasn\'t sync fully with network or being re-sync. More info:\n```'
                               f'networkBlockCount:     {t_networkBlockCount}\n'
                               f'localDaemonBlockCount: {t_localDaemonBlockCount}\n'
                               f'Progress %:            {t_percent}\n```'
                               )
                return
            else:
                pass
        # End of wallet status

        main_address = getattr(getattr(config,"daemon"+COIN_NAME),"MainAddress")
        if CoinAddress == main_address:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, Can not send to this address:\n```{CoinAddress}``` ')
            return
        
        if len(valid_address) == 2:
            tip = None
            try:
                check_in = await store.coin_check_balance_address_in_users(CoinAddress, COIN_NAME)
                if check_in:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, Can not send to this address:\n```{CoinAddress}``` ')
                    return
                if ctx.author.id not in TX_IN_PROCESS:
                    TX_IN_PROCESS.append(ctx.author.id)
                    try:
                        tip = await store.sql_external_cn_single_id(str(ctx.author.id), CoinAddress, real_amount, paymentid, COIN_NAME)
                        tip_tx_tipper = "Transaction hash: `{}`".format(tip['transactionHash'])
                        tip_tx_tipper += "\nA node/tx fee `{}{}` deducted from your balance.".format(num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                    await asyncio.sleep(config.interval.tx_lap_each)
                    TX_IN_PROCESS.remove(ctx.author.id)
                else:
                    await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
                    msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return                    
            except Exception as e:
                await logchanbot(traceback.format_exc())
            if tip:
                await ctx.message.add_reaction(get_emoji(COIN_NAME))
                await botLogChan.send(f'A user successfully executed `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}` with paymentid.')
                await ctx.author.send(
                                       f'{EMOJI_ARROW_RIGHTHOOK} You have sent {num_format_coin(real_amount, COIN_NAME)} '
                                       f'{COIN_NAME} '
                                       f'to `{iCoinAddress}`\n\n'
                                       f'Address: `{CoinAddress}`\n'
                                       f'Payment ID: `{paymentid}`\n'
                                       f'{tip_tx_tipper}')
                return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await botLogChan.send(f'A user failed to execute send `{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}` with paymentid.')
                msg = await ctx.send(f'{ctx.author.mention} Please try again or report.')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
        else:
            tip = None
            try:
                if ctx.author.id not in TX_IN_PROCESS:
                    TX_IN_PROCESS.append(ctx.author.id)
                    try:
                        tip = await store.sql_external_cn_single(str(ctx.author.id), CoinAddress, real_amount, COIN_NAME, SERVER_BOT, 'SEND')
                        tip_tx_tipper = "Transaction hash: `{}`".format(tip['transactionHash'])
                        # replace fee
                        tip['fee'] = get_tx_node_fee(COIN_NAME)
                        tip_tx_tipper += "\nTx Fee: `{}{}`".format(num_format_coin(tip['fee'], COIN_NAME), COIN_NAME)
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                    await asyncio.sleep(config.interval.tx_lap_each)
                    TX_IN_PROCESS.remove(ctx.author.id)
                    # add redis
                    await add_tx_action_redis(json.dumps([random_string, "SEND", str(ctx.author.id), ctx.author.name, float("%.3f" % time.time()), ctx.message.content, SERVER_BOT, "COMPLETE"]), False)
                else:
                    await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
                    msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
            except Exception as e:
                await logchanbot(traceback.format_exc())
            if tip:
                await ctx.message.add_reaction(get_emoji(COIN_NAME))
                await botLogChan.send(f'A user successfully executed `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                await ctx.author.send(f'{EMOJI_ARROW_RIGHTHOOK} You have sent {num_format_coin(real_amount, COIN_NAME)} '
                                              f'{COIN_NAME} '
                                              f'to `{CoinAddress}`\n'
                                              f'{tip_tx_tipper}')
                return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await botLogChan.send(f'A user failed to execute `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
                await ctx.send(f'{ctx.author.mention} Can not deliver TX for {COIN_NAME} right now. Try again soon.')
                # add to failed tx table
                await store.sql_add_failed_tx(COIN_NAME, str(ctx.author.id), ctx.author.name, real_amount, "SEND")
                return
    elif coin_family == "XMR" or coin_family == "XCH":
        MinTx = get_min_tx_amount(COIN_NAME)
        MaxTX = get_max_tx_amount(COIN_NAME)
        real_amount = int(amount * get_decimal(COIN_NAME))

        # If not Masari
        if COIN_NAME not in ["MSR", "UPX", "XCH", "XFX"]:
            valid_address = await validate_address_xmr(str(CoinAddress), COIN_NAME)
            if valid_address['valid'] == False or valid_address['nettype'] != 'mainnet':
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Address: `{CoinAddress}` '
                                   'is invalid.')
                    return
        elif coin_family == "XCH":
            valid_address = addressvalidation_xch.validate_address(CoinAddress, COIN_NAME)
            if valid_address == False:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Address: `{CoinAddress}` '
                               'is invalid.')
                return
        # OK valid address
        # TODO: validate XCH address
        user_from = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
        if user_from is None:
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

        # If balance 0, no need to check anything
        if actual_balance <= 0:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please check your **{COIN_NAME}** balance.')
            return
        NetFee = get_tx_node_fee(coin = COIN_NAME)
        # XMR
        # NetFee = await get_tx_fee_xmr(coin = COIN_NAME, amount = real_amount, to_address = CoinAddress)
        if real_amount + NetFee > actual_balance:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to send out '
                           f'{num_format_coin(real_amount, COIN_NAME)} '
                           f'{COIN_NAME}. You need to leave a node/tx fee: {num_format_coin(NetFee, COIN_NAME)} {COIN_NAME}')
            return
        if real_amount < MinTx:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transaction cannot be smaller than '
                           f'{num_format_coin(MinTx, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return
        if real_amount > MaxTX:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transaction cannot be bigger than '
                           f'{num_format_coin(MaxTX, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return

        SendTx = None
        check_in = await store.coin_check_balance_address_in_users(CoinAddress, COIN_NAME)
        if check_in:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, Can not send to this address:\n```{CoinAddress}``` ')
            return
        if ctx.author.id not in TX_IN_PROCESS:
            TX_IN_PROCESS.append(ctx.author.id)
            try:
                if coin_family == "XCH":
                    SendTx = await store.sql_external_xch_single(str(ctx.author.id), real_amount,
                                                                 CoinAddress, COIN_NAME, "SEND")
                    SendTx['tx_hash'] = SendTx['tx_hash']['name']
                else:
                    SendTx = await store.sql_external_xmr_single(str(ctx.author.id), real_amount,
                                                                 CoinAddress, COIN_NAME, "SEND", NetFee)
                # add redis
                await add_tx_action_redis(json.dumps([random_string, "SEND", str(ctx.author.id), ctx.author.name, float("%.3f" % time.time()), ctx.message.content, SERVER_BOT, "COMPLETE"]), False)
            except Exception as e:
                await logchanbot(traceback.format_exc())
            await asyncio.sleep(config.interval.tx_lap_each)
            TX_IN_PROCESS.remove(ctx.author.id)
        else:
            # reject and tell to wait
            msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You have another tx in process. Please wait it to finish. ')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        if SendTx:
            SendTx_hash = SendTx['tx_hash']
            extra_txt = "A node/tx fee `{} {}` deducted from your balance.".format(num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
            await ctx.message.add_reaction(get_emoji(COIN_NAME))
            await botLogChan.send(f'A user successfully executed `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
            await ctx.author.send(f'{EMOJI_ARROW_RIGHTHOOK} You have sent {num_format_coin(real_amount, COIN_NAME)} '
                                          f'{COIN_NAME} to `{CoinAddress}`.\n'
                                          f'Transaction hash: `{SendTx_hash}`\n'
                                          f'{extra_txt}')
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await botLogChan.send(f'A user failed to execute `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
            return
        return
    elif coin_family == "NANO":
        MinTx = get_min_tx_amount(COIN_NAME)
        MaxTX = get_max_tx_amount(COIN_NAME)
        real_amount = int(amount * get_decimal(COIN_NAME))
        addressLength = get_addrlen(COIN_NAME)

        # Validate address
        valid_address = await nano_validate_address(COIN_NAME, str(CoinAddress))
        if not valid_address == True:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}` is invalid.')
            return

        # OK valid address
        user_from = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
        if user_from is None:
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

        # If balance 0, no need to check anything
        if actual_balance <= 0:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Please check your **{COIN_NAME}** balance.')
            return

        if real_amount > actual_balance:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to send out '
                           f'{num_format_coin(real_amount, COIN_NAME)}')
            return
        if real_amount < MinTx:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transaction cannot be smaller than '
                           f'{num_format_coin(MinTx, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return
        if real_amount > MaxTX:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transaction cannot be bigger than '
                           f'{num_format_coin(MaxTX, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return

        SendTx = None
        check_in = await store.coin_check_balance_address_in_users(CoinAddress, COIN_NAME)
        if check_in:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, Can not send to this address:\n```{CoinAddress}``` ')
            return
        if ctx.author.id not in TX_IN_PROCESS:
            TX_IN_PROCESS.append(ctx.author.id)
            try:
                SendTx = await store.sql_external_nano_single(str(ctx.author.id), real_amount,
                                                              CoinAddress, COIN_NAME, "SEND")
                # add redis
                await add_tx_action_redis(json.dumps([random_string, "SEND", str(ctx.author.id), ctx.author.name, float("%.3f" % time.time()), ctx.message.content, SERVER_BOT, "COMPLETE"]), False)
            except Exception as e:
                await logchanbot(traceback.format_exc())
            await asyncio.sleep(config.interval.tx_lap_each)
            TX_IN_PROCESS.remove(ctx.author.id)
        else:
            # reject and tell to wait
            msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} You have another tx in process. Please wait it to finish. ')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        if SendTx:
            SendTx_hash = SendTx['block']
            await ctx.message.add_reaction(get_emoji(COIN_NAME))
            await botLogChan.send(f'A user successfully executed `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
            await ctx.author.send(f'{EMOJI_ARROW_RIGHTHOOK} You have sent {num_format_coin(real_amount, COIN_NAME)} '
                                          f'{COIN_NAME} to `{CoinAddress}`.\n'
                                          f'Transaction hash: `{SendTx_hash}`')
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await botLogChan.send(f'A user failed to execute `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
            return
        return
    if coin_family == "DOGE" or coin_family == "ERC-20" or coin_family == "TRC-20":
        if coin_family == "ERC-20" or coin_family == "TRC-20":
            token_info = await store.get_token_info(COIN_NAME)
            MinTx = token_info['real_min_tx']
            MaxTX = token_info['real_max_tx']
            NetFee = token_info['real_withdraw_fee']
        else:
            MinTx = get_min_tx_amount(coin = COIN_NAME)
            MaxTX = get_max_tx_amount(coin = COIN_NAME)
            NetFee = get_tx_node_fee(coin = COIN_NAME)
            valid_address = await doge_validaddress(str(CoinAddress), COIN_NAME)
            if 'isvalid' in valid_address:
                if str(valid_address['isvalid']) == "True":
                    pass
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Address: `{CoinAddress}` '
                                    'is invalid.')
                    return
        extra_fee_txt = f'You need to leave a node/tx fee: {num_format_coin(NetFee, COIN_NAME)} {COIN_NAME}'
        user_from = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
        if user_from is None:
            if coin_family == "ERC-20":
                w = await create_address_eth()
                userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, w)
            elif coin_family == "TRC-20":
                result = await store.create_address_trx()
                userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0, result)
            else:
                userregister = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)
        real_amount = float(amount)
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

        if real_amount + NetFee > actual_balance:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to send out '
                           f'{num_format_coin(real_amount, COIN_NAME)} '
                           f'{COIN_NAME}. {extra_fee_txt}')
            return
        if real_amount < MinTx:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transaction cannot be smaller than '
                           f'{num_format_coin(MinTx, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return
        if real_amount > MaxTX:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Transaction cannot be bigger than '
                           f'{num_format_coin(MaxTX, COIN_NAME)} '
                           f'{COIN_NAME}.')
            return
        SendTx = None
        check_in = await store.coin_check_balance_address_in_users(CoinAddress, COIN_NAME)
        if check_in:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, Can not send to this address:\n```{CoinAddress}``` ')
            return
        if ctx.author.id not in TX_IN_PROCESS:
            TX_IN_PROCESS.append(ctx.author.id)
            try:
                if COIN_NAME in ENABLE_COIN_ERC:
                    SendTx = await store.sql_external_erc_single(str(ctx.author.id), CoinAddress, real_amount, COIN_NAME, 'SEND', SERVER_BOT)
                elif COIN_NAME in ENABLE_COIN_TRC:
                    SendTx = await store.sql_external_trx_single(str(ctx.author.id), CoinAddress, real_amount, COIN_NAME, 'SEND', SERVER_BOT)
                else:
                    SendTx = await store.sql_external_doge_single(str(ctx.author.id), real_amount, NetFee,
                                                                  CoinAddress, COIN_NAME, "SEND")
                # add redis
                await add_tx_action_redis(json.dumps([random_string, "SEND", str(ctx.author.id), ctx.author.name, float("%.3f" % time.time()), ctx.message.content, SERVER_BOT, "COMPLETE"]), False)
            except Exception as e:
                await logchanbot(traceback.format_exc())
            await asyncio.sleep(config.interval.tx_lap_each)
            TX_IN_PROCESS.remove(ctx.author.id)
        else:
            await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
            msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        if SendTx:
            if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                extra_txt = f"A node/tx `{NetFee} {COIN_NAME}` deducted from your balance."
                await ctx.message.add_reaction(TOKEN_EMOJI)
            else:
                await ctx.message.add_reaction(get_emoji(COIN_NAME))
                extra_txt = "A node/tx fee `{} {}` deducted from your balance.".format(num_format_coin(get_tx_node_fee(COIN_NAME), COIN_NAME), COIN_NAME)
            await botLogChan.send(f'A user successfully executed `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
            await ctx.author.send(f'{EMOJI_ARROW_RIGHTHOOK} You have sent {num_format_coin(real_amount, COIN_NAME)} '
                                          f'{COIN_NAME} to `{CoinAddress}`.\n'
                                          f'Transaction hash: `{SendTx}`\n'
                                          f'{extra_txt}')
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await botLogChan.send(f'A user failed to execute `.send {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}`.')
            return
        return
    else:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                       f'`{CoinAddress}`')
        return


@bot.command(pass_context=True, name='address', aliases=['addr'], help=bot_help_address)
async def address(ctx, *args):
    prefix = await get_guild_prefix(ctx)

    # if public and there is a bot channel
    if isinstance(ctx.channel, discord.DMChannel) == False:
        serverinfo = await get_info_pref_coin(ctx)
        server_prefix = serverinfo['server_prefix']
        # check if bot channel is set:
        if serverinfo and serverinfo['botchan']:
            try: 
                if ctx.channel.id != int(serverinfo['botchan']):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    botChan = bot.get_channel(int(serverinfo['botchan']))
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, {botChan.mention} is the bot channel!!!')
                    return
            except ValueError:
                pass
        # end of bot channel check

    if len(args) == 0:
        if isinstance(ctx.message.channel, discord.DMChannel):
            COIN_NAME = 'WRKZ'
        else:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            try:
                COIN_NAME = args[0].upper()
                if COIN_NAME not in ENABLE_COIN:
                    if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                        pass
                    elif 'default_coin' in serverinfo:
                        COIN_NAME = serverinfo['default_coin'].upper()
                else:
                    pass
            except:
                if 'default_coin' in serverinfo:
                    COIN_NAME = serverinfo['default_coin'].upper()
            print("COIN_NAME: " + COIN_NAME)
        # TODO: change this.
        if COIN_NAME:
            main_address = getattr(getattr(config,"daemon"+COIN_NAME),"MainAddress")
            await ctx.send('**[ ADDRESS CHECKING EXAMPLES ]**\n\n'
                           f'```.address {main_address}\n'
                           'That will check if the address is valid. Integrated address is also supported. '
                           'If integrated address is input, bot will tell you the result of :address + paymentid\n\n'
                           f'{prefix}address <coin_address> <paymentid>\n'
                           'This will generate an integrate address.\n\n'
                           f'If you would like to get your address, please use {prefix}deposit {COIN_NAME} instead.```')
        else:
            await ctx.send('**[ ADDRESS CHECKING EXAMPLES ]**\n\n'
                           f'```.address coin_address\n'
                           'That will check if the address is valid. '
                           f'If you would like to get your address, please use {prefix}deposit {COIN_NAME} instead.```')
        return

    # Check if a user request address coin of another user
    # .addr COIN @mention
    if len(args) == 2 and len(ctx.message.mentions) == 1:
        COIN_NAME = None
        member = None
        try:
            COIN_NAME = args[0].upper()
            member = ctx.message.mentions[0]
            if COIN_NAME not in (ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_COIN_NANO+ENABLE_XMR+ENABLE_COIN_ERC+ENABLE_COIN_TRC):
                COIN_NAME = None
        except Exception as e:
            pass

        if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER**!')
            return

        if not is_coin_depositable(COIN_NAME):
            msg = await ctx.send(f'{EMOJI_ERROR} {ctx.author.mention} DEPOSITING is currently disable for {COIN_NAME}.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

        if COIN_NAME and member and isinstance(ctx.channel, discord.DMChannel) == False and member.bot == False:
            # OK there is COIN_NAME and member
            if member.id == ctx.author.id:
                await ctx.message.add_reaction(EMOJI_ERROR)
                return
            msg = await ctx.send(f'**ADDRESS REQ {COIN_NAME} **: {member.mention}, {str(ctx.author)} would like to get your address.')
            await msg.add_reaction(EMOJI_CHECKMARK)
            await msg.add_reaction(EMOJI_ZIPPED_MOUTH)
            def check(reaction, user):
                return user == member and reaction.message.author == bot.user and reaction.message.id == msg.id and str(reaction.emoji) \
                in (EMOJI_CHECKMARK, EMOJI_ZIPPED_MOUTH)
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=120, check=check)
            except asyncio.TimeoutError:
                await ctx.send(f'{ctx.author.mention} address requested timeout (120s) from {str(member.mention)}.')
                try:
                    await msg.delete()
                except Exception as e:
                    pass
                return
                
            if str(reaction.emoji) == EMOJI_CHECKMARK:
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                wallet = await store.sql_get_userwallet(str(member.id), COIN_NAME)
                if wallet is None:
                    if COIN_NAME in ENABLE_COIN_ERC:
                        w = await create_address_eth()
                        userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0, w)
                    elif COIN_NAME in ENABLE_COIN_TRC:
                        result = await store.create_address_trx()
                        userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0, result)
                    else:
                        userregister = await store.sql_register_user(str(member.id), COIN_NAME, SERVER_BOT, 0)
                    wallet = await store.sql_get_userwallet(str(member.id), COIN_NAME)
                user_address = wallet['balance_wallet_address']
                msg = await ctx.send(f'{ctx.author.mention} Here is the deposit **{COIN_NAME}** of {member.mention}:```{user_address}```')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            elif str(reaction.emoji) == EMOJI_ZIPPED_MOUTH:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{ctx.author.mention} your address request is rejected.')
                return

    CoinAddress = args[0]
    COIN_NAME = None

    if not re.match(r'^[A-Za-z0-9_]+$', CoinAddress):
        msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                             f'`{CoinAddress}`')
        await msg.add_reaction(EMOJI_OK_BOX)
        return
    # Check which coinname is it.
    COIN_NAME = get_cn_coin_from_address(CoinAddress)

    if COIN_NAME:
        if COIN_NAME == "TRON_TOKEN":
            validate_address = await store.trx_validate_address(CoinAddress)
            if validate_address:
                await ctx.message.add_reaction(EMOJI_CHECK)
                msg = await ctx.send(f'Token address: `{CoinAddress}`\n'
                                     'Checked: Valid.')
                await msg.add_reaction(EMOJI_OK_BOX)
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token address:\n'
                                     f'`{CoinAddress}`')
                await msg.add_reaction(EMOJI_OK_BOX)
            return
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
    else:
        if CoinAddress.startswith("0x"):
            if CoinAddress.upper().startswith("0X00000000000000000000000000000"):
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token:\n'
                                     f'`{CoinAddress}`')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            else:
                valid_address = await store.erc_validate_address(CoinAddress, "XMOON") # placeholder
                if valid_address and valid_address.upper() == CoinAddress.upper():
                    await ctx.message.add_reaction(EMOJI_CHECK)
                    msg = await ctx.send(f'Token address: `{CoinAddress}`\n'
                                         'Checked: Valid.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid token address:\n'
                                         f'`{CoinAddress}`')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid address:\n'
                                f'`{CoinAddress}`')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

    addressLength = get_addrlen(COIN_NAME)
    if coin_family in [ "BCN", "TRTL", "XMR"]:
        IntaddressLength = get_intaddrlen(COIN_NAME)

    if len(args) == 1:
        if coin_family == "DOGE":
            valid_address = await doge_validaddress(str(CoinAddress), COIN_NAME)
            if 'isvalid' in valid_address:
                if str(valid_address['isvalid']) == "True":
                    await ctx.message.add_reaction(EMOJI_CHECK)
                    msg = await ctx.send(f'Address: `{CoinAddress}`\n'
                                         f'Checked: Valid {COIN_NAME}.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    msg = await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                         'Checked: Invalid.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                    'Checked: Invalid.')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
        if coin_family == "NANO":
            valid_address = await nano_validate_address(COIN_NAME, str(CoinAddress))
            if valid_address == True:
                await ctx.message.add_reaction(EMOJI_CHECK)
                msg = await ctx.send(f'Address: `{CoinAddress}`\n'
                                     f'Checked: Valid {COIN_NAME}.')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                     'Checked: Invalid.')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
        elif COIN_NAME == "LTC":
            valid_address = await doge_validaddress(str(CoinAddress), COIN_NAME)
            if 'isvalid' in valid_address:
                if str(valid_address['isvalid']) == "True":
                    await ctx.message.add_reaction(EMOJI_CHECK)
                    msg = await ctx.send(f'Address: `{CoinAddress}`\n'
                                         f'Checked: Valid {COIN_NAME}.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    msg = await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                         'Checked: Invalid.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                'Checked: Invalid.')
                return
        elif COIN_NAME == "KVA":
            valid_address = await doge_validaddress(str(CoinAddress), COIN_NAME)
            if 'isvalid' in valid_address:
                if str(valid_address['isvalid']) == "True":
                    await ctx.message.add_reaction(EMOJI_CHECK)
                    msg = await ctx.send(f'Address: `{CoinAddress}`\n'
                                         f'Checked: Valid {COIN_NAME}.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    msg = await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                         'Checked: Invalid.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                'Checked: Invalid.')
                return
        elif COIN_NAME == "PGO":
            valid_address = await doge_validaddress(str(CoinAddress), COIN_NAME)
            if 'isvalid' in valid_address:
                if str(valid_address['isvalid']) == "True":
                    await ctx.message.add_reaction(EMOJI_CHECK)
                    msg = await ctx.send(f'Address: `{CoinAddress}`\n'
                                         f'Checked: Valid {COIN_NAME}.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    msg = await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                         'Checked: Invalid.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                    'Checked: Invalid.')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
        elif COIN_NAME in ENABLE_XMR:
            if COIN_NAME == "MSR":
                addr = None
                if len(CoinAddress) == 95:
                    try:
                        addr = address_msr(CoinAddress)
                    except Exception as e:
                        # await logchanbot(traceback.format_exc())
                        pass
                elif len(CoinAddress) == 106:
                    addr = None
                    try:
                        addr = address_msr(CoinAddress)
                    except Exception as e:
                        # await logchanbot(traceback.format_exc())
                        pass
                if addr == CoinAddress:
                    address_result = 'Valid: `{}`\n'.format(addr)                    
                    if type(addr).__name__ == "Address":
                        address_result += 'Main Address: `{}`\n'.format('True')
                    else:
                        address_result += 'Main Address: `{}`\n'.format('False')
                    if type(addr).__name__ == "IntegratedAddress":
                        address_result += 'Integrated: `{}`\n'.format('True')
                    else:
                        address_result += 'Integrated: `{}`\n'.format('False')
                    if type(addr).__name__ == "SubAddress":
                        address_result += 'Subaddress: `{}`\n'.format('True')
                    else:
                        address_result += 'Subaddress: `{}`\n'.format('False')
                    await ctx.message.add_reaction(EMOJI_CHECK)
                    await ctx.send(f'{EMOJI_CHECK} Address: `{CoinAddress}`\n{address_result}')
                    return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                    'Checked: Invalid.')
                    return
            elif COIN_NAME == "UPX":	
                addr = None	
                if len(CoinAddress) == 98 or len(CoinAddress) == 97:	
                    try:	
                        addr = address_upx(CoinAddress)	
                    except Exception as e:	
                        traceback.print_exc(file=sys.stdout)	
                        pass	
                elif len(CoinAddress) == 109:	
                    addr = None	
                    try:	
                        addr = address_upx(CoinAddress)	
                    except Exception as e:	
                        traceback.print_exc(file=sys.stdout)	
                        pass	
                if addr == CoinAddress:	
                    address_result = 'Valid: `{}`\n'.format(addr)                    	
                    if type(addr).__name__ == "Address":	
                        address_result += 'Main Address: `{}`\n'.format('True')	
                    else:	
                        address_result += 'Main Address: `{}`\n'.format('False')	
                    if type(addr).__name__ == "IntegratedAddress":	
                        address_result += 'Integrated: `{}`\n'.format('True')	
                    else:	
                        address_result += 'Integrated: `{}`\n'.format('False')	
                    if type(addr).__name__ == "SubAddress":	
                        address_result += 'Subaddress: `{}`\n'.format('True')	
                    else:	
                        address_result += 'Subaddress: `{}`\n'.format('False')	
                    await ctx.message.add_reaction(EMOJI_CHECK)	
                    await ctx.send(f'{EMOJI_CHECK} Address: `{CoinAddress}`\n{address_result}')	
                    return	
                else:	
                    await ctx.message.add_reaction(EMOJI_ERROR)	
                    await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'	
                                    'Checked: Invalid.')	
                    return
            else:
                valid_address = None
                try:
                    valid_address = await validate_address_xmr(str(CoinAddress), COIN_NAME)
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
                if valid_address is None or valid_address['valid'] == False:
                    await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                    'Checked: Invalid.')
                    return
                elif valid_address['valid'] == True:
                    address_result = 'Valid: `{}`\n'.format(str(valid_address['valid'])) + \
                                   'Integrated: `{}`\n'.format(str(valid_address['integrated'])) + \
                                   'Net Type: `{}`\n'.format(str(valid_address['nettype'])) + \
                                   'Subaddress: `{}`\n'.format(str(valid_address['subaddress']))
                    await ctx.message.add_reaction(EMOJI_CHECK)
                    await ctx.send(f'{EMOJI_CHECK} Address: `{CoinAddress}`\n{address_result}')
                    return

        if len(CoinAddress) == int(addressLength):
            valid_address = addressvalidation.validate_address_cn(CoinAddress, COIN_NAME)
            print(valid_address)
            if valid_address is None:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                'Checked: Invalid.')
                return
            else:
                await ctx.message.add_reaction(EMOJI_CHECK)
                if (valid_address == CoinAddress):
                    await ctx.send(f'Address: `{CoinAddress}`\n'
                                    'Checked: Valid.')
                return
            return
        elif len(CoinAddress) == int(IntaddressLength):
            # Integrated address
            valid_address = addressvalidation.validate_integrated_cn(CoinAddress, COIN_NAME)
            if valid_address == 'invalid':
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} Integrated Address: `{CoinAddress}`\n'
                                'Checked: Invalid.')
                return
            if len(valid_address) == 2:
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                iCoinAddress = CoinAddress
                CoinAddress = valid_address['address']
                paymentid = valid_address['integrated_id']
                await ctx.send(f'\nIntegrated Address: `{iCoinAddress}`\n\n'
                                f'Address: `{CoinAddress}`\n'
                                f'PaymentID: `{paymentid}`')
                return
        else:
            # incorrect length
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                            'Checked: Incorrect length')
            return
    if len(args) == 2:
        CoinAddress = args[0]
        paymentid = args[1]
        # generate integrated address:
        if len(CoinAddress) == int(addressLength):
            valid_address = addressvalidation.validate_address_cn(CoinAddress, COIN_NAME)
            if (valid_address is None):
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                                'Checked: Incorrect given address.')
                return
            else:
                pass
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} Address: `{CoinAddress}`\n'
                            'Checked: Incorrect length')
            return
        # Check payment ID
        if len(paymentid) == 64:
            if not re.match(r'[a-zA-Z0-9]{64,}', paymentid.strip()):
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} PaymentID: `{paymentid}`\n'
                                'Checked: Invalid. Should be in 64 correct format.')
                return
            else:
                pass
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} PaymentID: `{paymentid}`\n'
                            'Checked: Incorrect length')
            return
        # Make integrated address:
        integrated_address = addressvalidation.make_integrated_cn(CoinAddress, COIN_NAME, paymentid)
        if 'integrated_address' in integrated_address:
            iCoinAddress = integrated_address['integrated_address']
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            await ctx.send(f'\nNew integrated address: `{iCoinAddress}`\n\n'
                            f'Main address: `{CoinAddress}`\n'
                            f'Payment ID: `{paymentid}`\n')
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} ERROR Can not make integrated address.\n')
            return
    else:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send('**[ ADDRESS CHECKING EXAMPLES ]**\n\n'
                       '`.address WrkzRNDQDwFCBynKPc459v3LDa1gEGzG3j962tMUBko1fw9xgdaS9mNiGMgA9s1q7hS1Z8SGRVWzcGc8Sh8xsvfZ6u2wJEtoZB`\n'
                       'That will check if the address is valid. Integrated address is also supported. '
                       'If integrated address is input, bot will tell you the result of :address + paymentid\n\n'
                       '`.address <coin_address> <paymentid>`\n'
                       'This will generate an integrate address.\n\n')
        return


@bot.command(pass_context=True, name='paymentid', aliases=['payid'], help=bot_help_paymentid)
async def paymentid(ctx, coin: str = None):
    paymentid = None
    if coin and (coin.upper() in ENABLE_XMR):
        paymentid = addressvalidation.paymentid(8)
    else:
        paymentid = addressvalidation.paymentid()
    await ctx.message.add_reaction(EMOJI_OK_HAND)
    await ctx.send('**[ RANDOM PAYMENT ID ]**\n'
                   f'`{paymentid}`\n')
    return


@bot.command(pass_context=True, aliases=['stat'], help=bot_help_stats)
async def stats(ctx, coin: str = None):
    global TRTL_DISCORD, NOTICE_COIN
    COIN_NAME = None
    serverinfo = None
    if coin is None and isinstance(ctx.message.channel, discord.DMChannel) == False:
        serverinfo = await get_info_pref_coin(ctx)
        COIN_NAME = serverinfo['default_coin'].upper()
    elif coin is None and isinstance(ctx.message.channel, discord.DMChannel):
        COIN_NAME = "BOT"
    elif coin and isinstance(ctx.message.channel, discord.DMChannel) == False:
        serverinfo = await get_info_pref_coin(ctx)
        COIN_NAME = coin.upper()
    elif coin:
        COIN_NAME = coin.upper()

    if COIN_NAME not in (ENABLE_COIN+ENABLE_XMR+ENABLE_COIN_ERC+ENABLE_COIN_TRC) and COIN_NAME != "BOT":
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{ctx.author.mention} Unsupported or Unknown Ticker: **{COIN_NAME}**')
        return

    # TRTL discord
    if isinstance(ctx.message.channel, discord.DMChannel) == False and ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
        return

    if is_maintenance_coin(COIN_NAME) and (ctx.author.id not in MAINTENANCE_OWNER):
        await ctx.message.add_reaction(EMOJI_MAINTENANCE)
        await ctx.send(f'{EMOJI_RED_NO} {COIN_NAME} in maintenance.')
        return
    elif is_maintenance_coin(COIN_NAME) and (ctx.author.id in MAINTENANCE_OWNER):
        await ctx.message.add_reaction(EMOJI_MAINTENANCE)

    if COIN_NAME == "BOT":
        total_claimed = '{:,.0f}'.format(await store.sql_faucet_count_all())
        total_tx = await store.sql_count_tx_all()
        embed = discord.Embed(title="[ TIPBOT ]", description="TipBot Stats", timestamp=datetime.utcnow(), color=0xDEADBF)
        embed.set_author(name=bot.user.name, icon_url=bot.user.display_avatar)
        embed.add_field(name="Bot ID", value=str(bot.user.id), inline=True)
        embed.add_field(name="Guilds", value='{:,.0f}'.format(len(bot.guilds)), inline=True)
        embed.add_field(name="Shards", value='{:,.0f}'.format(bot.shard_count), inline=True)
        try:
            embed.add_field(name="Total Online", value='{:,.0f}'.format(sum(1 for m in bot.get_all_members() if m.status == discord.Status.online)), inline=True)
            embed.add_field(name="Users", value='{:,.0f}'.format(sum(1 for m in bot.get_all_members() if m.bot == False)), inline=True)
            embed.add_field(name="Bots", value='{:,.0f}'.format(sum(1 for m in bot.get_all_members() if m.bot == True)), inline=True)
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
            msg = await ctx.send(embed=embed)
            await msg.add_reaction(EMOJI_OK_BOX)
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
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
        msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} connection to daemon timeout after {str(timeout)} seconds. I am checking info from wallet now.')
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
            embed = discord.Embed(title=f"[ {COIN_NAME} ]", 
                                  description=desc, 
                                  timestamp=datetime.utcnow(), color=0xDEADBF)
            embed.set_author(name=bot.user.name, icon_url=bot.user.display_avatar)
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
                msg = await ctx.send(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                # if embedded denied
                msg = await ctx.send(f'**[ {COIN_NAME} ]**\n'
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
            embed = discord.Embed(title=f"[ {COIN_NAME} ]", 
                                  description=desc, 
                                  timestamp=datetime.utcnow(), color=0xDEADBF)
            embed.set_author(name=bot.user.name, icon_url=bot.user.display_avatar)
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
                msg = await ctx.send(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                # if embedded denied
                balance_str = ''
                if walletBalance and ('unlocked' in walletBalance) and ('locked' in walletBalance) and walletStatus:
                    balance_actual = num_format_coin(walletBalance['unlocked'], COIN_NAME)
                    balance_locked = num_format_coin(walletBalance['locked'], COIN_NAME)
                    balance_str = f'[TOTAL UNLOCKED] {balance_actual} {COIN_NAME}\n'
                    balance_str = balance_str + f'[TOTAL LOCKED]   {balance_locked} {COIN_NAME}'
                    msg = await ctx.send(f'**[ {COIN_NAME} ]**\n'
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
                    msg = await ctx.send(f'**[ {COIN_NAME} ]**\n'
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
            embed = discord.Embed(title=f"[ {COIN_NAME} ]", 
                                  description=desc, 
                                  timestamp=datetime.utcnow(), color=0xDEADBF)
            embed.set_author(name=bot.user.name, icon_url=bot.user.display_avatar)
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
                msg = await ctx.send(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                # if embedded denied
                balance_str = ''
                if ('unlocked' in walletBalance) and ('locked' in walletBalance):
                    balance_actual = num_format_coin(walletBalance['unlocked'], COIN_NAME)
                    balance_locked = num_format_coin(walletBalance['locked'], COIN_NAME)
                    balance_str = f'[TOTAL UNLOCKED] {balance_actual} {COIN_NAME}\n'
                    balance_str = balance_str + f'[TOTAL LOCKED]   {balance_locked} {COIN_NAME}'
                    msg = await ctx.send(f'**[ {COIN_NAME} ]**\n'
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
            msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME}\'s status unavailable.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
    elif COIN_NAME in ENABLE_COIN_ERC:
        try:
            token_info = await store.get_token_info(COIN_NAME)
            desc = f"Tip min/max: {num_format_coin(token_info['real_min_tip'], COIN_NAME)}-{num_format_coin(token_info['real_max_tip'], COIN_NAME)} {COIN_NAME}\n"
            desc += f"Tx min/max: {num_format_coin(token_info['real_min_tx'], COIN_NAME)}-{num_format_coin(token_info['real_max_tx'], COIN_NAME)} {COIN_NAME}\n"
            embed = discord.Embed(title=f"[ {COIN_NAME} ]", 
                                  description=desc, 
                                  timestamp=datetime.utcnow(), color=0xDEADBF)
            embed.set_author(name=bot.user.name, icon_url=bot.user.display_avatar)
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
                msg = await ctx.send(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
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
            embed = discord.Embed(title=f"[ {COIN_NAME} ]", 
                                  description=desc, 
                                  timestamp=datetime.utcnow(), color=0xDEADBF)
            embed.set_author(name=bot.user.name, icon_url=bot.user.display_avatar)
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
                msg = await ctx.send(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                pass
        except Exception as e:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await logchanbot(traceback.format_exc())
            print(traceback.format_exc())


@bot.group(pass_context=True, aliases=['fb'], help=bot_help_feedback)
async def feedback(ctx):
    prefix = await get_guild_prefix(ctx)
    if ctx.invoked_subcommand is None:
        if config.feedback_setting.enable != 1:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{ctx.author.mention} Feedback is not enable right now. Check back later.')
            return

        # Check if user has submitted any and reach limit
        check_feedback_user = await store.sql_get_feedback_count_last(str(ctx.author.id), config.feedback_setting.intervial_last_10mn_s)
        if check_feedback_user and check_feedback_user >= config.feedback_setting.intervial_last_10mn:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{ctx.author.mention} You had submitted {config.feedback_setting.intervial_last_10mn} already. '
                           'Waiting a bit before next submission.')
            return
        check_feedback_user = await store.sql_get_feedback_count_last(str(ctx.author.id), config.feedback_setting.intervial_each_user)
        if check_feedback_user and check_feedback_user >= 1:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{ctx.author.mention} You had submitted one feedback already for the last {config.feedback_setting.intervial_each_user}s.'
                           'Waiting a bit before next submission.')
            return
        # OK he can submitted
        try:
            msg = await ctx.send(f'{ctx.author.mention} We are welcome for all feedback, inquiry or suggestion. '
                                 f'You can also join our support server as in {prefix}about command.\n'
                                 f'Please type in your feedback here (timeout {config.feedback_setting.waiting_for_feedback_text}s):')
            # DESC
            feedback = None
            while feedback is None:
                waiting_feedbackmsg = None
                try:
                    waiting_feedbackmsg = await bot.wait_for('message', timeout=config.feedback_setting.waiting_for_feedback_text, check=lambda msg: msg.author == ctx.author)
                except asyncio.TimeoutError:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{ctx.author.mention} **Timeout** for feedback submission. '
                                   'You can try again later.')
                    return
                if waiting_feedbackmsg is None:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{ctx.author.mention} **Timeout** for feedback submission. '
                                   'You can try again later.')
                    return
                else:
                        feedback = waiting_feedbackmsg.content.strip()
                        if len(feedback) <= config.feedback_setting.min_chars:
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            msg = await ctx.send(f'{ctx.author.mention}, feedback message is too short.')
                            return
                        else:
                            # OK, let's add
                            feedback_id = str(uuid.uuid4())
                            text_in = "DM"
                            if isinstance(ctx.channel, discord.DMChannel) == False: text_in = str(ctx.message.channel.id)
                            howto_contact_back = "N/A"
                            msg = await ctx.send(f'{ctx.author.mention} (Optional) Please let us know if and how we can contact you back '
                                                 f'(timeout {config.feedback_setting.waiting_for_feedback_text}s) - default N/A:')
                            try:
                                waiting_howtoback = await bot.wait_for('message', timeout=config.feedback_setting.waiting_for_feedback_text, check=lambda msg: msg.author == ctx.author)
                            except asyncio.TimeoutError:
                                pass
                            else:
                                if len(waiting_howtoback.content.strip()) > 0: howto_contact_back = waiting_howtoback.content.strip()
                            add = await store.sql_feedback_add(str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator), 
                                                               feedback_id, text_in, feedback, howto_contact_back)
                            if add:
                                msg = await ctx.send(f'{ctx.author.mention} Thank you for your feedback / inquiry. Your feedback ref: **{feedback_id}**')
                                await msg.add_reaction(EMOJI_OK_BOX)
                                try:
                                    botLogChan = bot.get_channel(LOG_CHAN)
                                    await botLogChan.send(f'{EMOJI_INFORMATION} A user has submitted a feedback `{feedback_id}`')
                                except Exception as e:
                                    await logchanbot(traceback.format_exc())
                                return
                            else:
                                msg = await ctx.send(f'{ctx.author.mention} Internal Error.')
                                await msg.add_reaction(EMOJI_OK_BOX)
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            await ctx.message.add_reaction(EMOJI_ERROR)
            return


@feedback.command(aliases=['vfb'], help=bot_help_view_feedback)
async def view(ctx, ref: str):
    if config.feedback_setting.enable != 1:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{ctx.author.mention} Feedback is not enable right now. Check back later.')
        return
    get_feedback = await store.sql_feedback_by_ref(ref)
    if get_feedback is None:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{ctx.author.mention} We can not find feedback reference **{ref}**.')
        return
    else:
        # If he is bot owner or feedback owner:
        if int(get_feedback['user_id']) == ctx.author.id or ctx.author.id == OWNER_ID_TIPBOT:
            response_txt = 'Feedback ref: **{}** submitted by user id: {}, name: {}\n'.format(ref, get_feedback['user_id'], get_feedback['user_name'])
            response_txt += 'Content:\n\n{}\n\n'.format(get_feedback['feedback_text'])
            response_txt += 'Submitted date: {}'.format(datetime.fromtimestamp(get_feedback['feedback_date']))
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            msg = await ctx.send(f'{response_txt}')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{ctx.author.mention} You do not have permission to view **{ref}**.')
            return


@feedback.command(aliases=['ls'], help=bot_help_view_feedback_list)
async def list(ctx, userid: str=None):
    if config.feedback_setting.enable != 1:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{ctx.author.mention} Feedback is not enable right now. Check back later.')
        return
    if userid is None:
        get_feedback_list = await store.sql_feedback_list_by_user(str(ctx.author.id), 10)
        if get_feedback_list and len(get_feedback_list) > 0:
            table_data = [['Ref', 'Brief']]
            for each in get_feedback_list:
                table_data.append([each['feedback_id'], each['feedback_text'][0:48]])
            table = AsciiTable(table_data)
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            msg = await ctx.send(f'{ctx.author.mention} Your feedback list:```{table.table}```')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{ctx.author.mention} You do not have any feedback submitted.')
            return
    else:
        if ctx.author.id != OWNER_ID_TIPBOT:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{ctx.author.mention} You have no permission.')
            return
        else:
            get_feedback_list = await store.sql_feedback_list_by_user(userid, 10)
            if get_feedback_list and len(get_feedback_list) > 0:
                table_data = [['Ref', 'Brief']]
                for each in get_feedback_list:
                    table_data.append([each['feedback_id'], each['feedback_text'][0:48]])
                table = AsciiTable(table_data)
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                msg = await ctx.send(f'{ctx.author.mention} Feedback user {userid} list:```{table.table}```')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{ctx.author.mention} There is no feedback by {userid}.')
                return


@bot.command(pass_context=True, help=bot_help_height, hidden = True)
async def height(ctx, coin: str = None):
    global TRTL_DISCORD
    COIN_NAME = None
    serverinfo = None
    if coin is None:
        if isinstance(ctx.message.channel, discord.DMChannel):
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send('Please add ticker: '+ ', '.join(ENABLE_COIN).lower() + ' with this command if in DM.')
            return
        else:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            try:
                COIN_NAME = args[0].upper()
                if COIN_NAME not in ENABLE_COIN:
                    if COIN_NAME in ENABLE_COIN_DOGE:
                        pass
                    elif 'default_coin' in serverinfo:
                        COIN_NAME = serverinfo['default_coin'].upper()
                else:
                    pass
            except:
                if 'default_coin' in serverinfo:
                    COIN_NAME = serverinfo['default_coin'].upper()
            pass
    else:
        COIN_NAME = coin.upper()

    # check if bot channel is set:
    if serverinfo and serverinfo['botchan']:
        try: 
            if ctx.channel.id != int(serverinfo['botchan']):
                await ctx.message.add_reaction(EMOJI_ERROR)
                botChan = bot.get_channel(int(serverinfo['botchan']))
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention}, {botChan.mention} is the bot channel!!!')
                return
        except ValueError:
            pass
    # end of bot channel check

    # TRTL discord
    if isinstance(ctx.message.channel, discord.DMChannel) == False and ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
        return

    coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
    if COIN_NAME not in (ENABLE_COIN + ENABLE_XMR + ENABLE_XCH):
        await ctx.message.add_reaction(EMOJI_ERROR)
        msg = await ctx.send(f'{ctx.author.mention} Unsupported or Unknown Ticker: **{COIN_NAME}**')
        return
    elif is_maintenance_coin(COIN_NAME):
        await ctx.message.add_reaction(EMOJI_MAINTENANCE)
        msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} is under maintenance.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return

    gettopblock = None
    timeout = 60
    try:
        gettopblock = await daemonrpc_client.gettopblock(COIN_NAME, time_out=timeout)
    except asyncio.TimeoutError:
        msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} connection to daemon timeout after {str(timeout)} seconds.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return
    except Exception as e:
        await logchanbot(traceback.format_exc())

    if gettopblock:
        height = ""
        if coin_family in [ "BCN", "TRTL", "XMR"] and COIN_NAME != "TRTL":
            height = "{:,}".format(gettopblock['block_header']['height'])
        else:
            height = "{:,}".format(gettopblock['height'])
        msg = await ctx.send(f'**[ {COIN_NAME} HEIGHT]**: {height}\n')
        await msg.add_reaction(EMOJI_OK_BOX)
        return
    else:
        msg = await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME}\'s status unavailable.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return


@bot.command(pass_context=True, help=bot_help_disclaimer)
async def disclaimer(ctx):
    global DISCLAIM_MSG
    await ctx.send(f'{EMOJI_INFORMATION} **THANK YOU FOR USING** {DISCLAIM_MSG_LONG}')
    return


@bot.command(pass_context=True, help=bot_help_itag, hidden = True)
async def itag(ctx, *, itag_text: str = None):
    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.send(f'{EMOJI_RED_NO} This command can not be in private.')
        return
    ListiTag = await store.sql_itag_by_server(str(ctx.guild.id))
    if not ctx.message.attachments:
        # Find available tag
        if itag_text is None:
            if len(ListiTag) > 0:
                itags = (', '.join([w['itag_id'] for w in ListiTag])).lower()
                await ctx.send(f'Available itag: `{itags}`.\nPlease use `.itag tagname` to show it.')
                return
            else:
                await ctx.send('There is no **itag** in this server. Please add.\n')
                return
        else:
            # .itag -del tagid
            command_del = itag_text.split(" ")
            if len(command_del) >= 2:
                TagIt = await store.sql_itag_by_server(str(ctx.guild.id), command_del[1].upper())
                if command_del[0].upper() == "-DEL" and TagIt:
                    # check permission if there is attachment with .itag
                    if ctx.author.guild_permissions.manage_guild == False and ctx.author.guild_permissions.view_guild_insights == False:
                        await message.add_reaction(EMOJI_ERROR) 
                        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **itag** Permission denied.')
                        return
                    else:
                        DeliTag = await store.sql_itag_by_server_del(str(ctx.guild.id), command_del[1].upper())
                        if DeliTag:
                            await ctx.send(f'{ctx.author.mention} iTag **{command_del[1].upper()}** deleted.\n')
                        else:
                            await ctx.send(f'{ctx.author.mention} iTag **{command_del[1].upper()}** error deletion.\n')
                        return
                else:
                    await ctx.send(f'{ctx.author.mention} iTag unknow operation.\n')
                    return
            elif len(command_del) == 1:
                TagIt = await store.sql_itag_by_server(str(ctx.guild.id), itag_text.upper())
                if TagIt:
                    tagLink = config.itag.static_link + TagIt['stored_name']
                    await ctx.send(f'{tagLink}')
                    return
                else:
                    await ctx.send(f'There is no itag **{itag_text}** in this server.\n')
                    return
    else:
        if itag_text is None:
            await ctx.send(f'{EMOJI_RED_NO} You need to include **tag** for this image.')
            return
        else:
            # check permission if there is attachment with .itag
            if ctx.author.guild_permissions.manage_guild == False and ctx.author.guild_permissions.view_guild_insights == False:
                await message.add_reaction(EMOJI_ERROR) 
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} **itag** Permission denied.')
                return
            d = [i['itag_id'] for i in ListiTag]
            if itag_text.upper() in d:
                await ctx.send(f'{EMOJI_RED_NO} iTag **{itag_text}** already exists here.')
                return
            else:
                pass
    # we passed of no attachment
    attachment = ctx.message.attachments[0]
    if not (attachment.filename.lower()).endswith(('.gif', '.jpeg', '.jpg', '.png', '.mp4')):
        await ctx.send(f'{EMOJI_RED_NO} Attachment type rejected.')
        return
    else:
        print('Filename: {}'.format(attachment.filename))
    if attachment.size >= config.itag.max_size:
        await ctx.send(f'{EMOJI_RED_NO} File too big.')
        return
    else:
        print('Size: {}'.format(attachment.size))
    print("iTag: {}".format(itag_text))
    if re.match(r'^[a-zA-Z0-9_-]*$', itag_text):
        if len(itag_text) >= 32:
            await ctx.send(f'itag **{itag_text}** is too long.')
            return
    else:
        await ctx.send(f'{EMOJI_RED_NO} iTag id not accepted.')
        return
    link = attachment.url # https://cdn.discordapp.com/attachments
    attach_save_name = str(uuid.uuid4()) + '.' + link.split(".")[-1].lower()
    try:
        if link.startswith("https://cdn.discordapp.com/attachments"):
            async with aiohttp.ClientSession() as session:
                async with session.get(link) as resp:
                    if resp.status == 200:
                        if resp.headers["Content-Type"] not in ["image/gif", "image/png", "image/jpeg", "image/jpg", "video/mp4"]:
                            await ctx.send(f'{EMOJI_RED_NO} Unsupported format file.')
                            return
                        else: 
                            with open(config.itag.path + attach_save_name, 'wb') as f:
                                f.write(await resp.read())
                            # save to DB and inform
                            addiTag = await store.sql_itag_by_server_add(str(ctx.guild.id), itag_text.upper(),
                                                                         str(ctx.author), str(ctx.author.id),
                                                                         attachment.filename, attach_save_name, attachment.size)
                            if addiTag is None:
                                await ctx.send(f'{ctx.author.mention} Failed to add itag **{itag_text}**')
                                return
                            elif addiTag.upper() == itag_text.upper():
                                await ctx.send(f'{ctx.author.mention} Successfully added itag **{itag_text}**')
                                return
    except Exception as e:
        await logchanbot(traceback.format_exc())


@bot.command(pass_context=True, help=bot_help_tag)
async def tag(ctx, *args):
    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.send(f'{ctx.author.mention} {EMOJI_RED_NO} This command can not be in private.')
        return

    ListTag = await store.sql_tag_by_server(str(ctx.guild.id), None)

    if len(args) == 0:
        if len(ListTag) > 0:
            tags = (', '.join([w['tag_id'] for w in ListTag])).lower()
            msg = await ctx.send(f'{ctx.author.mention} Available tag: `{tags}`.\nPlease use `.tag tagname` to show it in detail.'
                                'If you have permission to manage discord server.\n'
                                'Use: `.tag -add|del tagname <Tag description ... >`')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        else:
            msg = await ctx.send(f'{ctx.author.mention} There is no tag in this server. Please add.\n'
                                'If you have permission to manage discord server.\n'
                                'Use: `.tag -add|-del tagname <Tag description ... >`')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
    elif len(args) == 1 or len(ctx.message.mentions) > 0:
        # if .tag test
        TagIt = await store.sql_tag_by_server(str(ctx.guild.id), args[0].upper())
        # If there is mention
        mention_users = None
        if len(ctx.message.mentions) > 0:
            try:
                mention_users = ''
                for each_user in ctx.message.mentions:
                    mention_users += '<@{}>, '.format(str(each_user.id))
            except Exception as e:
                print(traceback.format_exc())
                await logchanbot(traceback.format_exc())
        if TagIt:
            tagDesc = TagIt['tag_desc']
            try:
                if mention_users:
                    msg = await ctx.send(f'{mention_users} {ctx.author.mention} {tagDesc}')
                else:
                    msg = await ctx.send(f'{ctx.author.mention} {tagDesc}')
                await msg.add_reaction(EMOJI_OK_BOX)
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
            except Exception as e:
                print(traceback.format_exc())
                await logchanbot(traceback.format_exc())
            return
        else:
            msg = await ctx.send(f'{ctx.author.mention} There is no tag {args[0]} in this server.\n'
                                'If you have permission to manage discord server.\n'
                                'Use: ```.tag -add|-del tagname <Tag description ... >```')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
    if (args[0].lower() in ['-add', '-del']) and (ctx.author.guild_permissions.manage_guild == False and ctx.author.guild_permissions.view_guild_insights == False):
        msg = await ctx.send(f'{ctx.author.mention} Permission denied.')
        await msg.add_reaction(EMOJI_OK_BOX)
        return
    if args[0].lower() == '-add' and (ctx.author.guild_permissions.manage_guild or ctx.author.guild_permissions.view_guild_insights):
        if re.match('^[a-zA-Z0-9]+(-[a-zA-Z0-9]+)*$', args[1]):
            tag = args[1].upper()
            if len(tag) >= 32:
                await ctx.send(f'{ctx.author.mention} Tag ***{args[1]}*** is too long.')
                return

            tagDesc = ctx.message.content.strip()[(9 + len(tag) + 1):]
            if len(tagDesc) <= 3:
                msg = await ctx.send(f'{ctx.author.mention} Tag desc for ***{args[1]}*** is too short.')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            if len(ListTag) > 0:
                d = [i['tag_id'] for i in ListTag]
                if tag.upper() in d:
                    await ctx.send(f'{ctx.author.mention} Tag **{args[1]}** already exists here.')
                    return
            addTag = await store.sql_tag_by_server_add(str(ctx.guild.id), tag.strip(), tagDesc.strip(),
                                                       ctx.author.name, str(ctx.author.id))
            if addTag is None:
                msg = await ctx.send(f'{ctx.author.mention} Failed to add tag **{args[1]}**')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            if addTag.upper() == tag.upper():
                msg = await ctx.send(f'{ctx.author.mention} Successfully added tag **{args[1]}**')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            else:
                msg = await ctx.send(f'{ctx.author.mention} Failed to add tag **{args[1]}**')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
        else:
            msg = await ctx.send(f'{ctx.author.mention} Tag {args[1]} is not valid.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        return
    elif args[0].lower() == '-del' and (ctx.author.guild_permissions.manage_guild or ctx.author.guild_permissions.view_guild_insights):
        #print('Has permission:' + str(ctx.message.content))
        if re.match('^[a-zA-Z0-9]+(-[a-zA-Z0-9]+)*$', args[1]):
            tag = args[1].upper()
            delTag = await store.sql_tag_by_server_del(str(ctx.guild.id), tag.strip())
            if delTag is None:
                await ctx.send(f'{ctx.author.mention} Failed to delete tag ***{args[1]}***')
                return
            if delTag.upper() == tag.upper():
                await ctx.send(f'{ctx.author.mention} Successfully deleted tag ***{args[1]}***')
                return
            else:
                await ctx.send(f'{ctx.author.mention} Failed to delete tag ***{args[1]}***')
                return
        else:
            await ctx.send(f'Tag {args[1]} is not valid.')
            return
        return


@bot.command(pass_context=True, name='invite', aliases=['inviteme'], help=bot_help_invite)
async def invite(ctx):
    global BOT_INVITELINK_PLAIN
    await ctx.send(f'**[INVITE LINK]**: {BOT_INVITELINK_PLAIN}')


@bot.command(pass_context=True, help=bot_help_random_number)
async def rand(ctx, randstring: str = None):
    rand_numb = None
    if randstring is None:
        rand_numb = random.randint(1,100)
    else:
        randstring = randstring.replace(",", "")
        rand_min_max = randstring.split("-")
        if len(rand_min_max) <= 1:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid range given. Example, use: `rand 1-50`')
            return
        try:
            min_numb = int(rand_min_max[0])
            max_numb = int(rand_min_max[1])
            if max_numb - min_numb <= 0:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid range given. Example, use: `rand 1-50`')
                return
            else:
                rand_numb = random.randint(min_numb,max_numb)
        except ValueError:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid range given. Example, use: `rand 1-50`')
            return
    if rand_numb:
        await ctx.message.add_reaction(EMOJI_OK_BOX)
        try:
            msg = await ctx.send('{} Random number: **{:,}**'.format(ctx.author.mention, rand_numb))
            await msg.add_reaction(EMOJI_OK_BOX)
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
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


@register.error
async def register_error(ctx, error):
    prefix = await get_guild_prefix(ctx)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Missing your wallet address. '
                       f'You need to have a supported coin **address** after `register` command. Example: {prefix}register coin_address')
    return


@info.error
async def info_error(ctx, error):
    pass


@randtip.error
async def randtip_error(ctx, error):
    prefix = await get_guild_prefix(ctx)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Missing coin ticker and/or amount. '
                       f'Example: {prefix}randtip 10 doge')
    return


@balance.error
async def balance_error(ctx, error):
    pass


@botbalance.error
async def botbalance_error(ctx, error):
    prefix = await get_guild_prefix(ctx)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Missing Bot and/or ticker. '
                       f'You need to @mention_bot COIN.\nExample: {prefix}botbalance <@{bot.user.id}> **coin_name**')
    return


@withdraw.error
async def withdraw_error(ctx, error):
    prefix = await get_guild_prefix(ctx)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Missing amount and/or ticker. '
                       f'You need to tell me **AMOUNT** and/or **TICKER**.\nExample: {prefix}withdraw **1,000 coin_name**')
    return


@notifytip.error
async def notifytip_error(ctx, error):
    prefix = await get_guild_prefix(ctx)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Use {prefix}notifytip **on** or {prefix}notifytip **off**')
    return


@freetip.error
async def freetip_error(ctx, error):
    prefix = await get_guild_prefix(ctx)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Missing arguments. '
                       f'You need to tell me **amount** and **coin name**.\nExample: {prefix}freetip **1,000 coin_name**')
    return


@tip.error
async def tip_error(ctx, error):
    prefix = await get_guild_prefix(ctx)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Missing arguments. '
                       f'You need to tell me **amount** and who you want to tip to.\nExample: {prefix}tip **1,000 coin_name** <@{bot.user.id}>')
    return


@mtip.error
async def mtip_error(ctx, error):
    prefix = await get_guild_prefix(ctx)
    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.send('This command is not available in DM.')
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f'{ctx.author.mention} You do not have permission in this guild **{ctx.guild.name}** Please use normal {prefix}tip command.')
        return


@donate.error
async def donate_error(ctx, error):
    prefix = await get_guild_prefix(ctx)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Missing arguments. '
                       'You need to tell me **amount** and ticker.\n'
                       f'Example: {prefix}donate **1,000 coin_name**\n'
                       f'Get donation list we received: {prefix}donate list')
    return


@tipall.error
async def tipall_error(ctx, error):
    prefix = await get_guild_prefix(ctx)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Missing argument. '
                       f'You need to tell me **amount**.\nExample: {prefix}tipall **1,000 coin_name**')
    return


@send.error
async def send_error(ctx, error):
    prefix = await get_guild_prefix(ctx)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Missing arguments. \n'
                       f'Example: {prefix}send **amount coin_address**')
    return


@address.error
async def address_error(ctx, error):
    pass


@paymentid.error
async def payment_error(ctx, error):
    pass


@tag.error
async def tag_error(ctx, error):
    pass


@height.error
async def height_error(ctx, error):
    pass


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


async def bot_faucet(ctx):
    global TRTL_DISCORD
    get_game_stat = await store.sql_game_stat()
    table_data = [
        ['TICKER', 'Available', 'Claimed / Game']
    ]
    for COIN_NAME in [coinItem.upper() for coinItem in FAUCET_COINS]:
        sum_sub = 0
        wallet = await store.sql_get_userwallet(str(bot.user.id), COIN_NAME)
        if wallet is None:
            if COIN_NAME in ENABLE_COIN_ERC:
                coin_family = "ERC-20"
                w = await create_address_eth()
                wallet = await store.sql_register_user(str(bot.user.id), COIN_NAME, SERVER_BOT, 0, w)
            elif COIN_NAME in ENABLE_COIN_TRC:
                coin_family = "TRC-20"
                result = await store.create_address_trx()
                wallet = await store.sql_register_user(str(bot.user.id), COIN_NAME, SERVER_BOT, 0, result)
            else:
                coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                wallet = await store.sql_register_user(str(bot.user.id), COIN_NAME, SERVER_BOT, 0)
        userdata_balance = await store.sql_user_balance(str(bot.user.id), COIN_NAME)
        xfer_in = 0
        if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            xfer_in = await store.sql_user_balance_get_xfer_in(str(bot.user.id), COIN_NAME)
        if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
        elif COIN_NAME in ENABLE_COIN_NANO:
            actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
            actual_balance = round(actual_balance / get_decimal(COIN_NAME), 6) * get_decimal(COIN_NAME)
        else:
            actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
        elif COIN_NAME in ENABLE_COIN_TRC:
            coin_family = "TRC-20"
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")           
        try:
            if COIN_NAME in get_game_stat and coin_family in ["TRTL", "BCN", "XMR", "NANO", "XCH"]:
                actual_balance = actual_balance - int(get_game_stat[COIN_NAME])
                sum_sub = int(get_game_stat[COIN_NAME])
            elif COIN_NAME in get_game_stat and coin_family in ["DOGE", "ERC-20", "TRC-20"]:
                actual_balance = actual_balance - float(get_game_stat[COIN_NAME])
                sum_sub = float(get_game_stat[COIN_NAME])
        except Exception as e:
            await logchanbot(traceback.format_exc())
        balance_actual = num_format_coin(actual_balance, COIN_NAME)
        get_claimed_count = await store.sql_faucet_sum_count_claimed(COIN_NAME)
        if coin_family in ["TRTL", "BCN", "XMR", "NANO", "XCH"]:
            sub_claim = num_format_coin(int(get_claimed_count['claimed']) + sum_sub, COIN_NAME) if get_claimed_count['count'] > 0 else f"0.00{COIN_NAME}"
        elif coin_family in ["DOGE", "ERC-20", "TRC-20"]:
            sub_claim = num_format_coin(float(get_claimed_count['claimed']) + sum_sub, COIN_NAME) if get_claimed_count['count'] > 0 else f"0.00{COIN_NAME}"
        if actual_balance != 0:
            table_data.append([COIN_NAME, balance_actual, sub_claim])
        else:
            table_data.append([COIN_NAME, '0', sub_claim])
    table = AsciiTable(table_data)
    table.padding_left = 0
    table.padding_right = 0
    return table.table


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


# https://en.wikipedia.org/wiki/Primality_test
def is_prime(n: int) -> bool:
    """Primality test using 6k+-1 optimization."""
    if n <= 3:
        return n > 1
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i ** 2 <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


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


## Section of Trade
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
## END OF Section of Trade



@bot.command(usage="load <cog>")
@commands.is_owner()
async def load(ctx, extension):
    """Load specified cog"""
    extension = extension.lower()
    bot.load_extension(f'cogs.{extension}')
    await ctx.send('{} has been loaded.'.format(extension.capitalize()))


@bot.command(usage="unload <cog>")
@commands.is_owner()
async def unload(ctx, extension):
    """Unload specified cog"""
    extension = extension.lower()
    bot.unload_extension(f'cogs.{extension}')
    await ctx.send('{} has been unloaded.'.format(extension.capitalize()))


@bot.command(usage="reload <cog/guilds/utils/all>")
@commands.is_owner()
async def reload(ctx, extension):
    """Reload specified cog"""
    extension = extension.lower()
    bot.reload_extension(f'cogs.{extension}')
    await ctx.send('{} has been reloaded.'.format(extension.capitalize()))


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
