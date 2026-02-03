import tkinter as tk
from datetime import datetime, timedelta

class TouchMirrorTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("Touch Smart Mirror Timer")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg='black')
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self.font_family = "Noto Sans KR"
        
        # 데이터 초기화
        self.mode = "CLOCK" 
        self.running = False
        self.seconds_elapsed = 0
        self.alarm_time = None

        self.setup_ui()
        self.tick()

    def setup_ui(self):
        # 1. 상단 현재 시간
        self.clock_label = tk.Label(self.root, text="", font=(self.font_family, 30), 
                                    fg="gray", bg="black")
        self.clock_label.pack(pady=(40, 0))

        # 2. 중앙 메인 디스플레이 (시간 표시)
        self.display_label = tk.Label(self.root, text="00:00:00", 
                                      font=(self.font_family, 120, "bold"), 
                                      fg="white", bg="black")
        self.display_label.pack(expand=True, fill="both")

        # 3. 시간 조절 버튼 영역 (터치용 큼직한 버튼)
        self.adjust_frame = tk.Frame(self.root, bg="black")
        self.adjust_frame.pack(pady=20)
        
        # 타이머 설정을 위한 + 버튼들
        adjust_buttons = [
            ("+1분", 1), ("+5분", 5), ("+10분", 10), ("+30분", 30)
        ]
        for text, mins in adjust_buttons:
            btn = tk.Button(self.adjust_frame, text=text, font=(self.font_family, 18, "bold"),
                            bg="#333333", fg="#FFD700", width=6, height=2,
                            command=lambda m=mins: self.add_minutes(m))
            btn.pack(side="left", padx=10)

        # 4. 메인 제어 버튼 영역 (시작, 정지, 리셋 등)
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
        """터치로 시간을 추가하는 함수"""
        if not self.running:
            self.mode = "COUNTDOWN"
            self.seconds_elapsed += mins * 60
            self.display_label.config(text=self.format_time(self.seconds_elapsed), fg="#FFD700")

    def toggle_timer(self):
        """시작/정지 토글"""
        if self.seconds_elapsed > 0 or self.mode == "COUNTUP":
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
                    self.running = False
                    self.display_label.config(text="TIME UP!", fg="#FF4B2B")
                    self.start_stop_btn.config(text="타이머 시작", bg="#00D166")
            
            self.display_label.config(text=self.format_time(self.seconds_elapsed))

        self.root.after(1000, self.tick)

    def format_time(self, secs):
        m, s = divmod(secs, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def reset(self):
        self.running = False
        self.mode = "CLOCK"
        self.seconds_elapsed = 0
        self.display_label.config(text="00:00:00", fg="white")
        self.start_stop_btn.config(text="타이머 시작", bg="#00D166")

if __name__ == "__main__":
    root = tk.Tk()
    app = TouchMirrorTimer(root)
    root.mainloop()
