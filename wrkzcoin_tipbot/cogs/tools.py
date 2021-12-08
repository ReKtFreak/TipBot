import asyncio
import re
import sys
import time
import traceback
from datetime import datetime
import random

import discord
from discord.ext import commands
from dislash import InteractionClient, ActionRow, Button, ButtonStyle, Option, OptionType, OptionChoice
import dislash

import store
from Bot import *

from config import config

## NOTE:
##  * Not all message commands are available in slash commands


class Tool(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def bot_log(self):
        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)


    @inter_client.slash_command(description="Various tool's commands.")
    async def tool(self, ctx):
        # This is just a parent for subcommands
        # It's not necessary to do anything here,
        # but if you do, it runs for any subcommand nested below
        pass


    # For each subcommand you can specify individual options and other parameters,
    # see the "Objects and methods" reference to learn more.
    @tool.sub_command(
        usage="tool avatar <member>", 
        options=[
            Option('member', 'member', OptionType.USER, required=True)
        ],
        description="Get avatar of a user."
    )
    async def avatar(
        self,
        ctx,
        member: discord.Member
    ):
        if member is None:
            member = ctx.author
        try:
            if isinstance(ctx.channel, discord.DMChannel) == False:
                msg = await ctx.reply(f'Avatar image for {member.mention}:\n{str(member.display_avatar)}', components=[row_close_message])
                await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, discord.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
            else:
                msg = await ctx.reply(f'Avatar image for {member.mention}:\n{str(member.display_avatar)}')
        except Exception as e:
            await logchanbot(traceback.format_exc())


    @tool.sub_command(
        usage="tool prime <number>", 
        options=[
            Option('number', 'number', OptionType.STRING, required=True)
        ],
        description="Check a given number if it is a prime number."
    )
    async def prime(
        self, 
        ctx, 
        number: str
    ):
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

        number = number.replace(",", "")
        if len(number) >= 1900:
            await ctx.reply(f'{ctx.author.mention} {EMOJI_ERROR} given number is too long.')
            return
        try:
            value = is_prime(int(number))
            if value:
                await ctx.reply(f'{ctx.author.mention} {EMOJI_CHECKMARK} Given number is a prime number: ```{str(number)}```')
            else:
                await ctx.reply(f'{ctx.author.mention} {EMOJI_ERROR} Given number is not a prime number: ```{str(number)}```')
        except ValueError:
            await ctx.reply(f'{ctx.author.mention} {EMOJI_ERROR} Number error.')


    ### Message commands
    @commands.group(
        usage="tool <subcommand>", 
        aliases=['tools'], 
        description="Various tool commands."
    )
    async def tool(self, ctx):
        prefix = await get_guild_prefix(ctx)
        # Only WrkzCoin testing. Return if DM or other guild
        if isinstance(ctx.channel, discord.DMChannel) == True or ctx.guild.id != 460755304863498250:
            return
        if ctx.invoked_subcommand is None:
            await ctx.reply(f'{ctx.author.mention} Invalid {prefix}tool command.\n Please use {prefix}help tool')
            return


    @tool.command(
        usage="tool avatar <member>", 
        description="Get avatar of a user."
    )
    async def avatar(
        self, 
        ctx, 
        member: discord.Member = None
    ):
        if member is None:
            member = ctx.author
        try:
            if isinstance(ctx.channel, discord.DMChannel) == False:
                msg = await ctx.reply(f'Avatar image for {member.mention}:\n{str(member.display_avatar)}', components=[row_close_message])
                await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, discord.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
            else:
                msg = await ctx.reply(f'Avatar image for {member.mention}:\n{str(member.display_avatar)}')
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
        return


    @tool.command(
        usage="tool prime <number>", 
        description="Check a given number if it is a prime number."
    )
    async def prime(
        self, 
        ctx, 
        number_test: str
    ):
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
        number_test = number_test.replace(",", "")
        if len(number_test) >= 1900:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} **{number_test}** too long.')
            return
        try:
            value = is_prime(int(number_test))
            if value:
                await ctx.message.add_reaction(EMOJI_CHECKMARK)
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
        except ValueError:
            await ctx.message.add_reaction(EMOJI_ERROR)
        return


    @tool.command(
        usage="tool emoji", 
        description="Get emoji value by re-acting."
    )
    async def emoji(self, ctx):
        try:
            embed = discord.Embed(title='EMOJI INFO', description=f'{ctx.author.mention}, Re-act and getinfo', colour=7047495)
            embed.add_field(name="EMOJI", value='None', inline=True)
            embed.set_footer(text="Timeout: 60s")
            msg = await ctx.reply(embed=embed)

            def check(reaction, user):
                return user == ctx.author and reaction.message.author == self.bot.user and reaction.message.id == msg.id
            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60, check=check)
                except asyncio.TimeoutError:
                    await ctx.message.add_reaction(EMOJI_ALARMCLOCK)
                    try:
                        await msg.delete()
                    except Exception as e:
                        pass
                    break
                    return
                if reaction.emoji and str(reaction.emoji) != EMOJI_OK_BOX:
                    try:
                        embed = discord.Embed(title='EMOJI INFO', description=f'{ctx.author.mention}, Re-act and getinfo', colour=7047495)
                        embed.add_field(name=f'EMOJI {reaction.emoji}', value='`{}`'.format(str(reaction.emoji) if re.findall(r'<?:\w*:\d*>', str(reaction.emoji)) else f'U+{ord(reaction.emoji):X}'), inline=True)
                        embed.set_footer(text="Timeout: 60s")
                        await msg.edit(embed=embed)
                        await msg.add_reaction(EMOJI_OK_BOX)
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                elif str(reaction.emoji) == EMOJI_OK_BOX:
                    return
        except Exception as e:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await logchanbot(traceback.format_exc())
        return


    @tool.command(
        usage="tool dec2hex <param>", 
        description="Convert decimal to hex."
    )
    async def dec2hex(
        self, 
        ctx, 
        decimal: str
    ):
        decimal = decimal.replace(",", "")
        if len(decimal) >= 32:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} **{decimal}** too long.')
            return
        try:
            value = hex(int(decimal))
            if isinstance(ctx.channel, discord.DMChannel) == False:
                msg = await ctx.reply(f'{ctx.author.mention} decimal of **{decimal}** is equal to hex:```{value}```', components=[row_close_message])
                await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, discord.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
            else:
                msg = await ctx.reply(f'{ctx.author.mention} decimal of **{decimal}** is equal to hex:```{value}```')
        except ValueError:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} **{decimal}** is an invalid decimal / integer.')
        return


    @tool.command(
        usage="tool hex2dec <param>", 
        description="Convert hex to decimal."
    )
    async def hex2dec(
        self, 
        ctx, 
        hex_string: str
    ):
        if len(hex_string) >= 100:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} **{hex_string}** too long.')
            return
        try:
            value = int(hex_string, 16)
            if isinstance(ctx.channel, discord.DMChannel) == False:
                msg = await ctx.reply(f'{ctx.author.mention} hex of **{hex_string}** is equal to decimal:```{str(value)}```', components=[row_close_message])
                await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, discord.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
            else:
                msg = await ctx.reply(f'{ctx.author.mention} hex of **{hex_string}** is equal to decimal:```{str(value)}```')
        except ValueError:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} **{hex_string}** is an invalid hex.')
        return


    @tool.command(
        usage="tool hex2str <param>", 
        aliases=['hex2ascii'], 
        description="Convert hex to string."
    )
    async def hex2str(
        self, 
        ctx, 
        hex_string: str
    ):
        if len(hex_string) >= 1000:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} **{hex_string}** too long.')
            return
        try:
            value = int(hex_string, 16)
        except ValueError:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} **{hex_string}** is an invalid hex.')
            return
        try:
            str_value = str(bytes.fromhex(hex_string).decode())
            if isinstance(ctx.channel, discord.DMChannel) == False:
                msg = await ctx.reply(f'{ctx.author.mention} hex of **{hex_string}** in ascii is:```{str_value}```', components=[row_close_message])
                await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, discord.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
            else:
                msg = await ctx.reply(f'{ctx.author.mention} hex of **{hex_string}** in ascii is:```{str_value}```')
        except Exception as e:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} **{hex_string}** I can not decode.')
            await logchanbot(traceback.format_exc())
        return


    @tool.command(
        usage="tool str2hex <param>", 
        aliases=['ascii2hex'], 
        description="Convert string to hex."
    )
    async def str2hex(self, ctx, str2hex: str):
        if len(str2hex) >= 1000:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} **{str2hex}** too long.')
            return
        if not is_ascii(str2hex):
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} **{str2hex}** is not valid ascii.')
            return
        try:
            hex_value = str(binascii.hexlify(str2hex.encode('utf_8')).decode('utf_8'))
            if isinstance(ctx.channel, discord.DMChannel) == False:
                msg = await ctx.reply(f'{ctx.author.mention} ascii of **{str2hex}** in hex is:```{hex_value}```', components=[row_close_message])
                await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, discord.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
            else:
                msg = await ctx.reply(f'{ctx.author.mention} ascii of **{str2hex}** in hex is:```{hex_value}```')
        except Exception as e:
            await logchanbot(traceback.format_exc())
        return


    @tool.command(
        usage="tool trans <to language> <text>", 
        aliases=['translate', 'tran'], 
        description="Text to speech."
    )
    async def trans(
        self, 
        ctx, 
        to_lang: str, 
        *, 
        speech: str
    ):
        to_lang = to_lang.lower()
        LANGUAGES = {
            'af': 'afrikaans',
            'sq': 'albanian',
            'am': 'amharic',
            'ar': 'arabic',
            'hy': 'armenian',
            'az': 'azerbaijani',
            'eu': 'basque',
            'be': 'belarusian',
            'bn': 'bengali',
            'bs': 'bosnian',
            'bg': 'bulgarian',
            'ca': 'catalan',
            'ceb': 'cebuano',
            'ny': 'chichewa',
            'zh-cn': 'chinese (simplified)',
            'zh-tw': 'chinese (traditional)',
            'co': 'corsican',
            'hr': 'croatian',
            'cs': 'czech',
            'da': 'danish',
            'nl': 'dutch',
            'en': 'english',
            'eo': 'esperanto',
            'et': 'estonian',
            'tl': 'filipino',
            'fi': 'finnish',
            'fr': 'french',
            'fy': 'frisian',
            'gl': 'galician',
            'ka': 'georgian',
            'de': 'german',
            'el': 'greek',
            'gu': 'gujarati',
            'ht': 'haitian creole',
            'ha': 'hausa',
            'haw': 'hawaiian',
            'iw': 'hebrew',
            'he': 'hebrew',
            'hi': 'hindi',
            'hmn': 'hmong',
            'hu': 'hungarian',
            'is': 'icelandic',
            'ig': 'igbo',
            'id': 'indonesian',
            'ga': 'irish',
            'it': 'italian',
            'ja': 'japanese',
            'jw': 'javanese',
            'kn': 'kannada',
            'kk': 'kazakh',
            'km': 'khmer',
            'ko': 'korean',
            'ku': 'kurdish (kurmanji)',
            'ky': 'kyrgyz',
            'lo': 'lao',
            'la': 'latin',
            'lv': 'latvian',
            'lt': 'lithuanian',
            'lb': 'luxembourgish',
            'mk': 'macedonian',
            'mg': 'malagasy',
            'ms': 'malay',
            'ml': 'malayalam',
            'mt': 'maltese',
            'mi': 'maori',
            'mr': 'marathi',
            'mn': 'mongolian',
            'my': 'myanmar (burmese)',
            'ne': 'nepali',
            'no': 'norwegian',
            'or': 'odia',
            'ps': 'pashto',
            'fa': 'persian',
            'pl': 'polish',
            'pt': 'portuguese',
            'pa': 'punjabi',
            'ro': 'romanian',
            'ru': 'russian',
            'sm': 'samoan',
            'gd': 'scots gaelic',
            'sr': 'serbian',
            'st': 'sesotho',
            'sn': 'shona',
            'sd': 'sindhi',
            'si': 'sinhala',
            'sk': 'slovak',
            'sl': 'slovenian',
            'so': 'somali',
            'es': 'spanish',
            'su': 'sundanese',
            'sw': 'swahili',
            'sv': 'swedish',
            'tg': 'tajik',
            'ta': 'tamil',
            'te': 'telugu',
            'th': 'thai',
            'tr': 'turkish',
            'uk': 'ukrainian',
            'ur': 'urdu',
            'ug': 'uyghur',
            'uz': 'uzbek',
            'vi': 'vietnamese',
            'cy': 'welsh',
            'xh': 'xhosa',
            'yi': 'yiddish',
            'yo': 'yoruba',
            'zu': 'zulu',
        }
        if to_lang not in LANGUAGES or to_lang.upper() == 'HELP':
            await ctx.message.add_reaction(EMOJI_INFORMATION)
            await ctx.reply(f'{ctx.author.mention} Supported language code: https://tipbot-static.wrkz.work/language_codes.txt')
            return
        else:
            def user_translated(text, to_lang: str):
                translator = Translator()
                translated = translator.translate(text, dest=to_lang)
                speech_txt = (translated.text)
                tts = gTTS(text=speech_txt, lang=to_lang)
                rand_str = time.strftime("%Y%m%d-%H%M_") + str(uuid.uuid4())
                random_mp3_name = rand_str + ".mp3"
                random_mp4_name = rand_str + ".mp4"
                tts.save(config.tts.tts_saved_path + random_mp3_name)
                import subprocess
                command = f'ffmpeg -i {config.tts.tts_saved_path + random_mp3_name} -filter_complex "[0:a]showwaves=s=640x360:mode=cline:r=30,colorkey=0x000000:0.01:0.1,format=yuv420p[vid]" -map "[vid]" -map 0:a -codec:v libx264 -crf 18 -c:a copy {config.tts.tts_saved_path + random_mp4_name}'
                process_video = subprocess.Popen(command, shell=True)
                process_video.wait(timeout=20000) # 20s waiting
                os.remove(config.tts.tts_saved_path + random_mp3_name)
                return {'file': random_mp4_name, 'original': text, 'translated': translated.text, 'src_lang': translated.src, 'to_lang': to_lang}
            try:
                async with ctx.typing():
                    make_voice = functools.partial(user_translated, speech, to_lang)
                    voice_file = await self.bot.loop.run_in_executor(None, make_voice)
                    file = discord.File(config.tts.tts_saved_path + voice_file['file'], filename=voice_file['file'])
                    if isinstance(ctx.channel, discord.DMChannel) == False:
                        msg = await ctx.reply(file=file, content="{}: {}".format(ctx.author.mention, voice_file['translated']), components=[row_close_message])
                        await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, discord.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
                    else:
                        msg = await ctx.reply(file=file, content="{}: {}".format(ctx.author.mention, voice_file['translated']))
                    await store.sql_add_trans_tts(str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator), \
                                speech, voice_file['translated'], voice_file['src_lang'], to_lang, voice_file['file'], SERVER_BOT)
            except Exception as e:
                await logchanbot(traceback.format_exc())
                await ctx.reply(f'{ctx.author.mention} Translate: Internal error. The media file could be too big to upload here. Please reduce your text length.')
        return


    @tool.command(
        usage="tool tts <text>", 
        description="Text to speech."
    )
    async def tts(
        self, 
        ctx, 
        *, 
        speech: str
    ):
        if not isEnglish(speech):
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} Currently, TTS supports English only.')
            return
        else:
            lang = 'en'
            def user_speech(text):
                speech_txt = (text)
                tts = gTTS(text=speech_txt, lang=lang)
                random_mp3_name = time.strftime("%Y%m%d-%H%M_") + str(uuid.uuid4()) + ".mp3"
                tts.save(config.tts.tts_saved_path + random_mp3_name)
                return random_mp3_name
            try:
                async with ctx.typing():
                    try:
                        make_voice = functools.partial(user_speech, speech)
                        voice_file = await self.bot.loop.run_in_executor(None, make_voice)
                        file = discord.File(config.tts.tts_saved_path + voice_file, filename=voice_file)
                        if isinstance(ctx.channel, discord.DMChannel) == False:
                            msg = await ctx.reply(file=file, content=f"{ctx.author.mention}", components=[row_close_message])
                            await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, discord.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
                        else:
                            msg = await ctx.reply(file=file, content=f"{ctx.author.mention}")
                        await store.sql_add_tts(str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator), \
                                    speech, lang, voice_file, SERVER_BOT)
                    except Exception as e:
                        await logchanbot(traceback.format_exc())
                        await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
            except Exception as e:
                await logchanbot(traceback.format_exc())
        return


    @tool.command(
        usage="tool ttskh <text>", 
        description="Text to speech in Khmer."
    )
    async def ttskh(
        self, 
        ctx, 
        *, 
        speech: str
    ):
        if not isKhmer(speech):
            await ctx.message.add_reaction(EMOJI_INFORMATION)
            await ctx.reply(f'{ctx.author.mention}  Some characters are not in fully in Khmer.')
        lang = 'km'
        def user_speech(text):
            speech_txt = (text)
            tts = gTTS(text=speech_txt, lang=lang)
            random_mp3_name = time.strftime("%Y%m%d-%H%M_") + str(uuid.uuid4()) + ".mp3"
            tts.save(config.tts.tts_saved_path + random_mp3_name)
            return random_mp3_name
        try:
            async with ctx.typing():
                try:
                    make_voice = functools.partial(user_speech, speech)
                    voice_file = await self.bot.loop.run_in_executor(None, make_voice)
                    file = discord.File(config.tts.tts_saved_path + voice_file, filename=voice_file)
                    if isinstance(ctx.channel, discord.DMChannel) == False:
                        msg = await ctx.reply(file=file, content=f"{ctx.author.mention}", components=[row_close_message])
                        await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, discord.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
                    else:
                        msg = await ctx.reply(file=file, content=f"{ctx.author.mention}")
                    await store.sql_add_tts(str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator), \
                                speech, lang, voice_file, SERVER_BOT)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
        except Exception as e:
            await logchanbot(traceback.format_exc())
        return


    @tool.command(
        usage="tool ttscn <text>", 
        description="Text to speech in Chinese."
    )
    async def ttscn(
        self, 
        ctx, 
        *, 
        speech: str
    ):
        if not isChinese(speech):
            await ctx.message.add_reaction(EMOJI_INFORMATION)
            await ctx.reply(f'{ctx.author.mention} Some characters are not in fully in Chinese.')
     
        lang = 'zh-CN'
        def user_speech(text):
            speech_txt = (text)
            tts = gTTS(text=speech_txt, lang=lang)
            random_mp3_name = time.strftime("%Y%m%d-%H%M_") + str(uuid.uuid4()) + ".mp3"
            tts.save(config.tts.tts_saved_path + random_mp3_name)
            return random_mp3_name
        try:
            async with ctx.typing():
                try:
                    make_voice = functools.partial(user_speech, speech)
                    voice_file = await self.bot.loop.run_in_executor(None, make_voice)
                    file = discord.File(config.tts.tts_saved_path + voice_file, filename=voice_file)
                    if isinstance(ctx.channel, discord.DMChannel) == False:
                        msg = await ctx.reply(file=file, content=f"{ctx.author.mention}", components=[row_close_message])
                        await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, discord.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
                    else:
                        msg = await ctx.reply(file=file, content=f"{ctx.author.mention}")
                    await store.sql_add_tts(str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator), \
                                speech, lang, voice_file, SERVER_BOT)
                except Exception as e:
                    await logchanbot(traceback.format_exc())
                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
        except Exception as e:
            await logchanbot(traceback.format_exc())
        return


    @tool.command(
        usage="tool find <text>", 
        aliases=['search'], 
        description="Search something in TipBot."
    )
    async def find(
        self, 
        ctx, 
        *, 
        searched_text: str
    ):
        # bot check in the first place
        if ctx.author.bot == True:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is not allowed using this.')
            return

        # disable game for TRTL discord
        if ctx.guild and ctx.guild.id == TRTL_DISCORD:
            await ctx.message.add_reaction(EMOJI_LOCKED)
            return

        if not re.match('^[a-zA-Z0-9-_ ]+$', searched_text):
            await ctx.reply(f'{EMOJI_ERROR} {ctx.author.mention} Invalid help searching text **{searched_text}**.')
            await ctx.message.add_reaction(EMOJI_ERROR)
            return

        prefix = await get_guild_prefix(ctx)
        serverinfo = await store.sql_info_by_server(str(ctx.guild.id))
        if ctx.guild and serverinfo and 'enable_find' in serverinfo and serverinfo['enable_find'] == "NO":
            return

        if len(searched_text) >= 100:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} Searched text is too long.')
            return

        if not is_ascii(searched_text):
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} **{searched_text}** is not valid text.')
            return
        try:
            # Let's search
            searching = None

            async with ctx.typing():
                # search one title first
                finding = await store.sql_help_doc_get('any', searched_text)
                if finding is None:
                    searching = await store.sql_help_doc_search(searched_text, 5)
            if finding or (searching and len(searching) >= 1):
                if finding:
                    first_result = finding
                else:
                    first_result = searching[0]
                embed = discord.Embed(title='TipBot Find', description=f'`{searched_text}`', timestamp=datetime.utcnow())
                embed.add_field(name="Title", value="```{}```".format(first_result['what'].replace('prefix', prefix)), inline=False)
                embed.add_field(name="Content", value="```{}```".format(first_result['detail'].replace('prefix', prefix)), inline=False)
                if 'example' in first_result and first_result['example'] and len(first_result['example'].strip()) > 0:
                    embed.add_field(name="More", value="```{}```".format(first_result['example'].replace('prefix', prefix)), inline=False)
                embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
                embed.set_footer(text=f"Find requested by {ctx.author.name}#{ctx.author.discriminator}")
                if isinstance(ctx.channel, discord.DMChannel) == False:
                    msg = await ctx.reply(embed=embed, components=[row_close_message])
                    await store.add_discord_bot_message(str(msg.id), "DM" if isinstance(ctx.channel, discord.DMChannel) else str(ctx.guild.id), str(ctx.author.id))
                else:
                    msg = await ctx.reply(embed=embed)
                reaction_numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🆗']
                if searching and len(searching) > 1:
                    i = 0
                    for item in searching:
                        await msg.add_reaction(reaction_numbers[i])
                        i += 1
                    while True:
                        def check(reaction, user):
                            return user == ctx.author and reaction.message.author == self.bot.user and reaction.message.id == msg.id and reaction.emoji \
                            in reaction_numbers

                        done, pending = await asyncio.wait([
                                            self.bot.wait_for('reaction_remove', timeout=60, check=check),
                                            self.bot.wait_for('reaction_add', timeout=60, check=check)
                                        ], return_when=asyncio.FIRST_COMPLETED)
                        try:
                            # stuff = done.pop().result()
                            reaction, user = done.pop().result()
                        except asyncio.TimeoutError:
                            break
                            
                        try:
                            emoji_n = reaction_numbers.index(str(reaction.emoji))
                            if emoji_n <= len(searching):
                                first_result = searching[emoji_n-1]
                                embed = discord.Embed(title='TipBot Find {}/{}'.format(emoji_n+1, len(searching)), description=f'`{searched_text}`', timestamp=datetime.utcnow())
                                embed.add_field(name="Title", value="```{}```".format(first_result['what'].replace('prefix', prefix)), inline=False)
                                embed.add_field(name="Content", value="```{}```".format(first_result['detail'].replace('prefix', prefix)), inline=False)
                                if 'example' in first_result and first_result['example'] and len(first_result['example'].strip()) > 0:
                                    embed.add_field(name="More", value="```{}```".format(first_result['example'].replace('prefix', prefix)), inline=False)
                                embed.add_field(name="OTHER LINKS", value="{} / {} / {}".format("[Invite TipBot](http://invite.discord.bot.tips)", "[Support Server](https://discord.com/invite/GpHzURM)", "[TipBot Github](https://github.com/wrkzcoin/TipBot)"), inline=False)
                                embed.set_footer(text=f"Find requested by {ctx.author.name}#{ctx.author.discriminator}")
                                await msg.edit(embed=embed)
                        except Exception as e:
                            pass
            else:
                await ctx.message.add_reaction(EMOJI_INFORMATION)
                await ctx.reply(f'{ctx.author.mention} Searching.. **{searched_text}** and has no result.')
            return
        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
        except Exception as e:
            await logchanbot(traceback.format_exc())
        return


def setup(bot):
    bot.add_cog(Tool(bot))