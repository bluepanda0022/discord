from pypresence import Presence
import time

client_id = "1285470462104830036"
RPC = Presence(client_id)  # 인스턴스 생성
RPC.connect()  # Discord에 연결

def update_presence():
    RPC.update(
        state="Playing Solo",
        details="Competitive",
        start=int(time.time()),  # 현재 시간
        large_image="numbani",  # 큰 이미지 이름
        large_text="Numbani",  # 큰 이미지 텍스트
        small_image="rogue",  # 작은 이미지 이름
        small_text="Rogue - Level 100",  # 작은 이미지 텍스트
        join="MTI4NzM0OjFpMmhuZToxMjMxMjM="  # 이 값은 필요할 경우에만 사용
    )

update_presence()

# 프로그램이 종료되지 않도록 유지
while True:
    time.sleep(15)  # 15초마다 업데이트
    update_presence()  # 업데이트 호출