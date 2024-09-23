import discord
from discord.ext import commands
import yt_dlp as youtube_dl
from youtubesearchpython import VideosSearch

# 디스코드 봇의 Intents 설정
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# 봇 인스턴스 생성
bot = commands.Bot(command_prefix='/', intents=intents)

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

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

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
async def 나가(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send('음성 채널에서 나왔습니다.')
    else:
        await ctx.send('봇이 음성 채널에 있지 않습니다.')

# 봇 토큰 설정 
bot.run('MTI4NTQ3MDQ2MjEwNDgzMDAzNg.G6UQXQ.UpdeB_7_Ppla8P0AMCcgVWdRcDi6OblePv83Aw')