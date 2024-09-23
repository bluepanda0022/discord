import discord
from discord.ext import commands
import random
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
        result = random.choice(["성공", "실패"])
        initialize_user(interaction)

        if result == "성공":
            user_money[self.user_id] += self.amount
            await interaction.response.send_message(
                f"{color} 버튼 클릭! 성공! {self.amount}원을 얻었습니다. 현재 보유 금액: {user_money[self.user_id]}원")
        else:
            user_money[self.user_id] -= self.amount
            await interaction.response.send_message(
                f"{color} 버튼 클릭! 실패! {self.amount}원이 차감되었습니다. 현재 보유 금액: {user_money[self.user_id]}원")

        for child in self.children:
            child.disabled = True

        await interaction.message.edit(view=self)

@bot.tree.command(name="관리자", description="서버의 관리자 역할을 가진 사용자 목록을 출력합니다.")
async def 관리자(interaction: discord.Interaction):
    admin_ids = get_admin_ids(interaction.guild)
    if admin_ids:
        admin_mentions = [interaction.guild.get_member(id).mention for id in admin_ids]
        await interaction.response.send_message(f'관리자 역할을 가진 사용자: {", ".join(admin_mentions)}')
    else:
        await interaction.response.send_message('관리자 역할을 가진 사용자가 없습니다.')

@bot.tree.command(name="들어오기", description="봇을 현재 음성 채널로 초대합니다.")
async def 들어오기(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if voice_client and voice_client.is_connected():
            await voice_client.move_to(channel)
        else:
            voice_client = await channel.connect()

        await interaction.response.send_message(f'{bot.user.name}이(가) {channel.name}에 들어왔습니다.')
    else:
        await interaction.response.send_message('먼저 음성 채널에 들어가 주세요.')

@bot.tree.command(name="재생", description="YouTube에서 검색어로 음악을 재생합니다.")
async def 재생(interaction: discord.Interaction, 노래: str):
    if not 노래:
        await interaction.response.send_message('검색어를 입력해 주세요. 예: /재생 Never Gonna Give You Up')
        return

    try:
        videos_search = VideosSearch(노래, limit=1)
        result = videos_search.result()

        if not result['result']:
            await interaction.response.send_message('검색 결과가 없습니다.')
            return
    except Exception as e:
        await interaction.response.send_message(f'유튜브 검색 중 오류 발생: {str(e)}')
        return

    await interaction.response.defer()  # 응답 지연을 알림

    try:
        video_url = result['result'][0]['link']
    except (IndexError, KeyError) as e:
        await interaction.response.send_message(f'유효한 비디오 URL을 찾지 못했습니다: {str(e)}')
        return

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'extract_flat': True,
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            audio_url = info['url']
    except Exception as e:
        await interaction.response.send_message(f'오디오 URL 추출 중 오류 발생: {str(e)}')
        return

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    audio_source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
    if interaction.guild.voice_client is None:
        if interaction.user.voice:
            channel = interaction.user.voice.channel
            await channel.connect()
        else:
            await interaction.response.send_message('먼저 음성 채널에 들어가 주세요.')
            return

    interaction.guild.voice_client.play(audio_source)
    await interaction.response.send_message('재생 중...')

@bot.tree.command(name="멈추기", description="현재 재생 중인 음악을 멈춥니다.")
async def 멈추기(interaction: discord.Interaction):
    if interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        await interaction.response.send_message('음악이 멈추었습니다.')
    else:
        await interaction.response.send_message('현재 재생 중인 음악이 없습니다.')

@bot.tree.command(name="일시정지", description="현재 재생 중인 음악을 일시 정지합니다.")
async def 일시정지(interaction: discord.Interaction):
    if interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.pause()
        await interaction.response.send_message('음악을 일시 정지했습니다.')
    else:
        await interaction.response.send_message('현재 재생 중인 음악이 없습니다.')

@bot.tree.command(name="재개", description="일시 정지된 음악을 재개합니다.")
async def 재개(interaction: discord.Interaction):
    if interaction.guild.voice_client.is_paused():
        interaction.guild.voice_client.resume()
        await interaction.response.send_message('음악을 재개합니다.')
    else:
        await interaction.response.send_message('현재 음악이 일시 정지 상태가 아닙니다.')

@bot.tree.command(name="나가", description="음성 채널에서 나갑니다.")
async def 나가(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message('음성 채널에서 나왔습니다.')
    else:
        await interaction.response.send_message('봇이 음성 채널에 있지 않습니다.')

@bot.tree.command(name="돈", description="현재 보유 금액을 확인합니다.")
async def 돈(interaction: discord.Interaction):
    initialize_user(interaction)
    money = user_money[interaction.user.id]
    await interaction.response.send_message(f'{interaction.user.mention}님, 당신의 전재산은 {money}원입니다.')

@bot.tree.command(name="룰렛", description="룰렛을 돌리고 결과에 따라 돈을 얻거나 잃습니다.")
async def 룰렛(interaction: discord.Interaction):
    initialize_user(interaction)
    modal = BettingModal(interaction.user.id)
    await interaction.response.send_modal(modal)

# 봇 실행
bot.run('MTI4NTQ3MDQ2MjEwNDgzMDAzNg.G6UQXQ.UpdeB_7_Ppla8P0AMCcgVWdRcDi6OblePv83Aw')
