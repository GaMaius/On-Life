import tkinter as tk
from datetime import datetime
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# 1. Firebase 초기화
cred = credentials.Certificate("serviceAccountKey.json") # 다운로드한 키 파일 경로
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://status-ef996-default-rtdb.firebaseio.com/'
})

class SmartMirrorStatus:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Mirror Status Board")
        self.root.attributes("-fullscreen", True)  # 전체화면
        self.root.configure(bg='black')
        self.root.bind("<Escape>", lambda e: self.root.destroy()) # Esc 누르면 종료

        # 상태별 설정 (메시지, 컬러)
        self.status_data = {
            "업무 중": {"text": "업무 중", "color": "#00D166"},
            "회의 중": {"text": "회의 중", "color": "#FF4B2B"},
            "잠시 자리 비움": {"text": "잠시 자리 비움", "color": "#FFD700"},
            "퇴근": {"text": "퇴근", "color": "#1E90FF"}
        }

        self.setup_ui()
        self.update_clock()
        self.listen_to_db()

    def setup_ui(self):
        # 폰트 설정 변수 (관리가 편하게 따로 뺌)
        font_family = "Noto Sans KR"
        
        # 상단 시계 영역 (크기 40 -> 45)
        self.time_label = tk.Label(self.root, text="", 
                                font=(font_family, 45), 
                                fg="white", bg="black")
        self.time_label.pack(pady=(100, 10)) 

        # 중앙 상태 표시 영역 (크기 62 -> 80으로 대폭 확대)
        self.status_label = tk.Label(self.root, text="상태를 선택하세요", 
                                    font=(font_family, 80, "bold"), 
                                    fg="white", bg="black",
                                    anchor="center")
        # 글자가 커진 만큼 내부 수직 여백(ipady)을 더 넉넉히 줍니다.
        self.status_label.pack(expand=True, fill="both", ipady=50) 

        # 하단 버튼 컨테이너
        btn_frame = tk.Frame(self.root, bg="black")
        btn_frame.pack(side="bottom", pady=(0, 80))

        for key, value in self.status_data.items():
            # 버튼 폰트도 Noto Sans로 통일 (크기 14 -> 16)
            btn = tk.Button(btn_frame, text=key, width=12, height=2,
                            font=(font_family, 16, "bold"),
                            bg="#222222", fg="white",
                            activebackground=value["color"],
                            command=lambda k=key: self.change_status(k))
            btn.pack(side="left", padx=20)

    def update_clock(self):
        now = datetime.now().strftime("%H:%M:%S")
        self.time_label.config(text=now)
        self.root.after(1000, self.update_clock)

    def change_status(self, status_key):
        # Firebase에 데이터 업로드
        ref = db.reference('current_status')
        ref.set(status_key)
        # 로컬 UI 즉시 업데이트
        self.update_ui(status_key)

    def update_ui(self, status_key):
        data = self.status_data.get(status_key)
        if data:
            self.status_label.config(text=data["text"], fg=data["color"])

    def listen_to_db(self):
        # DB 값이 외부(모바일 등)에서 바뀌었을 때도 감지하여 UI 업데이트
        def callback(event):
            if event.data:
                self.update_ui(event.data)
        
        db.reference('current_status').listen(callback)

if __name__ == "__main__":
    root = tk.Tk()
    app = SmartMirrorStatus(root)
    root.mainloop()
