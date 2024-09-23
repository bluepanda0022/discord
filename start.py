import discord
import json
import sqlite3
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

#데이터베이스 테이블 생성
def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()

    # 사용자 돈 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_money (
        user_id INTEGER PRIMARY KEY,
        money INTEGER
    )
    ''')

    # 플레이리스트 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS playlists (
        name TEXT PRIMARY KEY,
        song_urls TEXT
    )
    ''')

    conn.commit()
    conn.close()

# 봇 시작 시 데이터베이스 초기화
init_db()

#데이터베이스에 저장
def save_data():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()

    # 사용자 돈 저장
    for user_id, money in user_money.items():
        cursor.execute('''
        INSERT INTO user_money (user_id, money)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET money = excluded.money
        ''', (user_id, money))

    # 플레이리스트 저장
    for playlist_name, song_urls in playlists.items():
        cursor.execute('''
        INSERT INTO playlists (name, song_urls)
        VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET song_urls = excluded.song_urls
        ''', (playlist_name, json.dumps(song_urls)))

    conn.commit()
    conn.close()

#데이터베이스에서 데이터 불러오기 
def load_data():
    global user_money, playlists
    try:
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()

        # 사용자 돈 불러오기
        user_money = {}
        cursor.execute('SELECT user_id, money FROM user_money')
        for row in cursor.fetchall():
            user_money[row[0]] = row[1]

        # 플레이리스트 불러오기
        playlists = {}
        cursor.execute('SELECT name, song_urls FROM playlists')
        for row in cursor.fetchall():
            playlists[row[0]] = json.loads(row[1])

        conn.close()
    except sqlite3.OperationalError as e:
        print(f"데이터베이스 오류: {e}")
    
    
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

class BettingModal(Modal):
    def __init__(self, user_id):
        super().__init__(title="배팅 금액 입력")
        self.user_id = user_id
        self.amount = None
        self.add_item(TextInput(label="배팅 금액", placeholder="예: 5000", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.amount = int(self.children[0].value)
            if self.amount <= 0:
                await interaction.response.send_message("배팅 금액은 1원 이상이어야 합니다.", ephemeral=True)
            else:
                view = ColorButtonView(self.user_id, self.amount)
                await interaction.response.send_message("배팅 금액을 설정하였습니다. 버튼을 클릭하여 결과를 확인하세요!", view=view)
        except ValueError:
            await interaction.response.send_message("유효한 금액을 입력해 주세요.", ephemeral=True)

    async def on_error(self, error: Exception, interaction: discord.Interaction):
        await interaction.response.send_message(f"오류 발생: {str(error)}", ephemeral=True)

class ColorButtonView(View):
    def __init__(self, user_id, amount):
        super().__init__()
        self.user_id = user_id
        self.amount = amount

    @discord.ui.button(label="빨강", style=discord.ButtonStyle.danger)
    async def red_button(self, interaction: discord.Interaction, button: Button):
        await self.handle_click(interaction, "빨강")

    @discord.ui.button(label="파랑", style=discord.ButtonStyle.primary)
    async def blue_button(self, interaction: discord.Interaction, button: Button):
        await self.handle_click(interaction, "파랑")

    async def handle_click(self, interaction: discord.Interaction, color: str):
        try:
            initialize_user(interaction)  # 사용자 초기화

            result = random.choice(["성공", "실패"])

            if result == "성공":
                user_money[self.user_id] += self.amount
                await interaction.response.send_message(f"{color} 버튼 클릭! 성공! {self.amount}원을 얻었습니다. 현재 보유 금액: {user_money[self.user_id]}원")
            else:
                user_money[self.user_id] -= self.amount
                await interaction.response.send_message(f"{color} 버튼 클릭! 실패! {self.amount}원이 차감되었습니다. 현재 보유 금액: {user_money[self.user_id]}원")

            # 버튼을 비활성화합니다.
            for child in self.children:
                child.disabled = True
            
            # 변경된 버튼 상태를 업데이트합니다.
            await interaction.message.edit(view=self)

        except KeyError:
            await interaction.response.send_message("오류 발생: 사용자 정보를 찾을 수 없습니다.")
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}")

@bot.event
async def on_ready():
    load_data()
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()  # 슬래시 명령어 동기화

@tree.command(name="관리자", description="서버의 관리자 역할을 가진 사용자 목록을 출력합니다.")
async def 관리자(interaction: discord.Interaction):
    admin_ids = get_admin_ids(interaction.guild)
    if admin_ids:
        admin_mentions = [interaction.guild.get_member(id).mention for id in admin_ids]
        await interaction.response.send_message(f'관리자 역할을 가진 사용자: {", ".join(admin_mentions)}')
    else:
        await interaction.response.send_message('관리자 역할을 가진 사용자가 없습니다.')

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

        self.audio_source = discord.PCMVolumeTransformer(audio_source, volume=1.0)
        self.interaction.guild.voice_client.play(self.audio_source)
        
        # 응답 지연을 위해 defer 사용
        await self.interaction.response.defer()
        await asyncio.sleep(1)  # 충분한 시간 지연
        await self.interaction.followup.send('재생 중...')
        self.is_paused = False

    async def stop(self):
        if self.interaction.guild.voice_client and self.interaction.guild.voice_client.is_playing():
            self.interaction.guild.voice_client.stop()
            self.audio_source = None
            self.is_paused = False
            await self.interaction.response.defer()
            await asyncio.sleep(1)
            await self.interaction.followup.send('음악을 멈췄습니다.')
        else:
            await self.interaction.response.send_message('현재 재생 중인 음악이 없습니다.')

    async def pause(self):
        if self.interaction.guild.voice_client and self.interaction.guild.voice_client.is_playing():
            self.interaction.guild.voice_client.pause()
            self.is_paused = True
            await self.interaction.response.defer()
            await asyncio.sleep(1)
            await self.interaction.followup.send('음악을 일시 정지했습니다.')
        else:
            await self.interaction.response.send_message('현재 재생 중인 음악이 없습니다.')

    async def resume(self):
        if self.is_paused and self.audio_source:
            await self.play(self.audio_source)
            self.interaction.guild.voice_client.resume()
            await self.interaction.response.defer()
            await asyncio.sleep(1)
            await self.interaction.followup.send('음악을 재개합니다.')
        else:
            await self.interaction.response.send_message('현재 음악이 일시 정지된 상태가 아닙니다.')

@tree.command(name="들어오기", description="봇을 현재 음성 채널로 초대합니다.")
async def 들어오기(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        if interaction.guild.voice_client is None:
            await channel.connect()
        else:
            await interaction.guild.voice_client.move_to(channel)
        await interaction.response.send_message(f'{bot.user.name}이(가) {channel.name}에 들어왔습니다.')
    else:
        await interaction.response.send_message('먼저 음성 채널에 들어가 주세요.')

@tree.command(name="재생", description="YouTube에서 검색어로 음악을 재생합니다.")
async def 재생(interaction: discord.Interaction, query: str):
    if query is None:
        await interaction.response.send_message('검색어를 입력해 주세요. 예: /재생 Never Gonna Give You Up')
        return

    # YouTube에서 노래 검색
    videos_search = VideosSearch(query, limit=1)
    result = videos_search.result()
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

@tree.command(name="나가", description="음성 채널에서 나갑니다.")
async def 나가(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message('음성 채널에서 나왔습니다.')
    else:
        await interaction.response.send_message('봇이 음성 채널에 있지 않습니다.')

@bot.tree.command(name="돈", description="현재 보유 금액을 확인합니다.")
async def 돈(interaction: discord.Interaction):
    """현재 보유 금액을 확인합니다."""
    initialize_user(interaction)
    money = user_money[interaction.user.id]
    await interaction.response.send_message(f'{interaction.user.mention}님, 당신의 전재산은 {money}원입니다.')

@bot.tree.command(name="룰렛", description="룰렛을 돌리고 결과에 따라 돈을 얻거나 잃습니다.")
async def 룰렛(interaction: discord.Interaction, bet: int):
    """룰렛을 돌리고 결과에 따라 돈을 얻거나 잃습니다."""
    initialize_user(interaction)

    user_balance = user_money[interaction.user.id]

    if bet <= 0:
        await interaction.response.send_message('베팅 금액은 1원 이상이어야 합니다.')
        return

    if bet > user_balance:
        await interaction.response.send_message('보유 금액이 부족합니다.')
        return

    outcomes = ['빨강', '검정', '초록']
    result = random.choice(outcomes)

    if result == '빨강':
        user_money[interaction.user.id] += bet
        await interaction.response.send_message(f'룰렛 결과: 빨강! {bet}원을 얻었습니다. 현재 보유 금액: {user_money[interaction.user.id]}원')
    elif result == '검정':
        user_money[interaction.user.id] -= bet
        await interaction.response.send_message(f'룰렛 결과: 검정! {bet}원을 잃었습니다. 현재 보유 금액: {user_money[interaction.user.id]}원')
    else:
        await interaction.response.send_message(f'룰렛 결과: 초록! 베팅한 금액이 반환됩니다. 현재 보유 금액: {user_money[interaction.user.id]}원')

@bot.tree.command(name="게임", description="게임을 시작합니다. 배팅 금액을 입력받고 버튼을 클릭하여 결과를 확인하세요.")
async def 게임(interaction: discord.Interaction):
    """게임을 시작합니다. 배팅 금액을 입력받고 버튼을 클릭하여 결과를 확인하세요."""
    await interaction.response.send_modal(BettingModal(interaction.user.id))

@bot.tree.command(name="돈추가", description="특정 유저에게 돈을 추가합니다.")
async def 돈추가(interaction: discord.Interaction, member: discord.Member, amount: int):
    """특정 유저에게 돈을 추가합니다."""
    admin_ids = get_admin_ids(interaction.guild)
    if interaction.user.id not in admin_ids:
        await interaction.response.send_message('이 명령어를 사용할 권한이 없습니다.')
        return

    if amount <= 0:
        await interaction.response.send_message('추가할 금액은 1원 이상이어야 합니다.')
        return

    if member.id not in user_money:
        user_money[member.id] = 0

    user_money[member.id] += amount
    await interaction.response.send_message(f'{member.mention}님에게 {amount}원을 추가했습니다. 현재 보유 금액: {user_money[member.id]}원')

@bot.tree.command(name="돈차감", description="특정 유저에게서 돈을 차감합니다.")
async def 돈차감(interaction: discord.Interaction, member: discord.Member, amount: int):
    """특정 유저에게서 돈을 차감합니다."""
    admin_ids = get_admin_ids(interaction.guild)
    if interaction.user.id not in admin_ids:
        await interaction.response.send_message('이 명령어를 사용할 권한이 없습니다.')
        return

    if amount <= 0:
        await interaction.response.send_message('차감할 금액은 1원 이상이어야 합니다.')
        return

    if member.id not in user_money:
        user_money[member.id] = 0

    if amount > user_money[member.id]:
        await interaction.response.send_message('보유 금액이 부족합니다.')
        return

    user_money[member.id] -= amount
    await interaction.response.send_message(f'{member.mention}님에게서 {amount}원을 차감했습니다. 현재 보유 금액: {user_money[member.id]}원')

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

#자동 저장   
@bot.event
async def on_disconnect():
    save_data()

# 봇 토큰 설정
bot.run('MTI4NTQ3MDQ2MjEwNDgzMDAzNg.G6UQXQ.UpdeB_7_Ppla8P0AMCcgVWdRcDi6OblePv83Aw')