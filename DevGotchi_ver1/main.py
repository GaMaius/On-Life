# main.py
import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from config import Config
from data_manager import DataManager
from vision_engine import VisionEngine # 이전 코드 사용
from brain import BrainHandler
from game_manager import GameManager

class ModernMirror(QMainWindow):
    def __init__(self):
        super().__init__()
        # 모듈 초기화
        self.dm = DataManager()
        self.vision = VisionEngine()
        self.brain = BrainHandler()
        self.game = GameManager()
        self.tasks = [] # 할 일 목록
        
        self.init_ui()
        self.init_video()
        self.init_timers()
        self.dm.log_interaction("System", "Boot_Complete")

    def init_ui(self):
        self.setWindowTitle("Dev-Gotchi: Desk Edition")
        self.setGeometry(0, 0, 1024, 600)
        # 배경색 설정
        self.setStyleSheet(f"background-color: {Config.COLOR_BG}; font-family: '{Config.FONT_FAMILY}';")

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # === [Left Column] Character & Status ===
        left_panel = QFrame()
        left_panel.setStyleSheet(f"background-color: {Config.COLOR_PANEL}; border-radius: 20px;")
        left_layout = QVBoxLayout(left_panel)

        # 1. Character Image (Chick)
        self.char_img = QLabel()
        self.char_img.setAlignment(Qt.AlignCenter)
        try:
            pixmap = QPixmap(Config.IMAGE_PATH) # 병아리 사진 로드
            if not pixmap.isNull():
                self.char_img.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.char_img.setText("NO IMAGE")
        except:
            self.char_img.setText("Character\nImage")
        self.char_img.setStyleSheet("border: 2px solid #333; border-radius: 10px;")
        left_layout.addWidget(self.char_img)

        # 2. HP/XP Bars
        status_form = QFormLayout()
        
        self.hp_bar = QProgressBar()
        self.hp_bar.setRange(0, Config.MAX_HP)
        self.hp_bar.setValue(100)
        self.hp_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {Config.COLOR_HP}; }}")
        
        self.xp_bar = QProgressBar()
        self.xp_bar.setRange(0, 100) # Lv1 기준
        self.xp_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {Config.COLOR_XP}; }}")
        
        self.lbl_level = QLabel("Lv.1 🐣")
        self.lbl_level.setStyleSheet(f"color: {Config.COLOR_TEXT_MAIN}; font-size: 18px; font-weight: bold;")

        left_layout.addWidget(self.lbl_level)
        left_layout.addWidget(QLabel("체력 (HP)", styleSheet="color:white;"))
        left_layout.addWidget(self.hp_bar)
        left_layout.addWidget(QLabel("성장 (XP)", styleSheet="color:white;"))
        left_layout.addWidget(self.xp_bar)
        
        left_layout.addStretch(1)

        # === [Center Column] Camera & Interaction ===
        center_panel = QVBoxLayout()
        
        # 3. Camera Feed (Natural Color)
        self.video_label = QLabel()
        self.video_label.setFixedSize(480, 360)
        self.video_label.setStyleSheet("background-color: #000; border-radius: 15px; border: 2px solid #333;")
        center_panel.addWidget(self.video_label, alignment=Qt.AlignCenter)

        # 4. Chat Area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(f"background-color: {Config.COLOR_PANEL}; color: white; border-radius: 10px; padding: 10px;")
        self.chat_display.setFixedHeight(100)
        center_panel.addWidget(self.chat_display)

        # 5. Input
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("AI에게 말을 걸어보세요 (예: 오후 2시 회의 등록해줘)")
        self.input_field.setStyleSheet(f"background-color: #333; color: white; padding: 10px; border-radius: 10px;")
        self.input_field.returnPressed.connect(self.send_message)
        center_panel.addWidget(self.input_field)

        # === [Right Column] Task & Quests ===
        right_panel = QFrame()
        right_panel.setStyleSheet(f"background-color: {Config.COLOR_PANEL}; border-radius: 20px;")
        right_layout = QVBoxLayout(right_panel)

        right_layout.addWidget(QLabel("📅 오늘의 업무 (Tasks)", styleSheet="font-size: 16px; font-weight:bold; color:white;"))
        self.task_list = QListWidget()
        self.task_list.setStyleSheet("background-color: transparent; color: white; border: none; font-size: 14px;")
        right_layout.addWidget(self.task_list)

        right_layout.addWidget(QLabel("⚔️ 진행중인 퀘스트", styleSheet="font-size: 16px; font-weight:bold; color:white; margin-top: 20px;"))
        self.quest_list = QListWidget()
        self.quest_list.setStyleSheet("background-color: transparent; color: #FFD93D; border: none;")
        right_layout.addWidget(self.quest_list)
        
        # 퀘스트 추가 버튼들
        btn_q1 = QPushButton("🧘 스트레칭 하기")
        btn_q1.clicked.connect(lambda: self.start_quest("stretch"))
        btn_q1.setStyleSheet("background-color: #333; color: white; padding: 5px;")
        right_layout.addWidget(btn_q1)

        btn_q2 = QPushButton("🔥 25분 집중")
        btn_q2.clicked.connect(lambda: self.start_quest("focus_25m"))
        btn_q2.setStyleSheet("background-color: #333; color: white; padding: 5px;")
        right_layout.addWidget(btn_q2)

        # Layout Assembly
        main_layout.addWidget(left_panel, 2)
        main_layout.addLayout(center_panel, 5)
        main_layout.addWidget(right_panel, 3)

    def init_video(self):
        self.cap = cv2.VideoCapture(0)
        self.video_timer = QTimer()
        self.video_timer.timeout.connect(self.update_video)
        self.video_timer.start(30)

    def init_timers(self):
        self.game_timer = QTimer()
        self.game_timer.timeout.connect(self.update_game)
        self.game_timer.start(1000) # 1초마다 게임 상태 업데이트

    def update_video(self):
        ret, frame = self.cap.read()
        if not ret: return

        # Vision Analysis
        posture_score, is_drowsy, is_smiling, _ = self.vision.analyze_frame(frame)
        self.current_posture = posture_score
        self.current_drowsy = is_drowsy
        self.current_smiling = is_smiling

        # Draw Detection Boxes (Simple)
        if is_drowsy:
            cv2.putText(frame, "WAKE UP!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

        # Convert to Qt Image (No Blue Tint - Natural Color)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img).scaled(480, 360, Qt.KeepAspectRatio))

    def update_game(self):
        # 1. Update Logic
        is_bad = getattr(self, 'current_posture', 0) > Config.POSTURE_THRESHOLD
        is_sleep = getattr(self, 'current_drowsy', False)
        
        self.game.update(is_bad, is_sleep, True)
        
        # 2. Update UI
        self.hp_bar.setValue(int(self.game.hp))
        self.xp_bar.setValue(int(self.game.xp))
        self.lbl_level.setText(f"Lv.{self.game.level} 🐣")
        
        # 3. Quest List Update
        self.quest_list.clear()
        for q in self.game.quests:
            status = "✅" if q.is_completed else f"⏳ {int(q.progress)}s"
            self.quest_list.addItem(f"{q.name} - {status}")

        # 4. Warning Alert
        if self.game.hp < 30:
            self.setStyleSheet(f"background-color: #300; font-family: '{Config.FONT_FAMILY}';") # 붉은 배경 경고
        else:
            self.setStyleSheet(f"background-color: {Config.COLOR_BG}; font-family: '{Config.FONT_FAMILY}';")

    def start_quest(self, type):
        self.game.add_quest(type)
        self.chat_display.append(f"<b>SYSTEM:</b> 퀘스트가 시작되었습니다!")

    def send_message(self):
        text = self.input_field.text()
        if not text: return
        
        self.chat_display.append(f"<b>나:</b> {text}")
        self.input_field.clear()
        
        # AI 호출
        self.brain.chat(text, self.game.level, self.on_ai_response)

    def on_ai_response(self, text, task_info):
        self.chat_display.append(f"<b>비서:</b> {text}")
        
        # 일정 등록 로직
        if task_info:
            task_str = f"[{task_info.get('time', '오늘')}] {task_info.get('content')}"
            self.tasks.append(task_str)
            self.task_list.addItem(task_str)
            self.dm.log_interaction("Task_Added", task_str)

    def closeEvent(self, event):
        self.cap.release()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ModernMirror()
    win.show()
    sys.exit(app.exec_())