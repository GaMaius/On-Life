import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QStackedWidget, 
                             QListWidget, QFrame, QGridLayout, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon

# 그래프 시각화 (Matplotlib)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

# 모듈 연결
from data_manager import DataManager
from brain import BrainAgent

# ==========================================
# [설정] 여기에 OpenAI API 키를 입력하세요
API_KEY = "sk-proj-..." 
# ==========================================

class SmartMirror(QMainWindow):
    def __init__(self):
        super().__init__()
        # 1. 데이터 및 AI 엔진 초기화
        self.db = DataManager()
        self.ai = BrainAgent(API_KEY, self.db)
        
        # 2. 기본 UI 설정 (10.1인치 해상도, 다크모드)
        self.setWindowTitle("Smart Mirror - Data Driven Platform")
        self.setGeometry(0, 0, 1024, 600)
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QLabel { color: white; }
            QPushButton { 
                background-color: #1F1B24; 
                color: white; 
                border-radius: 10px; 
                border: 1px solid #333;
                font-size: 18px;
            }
            QPushButton:pressed { background-color: #BB86FC; color: black; }
        """)

        # 3. 중앙 위젯 설정
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 4. 상단 상태바 (시간/날씨)
        self.init_statusbar()

        # 5. 화면 스택 (페이지 전환용)
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        # 6. 각 페이지 생성
        self.page_home = self.create_home_page()
        self.page_schedule = self.create_schedule_page()
        self.page_ai = self.create_ai_page()
        self.page_insight = self.create_insight_page() # 핵심: 인포그래픽

        self.stack.addWidget(self.page_home)      # Index 0
        self.stack.addWidget(self.page_schedule)  # Index 1
        self.stack.addWidget(self.page_ai)        # Index 2
        self.stack.addWidget(self.page_insight)   # Index 3

        # 초기 실행 로그
        self.db.log_interaction("System", "Boot_Complete", "Home")

    def init_statusbar(self):
        bar = QHBoxLayout()
        
        self.date_label = QLabel("2026.02.03 (화)")
        self.date_label.setFont(QFont("Arial", 14))
        self.date_label.setStyleSheet("color: #B0BEC5;")
        
        self.time_label = QLabel("00:00")
        self.time_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.time_label.setStyleSheet("color: #BB86FC;")

        bar.addWidget(self.date_label)
        bar.addStretch(1)
        bar.addWidget(self.time_label)
        
        self.main_layout.addLayout(bar)
        
        # 1초마다 시간 갱신
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

    def update_time(self):
        from datetime import datetime
        now = datetime.now()
        self.time_label.setText(now.strftime("%H:%M"))

    # --- 페이지 전환 로직 (데이터 수집 포함) ---
    def go_to_page(self, index, page_name):
        self.stack.setCurrentIndex(index)
        # [Type A] 페이지 전환 로그 수집
        self.db.log_interaction("Navigation", "Page_Switch", page_name)
        # [Type B] 전환 시점의 상황(Context) 수집
        self.db.log_context({"screen_mode": "Active", "time": self.time_label.text()})
        
        # 인사이트 페이지면 그래프 갱신
        if index == 3:
            self.refresh_infographic()

    # --- [UI] 공통 컴포넌트 ---
    def create_back_btn(self):
        btn = QPushButton("⬅ Home")
        btn.setFixedSize(120, 50)
        btn.setStyleSheet("background-color: transparent; color: #03DAC6; font-weight: bold; border: none;")
        btn.clicked.connect(lambda: self.go_to_page(0, "Home"))
        return btn

    # --- [Page 0] 홈 화면 ---
    def create_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # 환영 메시지
        welcome = QLabel("안녕하세요, 가람님.\n데이터 기반 스마트 라이프를 시작하세요.")
        welcome.setAlignment(Qt.AlignCenter)
        welcome.setFont(QFont("Arial", 20))
        layout.addWidget(welcome)
        layout.addSpacing(30)

        # 메뉴 버튼 그리드
        grid = QGridLayout()
        
        btn_schedule = QPushButton("📅 일정 확인")
        btn_schedule.setFixedSize(250, 150)
        btn_schedule.clicked.connect(lambda: self.go_to_page(1, "Schedule"))
        
        btn_ai = QPushButton("🤖 AI 비서\n(Dev-Gotchi)")
        btn_ai.setFixedSize(250, 150)
        btn_ai.clicked.connect(lambda: self.go_to_page(2, "AI_Companion"))
        
        btn_insight = QPushButton("📊 데이터 인사이트\n(Infographic)")
        btn_insight.setFixedSize(510, 100)
        btn_insight.setStyleSheet("background-color: #2D2D2D; color: #FF0266; font-weight: bold;")
        btn_insight.clicked.connect(lambda: self.go_to_page(3, "Insight"))

        grid.addWidget(btn_schedule, 0, 0)
        grid.addWidget(btn_ai, 0, 1)
        grid.addWidget(btn_insight, 1, 0, 1, 2, Qt.AlignCenter)
        
        layout.addLayout(grid)
        layout.addStretch(1)
        return page

    # --- [Page 1] 일정 화면 ---
    def create_schedule_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.create_back_btn())
        
        title = QLabel("오늘의 주요 일정")
        title.setFont(QFont("Arial", 22, QFont.Bold))
        layout.addWidget(title)

        list_widget = QListWidget()
        list_widget.setStyleSheet("font-size: 20px; background-color: #1E1E1E; padding: 10px; border-radius: 10px;")
        
        items = [
            "09:00 - 메이커톤 오프닝 세션",
            "12:00 - 팀 점심 식사",
            "14:00 - 멘토링 및 중간 점검",
            "18:00 - 1일차 개발 마감",
            "20:00 - 데이터 파이프라인 검증"
        ]
        list_widget.addItems(items)
        layout.addWidget(list_widget)
        return page

    # --- [Page 2] AI 비서 화면 ---
    def create_ai_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.create_back_btn())

        self.ai_status = QLabel("Dev-Gotchi: 무엇을 도와드릴까요?")
        self.ai_status.setWordWrap(True)
        self.ai_status.setStyleSheet("font-size: 20px; color: #BB86FC; padding: 20px; border: 1px solid #333; border-radius: 15px;")
        layout.addWidget(self.ai_status)

        # 테스트용 버튼 (실제로는 STT/TTS)
        btn_ask = QPushButton("🎤 '내일 날씨 어때?' 라고 물어보기")
        btn_ask.setFixedHeight(60)
        btn_ask.clicked.connect(self.ask_ai_demo)
        layout.addWidget(btn_ask)
        
        layout.addStretch(1)
        return page

    def ask_ai_demo(self):
        # UI 업데이트
        self.ai_status.setText("Dev-Gotchi: 생각하는 중...")
        QApplication.processEvents() # UI 갱신 강제

        # AI 호출 (로그 자동 수집됨)
        response = self.ai.chat("내일 부산 날씨 알려줘")
        self.ai_status.setText(f"Dev-Gotchi: {response}")

    # --- [Page 3] 데이터 인사이트 (인포그래픽) ---
    def create_insight_page(self):
        page = QWidget()
        self.insight_layout = QVBoxLayout(page)
        
        header = QHBoxLayout()
        header.addWidget(self.create_back_btn())
        title = QLabel("Data-Driven Insight Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #03DAC6;")
        header.addWidget(title)
        header.addStretch(1)
        self.insight_layout.addLayout(header)

        # Matplotlib 캔버스 (그래프 영역)
        self.figure = plt.figure(facecolor='#121212')
        self.canvas = FigureCanvas(self.figure)
        self.insight_layout.addWidget(self.canvas)
        
        info = QLabel("* 이 데이터는 '가이드라인 Section 3'에 따라 실시간으로 수집된 로그를 시각화한 것입니다.")
        info.setStyleSheet("color: gray; font-size: 12px;")
        self.insight_layout.addWidget(info)

        return page

    def refresh_infographic(self):
        """저장된 로그를 분석해 그래프를 그립니다."""
        # 1. 데이터 가져오기
        page_counts, latencies, _ = self.db.get_analysis()
        
        self.figure.clear()
        
        # 2. Subplot 1: 기능별 사용 빈도 (Bar Chart)
        ax1 = self.figure.add_subplot(121) # 1행 2열 중 1번
        if page_counts:
            pages = list(page_counts.keys())
            counts = list(page_counts.values())
            colors = ['#03DAC6', '#BB86FC', '#CF6679', '#FF0266']
            ax1.bar(pages, counts, color=colors[:len(pages)])
        
        ax1.set_title("Feature Usage (Interaction)", color='white', fontsize=12)
        ax1.tick_params(colors='white', rotation=45)
        ax1.set_facecolor('#1E1E1E')
        
        # 3. Subplot 2: 시스템 응답 지연 (Line Chart)
        ax2 = self.figure.add_subplot(122) # 1행 2열 중 2번
        if latencies:
            ax2.plot(latencies, marker='o', color='#03DAC6', linestyle='-')
            ax2.text(len(latencies)-1, latencies[-1], f"{latencies[-1]}ms", color='white')
        
        ax2.set_title("System Latency (Telemetry)", color='white', fontsize=12)
        ax2.set_ylabel("ms", color='white')
        ax2.tick_params(colors='white')
        ax2.set_facecolor('#1E1E1E')
        ax2.grid(True, linestyle='--', alpha=0.3)

        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SmartMirror()
    window.show()
    sys.exit(app.exec_())