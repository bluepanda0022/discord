import discord
import random
from discord.ext import commands
import yt_dlp as youtube_dl
from youtubesearchpython import VideosSearch
from discord.ui import Button, View, Modal, TextInput
import asyncio
from discord import app_commands

# 디스코드 봇의 Intents 설정
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True


# 봇 인스턴스 생성
bot = commands.Bot(command_prefix='/', intents=intents)

# 사용자 돈을 저장하기 위한 딕셔너리
user_money = {}

# 플레이리스트 저장용 딕셔너리
playlists = {}

#돈
def initialize_user(ctx):
    if ctx.author.id not in user_money:
        user_money[ctx.author.id] = 1000000   # 기본 돈 1000000원
        
# 서버에서 관리자의 역할을 가져오는 함수
def get_admin_ids(guild):
    admin_role = discord.utils.get(guild.roles, name='관리자')  # 'admin' 역할 이름
    if admin_role:
        return [member.id for member in admin_role.members]
    return []

#음악 플레이어
class AudioPlayer:
    def __init__(self, ctx):
        self.ctx = ctx

    async def play(self, audio_source):
        if self.ctx.voice_client is None:
            if self.ctx.author.voice:
                channel = self.ctx.author.voice.channel
                await channel.connect()
            else:
                await self.ctx.send('먼저 음성 채널에 들어가 주세요.')
                return

        source = discord.PCMVolumeTransformer(audio_source, volume=1.0)
        self.ctx.voice_client.play(source)
        await self.ctx.send('재생 중...')

    async def stop(self):
        if self.ctx.voice_client and self.ctx.voice_client.is_playing():
            self.ctx.voice_client.stop()
            await self.ctx.send('음악을 멈췄습니다.')
        else:
            await self.ctx.send('현재 재생 중인 음악이 없습니다.')
            
            
            
@bot.command()
async def 들어와(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            await channel.connect()
        else:
            await ctx.voice_client.move_to(channel)
        await ctx.send(f'{bot.user.name}이(가) {channel.name}에 들어왔습니다.')
    else:
        await ctx.send('먼저 음성 채널에 들어가 주세요.')

@bot.command()
async def 재생(ctx, *, query=None):
    if query is None:
        await ctx.send('검색어를 입력해 주세요. 예: /재생 Never Gonna Give You Up')
        return

    # YouTube에서 노래 검색
    videos_search = VideosSearch(query, limit=1)
    result = videos_search.result()
    if not result['result']:
        await ctx.send('검색 결과가 없습니다.')
        return

    # 첫 번째 검색 결과의 URL을 가져옵니다.
    video_url = result['result'][0]['link']

    # YouTube DL을 사용하여 스트리밍 URL을 얻습니다.
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'extract_flat': True,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        audio_url = info['url']

    # AudioSource 클래스의 사용
    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    audio_source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
    player = AudioPlayer(ctx)
    await player.play(audio_source)

@bot.command()
async def 멈춰(ctx):
    player = AudioPlayer(ctx)
    await player.stop()

@bot.command()
async def 나가(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send('음성 채널에서 나왔습니다.')
    else:
        await ctx.send('봇이 음성 채널에 있지 않습니다.')
        
@bot.command()
async def 돈(ctx):
    """현재 보유 금액을 확인합니다."""
    initialize_user(ctx)
    money = user_money[ctx.author.id]
    await ctx.send(f'{ctx.author.mention}님, 현재 보유 금액은 {money}원입니다.')

@bot.command()
async def 룰렛(ctx, bet: int = None):
    """룰렛을 돌리고 결과에 따라 돈을 얻거나 잃습니다.
    사용 예: /룰렛 1000
    """
    initialize_user(ctx)

    user_balance = user_money[ctx.author.id]
    
    if bet is None:
        await ctx.send('베팅 금액을 입력해주세요.')
        return

    if bet <= 0:
        await ctx.send('베팅 금액은 1원 이상이어야 합니다.')
        return

    if bet > user_balance:
        await ctx.send('보유 금액이 부족합니다.')
        return


    outcomes = ['빨강', '검정', '초록']
    result = random.choice(outcomes)

    if result == '빨강':
        user_money[ctx.author.id] += bet
        await ctx.send(f'룰렛 결과: 빨강! {bet}원을 얻었습니다. 현재 보유 금액: {user_money[ctx.author.id]}원')
    elif result == '검정':
        user_money[ctx.author.id] -= bet
        await ctx.send(f'룰렛 결과: 검정! {bet}원을 잃었습니다. 현재 보유 금액: {user_money[ctx.author.id]}원')
    else:
        await ctx.send(f'룰렛 결과: 초록! 베팅한 금액이 반환됩니다. 현재 보유 금액: {user_money[ctx.author.id]}원')
        
@bot.command()
async def 돈추가(ctx, member: discord.Member, amount: int):
    """특정 유저에게 돈을 추가합니다.
    사용 예: /돈추가 @유저 5000
    """
    admin_ids = get_admin_ids(ctx.guild)
    if ctx.author.id not in admin_ids:
        await ctx.send('이 명령어를 사용할 권한이 없습니다.')
        return

    if amount <= 0:
        await ctx.send('추가할 금액은 1원 이상이어야 합니다.')
        return

    if member.id not in user_money:
        user_money[member.id] = 10000

    user_money[member.id] += amount
    await ctx.send(f'{member.mention}님에게 {amount}원이 추가되었습니다. 현재 보유 금액: {user_money[member.id]}원')
    
@bot.command()
async def 돈차감(ctx, member: discord.Member, amount: int):
    """특정 유저에게서 돈을 차감합니다.
    사용 예: /돈차감 @유저 2000
    """
    admin_ids = get_admin_ids(ctx.guild)
    if ctx.author.id not in admin_ids:
        await ctx.send('이 명령어를 사용할 권한이 없습니다.')
        return

    if amount <= 0:
        await ctx.send('차감할 금액은 1원 이상이어야 합니다.')
        return

    if member.id not in user_money:
        user_money[member.id] = 10000

    if amount > user_money[member.id]:
        await ctx.send('보유 금액이 부족합니다.')
        return

    user_money[member.id] -= amount
    await ctx.send(f'{member.mention}님에게서 {amount}원이 차감되었습니다. 현재 보유 금액: {user_money[member.id]}원')

#플레이리스트 기능        
@bot.command(name="플레이리스트추가", description="플레이리스트에 노래를 추가합니다.")

async def 플레이리스트추가(self, interaction: discord.Interaction, playlist_name: str, song_url: str):
    """플레이리스트에 노래를 추가합니다."""
    if playlist_name not in self.playlists:
        self.playlists[playlist_name] = []

    self.playlists[playlist_name].append(song_url)
    await interaction.response.send_message(f'{playlist_name} 플레이리스트에 노래가 추가되었습니다.')

@bot.command(name="플레이리스트삭제", description="플레이리스트를 삭제합니다.")
async def 플레이리스트삭제(self, interaction: discord.Interaction, playlist_name: str):
    """플레이리스트를 삭제합니다."""
    if playlist_name in self.playlists:
        del self.playlists[playlist_name]
        await interaction.response.send_message(f'{playlist_name} 플레이리스트가 삭제되었습니다.')
    else:
        await interaction.response.send_message('존재하지 않는 플레이리스트입니다.')

@bot.command(name="플레이리스트재생", description="플레이리스트의 모든 노래를 순차적으로 재생합니다.")
async def 플레이리스트재생(self, interaction: discord.Interaction, playlist_name: str):
    """플레이리스트의 모든 노래를 순차적으로 재생합니다."""
    if playlist_name not in self.playlists:
        await interaction.response.send_message('존재하지 않는 플레이리스트입니다.')
        return

    if interaction.guild.voice_client is None:
        if interaction.user.voice:
            channel = interaction.user.voice.channel
            await channel.connect()
        else:
            await interaction.response.send_message('먼저 음성 채널에 들어가 주세요.')
            return

    for song_url in self.playlists[playlist_name]:
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'extract_flat': True,
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(song_url, download=False)
                audio_url = info['url']

            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn'
            }

            audio_source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)

            if self.player is None:
                self.player = AudioPlayer(interaction, self.bot)  # 필요한 경우에만 생성

            await self.player.play(audio_source)
            while interaction.guild.voice_client.is_playing():
                await asyncio.sleep(1)

        except (youtube_dl.utils.DownloadError, KeyError, Exception) as e:
            await interaction.followup.send(f'노래 재생 중 오류 발생: {e}')

    await interaction.response.send_message(f'{playlist_name} 플레이리스트의 모든 노래가 재생되었습니다.')
       
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user.name}')
    


# 봇 토큰 설정
bot.run('MTI4NzAxOTMxNDY4MzA1NjE5MA.GEi2M8.c944aeOpaxf7K9y46G-0AM7InAjjzI7-zveN-s')
