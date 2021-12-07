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

class Games(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def bot_log(self):
        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)


    @commands.group(
        usage="game <subcommand>", 
        aliases=['games'], 
        description="Various game commands."
    )
    async def game(self, ctx):
        await self.bot_log()

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        # bot check in the first place
        if ctx.author.bot == True:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is not allowed using this.')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} (Bot) using **game** {ctx.guild.name} / {ctx.guild.id}')
            return

        if isinstance(ctx.channel, discord.DMChannel) == True:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} No, not working with DM.')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried using **game** in **DM**')
            return

        try: 
            # check if game is enabled
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if serverinfo and serverinfo['enable_game'] == "NO":
                await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **game** in {ctx.guild.name} / {ctx.guild.id} which is disable.')
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, **Game** in this guild is disable.')
                return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            pass
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
        # end of game is enabled

        # check if bot is going to restart
        if IS_RESTARTING:
            await ctx.message.add_reaction(EMOJI_REFRESH)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
            return

        prefix = await get_guild_prefix(ctx)
        if ctx.invoked_subcommand is None:
            await ctx.reply(f'{ctx.author.mention} Invalid {prefix}game command.\n Please use {prefix}help game')
            return


    @game.command(
        usage="game stat", 
        description="Show game statistic."
    )
    async def stat(self, ctx):
        await self.bot_log()

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        get_game_stat = await store.sql_game_stat()
        if get_game_stat and len(get_game_stat) > 0:   
            stat = discord.Embed(title='TipBot Game Stat', description='', timestamp=datetime.utcnow(), colour=7047495)
            stat.add_field(name='Total Plays', value='{}'.format(get_game_stat['paid_play']+get_game_stat['free_play']), inline=True)
            stat.add_field(name='Total Free Plays', value='{}'.format(get_game_stat['free_play']), inline=True)
            stat.add_field(name='Total Paid Plays', value='{}'.format(get_game_stat['paid_play']), inline=True)
            for COIN_NAME in GAME_COIN:
                stat.add_field(name='Paid in {}'.format(COIN_NAME), value='{}{}'.format(num_format_coin(get_game_stat[COIN_NAME], COIN_NAME), COIN_NAME), inline=True)
            stat.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
            try:
                msg = await ctx.reply(embed=stat)
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                await msg.add_reaction(EMOJI_OK_BOX)
            except Exception as e:
                await ctx.author.send(embed=stat)
                await logchanbot(traceback.format_exc())
        return


    @game.command(
        usage="game blackjack", 
        aliases=['bj'], 
        description="Blackjack, original code by Al Sweigart al@inventwithpython.com."
    )
    async def blackjack(self, ctx):
        await self.bot_log()

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo and 'enable_game' in serverinfo and serverinfo['enable_game'] == "NO":
            prefix = serverinfo['prefix']
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Game is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING GAME`')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}game** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
            return

        free_game = False
        won = False

        # check if user create account less than 3 days
        try:
            account_created = ctx.author.created_at
            if (datetime.utcnow() - account_created).total_seconds() <= config.game.account_age_to_play:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Your account is very new. Wait a few days before using this.')
                return
        except Exception as e:
            await logchanbot(traceback.format_exc())

        try: 
            index_game = "game_blackjack_channel"
            # check if bot channel is set:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if serverinfo and serverinfo[index_game]:
                if ctx.channel.id != int(serverinfo[index_game]):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    gameChan = self.bot.get_channel(int(serverinfo[index_game]))
                    if gameChan:
                        await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, {gameChan.mention} is for game **blackjack** channel!!!')
                        return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            pass
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
        # end of bot channel check

        count_played = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, False)
        count_played_free = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, True)
        if count_played and count_played >= config.game.max_daily_play:
            free_game = True
            await ctx.message.add_reaction(EMOJI_ALARMCLOCK)

        if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
            await ctx.reply(f'{ctx.author.mention} You are ongoing with one **game** play.')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return

        game_text = '''
    Rules:
        Try to get as close to 21 without going over.
        Kings, Queens, and Jacks are worth 10 points.
        Aces are worth 1 or 11 points.
        Cards 2 through 10 are worth their face value.
        (H)it to take another card.
        (S)tand to stop taking cards.
        The dealer stops hitting at 17.'''

        try:
            await ctx.reply(f'{ctx.author.mention} ```{game_text}```')
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
            return

        time_start = int(time.time())
        game_over = False
        player_over = False

        deck = blackjack_getDeck()
        dealerHand = [deck.pop(), deck.pop()]
        playerHand = [deck.pop(), deck.pop()]

        if ctx.author.id not in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.append(ctx.author.id)

        while not game_over:
            # check if bot is going to restart
            if IS_RESTARTING:
                await ctx.message.add_reaction(EMOJI_REFRESH)
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
                return
            while not player_over:  # Keep looping until player stands or busts.
                # check if bot is going to restart
                if IS_RESTARTING:
                    await ctx.message.add_reaction(EMOJI_REFRESH)
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
                    return
                get_display = blackjack_displayHands(playerHand, dealerHand, False)
                # Sometimes bot sending failure. If fails, we finish it.
                try:
                    msg = await ctx.reply('{} **BLACKJACK**\n'
                                         '```DEALER: {}\n'
                                         '{}\n'
                                         'PLAYER:  {}\n'
                                         '{}```Please re-act {}: Stand, {}: Hit'.format(ctx.author.mention, get_display['dealer_header'], 
                                         get_display['dealer'], get_display['player_header'], get_display['player'], EMOJI_LETTER_S, EMOJI_LETTER_H))
                    await msg.add_reaction(EMOJI_LETTER_S)
                    await msg.add_reaction(EMOJI_LETTER_H)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                    game_over = True
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot failed to start BlackJack message. Please re-try.')
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    break
                    return
                # Check if the player has bust:
                if blackjack_getCardValue(playerHand) >= 21:
                    player_over = True
                    break
                
                def check(reaction, user):
                    return user == ctx.author and reaction.message.author == self.bot.user and reaction.message.id == msg.id and str(reaction.emoji) \
                    in (EMOJI_LETTER_S, EMOJI_LETTER_H)
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60, check=check)
                except asyncio.TimeoutError:
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    await ctx.reply(f'{ctx.author.mention} **BLACKJACK GAME ** has waited you too long. Game exits.')
                    try:
                        await msg.delete()
                    except Exception as e:
                        pass
                    return
                if str(reaction.emoji) == EMOJI_LETTER_H:
                    # Hit/doubling down takes another card.
                    newCard = deck.pop()
                    rank, suit = newCard
                    try:
                        await ctx.reply('{} **BLACKJACK** You drew a {} of {}'.format(ctx.author.mention, rank, suit))
                    except Exception as e:
                        if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                            GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    playerHand.append(newCard)

                    if blackjack_getCardValue(playerHand) >= 21:
                        # The player has busted:
                        player_over = True
                        break
                elif str(reaction.emoji) == EMOJI_LETTER_S:
                    player_over = True
                    break

            # Handle the dealer's actions:
            if blackjack_getCardValue(playerHand) <= 21:
                if blackjack_getCardValue(dealerHand) >= 17:
                    game_over = True
                    break
                else:
                    while blackjack_getCardValue(dealerHand) < 17:
                        # The dealer hits:
                        try:
                            dealer_msg = await ctx.reply('{} **BLACKJACK**\n'
                                                        '```Dealer hits...```'.format(ctx.author.mention))
                        except Exception as e:
                            if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                                GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                        newCard = deck.pop()
                        rank, suit = newCard
                        dealerHand.append(newCard)
                        await asyncio.sleep(2)
                        await dealer_msg.edit(content='{} **BLACKJACK** Dealer drew a {} of {}'.format(ctx.author.mention, rank, suit))
                        if blackjack_getCardValue(dealerHand) > 21:
                            game_over = True  # The dealer has busted.
                            break
                        else:
                            await asyncio.sleep(2)
            else:
                game_over = True
                break

        dealer_get_display = blackjack_displayHands(playerHand, dealerHand, True)
        try:
            await ctx.reply('{} **BLACKJACK**\n'
                           '```DEALER: {}\n'
                           '{}\n'
                           'PLAYER:  {}\n'
                           '{}```'.format(ctx.author.mention, dealer_get_display['dealer_header'], 
                           dealer_get_display['dealer'], dealer_get_display['player_header'], dealer_get_display['player']))
        except Exception as e:
            if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)

        playerValue = blackjack_getCardValue(playerHand)
        dealerValue = blackjack_getCardValue(dealerHand)
        # Handle whether the player won, lost, or tied:
        COIN_NAME = random.choice(GAME_COIN)
        amount = GAME_SLOT_REWARD[COIN_NAME]
        if COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "ERC-20"
        elif COIN_NAME in ENABLE_COIN_ERC:
            coin_family = "TRC-20"
        else:
            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
        real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
        result = f'You got reward of **{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}** to Tip balance!'
        if free_game == True:
            result = f'You do not get any reward because it is a free game! Waiting to refresh your paid plays (24h max).'
        try:
            if dealerValue > 21:
                won = True
                await ctx.reply('{} **BLACKJACK**\n'
                               '```Dealer busts! You win! {}```'.format(ctx.author.mention, result))
            elif playerValue > 21 or playerValue < dealerValue:
                await ctx.reply('{} **BLACKJACK**\n'
                               '```You lost!```'.format(ctx.author.mention))
            elif playerValue > dealerValue:
                won = True
                await ctx.reply('{} **BLACKJACK**\n'
                               '```You won! {}```'.format(ctx.author.mention, result))
            elif playerValue == dealerValue:
                await ctx.reply('{} **BLACKJACK**\n'
                               '```It\'s a tie!```'.format(ctx.author.mention))
        except Exception as e:
            await logchanbot(traceback.format_exc())
        if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
        if free_game == True:
            try:
                await store.sql_game_free_add('BLACKJACK: PLAYER={}, DEALER={}'.format(playerValue, dealerValue), str(ctx.author.id), \
                'WIN' if won else 'LOSE', str(ctx.guild.id), 'BLACKJACK', int(time.time()) - time_start, SERVER_BOT)
            except Exception as e:
                await logchanbot(traceback.format_exc())
        else:
            try:
                reward = await store.sql_game_add('BLACKJACK: PLAYER={}, DEALER={}'.format(playerValue, dealerValue), str(ctx.author.id), \
                COIN_NAME, 'WIN' if won else 'LOSE', real_amount if won else 0, get_decimal(COIN_NAME) if won else 0, str(ctx.guild.id), 'BLACKJACK', int(time.time()) - time_start, SERVER_BOT)
            except Exception as e:
                await logchanbot(traceback.format_exc())


    @game.command(
        usage="game slot", 
        aliases=['slots'], 
        description="Play a slot game."
    )
    async def slot(self, ctx):
        await self.bot_log()

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo and 'enable_game' in serverinfo and serverinfo['enable_game'] == "NO":
            prefix = serverinfo['prefix']
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Game is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING GAME`')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}game** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
            return

        free_game = False
        # Only WrkzCoin testing. Return if DM or other guild

        # check if user create account less than 3 days
        try:
            account_created = ctx.author.created_at
            if (datetime.utcnow() - account_created).total_seconds() <= config.game.account_age_to_play:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Your account is very new. Wait a few days before using this.')
                return
        except Exception as e:
            await logchanbot(traceback.format_exc())

        try: 
            index_game = "game_slot_channel"
            # check if bot channel is set:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if serverinfo and serverinfo[index_game]:
                if ctx.channel.id != int(serverinfo[index_game]):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    gameChan = self.bot.get_channel(int(serverinfo[index_game]))
                    if gameChan:
                        await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, {gameChan.mention} is for game **slot** channel!!!')
                        return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            pass
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
        # end of bot channel check

        count_played = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, False)
        count_played_free = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, True)
        if count_played and count_played >= config.game.max_daily_play:
            free_game = True
            await ctx.message.add_reaction(EMOJI_ALARMCLOCK)

        # Portion from https://github.com/MitchellAW/Discord-Bot/blob/master/features/rng.py
        slots = ['chocolate_bar', 'bell', 'tangerine', 'apple', 'cherries', 'seven']
        slot1 = slots[random.randint(0, 5)]
        slot2 = slots[random.randint(0, 5)]
        slot3 = slots[random.randint(0, 5)]
        slotOutput = '|\t:{}:\t|\t:{}:\t|\t:{}:\t|'.format(slot1, slot2, slot3)

        time_start = int(time.time())

        if ctx.author.id not in GAME_SLOT_IN_PRGORESS:
            GAME_SLOT_IN_PRGORESS.append(ctx.author.id)
        else:
            await ctx.reply(f'{ctx.author.mention} You are ongoing with one **game** play.')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return
        won = False
        won_x = 1
        slotOutput_2 = '$ TRY AGAIN! $'
        result = 'You lose! Good luck later!'
        if slot1 == slot2 == slot3 == 'seven':
            slotOutput_2 = '$$ JACKPOT $$\n'
            won = True
            won_x = 25
        elif slot1 == slot2 == slot3:
            slotOutput_2 = '$$ GREAT $$'
            won = True
            won_x = 10
        try:
            if free_game == False:
                if won:
                    COIN_NAME = random.choice(GAME_COIN)
                    amount = GAME_SLOT_REWARD[COIN_NAME] * won_x
                    if COIN_NAME in ENABLE_COIN_ERC:
                        coin_family = "ERC-20"
                    elif COIN_NAME in ENABLE_COIN_TRC:
                        coin_family = "TRC-20"
                    else:
                        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                    real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
                    reward = await store.sql_game_add(slotOutput, str(ctx.author.id), COIN_NAME, 'WIN', real_amount, get_decimal(COIN_NAME), str(ctx.guild.id), 'SLOT', int(time.time()) - time_start, SERVER_BOT)
                    result = f'You won! {ctx.author.mention} got reward of **{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}** to Tip balance!'
                else:
                    reward = await store.sql_game_add(slotOutput, str(ctx.author.id), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'SLOT', int(time.time()) - time_start, SERVER_BOT)
            else:
                if won:
                    result = f'You won! but this is a free game without **reward**! Waiting to refresh your paid plays (24h max).'
                try:
                    await store.sql_game_free_add(slotOutput, str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'SLOT', int(time.time()) - time_start, SERVER_BOT)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
        except Exception as e:
            await logchanbot(traceback.format_exc())
        embed = discord.Embed(title="TIPBOT FREE SLOT ({} REWARD)".format("WITHOUT" if free_game else "WITH"), description="Anyone can freely play!", color=0x00ff00)
        embed.add_field(name="Player", value="{}#{}".format(ctx.author.name, ctx.author.discriminator), inline=False)
        embed.add_field(name="Last 24h you played", value=str(count_played_free+count_played+1), inline=False)
        embed.add_field(name="Result", value=slotOutput, inline=False)
        embed.add_field(name="Comment", value=slotOutput_2, inline=False)
        embed.add_field(name="Reward", value=result, inline=False)
        embed.add_field(name='More', value=f'[TipBot Github](https://github.com/wrkzcoin/TipBot) | {BOT_INVITELINK} ', inline=False)
        if won == False:
            embed.set_footer(text="Randomed Coin: {} | Message shall be deleted after 5s.".format(config.game.coin_game))
        else:
            embed.set_footer(text="Randomed Coin: {}".format(config.game.coin_game))
        try:
            await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
            await asyncio.sleep(config.game.game_slot_sleeping) # sleep 5s
            if ctx.author.id in GAME_SLOT_IN_PRGORESS:
                GAME_SLOT_IN_PRGORESS.remove(ctx.author.id)
            msg = await ctx.reply(embed=embed)
            await msg.add_reaction(EMOJI_OK_BOX)
            if won == False:
                # Delete lose game after 10s
                await asyncio.sleep(10)
                try:
                    await msg.delete()
                except discord.errors.NotFound as e:
                    pass
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await logchanbot(traceback.format_exc())
        except discord.errors.NotFound as e:
            pass
        if ctx.author.id in GAME_SLOT_IN_PRGORESS:
            GAME_SLOT_IN_PRGORESS.remove(ctx.author.id)
        return


    @game.command(
        usage="game bagel", 
        aliases=['bagel1'], 
        description="Bagels, a deductive logic game."
    )
    async def bagel(self, ctx):
        await self.bot_log()

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo and 'enable_game' in serverinfo and serverinfo['enable_game'] == "NO":
            prefix = serverinfo['prefix']
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Game is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING GAME`')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}game** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
            return

        # Credit: https://github.com/asweigart/PythonStdioGames
        free_game = False

        # check if user create account less than 3 days
        try:
            account_created = ctx.author.created_at
            if (datetime.utcnow() - account_created).total_seconds() <= config.game.account_age_to_play:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Your account is very new. Wait a few days before using this.')
                return
        except Exception as e:
            await logchanbot(traceback.format_exc())

        try: 
            index_game = "game_bagel_channel"
            # check if bot channel is set:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if serverinfo and serverinfo[index_game]:
                if ctx.channel.id != int(serverinfo[index_game]):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    gameChan = self.bot.get_channel(int(serverinfo[index_game]))
                    if gameChan:
                        await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, {gameChan.mention} is for game **bagel** channel!!!')
                        return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            pass
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
        # end of bot channel check

        if ctx.author.id not in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.append(ctx.author.id)
        else:
            await ctx.reply(f'{ctx.author.mention} You are ongoing with one **game** play.')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return

        count_played = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, False)
        count_played_free = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, True)
        if count_played and count_played >= config.game.max_daily_play:
            free_game = True
            await ctx.message.add_reaction(EMOJI_ALARMCLOCK)

        won = False
        NUM_DIGITS = 3  # (!) Try setting this to 1 or 10.
        MAX_GUESSES = 10  # (!) Try setting this to 1 or 100.
        game_text = '''Bagels, a deductive logic game.

    I am thinking of a {}-digit number with no repeated digits.
    Try to guess what it is. Here are some clues:
    When I say:    That means:
      Pico         One digit is correct but in the wrong position.
      Fermi        One digit is correct and in the right position.
      Bagels       No digit is correct.

    For example, if the secret number was 248 and your guess was 843, the
    clues would be Fermi Pico.'''.format(NUM_DIGITS)

        time_start = int(time.time())

        await ctx.reply(f'{ctx.author.mention} ```{game_text}```')
        secretNum = bagels_getSecretNum(NUM_DIGITS)

        try:
            await ctx.reply(f'{ctx.author.mention} I have thought up a number. You have {MAX_GUESSES} guesses to get it.')
            guess = None
            numGuesses = 0
            while guess is None:
                # check if bot is going to restart
                if IS_RESTARTING:
                    await ctx.message.add_reaction(EMOJI_REFRESH)
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
                    return
                waiting_numbmsg = None
                def check(m):
                    return m.author == ctx.author and m.guild.id == ctx.guild.id
                try:
                    waiting_numbmsg = await self.bot.wait_for('message', timeout=60, check=check)
                except asyncio.TimeoutError:
                    await ctx.message.add_reaction(EMOJI_ALARMCLOCK)
                    await ctx.reply(f'{ctx.author.mention} **Bagel Timeout**. The answer was **{secretNum}**.')
                    if free_game == True:
                        try:
                            await store.sql_game_free_add(str(secretNum), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(str(secretNum), str(ctx.author.id), 'None', 'WIN' if won else 'LOSE', 0, 0, str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    return
                if waiting_numbmsg is None:
                    await ctx.message.add_reaction(EMOJI_ALARMCLOCK)
                    await ctx.reply(f'{ctx.author.mention} **Bagel Timeout**. The answer was **{secretNum}**.')
                    if free_game == True:
                        try:
                            await store.sql_game_free_add(str(secretNum), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(str(secretNum), str(ctx.author.id), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    return
                else:
                    guess = waiting_numbmsg.content.strip()
                    try:
                        guess_chars = [str(char) for char in str(guess)]
                        if len(guess) != NUM_DIGITS or not guess.isdecimal():
                            guess = None
                            await ctx.reply(f'{ctx.author.mention} **Bagel: ** Please use {NUM_DIGITS} numbers!')
                        elif len([x for x in guess_chars if guess_chars.count(x) >= 2]) > 0:
                            guess = None
                            await ctx.reply(f'{ctx.author.mention} **Bagel: ** Please do not use repeated numbers!')
                        else:
                            if guess == secretNum:
                                result = 'But this is a free game without **reward**! Waiting to refresh your paid plays (24h max).'
                                won = True
                                if won and free_game == False:
                                    won_x = 5
                                    COIN_NAME = random.choice(GAME_COIN)
                                    amount = GAME_SLOT_REWARD[COIN_NAME] * won_x
                                    if COIN_NAME in ENABLE_COIN_ERC:
                                        coin_family = "ERC-20"
                                    elif COIN_NAME in ENABLE_COIN_TRC:
                                        coin_family = "TRC-20"
                                    else:
                                        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                                    real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
                                    reward = await store.sql_game_add(str(secretNum), str(ctx.author.id), COIN_NAME, 'WIN', real_amount, get_decimal(COIN_NAME), str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                                    result = f'{ctx.author.mention} got reward of **{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}** to Tip balance!'
                                elif won == False and free_game == True:
                                    reward = await store.sql_game_add(str(secretNum), str(ctx.author.id), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                                elif free_game == True:
                                    try:
                                        await store.sql_game_free_add(str(secretNum), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                                    except Exception as e:
                                        await logchanbot(traceback.format_exc())
                                if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                                    GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                                await ctx.reply(f'{ctx.author.mention} **Bagel: ** You won! The answer was **{secretNum}**. You had guessed **{numGuesses+1}** times only. {result}')
                                return
                            else:
                                clues = bagels_getClues(guess, secretNum)
                                await ctx.reply(f'{ctx.author.mention} **Bagel: #{numGuesses+1} ** {clues}')
                                guess = None
                                numGuesses += 1
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                if numGuesses >= MAX_GUESSES:
                    await ctx.reply(f'{ctx.author.mention} **Bagel: ** You run out of guesses and you did it **{numGuesses}** times. Game over! The answer was **{secretNum}**')
                    if free_game == True:
                        try:
                            await store.sql_game_free_add(str(secretNum), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(str(secretNum), str(ctx.author.id), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    return
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            await ctx.message.add_reaction(EMOJI_ERROR)
            return
        if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)


    @game.command(
        usage="game bagel2", 
        aliases=['bagels2'], 
        description="Bagels, a deductive logic game."
    )
    async def bagel2(self, ctx):
        await self.bot_log()

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo and 'enable_game' in serverinfo and serverinfo['enable_game'] == "NO":
            prefix = serverinfo['prefix']
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Game is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING GAME`')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}game** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
            return

        # Credit: https://github.com/asweigart/PythonStdioGames
        free_game = False

        # check if user create account less than 3 days
        try:
            account_created = ctx.author.created_at
            if (datetime.utcnow() - account_created).total_seconds() <= config.game.account_age_to_play:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Your account is very new. Wait a few days before using this.')
                return
        except Exception as e:
            await logchanbot(traceback.format_exc())

        try: 
            index_game = "game_bagel_channel"
            # check if bot channel is set:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if serverinfo and serverinfo[index_game]:
                if ctx.channel.id != int(serverinfo[index_game]):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    gameChan = self.bot.get_channel(int(serverinfo[index_game]))
                    if gameChan:
                        await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, {gameChan.mention} is for game **bagel** channel!!!')
                        return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            pass
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
        # end of bot channel check

        if ctx.author.id not in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.append(ctx.author.id)
        else:
            await ctx.reply(f'{ctx.author.mention} You are ongoing with one **game** play.')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return

        count_played = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, False)
        count_played_free = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, True)
        if count_played and count_played >= config.game.max_daily_play:
            free_game = True
            await ctx.message.add_reaction(EMOJI_ALARMCLOCK)

        won = False
        NUM_DIGITS = 4  # (!) Try setting this to 1 or 10.
        MAX_GUESSES = 15  # (!) Try setting this to 1 or 100.
        secretNum = bagels_getSecretNum(NUM_DIGITS)
        split_number = [int(d) for d in str(secretNum)]
        hint = []
        hint.append('First number + Second number = {}'.format(split_number[0] + split_number[1]))
        hint.append('First number + Third number = {}'.format(split_number[0] + split_number[2]))
        hint.append('First number + Forth number = {}'.format(split_number[0] + split_number[3]))
        hint.append('Second number + Third number = {}'.format(split_number[1] + split_number[2]))
        hint.append('Second number + Forth number = {}'.format(split_number[1] + split_number[3]))
        hint.append('Third number + Forth number = {}'.format(split_number[2] + split_number[3]))

        hint.append('First number * Second number = {}'.format(split_number[0] * split_number[1]))
        hint.append('First number * Third number = {}'.format(split_number[0] * split_number[2]))
        hint.append('First number * Forth number = {}'.format(split_number[0] * split_number[3]))
        hint.append('Second number * Third number = {}'.format(split_number[1] * split_number[2]))
        hint.append('Second number * Forth number = {}'.format(split_number[1] * split_number[3]))
        hint.append('Third number * Forth number = {}'.format(split_number[2] * split_number[3]))
        numb_hint = 2
        random.shuffle(hint)
        if numb_hint > 0:
            i = 0
            hint_string = ''
            while i < numb_hint:
                hint_string += hint[i] + '\n'
                i += 1

        game_text = '''Bagels, a deductive logic game.

    I am thinking of a {}-digit number with no repeated digits.
    Try to guess what it is. Here are some clues:
    When I say:    That means:
      Pico         One digit is correct but in the wrong position.
      Fermi        One digit is correct and in the right position.
      Bagels       No digit is correct.

    For example, if the secret number was 248 and your guess was 843, the
    clues would be Fermi Pico.

    Hints:
    {}
    '''.format(NUM_DIGITS, hint_string)
        await ctx.reply(f'{ctx.author.mention} ```{game_text}```')

        time_start = int(time.time())

        try:
            await ctx.reply(f'{ctx.author.mention} I have thought up a number. You have {MAX_GUESSES} guesses to get it.')
            guess = None
            numGuesses = 0
            while guess is None:
                # check if bot is going to restart
                if IS_RESTARTING:
                    await ctx.message.add_reaction(EMOJI_REFRESH)
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
                    return
                waiting_numbmsg = None
                def check(m):
                    return m.author == ctx.author and m.guild.id == ctx.guild.id
                try:
                    waiting_numbmsg = await self.bot.wait_for('message', timeout=60, check=check)
                except asyncio.TimeoutError:
                    await ctx.message.add_reaction(EMOJI_ALARMCLOCK)
                    await ctx.reply(f'{ctx.author.mention} **Bagel Timeout**. The answer was **{secretNum}**.')
                    if free_game == True:
                        try:
                            await store.sql_game_free_add(str(secretNum), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(str(secretNum), str(ctx.author.id), 'None', 'WIN' if won else 'LOSE', 0, 0, str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    return
                if waiting_numbmsg is None:
                    await ctx.message.add_reaction(EMOJI_ALARMCLOCK)
                    await ctx.reply(f'{ctx.author.mention} **Bagel Timeout**. The answer was **{secretNum}**.')
                    if free_game == True:
                        try:
                            await store.sql_game_free_add(str(secretNum), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(str(secretNum), str(ctx.author.id), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    return
                else:
                    guess = waiting_numbmsg.content.strip()
                    try:
                        guess_chars = [str(char) for char in str(guess)]
                        if len(guess) != NUM_DIGITS or not guess.isdecimal():
                            guess = None
                            await ctx.reply(f'{ctx.author.mention} **Bagel: ** Please use {NUM_DIGITS} numbers!')
                        elif len([x for x in guess_chars if guess_chars.count(x) >= 2]) > 0:
                            guess = None
                            await ctx.reply(f'{ctx.author.mention} **Bagel: ** Please do not use repeated numbers!')
                        else:
                            if guess == secretNum:
                                result = 'But this is a free game without **reward**! Waiting to refresh your paid plays (24h max).'
                                won = True
                                if won and free_game == False:
                                    won_x = 5
                                    COIN_NAME = random.choice(GAME_COIN)
                                    amount = GAME_SLOT_REWARD[COIN_NAME] * won_x
                                    if COIN_NAME in ENABLE_COIN_ERC:
                                        coin_family = "ERC-20"
                                    elif COIN_NAME in ENABLE_COIN_TRC:
                                        coin_family = "TRC-20"
                                    else:
                                        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                                    real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
                                    reward = await store.sql_game_add(str(secretNum), str(ctx.author.id), COIN_NAME, 'WIN', real_amount, get_decimal(COIN_NAME), str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                                    result = f'{ctx.author.mention} got reward of **{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}** to Tip balance!'
                                elif won == False and free_game == True:
                                    reward = await store.sql_game_add(str(secretNum), str(ctx.author.id), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                                elif free_game == True:
                                    try:
                                        await store.sql_game_free_add(str(secretNum), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                                    except Exception as e:
                                        await logchanbot(traceback.format_exc())
                                if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                                    GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                                await ctx.reply(f'{ctx.author.mention} **Bagel: ** You won! The answer was **{secretNum}**. You had guessed **{numGuesses+1}** times only. {result}')
                                return
                            else:
                                clues = bagels_getClues(guess, secretNum)
                                await ctx.reply(f'{ctx.author.mention} **Bagel: #{numGuesses+1} ** {clues}')
                                guess = None
                                numGuesses += 1
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                if numGuesses >= MAX_GUESSES:
                    await ctx.reply(f'{ctx.author.mention} **Bagel: ** You run out of guesses and you did it **{numGuesses}** times. Game over! The answer was **{secretNum}**')
                    if free_game == True:
                        try:
                            await store.sql_game_free_add(str(secretNum), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(str(secretNum), str(ctx.author.id), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    return
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            await ctx.message.add_reaction(EMOJI_ERROR)
            return
        if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)


    @game.command(
        usage="game bagel3", 
        aliases=['bagels3'], 
        description="Bagels, a deductive logic game."
    )
    async def bagel3(self, ctx):
        await self.bot_log()

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo and 'enable_game' in serverinfo and serverinfo['enable_game'] == "NO":
            prefix = serverinfo['prefix']
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Game is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING GAME`')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}game** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
            return

        # Credit: https://github.com/asweigart/PythonStdioGames
        free_game = False

        # check if user create account less than 3 days
        try:
            account_created = ctx.author.created_at
            if (datetime.utcnow() - account_created).total_seconds() <= config.game.account_age_to_play:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Your account is very new. Wait a few days before using this.')
                return
        except Exception as e:
            await logchanbot(traceback.format_exc())

        try: 
            index_game = "game_bagel_channel"
            # check if bot channel is set:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if serverinfo and serverinfo[index_game]:
                if ctx.channel.id != int(serverinfo[index_game]):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    gameChan = self.bot.get_channel(int(serverinfo[index_game]))
                    if gameChan:
                        await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, {gameChan.mention} is for game **bagel** channel!!!')
                        return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            pass
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
        # end of bot channel check

        if ctx.author.id not in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.append(ctx.author.id)
        else:
            await ctx.reply(f'{ctx.author.mention} You are ongoing with one **game** play.')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return

        count_played = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, False)
        count_played_free = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, True)
        if count_played and count_played >= config.game.max_daily_play:
            free_game = True
            await ctx.message.add_reaction(EMOJI_ALARMCLOCK)

        won = False
        NUM_DIGITS = 5  # (!) Try setting this to 1 or 10.
        MAX_GUESSES = 15  # (!) Try setting this to 1 or 100.
        secretNum = bagels_getSecretNum(NUM_DIGITS)
        split_number = [int(d) for d in str(secretNum)]
        hint = []
        hint.append('First number + Second number = {}'.format(split_number[0] + split_number[1]))
        hint.append('First number + Third number = {}'.format(split_number[0] + split_number[2]))
        hint.append('First number + Forth number = {}'.format(split_number[0] + split_number[3]))
        hint.append('First number + Fifth number = {}'.format(split_number[0] + split_number[4]))
        hint.append('Second number + Third number = {}'.format(split_number[1] + split_number[2]))
        hint.append('Second number + Forth number = {}'.format(split_number[1] + split_number[3]))
        hint.append('Second number + Fifth number = {}'.format(split_number[1] + split_number[4]))
        hint.append('Third number + Forth number = {}'.format(split_number[2] + split_number[3]))
        hint.append('Third number + Fifth number = {}'.format(split_number[2] + split_number[4]))
        hint.append('Forth number + Fifth number = {}'.format(split_number[3] + split_number[4]))
        
        hint.append('First number * Second number = {}'.format(split_number[0] * split_number[1]))
        hint.append('First number * Third number = {}'.format(split_number[0] * split_number[2]))
        hint.append('First number * Forth number = {}'.format(split_number[0] * split_number[3]))
        hint.append('First number * Fifth number = {}'.format(split_number[0] * split_number[4]))
        hint.append('Second number * Third number = {}'.format(split_number[1] * split_number[2]))
        hint.append('Second number * Forth number = {}'.format(split_number[1] * split_number[3]))
        hint.append('Second number * Fifth number = {}'.format(split_number[1] * split_number[4]))
        hint.append('Third number * Forth number = {}'.format(split_number[2] * split_number[3]))
        hint.append('Third number * Fifth number = {}'.format(split_number[2] * split_number[4]))
        hint.append('Forth number * Fifth number = {}'.format(split_number[3] * split_number[4]))
        numb_hint = 2
        random.shuffle(hint)
        if numb_hint > 0:
            i = 0
            hint_string = ''
            while i < numb_hint:
                hint_string += hint[i] + '\n'
                i += 1

        game_text = '''Bagels, a deductive logic game.

    I am thinking of a {}-digit number with no repeated digits.
    Try to guess what it is. Here are some clues:
    When I say:    That means:
      Pico         One digit is correct but in the wrong position.
      Fermi        One digit is correct and in the right position.
      Bagels       No digit is correct.

    For example, if the secret number was 248 and your guess was 843, the
    clues would be Fermi Pico.

    Hints:
    {}
    '''.format(NUM_DIGITS, hint_string)
        await ctx.reply(f'{ctx.author.mention} ```{game_text}```')

        time_start = int(time.time())

        try:
            await ctx.reply(f'{ctx.author.mention} I have thought up a number. You have {MAX_GUESSES} guesses to get it.')
            guess = None
            numGuesses = 0
            while guess is None:
                # check if bot is going to restart
                if IS_RESTARTING:
                    await ctx.message.add_reaction(EMOJI_REFRESH)
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
                    return
                waiting_numbmsg = None
                def check(m):
                    return m.author == ctx.author and m.guild.id == ctx.guild.id
                try:
                    waiting_numbmsg = await self.bot.wait_for('message', timeout=60, check=check)
                except asyncio.TimeoutError:
                    await ctx.message.add_reaction(EMOJI_ALARMCLOCK)
                    await ctx.reply(f'{ctx.author.mention} **Bagel Timeout**. The answer was **{secretNum}**.')
                    if free_game == True:
                        try:
                            await store.sql_game_free_add(str(secretNum), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(str(secretNum), str(ctx.author.id), 'None', 'WIN' if won else 'LOSE', 0, 0, str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    return
                if waiting_numbmsg is None:
                    await ctx.message.add_reaction(EMOJI_ALARMCLOCK)
                    await ctx.reply(f'{ctx.author.mention} **Bagel Timeout**. The answer was **{secretNum}**.')
                    if free_game == True:
                        try:
                            await store.sql_game_free_add(str(secretNum), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(str(secretNum), str(ctx.author.id), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    return
                else:
                    guess = waiting_numbmsg.content.strip()
                    try:
                        guess_chars = [str(char) for char in str(guess)]
                        if len(guess) != NUM_DIGITS or not guess.isdecimal():
                            guess = None
                            await ctx.reply(f'{ctx.author.mention} **Bagel: ** Please use {NUM_DIGITS} numbers!')
                        elif len([x for x in guess_chars if guess_chars.count(x) >= 2]) > 0:
                            guess = None
                            await ctx.reply(f'{ctx.author.mention} **Bagel: ** Please do not use repeated numbers!')
                        else:
                            if guess == secretNum:
                                result = 'But this is a free game without **reward**! Waiting to refresh your paid plays (24h max).'
                                won = True
                                if won and free_game == False:
                                    won_x = 5
                                    COIN_NAME = random.choice(GAME_COIN)
                                    amount = GAME_SLOT_REWARD[COIN_NAME] * won_x
                                    if COIN_NAME in ENABLE_COIN_ERC:
                                        coin_family = "ERC-20"
                                    elif COIN_NAME in ENABLE_COIN_TRC:
                                        coin_family = "TRC-20"
                                    else:
                                        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                                    real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
                                    reward = await store.sql_game_add(str(secretNum), str(ctx.author.id), COIN_NAME, 'WIN', real_amount, get_decimal(COIN_NAME), str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                                    result = f'{ctx.author.mention} got reward of **{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}** to Tip balance!'
                                elif won == False and free_game == True:
                                    reward = await store.sql_game_add(str(secretNum), str(ctx.author.id), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                                elif free_game == True:
                                    try:
                                        await store.sql_game_free_add(str(secretNum), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                                    except Exception as e:
                                        await logchanbot(traceback.format_exc())
                                if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                                    GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                                await ctx.reply(f'{ctx.author.mention} **Bagel: ** You won! The answer was **{secretNum}**. You had guessed **{numGuesses+1}** times only. {result}')
                                return
                            else:
                                clues = bagels_getClues(guess, secretNum)
                                await ctx.reply(f'{ctx.author.mention} **Bagel: #{numGuesses+1} ** {clues}')
                                guess = None
                                numGuesses += 1
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                if numGuesses >= MAX_GUESSES:
                    await ctx.reply(f'{ctx.author.mention} **Bagel: ** You run out of guesses and you did it **{numGuesses}** times. Game over! The answer was **{secretNum}**')
                    if free_game == True:
                        try:
                            await store.sql_game_free_add(str(secretNum), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(str(secretNum), str(ctx.author.id), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'BAGEL', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    return
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            await ctx.message.add_reaction(EMOJI_ERROR)
            return
        if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)


    @game.command(
        usage="game maze", 
        aliases=['mazes'], 
        description="Interactive 2D ascii maze game."
    )
    async def maze(self, ctx):
        await self.bot_log()

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo and 'enable_game' in serverinfo and serverinfo['enable_game'] == "NO":
            prefix = serverinfo['prefix']
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Game is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING GAME`')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}game** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
            return

        # Credit: https://github.com/asweigart/PythonStdioGames
        free_game = False
        won = False

        try: 
            index_game = "game_maze_channel"
            # check if bot channel is set:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if serverinfo and serverinfo[index_game]:
                if ctx.channel.id != int(serverinfo[index_game]):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    gameChan = self.bot.get_channel(int(serverinfo[index_game]))
                    if gameChan:
                        await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, {gameChan.mention} is for game **maze** channel!!!')
                        return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            pass
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
        # end of bot channel check

        if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
            await ctx.reply(f'{ctx.author.mention} You are ongoing with one **game** play.')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return

        count_played = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, False)
        if count_played and count_played >= config.game.max_daily_play:
            free_game = True
            await ctx.message.add_reaction(EMOJI_ALARMCLOCK)

        # Make random height and width
        try:
            if ctx.guild.id not in GAME_MAZE_IN_PROCESS:
                GAME_MAZE_IN_PROCESS.append(ctx.guild.id)
            else:
                await ctx.reply(f'{ctx.author.mention} There is one **MAZE** started by a user in this guild already.')
                await ctx.message.add_reaction(EMOJI_ERROR)
                return
            WALL = '#'
            WIDTH = random.choice([25, 27, 29, 31, 33, 35])
            HEIGHT = random.choice([15, 17, 19, 21, 23, 25])
            SEED = random.randint(25, 50)
            EMPTY = ' '
            maze_data = await maze_createMazeDump(WIDTH, HEIGHT, SEED)
            playerx, playery = 1, 1
            exitx, exity = WIDTH - 2, HEIGHT - 2
            maze_created = maze_displayMaze(maze_data, WIDTH, HEIGHT, playerx, playery, exitx, exity)
            msg = await ctx.reply(f'{ctx.author.mention} New Maze:\n```{maze_created}```')
            await msg.add_reaction(EMOJI_UP)
            await msg.add_reaction(EMOJI_DOWN)
            await msg.add_reaction(EMOJI_LEFT)
            await msg.add_reaction(EMOJI_RIGHT)
            await msg.add_reaction(EMPTY_DISPLAY)
            await msg.add_reaction(EMOJI_OK_BOX)

            time_start = int(time.time())
            while (playerx, playery) != (exitx, exity):
                # check if bot is going to restart
                if IS_RESTARTING:
                    await ctx.message.add_reaction(EMOJI_REFRESH)
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
                    return
                def check(reaction, user):
                    return user == ctx.author and reaction.message.author == self.bot.user and reaction.message.id == msg.id and str(reaction.emoji) \
                    in (EMOJI_UP, EMOJI_DOWN, EMOJI_LEFT, EMOJI_RIGHT, EMOJI_OK_BOX)

                done, pending = await asyncio.wait([
                                    self.bot.wait_for('reaction_remove', timeout=60, check=check),
                                    self.bot.wait_for('reaction_add', timeout=60, check=check)
                                ], return_when=asyncio.FIRST_COMPLETED)
                try:
                    # stuff = done.pop().result()
                    reaction, user = done.pop().result()
                except asyncio.TimeoutError:
                    if ctx.guild.id in GAME_MAZE_IN_PROCESS:
                        GAME_MAZE_IN_PROCESS.remove(ctx.guild.id)

                    if free_game == True:
                        try:
                            await store.sql_game_free_add(json.dumps(remap_keys(maze_data)), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'MAZE', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(json.dumps(remap_keys(maze_data)), str(ctx.author.id), 'None', 'WIN' if won else 'LOSE', 0, 0, str(ctx.guild.id), 'MAZE', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    await ctx.reply(f'{ctx.author.mention} **MAZE GAME** has waited you too long. Game exits.')
                    try:
                        await msg.delete()
                    except Exception as e:
                        pass
                    return
                for future in pending:
                    future.cancel()  # we don't need these anymore
                    
                if str(reaction.emoji) == EMOJI_OK_BOX:
                    await ctx.reply(f'{ctx.author.mention} You gave up the current game.')
                    if ctx.guild.id in GAME_MAZE_IN_PROCESS:
                        GAME_MAZE_IN_PROCESS.remove(ctx.guild.id)

                    if free_game == True:
                        try:
                            await store.sql_game_free_add(json.dumps(remap_keys(maze_data)), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'MAZE', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(json.dumps(remap_keys(maze_data)), str(ctx.author.id), 'None', 'WIN' if won else 'LOSE', 0, 0, str(ctx.guild.id), 'MAZE', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    await asyncio.sleep(1)
                    try:
                        await msg.delete()
                    except Exception as e:
                        pass
                    break
                    return
                
                if (str(reaction.emoji) == EMOJI_UP and maze_data[(playerx, playery - 1)] == EMPTY) \
                or (str(reaction.emoji) == EMOJI_DOWN and maze_data[(playerx, playery + 1)] == EMPTY) \
                or (str(reaction.emoji) == EMOJI_LEFT and maze_data[(playerx - 1, playery)] == EMPTY) \
                or (str(reaction.emoji) == EMOJI_RIGHT and maze_data[(playerx + 1, playery)] == EMPTY):
                    if str(reaction.emoji) == EMOJI_UP:
                        while True:
                            playery -= 1
                            if (playerx, playery) == (exitx, exity):
                                break
                            if maze_data[(playerx, playery - 1)] == WALL:
                                break  # Break if we've hit a wall.
                            if (maze_data[(playerx - 1, playery)] == EMPTY
                                or maze_data[(playerx + 1, playery)] == EMPTY):
                                break  # Break if we've reached a branch point.
                    elif str(reaction.emoji) == EMOJI_DOWN:
                        while True:
                            playery += 1
                            if (playerx, playery) == (exitx, exity):
                                break
                            if maze_data[(playerx, playery + 1)] == WALL:
                                break  # Break if we've hit a wall.
                            if (maze_data[(playerx - 1, playery)] == EMPTY
                                or maze_data[(playerx + 1, playery)] == EMPTY):
                                break  # Break if we've reached a branch point.
                    elif str(reaction.emoji) == EMOJI_LEFT:
                        while True:
                            playerx -= 1
                            if (playerx, playery) == (exitx, exity):
                                break
                            if maze_data[(playerx - 1, playery)] == WALL:
                                break  # Break if we've hit a wall.
                            if (maze_data[(playerx, playery - 1)] == EMPTY
                                or maze_data[(playerx, playery + 1)] == EMPTY):
                                break  # Break if we've reached a branch point.
                    elif str(reaction.emoji) == EMOJI_RIGHT:
                        while True:
                            playerx += 1
                            if (playerx, playery) == (exitx, exity):
                                break
                            if maze_data[(playerx + 1, playery)] == WALL:
                                break  # Break if we've hit a wall.
                            if (maze_data[(playerx, playery - 1)] == EMPTY
                                or maze_data[(playerx, playery + 1)] == EMPTY):
                                break  # Break if we've reached a branch point.
                try:
                    maze_edit = maze_displayMaze(maze_data, WIDTH, HEIGHT, playerx, playery, exitx, exity)
                    await msg.edit(content=f'{ctx.author.mention} Maze:\n```{maze_edit}```')
                except Exception as e:
                    await logchanbot(traceback.format_exc())
            if (playerx, playery) == (exitx, exity):
                won = True
                # Handle whether the player won, lost, or tied:
                COIN_NAME = random.choice(GAME_COIN)
                amount = GAME_SLOT_REWARD[COIN_NAME]
                if COIN_NAME in ENABLE_COIN_ERC:
                    coin_family = "ERC-20"
                elif COIN_NAME in ENABLE_COIN_TRC:
                    coin_family = "TRC-20"
                else:
                    coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
                result = f'You got reward of **{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}** to Tip balance!'
                if free_game == True:
                    result = f'You do not get any reward because it is a free game!'
                    try:
                        await store.sql_game_free_add(json.dumps(remap_keys(maze_data)), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'MAZE', int(time.time()) - time_start, SERVER_BOT)
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                else:
                    try:
                        reward = await store.sql_game_add(json.dumps(remap_keys(maze_data)), str(ctx.author.id), COIN_NAME, 'WIN' if won else 'LOSE', real_amount if won else 0, get_decimal(COIN_NAME) if won else 0, str(ctx.guild.id), 'MAZE', int(time.time()) - time_start, SERVER_BOT)
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                duration = seconds_str(int(time.time()) - time_start)
                if ctx.guild.id in GAME_MAZE_IN_PROCESS:
                    GAME_MAZE_IN_PROCESS.remove(ctx.guild.id)
                await ctx.reply(f'{ctx.author.mention} **MAZE** Grats! You completed! You completed in: **{duration}\n{result}**')
                return
        except Exception as e:
            await logchanbot(traceback.format_exc())
        if ctx.guild.id in GAME_MAZE_IN_PROCESS:
            GAME_MAZE_IN_PROCESS.remove(ctx.guild.id)


    @game.command(
        usage="game hangman", 
        aliases=['hm'], 
        description="Old hangman game."
    )
    async def hangman(self, ctx):
        await self.bot_log()

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo and 'enable_game' in serverinfo and serverinfo['enable_game'] == "NO":
            prefix = serverinfo['prefix']
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Game is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING GAME`')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}game** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
            return

        # Credit: https://github.com/asweigart/PythonStdioGames
        free_game = False

        # check if user create account less than 3 days
        try:
            account_created = ctx.author.created_at
            if (datetime.utcnow() - account_created).total_seconds() <= config.game.account_age_to_play:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Your account is very new. Wait a few days before using this.')
                return
        except Exception as e:
            await logchanbot(traceback.format_exc())

        try: 
            index_game = "game_hangman_channel"
            # check if bot channel is set:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if serverinfo and serverinfo[index_game]:
                if ctx.channel.id != int(serverinfo[index_game]):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    gameChan = self.bot.get_channel(int(serverinfo[index_game]))
                    if gameChan:
                        await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, {gameChan.mention} is for game **hangman** channel!!!')
                        return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            pass
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
        # end of bot channel check

        if ctx.author.id not in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.append(ctx.author.id)
        else:
            await ctx.reply(f'{ctx.author.mention} You are ongoing with one **game** play.')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return

        count_played = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, False)
        count_played_free = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, True)
        if count_played and count_played >= config.game.max_daily_play:
            free_game = True
            await ctx.message.add_reaction(EMOJI_ALARMCLOCK)

        won = False

        time_start = int(time.time())
        # Setup variables for a new game:
        missedLetters = []  # List of incorrect letter guesses.
        correctLetters = []  # List of correct letter guesses.
        secretWord = random.choice(HANGMAN_WORDS).upper()  # The word the player must guess.
        game_text = '''Hangman, '''
        hm_draw = hm_drawHangman(missedLetters, correctLetters, secretWord)
        hm_picture = hm_draw['picture']
        hm_word_line = hm_draw['word_line']
        await ctx.reply(f'{ctx.author.mention} ```{game_text}\n{hm_picture}\n\n{hm_word_line}```')
        try:
            await ctx.reply(f'{ctx.author.mention} **HANGMAN** Please enter a single letter:')
            guess = None
            while guess is None:
                # check if bot is going to restart
                if IS_RESTARTING:
                    await ctx.message.add_reaction(EMOJI_REFRESH)
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
                    return
                waiting_numbmsg = None
                def check(m):
                    return m.author == ctx.author and m.guild.id == ctx.guild.id
                try:
                    waiting_numbmsg = await self.bot.wait_for('message', timeout=60, check=check)
                except asyncio.TimeoutError:
                    await ctx.message.add_reaction(EMOJI_ALARMCLOCK)
                    await ctx.reply(f'{ctx.author.mention} **HANGMAN Timeout**. The answer was **{secretWord}**.')
                    if free_game == True:
                        try:
                            await store.sql_game_free_add(secretWord, str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'HANGMAN', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(secretWord, str(ctx.author.id), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'HANGMAN', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    return
                if waiting_numbmsg is None:
                    await ctx.message.add_reaction(EMOJI_ALARMCLOCK)
                    await ctx.reply(f'{ctx.author.mention} **HANGMAN Timeout**. The answer was **{secretWord}**.')
                    if free_game == True:
                        try:
                            await store.sql_game_free_add(secretWord, str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'HANGMAN', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(secretWord, str(ctx.author.id), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'HANGMAN', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    return
                else:
                    guess = waiting_numbmsg.content.strip().upper()
                    if guess in missedLetters + correctLetters:
                        await ctx.reply(f'{ctx.author.mention} **HANGMAN**. You already guessed **{guess}**.')
                        guess = None
                    elif not guess.isalpha() and guess != '-':
                        guess = None
                        await ctx.reply(f'{ctx.author.mention} **HANGMAN**. Please use letter.')
                    elif len(guess) > 1:
                        guess = None
                        await ctx.reply(f'{ctx.author.mention} **HANGMAN**. Please use only one alphabet.')
                    elif guess in secretWord:
                        # Add the correct guess to correctLetters:
                        correctLetters.append(guess)
                        # Check if the player has won:
                        foundAllLetters = True  # Start off assuming they've won.
                        result = 'But this is a free game without **reward**! Waiting to refresh your paid plays (24h max).'
                        for secretWordLetter in secretWord:
                            if secretWordLetter not in correctLetters:
                                # There's a letter in the secret word that isn't
                                # yet in correctLetters, so the player hasn't won:
                                foundAllLetters = False
                        if foundAllLetters and free_game == False:
                            COIN_NAME = random.choice(GAME_COIN)
                            amount = GAME_SLOT_REWARD[COIN_NAME]
                            if COIN_NAME in ENABLE_COIN_ERC:
                                coin_family = "ERC-20"
                            elif COIN_NAME in ENABLE_COIN_TRC:
                                coin_family = "TRC-20"
                            else:
                                coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                            real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
                            reward = await store.sql_game_add(secretWord, str(ctx.author.id), COIN_NAME, 'WIN', real_amount, get_decimal(COIN_NAME), str(ctx.guild.id), 'HANGMAN', int(time.time()) - time_start, SERVER_BOT)
                            result = f'{ctx.author.mention} got reward of **{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}** to Tip balance!'
                        elif foundAllLetters and free_game == True:
                            reward = await store.sql_game_free_add(secretWord, str(ctx.author.id), 'WIN', str(ctx.guild.id), 'HANGMAN', int(time.time()) - time_start, SERVER_BOT)
                        if foundAllLetters:
                            if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                                GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                            await ctx.reply(f'{ctx.author.mention} **HANGMAN**: You won! The answer was **{secretWord}**. {result}')
                            return
                        else:
                            hm_draw = hm_drawHangman(missedLetters, correctLetters, secretWord)
                            hm_picture = hm_draw['picture']
                            hm_missed = hm_draw['missed_letter']
                            hm_word_line = hm_draw['word_line']
                            await ctx.reply(f'{ctx.author.mention} **HANGMAN: **```{hm_picture}\n\n{hm_word_line}\n{hm_missed}```')
                        guess = None
                    else:
                        # The player has guessed incorrectly:
                        missedLetters.append(guess)
                        guess = None
                        # Check if player has guessed too many times and lost. (The
                        # "- 1" is because we don't count the empty gallows in
                        # HANGMAN_PICS.)
                        hm_draw = hm_drawHangman(missedLetters, correctLetters, secretWord)
                        if len(missedLetters) == 6: # len(HANGMAN_PICS) = 7
                            hm_picture = hm_draw['picture']
                            hm_missed = hm_draw['missed_letter']
                            if free_game:
                                await store.sql_game_free_add(secretWord, str(ctx.author.id), 'LOSE', str(ctx.guild.id), 'HANGMAN', int(time.time()) - time_start, SERVER_BOT)
                            else:
                                await store.sql_game_add(secretWord, str(ctx.author.id), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'HANGMAN', int(time.time()) - time_start, SERVER_BOT)
                            await ctx.reply(f'{ctx.author.mention} **HANGMAN: ** You run out of guesses. Game over! The answer was **{secretWord}**```{hm_picture}```')
                            if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                                GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                            return
                        else:
                            hm_picture = hm_draw['picture']
                            hm_missed = hm_draw['missed_letter']
                            hm_word_line = hm_draw['word_line']
                            await ctx.reply(f'{ctx.author.mention} ```{hm_picture}\n\n{hm_word_line}\n{hm_missed}```')
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            await ctx.message.add_reaction(EMOJI_ERROR)
            return
        if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)


    @game.command(
        usage="game dice", 
        aliases=['dices'], 
        description="Simple dice game."
    )
    async def dice(self, ctx):
        await self.bot_log()

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo and 'enable_game' in serverinfo and serverinfo['enable_game'] == "NO":
            prefix = serverinfo['prefix']
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Game is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING GAME`')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}game** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
            return

        # Credit: https://github.com/asweigart/PythonStdioGames
        free_game = False

        # check if user create account less than 3 days
        try:
            account_created = ctx.author.created_at
            if (datetime.utcnow() - account_created).total_seconds() <= config.game.account_age_to_play:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Your account is very new. Wait a few days before using this.')
                return
        except Exception as e:
            await logchanbot(traceback.format_exc())

        try: 
            index_game = "game_dice_channel"
            # check if bot channel is set:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if serverinfo and serverinfo[index_game]:
                if ctx.channel.id != int(serverinfo[index_game]):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    gameChan = self.bot.get_channel(int(serverinfo[index_game]))
                    if gameChan:
                        await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, {gameChan.mention} is for game **dice** channel!!!')
                        return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            pass
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
        # end of bot channel check

        if ctx.author.id not in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.append(ctx.author.id)
        else:
            await ctx.reply(f'{ctx.author.mention} You are ongoing with one **game** play.')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return

        count_played = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, False)
        count_played_free = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, True)
        if count_played and count_played >= config.game.max_daily_play:
            free_game = True
            await ctx.message.add_reaction(EMOJI_ALARMCLOCK)

        won = False
        game_text = '''A player rolls two dice. Each die has six faces. 
    These faces contain 1, 2, 3, 4, 5, and 6 spots. 
    After the dice have come to rest, the sum of the spots on the two upward faces is calculated. 

    * If the sum is 7 or 11 on the first throw, the player wins.
     
    * If the sum is not 7 or 11 on the first throw, then the sum becomes the player's "point." 
    To win, you must continue rolling the dice until you "make your point." 

    * The player loses if they got 7 or 11 for their points.'''
        time_start = int(time.time())
        msg = await ctx.reply(f'{ctx.author.mention} ```{game_text}```')
        await msg.add_reaction(EMOJI_OK_BOX)

        if ctx.author.id not in GAME_DICE_IN_PRGORESS:
            GAME_DICE_IN_PRGORESS.append(ctx.author.id)
        else:
            await ctx.reply(f'{ctx.author.mention} You are ongoing with one **game dice** play.')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return
        # sleep 3s
        await asyncio.sleep(3)

        try:
            game_over = False
            sum_dice = 0
            dice_time = 0
            while not game_over:
                dice1 = random.randint(1, 6)
                dice2 = random.randint(1, 6)
                dice_time += 1
                msg = await ctx.reply(f'#{dice_time} {ctx.author.mention} your dices: **{dice1}** and **{dice2}**')
                if sum_dice == 0:
                    # first dice
                    sum_dice = dice1 + dice2
                    if sum_dice == 7 or sum_dice == 11:
                        won = True
                        game_over = True
                        break
                else:
                    # not first dice
                    if dice1 + dice2 == 7 or dice1 + dice2 == 11:
                        game_over = True
                    elif dice1 + dice2 == sum_dice:
                        won = True
                        game_over = True
                        break
                if game_over == False:
                    msg = await ctx.reply(f'{ctx.author.mention} re-throwing dices...')
                    await msg.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
                    await asyncio.sleep(2)
            # game end, check win or lose
            try:
                result = ''
                if free_game == False:
                    won_x = 2
                    if won:
                        COIN_NAME = random.choice(GAME_COIN)
                        amount = GAME_SLOT_REWARD[COIN_NAME] * won_x
                        if COIN_NAME in ENABLE_COIN_ERC:
                            coin_family = "ERC-20"
                        elif COIN_NAME in ENABLE_COIN_TRC:
                            coin_family = "TRC-20"
                        else:
                            coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                        real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
                        reward = await store.sql_game_add('{}:{}:{}:{}'.format(dice_time, sum_dice, dice1, dice2), str(ctx.author.id), COIN_NAME, 'WIN', real_amount, get_decimal(COIN_NAME), str(ctx.guild.id), 'DICE', int(time.time()) - time_start, SERVER_BOT)
                        result = f'You won! {ctx.author.mention} got reward of **{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}** to Tip balance!'
                    else:
                        reward = await store.sql_game_add('{}:{}:{}:{}'.format(dice_time, sum_dice, dice1, dice2), str(ctx.author.id), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'DICE', int(time.time()) - time_start, SERVER_BOT)
                        result = f'You lose!'
                else:
                    if won:
                        result = f'You won! but this is a free game without **reward**! Waiting to refresh your paid plays (24h max).'
                    else:
                        result = f'You lose!'
                    try:
                        await store.sql_game_free_add('{}:{}:{}:{}'.format(dice_time, sum_dice, dice1, dice2), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'DICE', int(time.time()) - time_start, SERVER_BOT)
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                await ctx.reply(f'{ctx.author.mention} **Dice: ** You threw dices **{dice_time}** times. {result}')
                if ctx.author.id in GAME_DICE_IN_PRGORESS:
                    GAME_DICE_IN_PRGORESS.remove(ctx.author.id)
                if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                    GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
            except Exception as e:
                await logchanbot(traceback.format_exc())
        except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            await ctx.message.add_reaction(EMOJI_ERROR)
        except Exception as e:
            await logchanbot(traceback.format_exc())
        if ctx.author.id in GAME_DICE_IN_PRGORESS:
            GAME_DICE_IN_PRGORESS.remove(ctx.author.id)
        if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)


    @game.command(
        usage="game snail <number>", 
        aliases=['snailrace'], 
        description="Snail racing game. You bet which one."
    )
    async def snail(
        self, 
        ctx, 
        bet_numb: str=None
    ):
        await self.bot_log()

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo and 'enable_game' in serverinfo and serverinfo['enable_game'] == "NO":
            prefix = serverinfo['prefix']
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Game is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING GAME`')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}game** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
            return

        # Credit: https://github.com/asweigart/PythonStdioGames
        free_game = False

        # check if user create account less than 3 days
        try:
            account_created = ctx.author.created_at
            if (datetime.utcnow() - account_created).total_seconds() <= config.game.account_age_to_play:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Your account is very new. Wait a few days before using this.')
                return
        except Exception as e:
            await logchanbot(traceback.format_exc())

        try: 
            index_game = "game_snail_channel"
            # check if bot channel is set:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if serverinfo and serverinfo[index_game]:
                if ctx.channel.id != int(serverinfo[index_game]):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    gameChan = self.bot.get_channel(int(serverinfo[index_game]))
                    if gameChan:
                        await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, {gameChan.mention} is for game **snail** channel!!!')
                        return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            pass
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
        # end of bot channel check

        if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
            await ctx.reply(f'{ctx.author.mention} You are ongoing with one **game** play.')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return

        count_played = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, False)
        count_played_free = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, True)
        if count_played and count_played >= config.game.max_daily_play:
            free_game = True
            await ctx.message.add_reaction(EMOJI_ALARMCLOCK)

        time_start = int(time.time())
        won = False
        game_text = '''Snail Race, Fast-paced snail racing action!'''
        # We do not always show credit
        if random.randint(1,100) < 30:
            msg = await ctx.reply(f'{ctx.author.mention} ```{game_text}```')
            await msg.add_reaction(EMOJI_OK_BOX)

        if bet_numb is None:
            await ctx.reply(f'{ctx.author.mention} There are 8 snail racers. Please put your snail number **(1 to 8)**')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return
        else:
            your_snail = 0
            try:
                your_snail = int(bet_numb)
            except ValueError:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Please put a valid snail number **(1 to 8)**')
                return
            if ctx.author.id not in GAME_INTERACTIVE_PRGORESS:
                GAME_INTERACTIVE_PRGORESS.append(ctx.author.id)

            MAX_NUM_SNAILS = 8
            MAX_NAME_LENGTH = 20
            FINISH_LINE = 22  # (!) Try modifying this number.

            if 1 <= your_snail <= MAX_NUM_SNAILS:
                # valid betting
                # sleep 1s
                await asyncio.sleep(1)
                try:
                    game_over = False
                    # Enter the names of each snail:
                    snailNames = []  # List of the string snail names.
                    for i in range(1, MAX_NUM_SNAILS + 1):
                        snailNames.append("#" + str(i))
                    start_line_mention = '{}#{} bet for #{}\n'.format(ctx.author.name, ctx.author.discriminator, your_snail)
                    
                    start_line = 'START' + (' ' * (FINISH_LINE - len('START')) + 'FINISH') + '\n'
                    start_line += '|' + (' ' * (FINISH_LINE - len('|')) + '|')
                    try:
                        msg_racing = await ctx.reply(f'{start_line_mention}```{start_line}```')
                    except Exception as e:
                        if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                            GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                        await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} **GAME SNAIL** failed to send message in {ctx.guild.name} / {ctx.guild.id}')
                        return

                    # sleep 2s
                    await asyncio.sleep(2)
                    snailProgress = {}
                    list_snails = ''
                    for snailName in snailNames:
                        list_snails += snailName[:MAX_NAME_LENGTH] + '\n'
                        list_snails += '@v'
                        snailProgress[snailName] = 0
                    try:
                        await msg_racing.edit(content=f'{start_line_mention}```{start_line}\n{list_snails}```')
                    except Exception as e:
                        if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                            GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                        await ctx.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} Failed to start snail game, please try again.')
                        return

                    while not game_over:
                        # Pick random snails to move forward:
                        for i in range(random.randint(1, MAX_NUM_SNAILS // 2)):
                            randomSnailName = random.choice(snailNames)
                            snailProgress[randomSnailName] += 1

                            # Check if a snail has reached the finish line:
                            if snailProgress[randomSnailName] == FINISH_LINE:
                                game_over = True
                                if '#' + str(your_snail) == randomSnailName:
                                    # You won
                                    won = True
                                # add to DB, game end, check win or lose
                                try:
                                    result = ''
                                    if free_game == False:
                                        won_x = 10
                                        if won:
                                            COIN_NAME = random.choice(GAME_COIN)
                                            amount = GAME_SLOT_REWARD[COIN_NAME] * won_x
                                            if COIN_NAME in ENABLE_COIN_ERC:
                                                coin_family = "ERC-20"
                                            elif COIN_NAME in ENABLE_COIN_TRC:
                                                coin_family = "TRC-20"
                                            else:
                                                coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                                            real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
                                            reward = await store.sql_game_add('BET:#{}/WINNER:{}'.format(your_snail, randomSnailName), str(ctx.author.id), COIN_NAME, 'WIN', real_amount, get_decimal(COIN_NAME), str(ctx.guild.id), 'SNAIL', int(time.time()) - time_start, SERVER_BOT)
                                            result = f'You won **snail#{str(your_snail)}**! {ctx.author.mention} got reward of **{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}** to Tip balance!'
                                        else:
                                            reward = await store.sql_game_add('BET:#{}/WINNER:{}'.format(your_snail, randomSnailName), str(ctx.author.id), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'SNAIL', int(time.time()) - time_start, SERVER_BOT)
                                            result = f'You lose! **snail{randomSnailName}** is the winner!!! You bet for **snail#{str(your_snail)}**'
                                    else:
                                        if won:
                                            result = f'You won! **snail#{str(your_snail)}** but this is a free game without **reward**! Waiting to refresh your paid plays (24h max).'
                                        else:
                                            result = f'You lose! **snail{randomSnailName}** is the winner!!! You bet for **snail#{str(your_snail)}**'
                                        try:
                                            await store.sql_game_free_add('BET:#{}/WINNER:{}'.format(your_snail, randomSnailName), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'SNAIL', int(time.time()) - time_start, SERVER_BOT)
                                        except Exception as e:
                                            await logchanbot(traceback.format_exc())
                                    await ctx.reply(f'{ctx.author.mention} **Snail Racing** {result}')
                                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                                    return
                                except Exception as e:
                                    await logchanbot(traceback.format_exc())
                                break
                        # (!) EXPERIMENT: Add a cheat here that increases a snail's progress
                        # if it has your name.

                        await asyncio.sleep(0.5)  # (!) EXPERIMENT: Try changing this value.
                        # Display the snails (with name tags):
                        list_snails = ''
                        for snailName in snailNames:
                            spaces = snailProgress[snailName]
                            list_snails += (' ' * spaces) + snailName[:MAX_NAME_LENGTH]
                            list_snails += '\n'
                            list_snails += ('.' * snailProgress[snailName]) + '@v'
                            list_snails += '\n'
                        try:
                            await msg_racing.edit(content=f'{start_line_mention}```{start_line}\n{list_snails}```')
                        except Exception as e:
                            if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                                GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                            await logchanbot(traceback.format_exc())
                            return
                    return
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                    GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
            else:
                # invalid betting
                if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                    GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Please put a valid snail number **(1 to 8)**')
                return


    @game.command(
        usage="game g2048", 
        aliases=['2048'], 
        description="Classic 2048 game. Slide all the tiles on the board in one of four directions."
    )
    async def g2048(self, ctx):
        await self.bot_log()

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo and 'enable_game' in serverinfo and serverinfo['enable_game'] == "NO":
            prefix = serverinfo['prefix']
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Game is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING GAME`')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}game** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
            return

        # Credit: https://github.com/asweigart/PythonStdioGames
        free_game = False

        # check if user create account less than 3 days
        try:
            account_created = ctx.author.created_at
            if (datetime.utcnow() - account_created).total_seconds() <= config.game.account_age_to_play:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Your account is very new. Wait a few days before using this.')
                return
        except Exception as e:
            await logchanbot(traceback.format_exc())

        try: 
            index_game = "game_2048_channel"
            # check if bot channel is set:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if serverinfo and serverinfo[index_game]:
                if ctx.channel.id != int(serverinfo[index_game]):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    gameChan = self.bot.get_channel(int(serverinfo[index_game]))
                    if gameChan:
                        await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, {gameChan.mention} is for game **2048** channel!!!')
                        return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            pass
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
        # end of bot channel check

        if ctx.author.id not in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.append(ctx.author.id)
        else:
            await ctx.reply(f'{ctx.author.mention} You are ongoing with one **game** play.')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return

        count_played = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, False)
        count_played_free = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, True)
        if count_played and count_played >= config.game.max_daily_play:
            free_game = True
            await ctx.message.add_reaction(EMOJI_ALARMCLOCK)

        won = False
        score = 0
        game_text = '''
    Slide all the tiles on the board in one of four directions. Tiles with
    like numbers will combine into larger-numbered tiles. A new 2 tile is
    added to the board on each move. You win if you can create a 2048 tile.
    You lose if the board fills up the tiles before then.'''
        # We do not always show credit
        if random.randint(1,100) < 30:
            msg = await ctx.reply(f'{ctx.author.mention} ```{game_text}```')
            await msg.add_reaction(EMOJI_OK_BOX)

        game_over = False
        gameBoard = g2048_getNewBoard()
        try:
            board = g2048_drawBoard(gameBoard) # string
            try:
                msg = await ctx.reply(f'**GAME 2048 starts**...')
            except Exception as e:
                if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                    GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} **GAME 2048** failed to send message in {ctx.guild.name} / {ctx.guild.id}')
                return

            await msg.add_reaction(EMOJI_UP)
            await msg.add_reaction(EMOJI_DOWN)
            await msg.add_reaction(EMOJI_LEFT)
            await msg.add_reaction(EMOJI_RIGHT)
            await msg.add_reaction(EMPTY_DISPLAY)
            await msg.add_reaction(EMOJI_OK_BOX)
            time_start = int(time.time())

            while not game_over:
                try:
                    await msg.edit(content=f'{ctx.author.mention}```GAME 2048\n{board}```Your score: **{score}**')
                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} **GAME 2048** was deleted or I can not find it. Game stop!')
                    return
                score = g2048_getScore(gameBoard)
                if IS_RESTARTING:
                    await ctx.message.add_reaction(EMOJI_REFRESH)
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
                    return
                def check(reaction, user):
                    return user == ctx.author and reaction.message.author == self.bot.user and reaction.message.id == msg.id and str(reaction.emoji) \
                    in (EMOJI_UP, EMOJI_DOWN, EMOJI_LEFT, EMOJI_RIGHT, EMOJI_OK_BOX)

                done, pending = await asyncio.wait([
                                    self.bot.wait_for('reaction_remove', timeout=120, check=check),
                                    self.bot.wait_for('reaction_add', timeout=120, check=check)
                                ], return_when=asyncio.FIRST_COMPLETED)
                try:
                    # stuff = done.pop().result()
                    reaction, user = done.pop().result()
                except asyncio.TimeoutError:
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    if free_game == True:
                        try:
                            await store.sql_game_free_add(board, str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), '2048', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(board, str(ctx.author.id), 'None', 'WIN' if won else 'LOSE', 0, 0, str(ctx.guild.id), '2048', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    await ctx.reply(f'{ctx.author.mention} **2048 GAME** has waited you too long. Game exits. Your score **{score}**.')
                    game_over = True
                    return
                for future in pending:
                    future.cancel()  # we don't need these anymore

                if str(reaction.emoji) == EMOJI_OK_BOX:
                    await ctx.reply(f'{ctx.author.mention} You gave up the current game. Your score **{score}**.')
                    game_over = True
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)

                    if free_game == True:
                        try:
                            await store.sql_game_free_add(board, str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), '2048', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(board, str(ctx.author.id), 'None', 'WIN' if won else 'LOSE', 0, 0, str(ctx.guild.id), '2048', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    await asyncio.sleep(1)
                    try:
                        await msg.delete()
                    except Exception as e:
                        pass
                    break
                    return

                playerMove = None
                if str(reaction.emoji) == EMOJI_UP:
                    playerMove = 'W'
                elif str(reaction.emoji) == EMOJI_DOWN:
                    playerMove = 'S'
                elif str(reaction.emoji) == EMOJI_LEFT:
                    playerMove = 'A'
                elif str(reaction.emoji) == EMOJI_RIGHT:
                    playerMove = 'D'
                if playerMove in ('W', 'A', 'S', 'D'):
                    gameBoard = g2048_makeMove(gameBoard, playerMove)
                    g2048_addTwoToBoard(gameBoard)
                    board = g2048_drawBoard(gameBoard)
                if g2048_isFull(gameBoard):
                    game_over = True
                    won = True # we assume won but it is not a winner
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    board = g2048_drawBoard(gameBoard)

                    # Handle whether the player won, lost, or tied:
                    COIN_NAME = random.choice(GAME_COIN)
                    amount = GAME_SLOT_REWARD[COIN_NAME] * (int(score / 100) if score / 100 > 1 else 1) # testing first
                    if COIN_NAME in ENABLE_COIN_ERC:
                        coin_family = "ERC-20"
                    elif COIN_NAME in ENABLE_COIN_TRC:
                        coin_family = "TRC-20"
                    else:
                        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                    real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
                    result = f'You got reward of **{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}** to Tip balance!'
                    duration = seconds_str(int(time.time()) - time_start)
                    if free_game == True:
                        result = f'You do not get any reward because it is a free game! Waiting to refresh your paid plays (24h max).'
                        try:
                            await store.sql_game_free_add(board, str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), '2048', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(board, str(ctx.author.id), COIN_NAME, 'WIN' if won else 'LOSE', real_amount if won else 0, get_decimal(COIN_NAME) if won else 0, str(ctx.guild.id), '2048', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    await msg.edit(content=f'**{ctx.author.mention} Game Over**```{board}```Your score: **{score}**\nYou have spent time: **{duration}**\n{result}')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return

        except Exception as e:
            await logchanbot(traceback.format_exc())
        if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)


    @commands.is_owner()
    @game.command(usage="game sokotest", hidden = True)
    async def sokotest(self, ctx, level:int=0):
        await self.bot_log()

        # Set up the constants:
        WIDTH = 'width'
        HEIGHT = 'height'

        # Characters in level files that represent objects:
        WALL = '#'
        FACE = '@'
        CRATE = '$'
        GOAL = '.'
        CRATE_ON_GOAL = '*'
        PLAYER_ON_GOAL = '+'
        EMPTY = ' '

        # How objects should be displayed on the screen:
        # WALL_DISPLAY = random.choice([':red_square:', ':orange_square:', ':yellow_square:', ':blue_square:', ':purple_square:']) # '#' # chr(9617)   # Character 9617 is '░'
        WALL_DISPLAY = random.choice(['🟥', '🟧', '🟨', '🟦', '🟪'])
        FACE_DISPLAY = '<:smiling_face:700888455877754991>'
        # CRATE_DISPLAY = ':brown_square:'  # Character 9679 is '▪'
        CRATE_DISPLAY = '🟫'
        # GOAL_DISPLAY = ':negative_squared_cross_mark:'
        GOAL_DISPLAY = '❎'
        # A list of chr() codes is at https://inventwithpython.com/chr
        # CRATE_ON_GOAL_DISPLAY = ':green_square:'
        CRATE_ON_GOAL_DISPLAY = '🟩'
        PLAYER_ON_GOAL_DISPLAY = '<:grinning_face:700888456028487700>'
        # EMPTY_DISPLAY = ':black_large_square:'
        # EMPTY_DISPLAY = '⬛' # already initial

        CHAR_MAP = {WALL: WALL_DISPLAY, FACE: FACE_DISPLAY,
                    CRATE: CRATE_DISPLAY, PLAYER_ON_GOAL: PLAYER_ON_GOAL_DISPLAY,
                    GOAL: GOAL_DISPLAY, CRATE_ON_GOAL: CRATE_ON_GOAL_DISPLAY,
                    EMPTY: EMPTY_DISPLAY}

        won = False
        game_text = f'''Push the solid crates {CRATE_DISPLAY} onto the {GOAL_DISPLAY}. You can only push,
    you cannot pull. Re-act with direction to move up-left-down-right,
    respectively. You can also reload game level.'''
        # We do not always show credit
        if random.randint(1,100) < 30:
            msg = await ctx.reply(f'{ctx.author.mention} ```{game_text}```')
            await msg.add_reaction(EMOJI_OK_BOX)

        get_level = await store.sql_game_get_level_tpl(level, 'SOKOBAN')
        
        if get_level is None:
            await ctx.reply(f'{ctx.author.mention} Check back later.')
            await ctx.message.add_reaction(EMOJI_INFORMATION)
            return

        def loadLevel(level_str: str):
            level_str = level_str
            currentLevel = {WIDTH: 0, HEIGHT: 0}
            y = 0

            # Add the line to the current level.
            # We use line[:-1] so we don't include the newline:
            for line in level_str.splitlines():
                line += "\n"
                for x, levelChar in enumerate(line[:-1]):
                    currentLevel[(x, y)] = levelChar
                y += 1

                if len(line) - 1 > currentLevel[WIDTH]:
                    currentLevel[WIDTH] = len(line) - 1
                if y > currentLevel[HEIGHT]:
                    currentLevel[HEIGHT] = y

            return currentLevel

        def displayLevel(levelData):
            # Draw the current level.
            solvedCrates = 0
            unsolvedCrates = 0

            level_display = ''
            for y in range(levelData[HEIGHT]):
                for x in range(levelData[WIDTH]):
                    if levelData.get((x, y), EMPTY) == CRATE:
                        unsolvedCrates += 1
                    elif levelData.get((x, y), EMPTY) == CRATE_ON_GOAL:
                        solvedCrates += 1
                    prettyChar = CHAR_MAP[levelData.get((x, y), EMPTY)]
                    level_display += prettyChar
                level_display += '\n'
            totalCrates = unsolvedCrates + solvedCrates
            level_display += "\nSolved: {}/{}".format(solvedCrates, totalCrates)
            return level_display

        currentLevel = loadLevel(get_level['template_str'])
        display_level = displayLevel(currentLevel)

        embed = discord.Embed(title=f'SOKOBAN GAME TEST RUN {ctx.author.name}#{ctx.author.discriminator}', description=f'{display_level}', timestamp=datetime.utcnow(), colour=7047495)
        embed.add_field(name="LEVEL", value=f'{level}')
        embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", 
                        "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
        try:
            msg = await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} **GAME SOKOBAN** failed to send embed in {ctx.guild.name} / {ctx.guild.id}')
            return


    @game.command(
        usage="game sokoban", 
        aliases=['soko'], 
        description="Sokoban interactive game."
    )
    async def sokoban(self, ctx):
        await self.bot_log()

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if serverinfo and 'enable_game' in serverinfo and serverinfo['enable_game'] == "NO":
            prefix = serverinfo['prefix']
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Game is not ENABLE yet in this guild. Please request Guild owner to enable by `{prefix}SETTING GAME`')
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} tried **{prefix}game** in {ctx.guild.name} / {ctx.guild.id} which is not ENABLE.')
            return

        free_game = False

        # check if user create account less than 3 days
        try:
            account_created = ctx.author.created_at
            if (datetime.utcnow() - account_created).total_seconds() <= config.game.account_age_to_play:
                await ctx.message.add_reaction(EMOJI_ERROR)
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Your account is very new. Wait a few days before using this.')
                return
        except Exception as e:
            await logchanbot(traceback.format_exc())

        try: 
            index_game = "game_sokoban_channel"
            # check if bot channel is set:
            serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
            if serverinfo and serverinfo[index_game]:
                if ctx.channel.id != int(serverinfo[index_game]):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    gameChan = self.bot.get_channel(int(serverinfo[index_game]))
                    if gameChan:
                        await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, {gameChan.mention} is for game **sokoban** channel!!!')
                        return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            pass
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await logchanbot(traceback.format_exc())
        # end of bot channel check

        if ctx.author.id not in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.append(ctx.author.id)
        else:
            await ctx.reply(f'{ctx.author.mention} You are ongoing with one **game** play.')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return

        count_played = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, False)
        count_played_free = await store.sql_game_count_user(str(ctx.author.id), config.game.duration_24h, SERVER_BOT, True)
        if count_played and count_played >= config.game.max_daily_play:
            free_game = True
            await ctx.message.add_reaction(EMOJI_ALARMCLOCK)

        # Set up the constants:
        WIDTH = 'width'
        HEIGHT = 'height'

        # Characters in level files that represent objects:
        WALL = '#'
        FACE = '@'
        CRATE = '$'
        GOAL = '.'
        CRATE_ON_GOAL = '*'
        PLAYER_ON_GOAL = '+'
        EMPTY = ' '

        # How objects should be displayed on the screen:
        # WALL_DISPLAY = random.choice([':red_square:', ':orange_square:', ':yellow_square:', ':blue_square:', ':purple_square:']) # '#' # chr(9617)   # Character 9617 is '░'
        WALL_DISPLAY = random.choice(['🟥', '🟧', '🟨', '🟦', '🟪'])
        FACE_DISPLAY = ':zany_face:' # '<:smiling_face:700888455877754991>' some guild not support having this
        # CRATE_DISPLAY = ':brown_square:'  # Character 9679 is '▪'
        CRATE_DISPLAY = '🟫'
        # GOAL_DISPLAY = ':negative_squared_cross_mark:'
        GOAL_DISPLAY = '❎'
        # A list of chr() codes is at https://inventwithpython.com/chr
        # CRATE_ON_GOAL_DISPLAY = ':green_square:'
        CRATE_ON_GOAL_DISPLAY = '🟩'
        PLAYER_ON_GOAL_DISPLAY = '😁' # '<:grinning_face:700888456028487700>'
        # EMPTY_DISPLAY = ':black_large_square:'
        # EMPTY_DISPLAY = '⬛' already initial

        CHAR_MAP = {WALL: WALL_DISPLAY, FACE: FACE_DISPLAY,
                    CRATE: CRATE_DISPLAY, PLAYER_ON_GOAL: PLAYER_ON_GOAL_DISPLAY,
                    GOAL: GOAL_DISPLAY, CRATE_ON_GOAL: CRATE_ON_GOAL_DISPLAY,
                    EMPTY: EMPTY_DISPLAY}

        won = False
        game_text = f'''Push the solid crates {CRATE_DISPLAY} onto the {GOAL_DISPLAY}. You can only push,
    you cannot pull. Re-act with direction to move up-left-down-right,
    respectively. You can also reload game level.'''
        # We do not always show credit
        if random.randint(1,100) < 30:
            msg = await ctx.reply(f'{ctx.author.mention} ```{game_text}```')
            await msg.add_reaction(EMOJI_OK_BOX)

        # get max level user already played.
        level = 0
        get_level_user = await store.sql_game_get_level_user(str(ctx.author.id), 'SOKOBAN')
        print(get_level_user)
        if get_level_user < 0:
            level = 0
        elif get_level_user >= 0:
            level = get_level_user + 1

        get_level = await store.sql_game_get_level_tpl(level, 'SOKOBAN')
        
        if get_level is None:
            if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
            await ctx.reply(f'{ctx.author.mention} Check back later.')
            await ctx.message.add_reaction(EMOJI_INFORMATION)
            await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} **GAME SOKOBAN** failed get level **{str(level)}** in {ctx.guild.name} / {ctx.guild.id}')
            return


        def loadLevel(level_str: str):
            level_str = level_str
            currentLevel = {WIDTH: 0, HEIGHT: 0}
            y = 0

            # Add the line to the current level.
            # We use line[:-1] so we don't include the newline:
            for line in level_str.splitlines():
                line += "\n"
                for x, levelChar in enumerate(line[:-1]):
                    currentLevel[(x, y)] = levelChar
                y += 1

                if len(line) - 1 > currentLevel[WIDTH]:
                    currentLevel[WIDTH] = len(line) - 1
                if y > currentLevel[HEIGHT]:
                    currentLevel[HEIGHT] = y

            return currentLevel

        def displayLevel(levelData):
            # Draw the current level.
            solvedCrates = 0
            unsolvedCrates = 0

            level_display = ''
            for y in range(levelData[HEIGHT]):
                for x in range(levelData[WIDTH]):
                    if levelData.get((x, y), EMPTY) == CRATE:
                        unsolvedCrates += 1
                    elif levelData.get((x, y), EMPTY) == CRATE_ON_GOAL:
                        solvedCrates += 1
                    prettyChar = CHAR_MAP[levelData.get((x, y), EMPTY)]
                    level_display += prettyChar
                level_display += '\n'
            totalCrates = unsolvedCrates + solvedCrates
            level_display += "\nSolved: {}/{}".format(solvedCrates, totalCrates)
            return level_display

        game_over = False

        try:
            currentLevel = loadLevel(get_level['template_str'])
            display_level = displayLevel(currentLevel)

            embed = discord.Embed(title=f'SOKOBAN GAME {ctx.author.name}#{ctx.author.discriminator}', description='**SOKOBAN GAME** starts...', timestamp=datetime.utcnow(), colour=7047495)
            embed.add_field(name="LEVEL", value=f'{level}')
            embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", 
                            "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
            try:
                msg = await ctx.reply(embed=embed)
            except Exception as e:
                if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                    GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                await self.botLogChan.send(f'{ctx.author.name} / {ctx.author.id} **GAME SOKOBAN** failed to send embed in {ctx.guild.name} / {ctx.guild.id}')
                await ctx.reply(f'{ctx.author.mention} I can not send any embed message here. Seemed no permission.')
                return
            await msg.add_reaction(EMOJI_UP)
            await msg.add_reaction(EMOJI_DOWN)
            await msg.add_reaction(EMOJI_LEFT)
            await msg.add_reaction(EMOJI_RIGHT)
            await msg.add_reaction(EMPTY_DISPLAY)
            await msg.add_reaction(EMOJI_REFRESH)
            await msg.add_reaction(EMOJI_OK_BOX)
            time_start = int(time.time())
            while not game_over:
                if IS_RESTARTING:
                    await ctx.message.add_reaction(EMOJI_REFRESH)
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
                    return

                display_level = displayLevel(currentLevel)
                embed = discord.Embed(title=f'SOKOBAN GAME {ctx.author.name}#{ctx.author.discriminator}', description=f'{display_level}', timestamp=datetime.utcnow(), colour=7047495)
                embed.add_field(name="LEVEL", value=f'{level}')
                embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", 
                                "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
                try:
                    await msg.edit(embed=embed)
                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} **GAME SOKOBAN** was deleted or I can not find it. Game stop!')
                    return
                # Find the player position:
                for position, character in currentLevel.items():
                    if character in (FACE, PLAYER_ON_GOAL):
                        playerX, playerY = position

                def check(reaction, user):
                    return user == ctx.author and reaction.message.author == self.bot.user and reaction.message.id == msg.id and str(reaction.emoji) \
                    in (EMOJI_UP, EMOJI_DOWN, EMOJI_LEFT, EMOJI_RIGHT, EMOJI_OK_BOX, EMOJI_REFRESH)

                done, pending = await asyncio.wait([
                                    self.bot.wait_for('reaction_remove', timeout=120, check=check),
                                    self.bot.wait_for('reaction_add', timeout=120, check=check)
                                ], return_when=asyncio.FIRST_COMPLETED)
                try:
                    # stuff = done.pop().result()
                    reaction, user = done.pop().result()
                except (asyncio.TimeoutError, asyncio.exceptions.TimeoutError) as e:
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
                    await ctx.reply(f'{ctx.author.mention} **SOKOBAN GAME** has waited you too long. Game exits.')
                    game_over = True

                    if free_game == True:
                        try:
                            await store.sql_game_free_add(str(level), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'SOKOBAN', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(str(level), str(ctx.author.id), 'None', 'WIN' if won else 'LOSE', 0, 0, str(ctx.guild.id), 'SOKOBAN', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    return
                for future in pending:
                    future.cancel()  # we don't need these anymore

                if str(reaction.emoji) == EMOJI_OK_BOX:
                    await ctx.reply(f'{ctx.author.mention} **SOKOBAN GAME** You gave up the current game.')
                    game_over = True
                    if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                        GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)

                    if free_game == True:
                        try:
                            await store.sql_game_free_add(str(level), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'SOKOBAN', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    else:
                        try:
                            reward = await store.sql_game_add(str(level), str(ctx.author.id), 'None', 'WIN' if won else 'LOSE', 0, 0, str(ctx.guild.id), 'SOKOBAN', int(time.time()) - time_start, SERVER_BOT)
                        except Exception as e:
                            await logchanbot(traceback.format_exc())
                    await asyncio.sleep(1)
                    try:
                        await msg.delete()
                    except Exception as e:
                        pass
                    break
                    return
                elif str(reaction.emoji) == EMOJI_REFRESH:
                    embed = discord.Embed(title=f'SOKOBAN GAME {ctx.author.name}#{ctx.author.discriminator}', description=f'**SOKOBAN GAME** reloading level **{level}**', timestamp=datetime.utcnow(), colour=7047495)
                    embed.add_field(name="LEVEL", value=f'{level}')
                    embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", 
                                    "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
                    await msg.edit(embed=embed)
                    currentLevel = loadLevel(get_level['template_str'])
                    await asyncio.sleep(2)
                    continue
                elif str(reaction.emoji) == EMOJI_UP:
                    moveX, moveY = 0, -1
                elif str(reaction.emoji) == EMOJI_DOWN:
                    moveX, moveY = 0, 1
                elif str(reaction.emoji) == EMOJI_LEFT:
                    moveX, moveY = -1, 0
                elif str(reaction.emoji) == EMOJI_RIGHT:
                     moveX, moveY = 1, 0
     
                moveToX = playerX + moveX
                moveToY = playerY + moveY
                moveToSpace = currentLevel.get((moveToX, moveToY), EMPTY)

                # If the move-to space is empty or a goal, just move there:
                if moveToSpace == EMPTY or moveToSpace == GOAL:
                    # Change the player's old position:
                    if currentLevel[(playerX, playerY)] == FACE:
                        currentLevel[(playerX, playerY)] = EMPTY
                    elif currentLevel[(playerX, playerY)] == PLAYER_ON_GOAL:
                        currentLevel[(playerX, playerY)] = GOAL

                    # Set the player's new position:
                    if moveToSpace == EMPTY:
                        currentLevel[(moveToX, moveToY)] = FACE
                    elif moveToSpace == GOAL:
                        currentLevel[(moveToX, moveToY)] = PLAYER_ON_GOAL

                # If the move-to space is a wall, don't move at all:
                elif moveToSpace == WALL:
                    pass

                # If the move-to space has a crate, see if we can push it:
                elif moveToSpace in (CRATE, CRATE_ON_GOAL):
                    behindMoveToX = playerX + (moveX * 2)
                    behindMoveToY = playerY + (moveY * 2)
                    behindMoveToSpace = currentLevel.get((behindMoveToX, behindMoveToY), EMPTY)
                    if behindMoveToSpace in (WALL, CRATE, CRATE_ON_GOAL):
                        # Can't push the crate because there's a wall or
                        # crate behind it:
                        continue
                    if behindMoveToSpace in (GOAL, EMPTY):
                        # Change the player's old position:
                        if currentLevel[(playerX, playerY)] == FACE:
                            currentLevel[(playerX, playerY)] = EMPTY
                        elif currentLevel[(playerX, playerY)] == PLAYER_ON_GOAL:
                            currentLevel[(playerX, playerY)] = GOAL

                        # Set the player's new position:
                        if moveToSpace == CRATE:
                            currentLevel[(moveToX, moveToY)] = FACE
                        elif moveToSpace == CRATE_ON_GOAL:
                            currentLevel[(moveToX, moveToY)] = PLAYER_ON_GOAL

                        # Set the crate's new position:
                        if behindMoveToSpace == EMPTY:
                            currentLevel[(behindMoveToX, behindMoveToY)] = CRATE
                        elif behindMoveToSpace == GOAL:
                            currentLevel[(behindMoveToX, behindMoveToY)] = CRATE_ON_GOAL

                # Check if the player has finished the level:
                levelIsSolved = True
                for position, character in currentLevel.items():
                    if character == CRATE:
                        levelIsSolved = False
                        break
                display_level = displayLevel(currentLevel)
                if levelIsSolved:
                    won = True
                    # game end, check win or lose
                    try:
                        result = ''
                        if free_game == False:
                            won_x = 2
                            if won:
                                COIN_NAME = random.choice(GAME_COIN)
                                amount = GAME_SLOT_REWARD[COIN_NAME] * won_x
                                if COIN_NAME in ENABLE_COIN_ERC:
                                    coin_family = "ERC-20"
                                elif COIN_NAME in ENABLE_COIN_TRC:
                                    coin_family = "TRC-20"
                                else:
                                    coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
                                real_amount = int(amount * get_decimal(COIN_NAME)) if coin_family in ["BCN", "XMR", "TRTL", "NANO", "XCH"] else float(amount)
                                reward = await store.sql_game_add(str(level), str(ctx.author.id), COIN_NAME, 'WIN', real_amount, get_decimal(COIN_NAME), str(ctx.guild.id), 'SOKOBAN', int(time.time()) - time_start, SERVER_BOT)
                                result = f'You won! {ctx.author.mention} got reward of **{num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}** to Tip balance!'
                            else:
                                reward = await store.sql_game_add(str(level), 'None', 'LOSE', 0, 0, str(ctx.guild.id), 'SOKOBAN', int(time.time()) - time_start, SERVER_BOT)
                                result = f'You lose!'
                        else:
                            if won:
                                result = f'You won! but this is a free game without **reward**! Waiting to refresh your paid plays (24h max).'
                            else:
                                result = f'You lose!'
                            try:
                                await store.sql_game_free_add(str(level), str(ctx.author.id), 'WIN' if won else 'LOSE', str(ctx.guild.id), 'SOKOBAN', int(time.time()) - time_start, SERVER_BOT)
                            except Exception as e:
                                await logchanbot(traceback.format_exc())
                        await ctx.reply(f'{ctx.author.mention} **SOKOBAN GAME** {result}')
                        if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                            GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)

                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                    embed = discord.Embed(title=f'SOKOBAN GAME FINISHED {ctx.author.name}#{ctx.author.discriminator}', description=f'{display_level}', timestamp=datetime.utcnow(), colour=7047495)
                    embed.add_field(name="LEVEL", value=f'{level}')
                    duration = seconds_str(int(time.time()) - time_start)
                    embed.add_field(name="DURATION", value=f'{duration}')
                    embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", 
                                    "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
                    await msg.edit(embed=embed)
                    game_over = True
                    break
                    return

            if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
                GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)
            return
        except Exception as e:
            await logchanbot(traceback.format_exc())
        if ctx.author.id in GAME_INTERACTIVE_PRGORESS:
            GAME_INTERACTIVE_PRGORESS.remove(ctx.author.id)

def setup(bot):
    bot.add_cog(Games(bot))