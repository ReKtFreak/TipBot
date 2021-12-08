import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from dislash import InteractionClient, ActionRow, Button, ButtonStyle, Option, OptionType, OptionChoice, SlashInteraction
import dislash
import re

from config import config
from Bot import *
from Bot import _tip


class TipMtip(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def bot_log(self):
        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)


    # /mtip amount coin @mention @mention ...
    # /mtip amount coin last xxxu
    # /mtip amount coin last yyyhrs
    # /mtip amount coin XXXXXXXX (via DM, secret tip)

    async def process_mtip(
        self,
        ctx,
        amount,
        coin,
        option
    ):
        # check if bot is going to restart
        if IS_RESTARTING: return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this."}
        # check if account locked
        account_lock = await alert_if_userlock(ctx, 'tip')
        if account_lock:  return {"error": f"{EMOJI_RED_NO} {MSG_LOCKED_ACCOUNT}"}
        # end of check if account locked

        if isinstance(ctx.channel, discord.DMChannel):
            return {"error": f"{EMOJI_RED_NO} This command can not be in private."}

        # Check if tx in progress
        if ctx.guild.id in TX_IN_PROCESS: return {"error": f"{EMOJI_ERROR} {ctx.author.mention} This guild `{ctx.guild.name}` has another tx in progress."}

        # TRTL discord
        if isinstance(ctx.channel, discord.DMChannel) == False and ctx.guild.id == TRTL_DISCORD and COIN_NAME != "TRTL":
            return {"error": f"{EMOJI_ERROR} {ctx.author.mention} Please use TRTL only."}


        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        COIN_NAME = coin.upper()

        if not is_coin_tipable(COIN_NAME):
            return {"error": f"{EMOJI_ERROR} {ctx.author.mention} TIPPING is currently disable for {COIN_NAME}."}

        if is_maintenance_coin(COIN_NAME):
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance."}

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
            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} not in allowed coins set by server manager."}
        # End of checking allowed coins

        if option.lower().startswith("last "):
            # last xxxu
            # last yyyhrs
            # try if the param is 1111u
            num_user = option.lower().replace("last ", "") # remove last
            if 'u' in num_user or 'user' in num_user or 'users' in num_user or 'person' in num_user or 'people' in num_user:
                num_user = num_user.replace("people", "")
                num_user = num_user.replace("person", "")
                num_user = num_user.replace("users", "")
                num_user = num_user.replace("user", "")
                num_user = num_user.replace("u", "")
                try:
                    num_user = int(num_user)
                    if len(ctx.guild.members) <= 10:
                        if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ERROR)
                        return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Please use normal mtip command. There are only few users."}
                    # Check if we really have that many user in the guild 20%
                    elif num_user >= len(ctx.guild.members):
                        try:
                            if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_INFORMATION)
                            await ctx.reply(f'{ctx.author.mention} Boss, you want to mtip more than the number of people in this guild!?.'
                                            ' Can be done :). Wait a while.... I am doing it. (**counting..**)')
                        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                            # No need to tip if failed to message
                            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} No permission."}
                        message_talker = await store.sql_get_messages(str(ctx.guild.id), str(ctx.channel.id), 0, len(ctx.guild.members))
                        if ctx.author.id in message_talker:
                            message_talker.remove(ctx.author.id)

                        if len(message_talker) == 0:
                            if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ERROR)
                            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} There is not sufficient user to count."}

                        elif len(message_talker) < len(ctx.guild.members) - 1: # minus bot
                            await ctx.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} I could not find sufficient talkers up to **{num_user}**. I found only **{len(message_talker)}** and tip to those **{len(message_talker)}** users if they are still here.')
                            # tip all user who are in the list
                            try:
                                await _tip_talker(ctx, amount, message_talker, True, COIN_NAME) # TODO
                            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                            except Exception as e:
                                traceback.print_exc(file=sys.stdout)
                                await logchanbot(traceback.format_exc())
                            return {"result": True}
                    elif num_user > 0:
                        message_talker = await store.sql_get_messages(str(ctx.guild.id), str(ctx.channel.id), 0, num_user + 1)
                        if ctx.author.id in message_talker:
                            message_talker.remove(ctx.author.id)
                        else:
                            # remove the last one
                            message_talker.pop()
                        if len(message_talker) == 0:
                            if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ERROR)
                            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} There is not sufficient user to count."}
                        elif len(message_talker) < num_user:
                            try:
                                if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_INFORMATION)
                                await ctx.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} I could not find sufficient talkers up to **{num_user}**. I found only **{len(message_talker)}** and tip to those **{len(message_talker)}** users if they are still here.')
                            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                # No need to tip if failed to message
                                if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                return {"error": f"{EMOJI_INFORMATION} {ctx.author.mention} No permission."}
                            # tip all user who are in the list
                            try:
                                await _tip_talker(ctx, amount, message_talker, True, COIN_NAME)
                            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                                # zipped mouth but still need to do tip talker
                                await _tip_talker(ctx, amount, message_talker, True, COIN_NAME)
                            except Exception as e:
                                traceback.print_exc(file=sys.stdout)
                                await logchanbot(traceback.format_exc())
                        else:
                            try:
                                await _tip_talker(ctx, amount, message_talker, True, COIN_NAME)
                            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                            except Exception as e:
                                traceback.print_exc(file=sys.stdout)
                                await logchanbot(traceback.format_exc())
                            return {"result": True}
                    else:
                        if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ERROR)
                        return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} What is this **{num_user}** number? Please give a number bigger than 0 :)"}
                except ValueError:
                    if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ERROR)
                    return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Invalid param after **LAST**."}
            else:
                time_given = None
                time_string = option.lower().replace("last ", "").strip() # remove last
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
                    traceback.print_exc(file=sys.stdout)
                    await logchanbot(traceback.format_exc())
                    return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Invalid time given after **last**."}
                try:
                    time_given = int(time_second)
                except ValueError:
                    if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ERROR)
                    return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Invalid time given check."}
                if time_given:
                    if time_given < 5*60 or time_given > 60*24*60*60:
                        if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ERROR)
                        return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} Please try time interval between 5minutes to 24hours."}
                    else:
                        message_talker = await store.sql_get_messages(str(ctx.guild.id), str(ctx.channel.id), time_given, None)
                        if ctx.author.id in message_talker:
                            message_talker.remove(ctx.author.id)
                        if len(message_talker) == 0:
                            if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ERROR)
                            return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} There is no active talker in such period."}
                        else:
                            try:
                                await _tip_talker(ctx, amount, message_talker, True, COIN_NAME)
                            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                                if type(ctx) is not dislash.interactions.app_command_interaction.SlashInteraction: await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                            except Exception as e:
                                traceback.print_exc(file=sys.stdout)
                                await logchanbot(traceback.format_exc())
                            return {"result": True}
        else:
            # Check if there are mentioned users or roles.
            list_member_ids = []
            list_m = re.findall(r'<@!?(\d+)>', option)
            list_r = re.findall(r'<@&(\d+)>', option)
            guild_members = ctx.guild.members
            if len(list_m) > 0:
                # members
                for each_m in list_m:
                    member = self.bot.get_user(int(each_m))
                    if member and member.id not in list_member_ids:
                        list_member_ids.append(int(each_m))
            if len(list_r) > 0:
                # roles
                for each_r in list_r:
                    get_role = discord.utils.get(ctx.guild.roles, id=int(each_r))
                    if get_role:
                        role_listMember = [member.id for member in guild_members if get_role in member.roles and member.id not in list_member_ids]
                        if len(role_listMember) >= 1:
                            list_member_ids += role_listMember
            # If he is in:
            if ctx.author.id in list_member_ids: list_member_ids.remove(ctx.author.id)
            if len(list_member_ids) > 0:
                try:
                    await _tip(ctx, amount, COIN_NAME, list_member_ids, True)
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
                    await logchanbot(traceback.format_exc())
            else:
                return {"error": f"{EMOJI_RED_NO} {ctx.author.mention} There is no user to tip to."}


    @dislash.guild_only()
    @inter_client.slash_command(
        usage="mtip", 
        options=[
            Option('amount', 'amount', OptionType.NUMBER, required=True),
            Option('coin_name', 'coin_name', OptionType.STRING, required=True),
            Option('option', 'last 12u, last 1hr, @mention @mention ..', OptionType.STRING, required=True)
        ],
        description="Moderator tip."
    )
    @dislash.has_permissions(manage_channels=True)
    async def mtip(
        self, 
        ctx,
        amount: float,
        coin_name: str,
        option: str
    ):
        await self.bot_log()
        process_mtip = await self.process_mtip(ctx, amount, coin_name, option)
        if process_mtip and "error" in process_mtip:
            await ctx.reply(process_mtip['error'])


    @commands.guild_only()
    @commands.command(
        usage="mtip <amount> [arg]", 
        aliases=['gtip', 'modtip', 'guildtip'], 
        description="Moderator tip."
    )
    @commands.has_permissions(manage_channels=True)
    async def mtip(
        self, 
        ctx, 
        amount: str, 
        coin_name: str,
        *,
        option
    ):
        amount = amount.replace(",", "")
        try:
            amount = Decimal(amount)
        except ValueError:
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount.')
            return

        process_mtip = await self.process_mtip(ctx, amount, coin_name, option)
        if process_mtip and "error" in process_mtip:
            await ctx.reply(process_mtip['error'])


def setup(bot):
    bot.add_cog(TipMtip(bot))