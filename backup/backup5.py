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
tree = bot.tree  # 슬래시 명령어 사용을 위한 tree 객체


# 사용자 돈을 저장하기 위한 딕셔너리
user_money = {}

# 플레이리스트 저장용 딕셔너리
playlists = {}



class BettingModal(Modal):
    def __init__(self, user_id):
        super().__init__(title="배팅 금액 입력")
        self.user_id = user_id
        self.amount = None
        self.add_item(TextInput(
            label="배팅 금액", 
            placeholder="예: 5000", 
            required=True,
            min_length=1,  # 최소 1자 이상 입력
            max_length=6   # 최대 6자까지 입력 (999,999원까지)
        ))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            input_value = self.children[0].value
            if not input_value.isdigit():  # 숫자인지 확인
                raise ValueError("숫자만 입력 가능합니다.")

            self.amount = int(input_value)
            if self.amount <= 0:
                await interaction.response.send_message("배팅 금액은 1원 이상이어야 합니다.", ephemeral=True)
            else:
                # ColorButtonView가 정의되어 있다고 가정
                view = ColorButtonView(self.user_id, self.amount)  
                await interaction.response.send_message("배팅 금액을 설정하였습니다. 버튼을 클릭하여 결과를 확인하세요!", view=view)
        except ValueError as e:
            await interaction.response.send_message(f"유효한 금액을 입력해 주세요: {str(e)}", ephemeral=True)

    async def on_error(self, error: Exception, interaction: discord.Interaction):
        # 에러 로깅 등 추가적인 처리 수행
        print(f"오류 발생: {str(error)}")  
        await interaction.response.send_message("오류가 발생했습니다. 잠시 후 다시 시도해 주세요.", ephemeral=True)



#음악관련 명령어를 포함하는 클래스
class AdminVoiceCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.player = None

    def get_admin_ids(self, guild):
        # 관리자 역할 ID를 가져오는 로직 구현 (예: 특정 역할 이름으로 검색)
        admin_role = discord.utils.get(guild.roles, name="관리자") 
        if admin_role:
            return [member.id for member in guild.members if admin_role in member.roles]
        else:
            return []
    @bot.tree.command(name="관리자", description="서버의 관리자 역할을 가진 사용자 목록을 출력합니다.")
    @app_commands.describe()
    async def 관리자(self, interaction: discord.Interaction):
        admin_ids = self.get_admin_ids(interaction.guild)
        if admin_ids:
            admin_mentions = [interaction.guild.get_member(id).mention for id in admin_ids]
            await interaction.response.send_message(f'관리자 역할을 가진 사용자: {", ".join(admin_mentions)}')
        else:
            await interaction.response.send_message('관리자 역할을 가진 사용자가 없습니다.')
    #들어오기
    @bot.tree.command(name="들어오기", description="봇을 현재 음성 채널로 초대합니다.")
    @app_commands.describe()
    async def 들어오기(self, interaction: discord.Interaction):
        if interaction.user.voice:
            channel = interaction.user.voice.channel
            voice_client = interaction.guild.voice_client

            try:
                if voice_client and voice_client.is_connected():
                    await voice_client.move_to(channel)
                else:
                    voice_client = await channel.connect()

                await interaction.response.send_message(f'{self.bot.user.name}이(가) {channel.name}에 들어왔습니다.')
            except Exception as e:
                await interaction.response.send_message(f'음성 채널 참여 중 오류 발생: {e}')
        else:
            await interaction.response.send_message('먼저 음성 채널에 들어가 주세요.')

    #재생
    @bot.tree.command(name="재생", description="YouTube에서 검색어로 음악을 재생합니다.")
    @app_commands.describe()
    async def 재생(self, interaction: discord.Interaction, 노래제목: str):
        if not 노래제목:
            await interaction.response.send_message('검색어를 입력해 주세요. 예: /재생 Never Gonna Give You Up')
            return

        try:
            videos_search = VideosSearch(노래제목, limit=1)
            result = videos_search.result()

            if not result['result']:
                await interaction.response.send_message('검색 결과가 없습니다.')
                return
        except KeyError as e:
            await interaction.response.send_message(f'유튜브 검색 결과 처리 중 오류(KeyError) 발생: {str(e)}')
            return
        except Exception as e:
            await interaction.response.send_message(f'유튜브 검색 중 예기치 않은 오류 발생: {str(e)}')
            return

        if not interaction.response.is_done():
            await interaction.followup.send('노래 재생을 시작합니다...')

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
            if not interaction.response.is_done():
                await interaction.response.defer()

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                audio_url = info['url']
        except youtube_dl.utils.DownloadError as e:
            await interaction.followup.send(f'오디오 다운로드 오류(DownloadError): {str(e)}')
            return
        except KeyError as e:
            await interaction.followup.send(f'오디오 정보 추출 중 오류(KeyError): {str(e)}')
            return
        except Exception as e:
            await interaction.followup.send(f'오디오 URL 추출 중 예기치 않은 오류 발생: {str(e)}')
            return

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        try:
            audio_source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        except discord.errors.ClientException as e:
            await interaction.followup.send(f'FFmpeg 클라이언트 오류 발생: {str(e)}')
            return
        except FileNotFoundError as e:
            await interaction.followup.send(f'FFmpeg 파일 경로 오류(FileNotFoundError): {str(e)}')
            return
        except Exception as e:
            await interaction.followup.send(f'FFmpeg 실행 중 예기치 않은 오류 발생: {str(e)}')
            return

        try:
            player = AudioPlayer(interaction)
            await player.play(audio_source)

            if not interaction.response.is_done():
                await interaction.followup.send('노래 재생을 시작합니다...')
        except discord.errors.ClientException as e:
            if not interaction.response.is_done():
                await interaction.followup.send(f'디스코드 클라이언트 재생 오류 발생: {str(e)}')
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.followup.send(f'오디오 재생 중 예기치 않은 오류 발생: {str(e)}')                
    
    #멈추기 명령어
    @bot.tree.command(name="멈추기", description="현재 재생 중인 음악을 멈춥니다.")
    @app_commands.describe()
    async def 멈추기(self, interaction: discord.Interaction):
        if self.player:
            try:
                await self.player.stop()
                await interaction.response.send_message('음악 재생을 멈췄습니다.')
            except Exception as e:
                await interaction.response.send_message(f'음악 재생 멈춤 중 오류 발생: {e}')
        else:
            await interaction.response.send_message('현재 재생 중인 음악이 없습니다.')
    #일시정지
    @bot.tree.command(name="일시정지", description="현재 재생 중인 음악을 일시 정지합니다.")
    @app_commands.describe()
    async def 일시정지(self, interaction: discord.Interaction):
        if self.player:
            try:
                await self.player.pause()
                await interaction.response.send_message('음악 재생을 일시 정지했습니다.')
            except Exception as e:
                await interaction.response.send_message(f'음악 재생 일시 정지 중 오류 발생: {e}')
        else:
            await interaction.response.send_message('현재 재생 중인 음악이 없습니다.')
    #재개
    @bot.tree.command(name="재개", description="일시 정지된 음악을 재개합니다.")
    @app_commands.describe()
    async def 재개(self, interaction: discord.Interaction):
        if self.player:
            try:
                await self.player.resume()
                await interaction.response.send_message('음악 재생을 재개했습니다.')
            except Exception as e:
                await interaction.response.send_message(f'음악 재생 재개 중 오류 발생: {e}')
        else:
            await interaction.response.send_message('현재 재생 중인 음악이 없습니다.')
    #나가
    @bot.tree.command(name="나가", description="음성 채널에서 나갑니다.")
    @app_commands.describe()
    async def 나가(self, interaction: discord.Interaction):
        

        if interaction.guild.voice_client:
            try:
                await interaction.guild.voice_client.disconnect()
                await interaction.response.send_message('음성 채널에서 나왔습니다.')
            except Exception as e:
                await interaction.response.send_message(f'음성 채널 퇴장 중 오류 발생: {e}')
        else:
            await interaction.response.send_message('봇이 음성 채널에 있지 않습니다.')
    
    #플레이리스트 기능        
    @bot.tree.command(name="플레이리스트추가", description="플레이리스트에 노래를 추가합니다.")
    @app_commands.describe()
    async def 플레이리스트추가(self, interaction: discord.Interaction, playlist_name: str, song_url: str):
        """플레이리스트에 노래를 추가합니다."""
        if playlist_name not in self.playlists:
            self.playlists[playlist_name] = []

        self.playlists[playlist_name].append(song_url)
        await interaction.response.send_message(f'{playlist_name} 플레이리스트에 노래가 추가되었습니다.')

    @bot.tree.command(name="플레이리스트삭제", description="플레이리스트를 삭제합니다.")
    @app_commands.describe()
    async def 플레이리스트삭제(self, interaction: discord.Interaction, playlist_name: str):
        """플레이리스트를 삭제합니다."""
        if playlist_name in self.playlists:
            del self.playlists[playlist_name]
            await interaction.response.send_message(f'{playlist_name} 플레이리스트가 삭제되었습니다.')
        else:
            await interaction.response.send_message('존재하지 않는 플레이리스트입니다.')

    @bot.tree.command(name="플레이리스트재생", description="플레이리스트의 모든 노래를 순차적으로 재생합니다.")
    @app_commands.describe()
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

#돈, 룰렛, 게임관련 기능 포함 클래스
class MoneyManagementCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_money = {}
        
    #초기 시드머니 설정
    def initialize_user(self, interaction):
        user_id = interaction.user.id
        if user_id not in self.user_money:
            self.user_money[user_id] = 500000  # 초기 시드머니

    def get_admin_ids(self, guild):
        # 관리자 역할 ID를 가져오는 로직 구현 (예: 특정 역할 이름으로 검색)
        admin_role = discord.utils.get(guild.roles, name="관리자") 
        if admin_role:
            return [member.id for member in guild.members if admin_role in member.roles]
        else:
            return []

    @bot.tree.command(name="돈", description="현재 보유 금액을 확인합니다.")
    @app_commands.describe()
    async def 돈(self, interaction: discord.Interaction):
        self.initialize_user(interaction)  # 사용자 초기화 호출
        money = self.user_money[interaction.user.id]
        await interaction.response.send_message(f'{interaction.user.mention}님, 당신의 전재산은 {money}원입니다.')


    @bot.tree.command(name="룰렛", description="룰렛을 돌리고 결과에 따라 돈을 얻거나 잃습니다.")
    @app_commands.describe()
    async def 룰렛(self, interaction: discord.Interaction, bet: int):
        """룰렛을 돌리고 결과에 따라 돈을 얻거나 잃습니다."""
        self.initialize_user(interaction)

        user_balance = self.user_money[interaction.user.id]

        if bet <= 0:
            await interaction.response.send_message('베팅 금액은 1원 이상이어야 합니다.')
            return

        if bet > user_balance:
            await interaction.response.send_message('보유 금액이 부족합니다.')
            return

        outcomes = ['빨강', '검정', '초록']
        result = random.choice(outcomes)

        if result == '빨강':
            self.user_money[interaction.user.id] += bet
            await interaction.response.send_message(f'룰렛 결과: 빨강! {bet}원을 얻었습니다. 현재 보유 금액: {self.user_money[interaction.user.id]}원')
        elif result == '검정':
            self.user_money[interaction.user.id] -= bet
            await interaction.response.send_message(f'룰렛 결과: 검정! {bet}원을 잃었습니다. 현재 보유 금액: {self.user_money[interaction.user.id]}원')
        else:
            await interaction.response.send_message(f'룰렛 결과: 초록! 베팅한 금액이 반환됩니다. 현재 보유 금액: {self.user_money[interaction.user.id]}원')

    @bot.tree.command(name="게임", description="게임을 시작합니다. 배팅 금액을 입력받고 버튼을 클릭하여 결과를 확인하세요.")
    @app_commands.describe()
    async def 게임(self, interaction: discord.Interaction):
        """게임을 시작합니다. 배팅 금액을 입력받고 버튼을 클릭하여 결과를 확인하세요."""
        await interaction.response.send_modal(BettingModal(interaction.user.id))

    @bot.tree.command(name="돈추가", description="특정 유저에게 돈을 추가합니다.")
    @app_commands.describe()
    async def 돈추가(self, interaction: discord.Interaction, 맴버: discord.Member, 돈 : int):
        """특정 유저에게 돈을 추가합니다."""
        admin_ids = self.get_admin_ids(interaction.guild)
        if interaction.user.id not in admin_ids:
            await interaction.response.send_message('이 명령어를 사용할 권한이 없습니다.')
            return

        try:
            amount = int(돈)
            if amount <= 0:
                await interaction.response.send_message('추가할 금액은 1원 이상이어야 합니다.')
                return

            self.initialize_user(interaction)
            self.user_money[맴버.id] += 돈
            await interaction.response.send_message(f'{맴버.mention}님에게 {돈}원을 추가했습니다. 현재 보유 금액: {self.user_money[맴버.id]}원')
        except ValueError:
            await interaction.response.send_message('추가할 금액은 숫자로 입력해야 합니다.')

    @bot.tree.command(name="돈차감", description="특정 유저에게서 돈을 차감합니다.")
    @app_commands.describe()
    async def 돈차감(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        """특정 유저에게서 돈을 차감합니다."""
        admin_ids = self.get_admin_ids(interaction.guild)
        if interaction.user.id not in admin_ids:
            await interaction.response.send_message('이 명령어를 사용할 권한이 없습니다.')
            return

        try:
            amount = int(amount)
            if amount <= 0:
                await interaction.response.send_message('차감할 금액은 1원 이상이어야 합니다.')
                return

            self.initialize_user(interaction)
            if amount > self.user_money[member.id]:
                await interaction.response.send_message('보유 금액이 부족합니다.')
                return

            self.user_money[member.id] -= amount
            await interaction.response.send_message(f'{member.mention}님에게서 {amount}원을 차감했습니다. 현재 보유 금액: {self.user_money[member.id]}원')
        except ValueError:
            await interaction.response.send_message('차감할 금액은 숫자로 입력해야 합니다.')

def initialize_user(self, interaction):
    if interaction.user.id not in self.user_money:
        self.user_money[interaction.user.id] = 500000 #초기 시드머니
            
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

class AudioPlayer:
    def __init__(self, interaction, bot):
        self.interaction = interaction
        self.bot = bot
        self.audio_source = None
        self.is_paused = False
        self.is_playing = False  # 재생 상태 변수 추가
   
    async def setup_hook():
    # This will be executed after the bot is connected and ready
        print("Setup hook called!") 

    bot.setup_hook = setup_hook 
    
    async def after_playback(self, error):
        self.is_playing = False
        self.is_paused = False
        if error:
            # 코루틴을 직접 호출합니다.
            await self.send_error_message(f"재생 중 오류 발생: {str(error)}")

    async def play(self, audio_source):
        try:
            if self.is_playing:
                await self.send_error_message("이미 다른 곡을 재생 중입니다.")
                return

            if self.interaction.guild.voice_client is None:
                if self.interaction.user.voice:
                    channel = self.interaction.user.voice.channel
                    await channel.connect()
                else:
                    await self.send_error_message('먼저 음성 채널에 들어가 주세요.')
                    return

            self.audio_source = discord.PCMVolumeTransformer(audio_source, volume=1.0)
        
            try:
                self.interaction.guild.voice_client.play(self.audio_source) 
            except discord.errors.ClientException as e:
                await self.send_error_message(f'재생 중 오류 발생: {str(e)}')
                return

            self.is_playing = True
            await self.interaction.response.send_message('재생 중...')
            self.is_paused = False

            asyncio.create_task(self.handle_playback_finished())

        except Exception as e:
            await self.send_error_message(f'오디오 재생 중 예기치 않은 오류 발생: {str(e)}')

    async def handle_playback_finished(self):
        """음악 재생이 완료된 후 호출되는 함수입니다."""
        while self.interaction.guild.voice_client.is_playing():
            await asyncio.sleep(1)

        # 재생이 끝난 후 처리할 작업들
        self.is_playing = False
        self.is_paused = False
        
    async def pause(self):
        try:
            if self.interaction.guild.voice_client and self.interaction.guild.voice_client.is_playing():
                self.interaction.guild.voice_client.pause()
                self.is_paused = True
                await self.interaction.response.send_message('음악을 일시 정지했습니다.')
            else:
                await self.interaction.response.send_message('현재 재생 중인 음악이 없습니다.')
        except AttributeError as e:
            await self.send_error_message(f'오류 발생: {str(e)}')

    async def resume(self):
        try:
            if self.is_paused and self.audio_source:
                self.interaction.guild.voice_client.resume()
                self.is_paused = False
                await self.interaction.response.send_message('음악을 재개합니다.')
            else:
                await self.interaction.response.send_message('현재 음악이 일시 정지된 상태가 아닙니다.')
        except AttributeError as e:
            await self.send_error_message(f'오류 발생: {str(e)}')

    async def send_error_message(self, message):
        if not self.interaction.response.is_done():
            await self.interaction.followup.send(message)
        else:
            await self.interaction.channel.send(message)

# 봇 이벤트 핸들러
@bot.event
async def on_ready():
    guild_id = 1144201109154566154  # 실제 길드 ID
    guild = discord.Object(id=guild_id)  # Object로 래핑
    bot.tree.clear_commands(guild=guild)  # await 제거
    print(f'Logged in as {bot.user.name}')

async def setup(bot):
    await bot.tree.sync()
    await bot.add_cog(AdminVoiceCommands(bot))
    await bot.add_cog(MoneyManagementCommands(bot))

# 봇 토큰 설정 및 실행
bot.run('MTI4NzAxOTMxNDY4MzA1NjE5MA.GEi2M8.c944aeOpaxf7K9y46G-0AM7InAjjzI7-zveN-s')