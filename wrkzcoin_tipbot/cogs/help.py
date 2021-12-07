import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class Help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def bot_log(self):
        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)


    @commands.command(usage="help <section>")
    @commands.bot_has_permissions(add_reactions=True)
    async def help(
        self, 
        ctx, 
        *, 
        section: str='MAIN'
    ):
        await self.bot_log()
        async def help_main_embed(ctx, prefix, section: str='MAIN'):
            prefix = await get_guild_prefix(ctx)
            embed = discord.Embed(title="List of commands", description="To avoid spamming other, you can do in Direct Message or Bot Channel", timestamp=datetime.utcnow(), color=0xDEADBF)
            help_specific = False

            if section.upper() == "GUILDSETTING":
                cmd_setting = ["setting prefix <.>", "setting default_coin <coin_name>", "setting tiponly <coin1> [coin2] [coin3] ..", "setting ignorechan", "setting del_ignorechan", \
                "setting <mute/unmute>", "setting game", "guild botchan", "guild tipmsg", "guild gamechan [name]"]
                embed.add_field(name="SERVER [GUILD]", value="`{}`".format(", ".join(cmd_setting)), inline=False)
                
                cmd_tag = ["tag", "tag <-add> <tag_name> <tag description>", "tag <-del> <tag_name>", "itag", "itag <itag_name> (need attachement)", "itag -del <tag_name>"]
                embed.add_field(name="TAG / ITAG", value="`{}`".format(", ".join(cmd_tag)), inline=False)

            elif section.upper() == "TIPPING":
                cmd_tip = ["tip <amount> [coin_name] @mention1 @mention2", "tipall <amount> [coin_name]", "tip <amount> [coin_name] [last 2h]",  "tip <amount> [coin_name] [last 10u]", "freetip <amount> <coin_name>", "randtip <amount> <coin_name>", "take"]
                embed.add_field(name="TIP COMMAND", value="`{}`".format(", ".join(cmd_tip)), inline=False)

                cmd_tip = ["mtip|gtip <amount> [coin_name] @mention1 @mention2", "mtip|gtip <amount> [coin_name] [last 2h]",  "mtip|gtip <amount> [coin_name] [last 10u]", "(Required permission)"]
                embed.add_field(name="GUILD TIP COMMAND", value="`{}`".format(", ".join(cmd_tip)), inline=False)

                cmd_user = ["balance [list]", "botbalance @mention_bot <coin_name>", "deposit <coin_name>", "notifytip <on/off>", "reg <coin_address>", "send <amount> <coin_address>", "withdraw <amount> <coin_name>", "account deposit"]
                embed.add_field(name="USER", value="`{}`".format(", ".join(cmd_user)), inline=False)

                cmd_voucher = ["voucher claim", "voucher fee", "voucher getclaim", "voucher getunclaim", "voucher make <amount> <coin_name> <comment>"]
                embed.add_field(name="VOUCHER", value="`{}`".format(", ".join(cmd_voucher)), inline=False)

            elif section.upper() == "GAMING":
                cmd_game = ["game bagel", "game bagel2", "game bagel3", "game blackjack", "game dice", "game 2048", "game hangman", "game maze", "game slot", "game snail <number>", "game sokoban", "game stat"]
                embed.add_field(name="GAMES", value="`{}`".format(", ".join(cmd_game)), inline=False)

            elif section.upper() == "TOOLING":
                cmd_fun = ["tb spank <@mention>", "tb punch <@mention>", "tb slap <@mention>", "tb praise <@mention>", "tb shoot <@mention>", "tb kick <@mention>", "tb fistbump <@mention>", "tb dance", "tb sketchme [@mention]", "tb draw [@mention]"]
                embed.add_field(name="FUN COMMAND", value="`{}`".format(", ".join(cmd_fun)), inline=False)

                cmd_dev = ["tool dec2hex <number>", "tool hex2dec <hex>", "tool hex2str <hex>", "tool str2hex <string>", "tool emoji"]
                embed.add_field(name="DEV COMMAND", value="`{}`".format(", ".join(cmd_dev)), inline=False)

                cmd_other = ["disclaimer", "cal <1+2+3>", "coininfo <coin_name>", "feedback", "paymentid", "rand <1-100>", "stats", "userinfo @mention", "pools <coin_name_full>"]
                embed.add_field(name="OTHER COMMAND", value="`{}`".format(", ".join(cmd_other)), inline=False)

            elif section.upper() == "MARKETING":
                cmd_market = ["cg <ticker>", "price <ticker>", "price <amount> <ticker>", "price <amount> <coin1> in <coin2>", "pricelist <ticker1> [ticker2].."]
                embed.add_field(name="MARKET COMMAND", value="`{}`".format(", ".join(cmd_market)), inline=False)

            elif section.upper() == "DISCLAIMER":
                embed.add_field(name="DISCLAIMER", value="{}".format(DISCLAIM_MSG_LONG), inline=False)

            else:
                # Try to find if there is a help to that
                help_item = await store.sql_help_doc_get('help', section)
                if help_item:
                    embed = discord.Embed(title=f"Help {section.upper()}", description="To avoid spamming other, you can do in a bot channel", timestamp=datetime.utcnow(), color=0xDEADBF)
                    embed.add_field(name="Explanation", value="```{}```".format(discord.utils.escape_markdown(help_item['detail'].replace('prefix', prefix))), inline=False)
                    help_specific = True
                    try:
                        if 'example' in help_item and help_item['example'] and len(help_item['example'].strip()) > 0:
                            embed.add_field(name="Example", value="`{}`".format(discord.utils.escape_markdown(help_item['example'].replace('prefix', prefix))), inline=False)
                        else:
                            embed.add_field(name="Example", value="`N/A`", inline=False)
                    except Exception as e:
                        pass
                else:
                    embed.add_field(name="What is this", value="`It's a cool cryptocurrency tipping bot`", inline=False)
                    embed.add_field(name="Why is it here", value="`Guild Manager or Owner invited it`", inline=False)
                    embed.add_field(name="What is it for", value="`Tipping cryptocurrency to other people, playing some discord text games and earning crypto, depositing and withdrawing is so easy, tipping is off-chain (no fee), and more`", inline=False)
                    embed.add_field(name="Tell me how to use it", value="`Re-act on each EMOJI for help commands`", inline=False)
                    embed.add_field(name="Any other info?", value="`Check link in the footer`", inline=False)
                    embed.add_field(name="It's not working", value="`We appreciate for any feedback such as submitting an issue in our Github, using feedback command, joining our discord and say it`", inline=False)

            # add donation to every section
            cmd_donation = ["donate <amount> <coin_name>", "donate list"]
            embed.add_field(name="DONATION", value="`{}`".format(", ".join(cmd_donation)), inline=False)

            if isinstance(ctx.message.channel, discord.DMChannel) == False:
                serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                coin_name = serverinfo['default_coin'].upper() if serverinfo else "WRKZ"
                embed.add_field(name="GUILD INFO", value="`ID: {}, Name: {}, Default Coin: {}, Prefix: {}`".format(ctx.guild.id, ctx.guild.name, coin_name, prefix), inline=False)

            if help_specific == False:
                embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
                embed.set_footer(text=f"Required - <>, Optional - [], Help: {EMOJI_HELP_HOUSE} Home, Help: {EMOJI_HELP_GUILD} Guild, {EMOJI_HELP_TIP} Tipping, {EMOJI_HELP_GAME} Game, {EMOJI_HELP_CG} Market, {EMOJI_HELP_TOOL} Tool, {EMOJI_HELP_NOTE} Disclaimer")
            else:
                embed.set_footer(text=f"Help requested by {ctx.author.name}#{ctx.author.discriminator}")
            return embed
        try:
            prefix = await get_guild_prefix(ctx)

            if not re.match('^[a-zA-Z0-9-_ ]+$', section):
                await ctx.reply(f'{EMOJI_ERROR} {ctx.author.mention} Invalid help topic.')
                await ctx.message.add_reaction(EMOJI_ERROR)
                return

            try:
                if isinstance(ctx.channel, discord.DMChannel) == False:
                    # check if bot channel is set:
                    serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
                    if serverinfo and serverinfo['botchan']:
                        if ctx.channel.id != int(serverinfo['botchan']):
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            botChan = self.bot.get_channel(int(serverinfo['botchan']))
                            if botChan:
                                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, {botChan.mention} is the bot channel!!!')
                            else:
                                await self.botLogChan.send(f'Guild {ctx.guild.name} / {ctx.guild.id} has defined botchan but I can not find it! ')
                                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention}, bot channel was defined but I can not find it in this guild. Please command help in DM instead.')
                                await msg.add_reaction(EMOJI_OK_BOX)
                            return
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                pass
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                await logchanbot(traceback.format_exc())
            # end of bot channel check

            try:
                embed = await help_main_embed(ctx, prefix, section)
                if isinstance(ctx.message.channel, discord.DMChannel) == False:
                    msg = await ctx.reply(embed=embed)
                else:
                    msg = await ctx.author.send(embed=embed)
                help_item = await store.sql_help_doc_get('help', section.upper())

                if section.upper() in ["MAIN", "GUILDSETTING", "TIPPING", "GAMING", "TOOLING", "MARKETING", "DISCLAIMER"] or help_item is None:
                    await msg.add_reaction(EMOJI_HELP_HOUSE)    
                    await msg.add_reaction(EMOJI_HELP_GUILD)
                    await msg.add_reaction(EMOJI_HELP_TIP)
                    await msg.add_reaction(EMOJI_HELP_GAME)
                    await msg.add_reaction(EMOJI_HELP_TOOL)
                    await msg.add_reaction(EMOJI_HELP_CG)
                    await msg.add_reaction(EMOJI_HELP_NOTE)
                    await msg.add_reaction(EMOJI_OK_BOX)
                else:
                    # No need interactive if single help
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return

                # TODO: react not work yet
                while True:
                    def check(reaction, user):
                        return user == ctx.author and reaction.message.author == self.bot.user and reaction.message.id == msg.id and str(reaction.emoji) \
                        in (EMOJI_HELP_HOUSE, EMOJI_HELP_GUILD, EMOJI_HELP_TIP, EMOJI_HELP_GAME, EMOJI_HELP_TOOL, EMOJI_HELP_NOTE, EMOJI_HELP_CG, EMOJI_OK_BOX)

                    done, pending = await asyncio.wait([
                                        self.bot.wait_for('reaction_remove', timeout=90, check=check),
                                        self.bot.wait_for('reaction_add', timeout=90, check=check)
                                    ], return_when=asyncio.FIRST_COMPLETED)
                    try:
                        # stuff = done.pop().result()
                        reaction, user = done.pop().result()
                    except Exception as e:
                        # timeout pass, just let it pass
                        pass
                        return

                    if str(reaction.emoji) == EMOJI_OK_BOX:
                        await asyncio.sleep(1)
                        try:
                            await msg.delete()
                        except Exception as e:
                            pass
                        return
                    elif str(reaction.emoji) == EMOJI_HELP_HOUSE:
                        section = "MAIN"
                    elif str(reaction.emoji) == EMOJI_HELP_GUILD:
                        section = "GUILDSETTING"
                    elif str(reaction.emoji) == EMOJI_HELP_TIP:
                        section = "TIPPING"
                    elif str(reaction.emoji) == EMOJI_HELP_GAME:
                        section = "GAMING"
                    elif str(reaction.emoji) == EMOJI_HELP_TOOL:
                        section = "TOOLING"
                    elif str(reaction.emoji) == EMOJI_HELP_CG:
                        section = "MARKETING"
                    elif str(reaction.emoji) == EMOJI_HELP_NOTE:
                        section = "DISCLAIMER"
                    embed = await help_main_embed(ctx, prefix, section)
                    await msg.edit(embed=embed)
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                await self.botLogChan.send(f'**Failed** Missing Permissions for sending help in guild {ctx.guild.id} / {ctx.guild.name} / # {ctx.message.channel.name}')
                await message.add_reaction(EMOJI_ERROR)
            except Exception as e:
                await logchanbot(traceback.format_exc())
        except Exception as e:
            traceback.print_exc(file=sys.stdout)


    # TODO: improve re-act
    async def help_setting(
        message, 
        prefix
    ):
        await self.bot_log()
        embed = discord.Embed(title=f"List of SETTING command {message.guild.name}", description="Required Managed Channel Permission", timestamp=datetime.utcnow())
        if isinstance(message.channel, discord.DMChannel) == True:
            await message.add_reaction(EMOJI_ERROR) 
            await message.author.send('This command can not be in private.')
            return
        else:
            embed.add_field(name=f"{prefix}setting prefix <prefix>", value="`Change bot prefix. Supported prefix: . ? * !`", inline=False)
            embed.add_field(name=f"{prefix}setting tiponly <coin1> [coin2] [coin3] ..", value="`Set tip-only to these coins`", inline=False)
            embed.add_field(name=f"{prefix}setting ignorechan", value="`Ignore this channel from tipping`", inline=False)
            embed.add_field(name=f"{prefix}setting del_ignorechan", value="`Delete this channel from ignored tipping channel`", inline=False)
            embed.add_field(name=f"{prefix}setting botchan #channel_name", value="`Restrict most bot command in #channel_name`", inline=False)
            embed.add_field(name=f"{prefix}setting game", value="`Enable / Disable game feature / command`", inline=False)
            embed.add_field(name=f"{prefix}setting <mute/unmute>", value="`Mute / Unmute the said text channel`", inline=False)
            embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
            embed.set_footer(text="Required - <>, Optional - []")
        try:
            msg = await message.channel.send(embed=embed)
            await msg.add_reaction(EMOJI_OK_BOX)
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            await self.botLogChan.send(f'**Failed** Missing Permissions for sending help_setting in guild {message.guild.id} / {message.guild.name} / # {message.channel.name}')
            await message.add_reaction(EMOJI_ERROR)
        return

def setup(bot):
    bot.add_cog(Help(bot))