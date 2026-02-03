import tkinter as tk
from datetime import datetime
import threading
import firebase_admin
from firebase_admin import credentials, db

# 1. Firebase 초기화
# serviceAccountKey.json 파일이 이 스크립트와 같은 폴더에 있어야 합니다.
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://status-ef996-default-rtdb.firebaseio.com/'
    })
except Exception as e:
    print(f"Firebase 초기화 실패: {e}")

class SmartMirrorStatus:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Mirror Status Board")
        self.root.attributes("-fullscreen", True)  # 전체화면 설정
        self.root.configure(bg='black')  # 거울 효과를 위한 블랙 배경
        self.root.bind("<Escape>", lambda e: self.root.destroy()) # Esc 키로 종료

        # 라즈베리 파이에 설치된 폰트에 따라 순차적으로 시도
        self.font_family = "Noto Sans KR" 
        
        # 상태별 설정 (메시지, 컬러 코드 반영)
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
        # 상단 시계 영역 (가독성을 위해 크게 배치)
        self.time_label = tk.Label(self.root, text="", 
                                font=(self.font_family, 50), 
                                fg="white", bg="black")
        self.time_label.pack(pady=(100, 20)) 

        # 중앙 상태 표시 영역 (터치스크린 최적화 크기)
        self.status_label = tk.Label(self.root, text="상태를 선택하세요", 
                                    font=(self.font_family, 85, "bold"), 
                                    fg="white", bg="black",
                                    anchor="center")
        self.status_label.pack(expand=True, fill="both", ipady=60) 

        # 하단 버튼 컨테이너 (터치하기 편하도록 크게 구성)
        btn_frame = tk.Frame(self.root, bg="black")
        btn_frame.pack(side="bottom", pady=(0, 100))

        for key, value in self.status_data.items():
            # 버튼 디자인: 손가락으로 누르기 좋은 width와 height
            btn = tk.Button(btn_frame, text=key, width=12, height=2,
                            font=(self.font_family, 18, "bold"),
                            bg="#222222", fg="white",
                            activebackground=value["color"],
                            relief="flat",
                            command=lambda k=key: self.change_status(k))
            btn.pack(side="left", padx=20)

    def update_clock(self):
        """1초마다 시계를 업데이트합니다."""
        now = datetime.now().strftime("%H:%M:%S")
        self.time_label.config(text=now)
        self.root.after(1000, self.update_clock)

    def change_status(self, status_key):
        """버튼 클릭 시 호출되는 함수 (멀티스레딩 적용)"""
        # 1. 로컬 UI를 즉시 업데이트하여 지연 현상 제거
        self.update_ui(status_key)
        
        # 2. Firebase 업로드는 별도의 스레드에서 수행 (Blocking 방지)
        threading.Thread(target=self.upload_to_firebase, args=(status_key,), daemon=True).start()

    def upload_to_firebase(self, status_key):
        """네트워크 통신을 담당하는 함수 (배경 실행)"""
        try:
            ref = db.reference('current_status')
            ref.set(status_key)
        except Exception as e:
            print(f"Firebase 업로드 오류: {e}")

    def update_ui(self, status_key):
        """화면의 텍스트와 색상을 변경합니다."""
        data = self.status_data.get(status_key)
        if data:
            self.status_label.config(text=data["text"], fg=data["color"])

    def listen_to_db(self):
        """외부(스마트폰 등)에서 변경된 상태를 감지합니다."""
        def callback(event):
            if event.data:
                # 메인 스레드에서 UI를 업데이트하도록 조치
                self.root.after(0, self.update_ui, event.data)
        
        db.reference('current_status').listen(callback)

if __name__ == "__main__":
    root = tk.Tk()
    app = SmartMirrorStatus(root)
    root.mainloop()
