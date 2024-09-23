import discord
from discord.ext import commands
import random
import yt_dlp as youtube_dl  # youtube_dl을 yt_dlp로 교체
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
tree = bot.tree  # 슬래시 명령어 사용을 위한 tree 객체

# 사용자 돈을 저장하기 위한 딕셔너리
user_money = {}

# 플레이리스트 저장용 딕셔너리
playlists = {}


# 서버에서 관리자의 역할을 가져오는 함수
def get_admin_ids(guild):
    admin_role = discord.utils.get(guild.roles, name='관리자')  # '관리자' 역할 이름
    if admin_role:
        return [member.id for member in admin_role.members]
    return []


# 기본 돈 함수
def initialize_user(interaction):
    if interaction.user.id not in user_money:
        user_money[interaction.user.id] = 10000  # 기본 돈 10000원


class AudioPlayer:
    def __init__(self, interaction):
        self.interaction = interaction
        self.audio_source = None
        self.is_paused = False

    async def play(self, audio_source):
        if self.interaction.guild.voice_client is None:
            if self.interaction.user.voice:
                channel = self.interaction.user.voice.channel
                await channel.connect()
            else:
                await self.interaction.response.send_message('먼저 음성 채널에 들어가 주세요.')
                return

        if not self.interaction.guild.voice_client.is_playing():
            self.audio_source = discord.PCMVolumeTransformer(audio_source, volume=1.0)
            self.interaction.guild.voice_client.play(self.audio_source)
            await self.interaction.response.send_message('재생 중...')
            self.is_paused = False
        else:
            await self.interaction.response.send_message('이미 음악이 재생 중입니다.')

    async def stop(self):
        if self.interaction.guild.voice_client and self.interaction.guild.voice_client.is_playing():
            self.interaction.guild.voice_client.stop()
            self.audio_source = None
            self.is_paused = False
            await self.interaction.response.send_message('음악을 멈췄습니다.')
        else:
            await self.interaction.response.send_message('현재 재생 중인 음악이 없습니다.')

    async def pause(self):
        if self.interaction.guild.voice_client and self.interaction.guild.voice_client.is_playing():
            self.interaction.guild.voice_client.pause()
            self.is_paused = True
            await self.interaction.response.send_message('음악을 일시 정지했습니다.')
        else:
            await self.interaction.response.send_message('현재 재생 중인 음악이 없습니다.')

    async def resume(self):
        if self.is_paused and self.audio_source:
            self.interaction.guild.voice_client.resume()
            await self.interaction.response.send_message('음악을 재개합니다.')
        else:
            await self.interaction.response.send_message('현재 음악이 일시 정지된 상태가 아닙니다.')

@tree.command()
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


@tree.command(name="재생", description="YouTube에서 검색어로 음악을 재생합니다.")
async def 재생(interaction: discord.Interaction, query: str):
    if not query:
        await interaction.response.send_message('검색어를 입력해 주세요. 예: /재생 Never Gonna Give You Up')
        return

    # YouTube에서 노래 검색
    videos_search = VideosSearch(query, limit=1)
    result = await asyncio.to_thread(videos_search.result)
    if not result['result']:
        await interaction.response.send_message('검색 결과가 없습니다.')
        return

    # 첫 번째 검색 결과의 URL을 가져옵니다.
    video_url = result['result'][0]['link']

    # yt-dlp을 사용하여 스트리밍 URL을 얻습니다.
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
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
    player = AudioPlayer(interaction)
    await player.play(audio_source)


@tree.command(name="멈추기", description="현재 재생 중인 음악을 멈춥니다.")
async def 멈추기(interaction: discord.Interaction):
    player = AudioPlayer(interaction)
    await player.stop()

@tree.command(name="일시정지", description="현재 재생 중인 음악을 일시 정지합니다.")
async def 일시정지(interaction: discord.Interaction):
    player = AudioPlayer(interaction)
    await player.pause()

@tree.command(name="재개", description="일시 정지된 음악을 재개합니다.")
async def 재개(interaction: discord.Interaction):
    player = AudioPlayer(interaction)
    await player.resume()
    
@tree.command(name="플레이리스트추가", description="플레이리스트에 노래를 추가합니다.")
async def 플레이리스트추가(interaction: discord.Interaction, playlist_name: str, song_url: str):
    """플레이리스트에 노래를 추가합니다."""
    if playlist_name not in playlists:
        playlists[playlist_name] = []

    playlists[playlist_name].append(song_url)
    await interaction.response.send_message(f'{playlist_name} 플레이리스트에 노래가 추가되었습니다.')

@tree.command(name="플레이리스트삭제", description="플레이리스트를 삭제합니다.")
async def 플레이리스트삭제(interaction: discord.Interaction, playlist_name: str):
    """플레이리스트를 삭제합니다."""
    if playlist_name in playlists:
        del playlists[playlist_name]
        await interaction.response.send_message(f'{playlist_name} 플레이리스트가 삭제되었습니다.')
    else:
        await interaction.response.send_message('존재하지 않는 플레이리스트입니다.')

@tree.command(name="플레이리스트재생", description="플레이리스트의 모든 노래를 순차적으로 재생합니다.")
async def 플레이리스트재생(interaction: discord.Interaction, playlist_name: str):
    """플레이리스트의 모든 노래를 순차적으로 재생합니다."""
    if playlist_name not in playlists:
        await interaction.response.send_message('존재하지 않는 플레이리스트입니다.')
        return

    if interaction.guild.voice_client is None:
        if interaction.user.voice:
            channel = interaction.user.voice.channel
            await channel.connect()
        else:
            await interaction.response.send_message('먼저 음성 채널에 들어가 주세요.')
            return

    for song_url in playlists[playlist_name]:
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'extract_flat': True,
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(song_url, download=False)
            audio_url = info['url']

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        audio_source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        player = AudioPlayer(interaction)
        await player.play(audio_source)
        while interaction.guild.voice_client.is_playing():
            await asyncio.sleep(1)  # Wait until the current song finishes

    await interaction.response.send_message(f'{playlist_name} 플레이리스트의 모든 노래가 재생되었습니다.')


@tree.command()
async def 돈(ctx):
    """현재 보유한 전재산을 확인합니다."""
    initialize_user(ctx)
    money = user_money[ctx.author.id]
    await ctx.send(f'{ctx.author.mention}님, 현재 보유한 재산은 {money}원입니다.')



@tree.command()
async def 룰렛(ctx, bet: int):
    """룰렛을 돌리고 결과에 따라 돈을 얻거나 잃습니다.
    사용 예: /룰렛 1000
    """
    initialize_user(ctx)

    user_balance = user_money[ctx.author.id]

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
        
@tree.command()
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
    
@tree.command()
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
      

# 봇 토큰 설정
bot.run('MTI4NTQ3MDQ2MjEwNDgzMDAzNg.G6UQXQ.UpdeB_7_Ppla8P0AMCcgVWdRcDi6OblePv83Aw')
