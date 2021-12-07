import sys, traceback
import time, timeago
import discord
from discord.ext import commands
from dislash import InteractionClient, ActionRow, Button, ButtonStyle, Option, OptionType

from config import config
from Bot import *

class BotBalance(commands.Cog):

    def __init__(self, bot):
        self.bot = bot



    @inter_client.slash_command(usage="botbalance <bot> <coin>",
                                options=[
                                    Option("botname", "Enter a bot", OptionType.USER, required=True),
                                    Option("coin", "Enter coin ticker/name", OptionType.STRING, required=True),
                                ],
                                description="Get Bot's balance by mention it.")
    async def botbalance(
        self, 
        ctx, 
        botname: discord.Member, 
        coin: str
    ):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} This command can not be in DM.')
            return

        if botname == ctx.author:
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Do you think you are a bot?')
            return
        if botname.bot == False:
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Only for bot!!')
            return
        else:
            user_id = botname.id
            COIN_NAME = coin.upper()
            balance_user = await get_balance_coin_user(user_id, COIN_NAME, discord_guild=False, server__bot=SERVER_BOT)
            embed = discord.Embed(title=f'Deposit for {botname.name}#{botname.discriminator}', description='`This is bot\'s tipjar address. Do not deposit here unless you want to deposit to this bot`', timestamp=datetime.utcnow(), colour=7047495)
            embed.set_author(name=botname.name, icon_url=botname.display_avatar)
            embed.add_field(name="{} Deposit Address".format(COIN_NAME), value="`{}`".format(balance_user['balance_wallet_address']), inline=False)
            if COIN_NAME in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
                token_info = await store.get_token_info(COIN_NAME)
                if token_info and COIN_NAME in ENABLE_COIN_ERC and token_info['contract'] and len(token_info['contract']) == 42:
                    embed.add_field(name="{} Contract".format(COIN_NAME), value="`{}`".format(token_info['contract']), inline=False)
                elif token_info and COIN_NAME in ENABLE_COIN_TRC and token_info['contract'] and len(token_info['contract']) >= 6:
                    embed.add_field(name="{} Contract/Token ID".format(COIN_NAME), value="`{}`".format(token_info['contract']), inline=False)
                if token_info and token_info['deposit_note']:
                    embed.add_field(name="{} Deposit Note".format(COIN_NAME), value="`{}`".format(token_info['deposit_note']), inline=False)
            embed.add_field(name=f"Balance {COIN_NAME}", value="`{} {}`".format(balance_user['balance_actual'], COIN_NAME), inline=False)
            await ctx.reply(embed=embed)


    @commands.command(
        usage="botbalance <bot> <coin>", 
        aliases=['botbal'], 
        description="Get Bot's balance by mention it."
    )
    async def botbalance(
        self, 
        ctx, 
        member: discord.Member, 
        coin: str
    ):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} This command can not be in DM.')
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
                        botChan = self.bot.get_channel(int(serverinfo['botchan']))
                        await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, {botChan.mention} is the bot channel!!!')
                        return
                except ValueError:
                    pass
            # end of bot channel check

        if member.bot == False:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Only for bot!!')
            return

        COIN_NAME = coin.upper()
        if COIN_NAME not in ENABLE_COIN+ENABLE_COIN_DOGE+ENABLE_XMR+ENABLE_COIN_NANO+ENABLE_COIN_ERC+ENABLE_COIN_TRC+ENABLE_XCH:
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} **INVALID TICKER {COIN_NAME}**!')
            return

        # TRTL discord
        if ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
            return

        if is_maintenance_coin(COIN_NAME):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
            return


        # Check if maintenance
        if IS_MAINTENANCE == 1:
            if int(ctx.author.id) in MAINTENANCE_OWNER:
                pass
            else:
                await ctx.message.add_reaction(EMOJI_WARNING)
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}')
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
                msg = await ctx.reply(embed=embed)
                await msg.add_reaction(EMOJI_OK_BOX)
                await ctx.message.add_reaction(EMOJI_OK_HAND)
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                msg = await ctx.reply(
                        f'**[ <@{member.id}> BALANCE]**\n'
                        f' Deposit Address: `{depositAddress}`\n'
                        f'{EMOJI_MONEYBAG} Available: {balance_actual} '
                        f'{COIN_NAME}\n'
                        '**This is bot\'s tipjar address. Do not deposit here unless you want to deposit to this bot.**')
                await msg.add_reaction(EMOJI_OK_BOX)
                await ctx.message.add_reaction(EMOJI_OK_HAND)
            return


def setup(bot):
    bot.add_cog(BotBalance(bot))