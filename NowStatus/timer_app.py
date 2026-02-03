import tkinter as tk
from datetime import datetime, timedelta
import pygame  # 소리 재생을 위해 추가

class TouchMirrorTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("Touch Smart Mirror Timer")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg='black')
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self.font_family = "Noto Sans KR" # 폰트 설치 확인 필수
        
        # 소리 초기화
        pygame.mixer.init()
        # 비프음 생성 (또는 .wav 파일 경로 지정 가능)
        # 여기서는 시스템 기본 비프음을 쓰거나 아래 설명대로 파일을 준비하세요.
        
        # 데이터 초기화
        self.mode = "CLOCK" 
        self.running = False
        self.seconds_elapsed = 0
        self.is_flashing = False # 깜빡임 상태 확인
        self.flash_state = False

        self.setup_ui()
        self.tick()

    def setup_ui(self):
        # 1. 상단 현재 시간
        self.clock_label = tk.Label(self.root, text="", font=(self.font_family, 30), 
                                    fg="gray", bg="black")
        self.clock_label.pack(pady=(40, 0))

        # 2. 중앙 메인 디스플레이
        self.display_label = tk.Label(self.root, text="00:00:00", 
                                      font=(self.font_family, 120, "bold"), 
                                      fg="white", bg="black")
        self.display_label.pack(expand=True, fill="both")

        # 3. 시간 조절 버튼 영역
        self.adjust_frame = tk.Frame(self.root, bg="black")
        self.adjust_frame.pack(pady=20)
        
        adjust_buttons = [("+1분", 1), ("+5분", 5), ("+10분", 10), ("+30분", 30)]
        for text, mins in adjust_buttons:
            btn = tk.Button(self.adjust_frame, text=text, font=(self.font_family, 18, "bold"),
                            bg="#333333", fg="#FFD700", width=6, height=2,
                            command=lambda m=mins: self.add_minutes(m))
            btn.pack(side="left", padx=10)

        # 4. 메인 제어 버튼 영역
        control_frame = tk.Frame(self.root, bg="black")
        control_frame.pack(side="bottom", pady=60)

        self.start_stop_btn = tk.Button(control_frame, text="카운트 다운", 
                                        font=(self.font_family, 20, "bold"),
                                        bg="#00D166", fg="white", width=12, height=2,
                                        command=self.toggle_timer)
        self.start_stop_btn.pack(side="left", padx=20)

        tk.Button(control_frame, text="카운트 업", font=(self.font_family, 20, "bold"),
                  bg="#1E90FF", fg="white", width=10, height=2,
                  command=self.start_countup).pack(side="left", padx=20)

        tk.Button(control_frame, text="리셋", font=(self.font_family, 20, "bold"),
                  bg="#FF4B2B", fg="white", width=8, height=2,
                  command=self.reset).pack(side="left", padx=20)

    def add_minutes(self, mins):
        if not self.running:
            self.stop_alarm() # 설정 중엔 알람 정지
            self.mode = "COUNTDOWN"
            self.seconds_elapsed += mins * 60
            self.display_label.config(text=self.format_time(self.seconds_elapsed), fg="#FFD700")

    def toggle_timer(self):
        if self.seconds_elapsed > 0 or self.mode == "COUNTUP":
            self.stop_alarm()
            self.running = not self.running
            self.start_stop_btn.config(text="정지" if self.running else "재개",
                                       bg="#FFA500" if self.running else "#00D166")

    def start_countup(self):
        self.reset()
        self.mode = "COUNTUP"
        self.running = True
        self.start_stop_btn.config(text="정지", bg="#FFA500")

    def tick(self):
        now = datetime.now()
        self.clock_label.config(text=now.strftime("%H:%M:%S"))

        if self.running:
            if self.mode == "COUNTUP":
                self.seconds_elapsed += 1
                self.display_label.config(fg="#00D166")
            elif self.mode == "COUNTDOWN":
                if self.seconds_elapsed > 0:
                    self.seconds_elapsed -= 1
                    self.display_label.config(fg="#FFD700")
                else:
                    self.trigger_alarm() # 0초 도달 시 알람 발생
            
            self.display_label.config(text=self.format_time(self.seconds_elapsed))

        self.root.after(1000, self.tick)

    def trigger_alarm(self):
        """0초 도달 시 시각/청각 알람 실행"""
        self.running = False
        self.is_flashing = True
        self.start_stop_btn.config(text="카운트 다운", bg="#00D166")
        self.flash_ui()
        self.play_beep()

    def flash_ui(self):
        """화면을 빨간색/검은색으로 깜빡이게 함"""
        if self.is_flashing:
            self.flash_state = not self.flash_state
            color = "#FF4B2B" if self.flash_state else "black"
            self.display_label.config(text="TIME UP!", fg=color)
            self.root.after(500, self.flash_ui)

    def play_beep(self):
        """알람 소리 재생 (삐- 삐-)"""
        if self.is_flashing:
            # 주파수를 이용해 비프음을 만들거나 사전에 준비된 beep.wav 재생
            # 여기서는 간단히 0.5초마다 소리를 냅니다.
            # 라즈베리 파이에 beep.wav 파일이 있다면 아래 주석 해제
            pygame.mixer.Sound("beep.wav").play()
            print("\a") # 터미널 비프음 (스피커 설정에 따라 소리 안 날 수 있음)
            self.root.after(1000, self.play_beep)

    def stop_alarm(self):
        """알람 및 깜빡임 중지"""
        self.is_flashing = False
        self.display_label.config(fg="white")

    def format_time(self, secs):
        m, s = divmod(secs, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def reset(self):
        self.stop_alarm()
        self.running = False
        self.mode = "CLOCK"
        self.seconds_elapsed = 0
        self.display_label.config(text="00:00:00", fg="white")
        self.start_stop_btn.config(text="카운트 다운", bg="#00D166")

if __name__ == "__main__":
    root = tk.Tk()
    app = TouchMirrorTimer(root)
    root.mainloop()
