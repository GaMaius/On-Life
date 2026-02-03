import sys
import cv2
import numpy as np
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QProgressBar, QVBoxLayout, QWidget, QLineEdit
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

from vision import VisionSystem
from brain import BrainAgent

# API 키 설정 (환경변수로 빼는 것 권장 [cite: 5])
MINIMAX_API_KEY = "여기에_MINIMAX_API_키_입력"

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    status_signal = pyqtSignal(dict)

    def run(self):
        cap = cv2.VideoCapture(0) # 웹캠 연결
        vision = VisionSystem()
        while True:
            ret, frame = cap.read()
            if ret:
                status, processed_frame = vision.process_frame(frame)
                self.change_pixmap_signal.emit(processed_frame)
                self.status_signal.emit(status)
                time.sleep(0.03) # 약 30FPS

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dev-Gotchi AI Mirror")
        self.setGeometry(100, 100, 1024, 600) # 10.1인치 해상도 맞춤
        
        self.brain = BrainAgent(MINIMAX_API_KEY)
        self.hp = 100
        self.current_status = {}

        self.initUI()
        self.start_video()

    def initUI(self):
        # 레이아웃 구성
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # 1. 카메라 화면 (배경)
        self.image_label = QLabel(self)
        self.layout.addWidget(self.image_label)

        # 2. HP 바 (게이미피케이션)
        self.hp_bar = QProgressBar(self)
        self.hp_bar.setMaximum(100)
        self.hp_bar.setValue(100)
        self.hp_bar.setStyleSheet("QProgressBar::chunk { background-color: #00FF00; }")
        self.layout.addWidget(self.hp_bar)

        # 3. AI 대화창
        self.chat_label = QLabel("Dev-Gotchi: 오늘도 화이팅!", self)
        self.chat_label.setStyleSheet("font-size: 20px; font-weight: bold; color: blue;")
        self.layout.addWidget(self.chat_label)

        # 4. 사용자 입력창
        self.input_box = QLineEdit(self)
        self.input_box.setPlaceholderText("비서에게 말 걸기...")
        self.input_box.returnPressed.connect(self.handle_input)
        self.layout.addWidget(self.input_box)

    def start_video(self):
        self.thread = VideoThread()
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.status_signal.connect(self.update_status)
        self.thread.start()

    def update_image(self, cv_img):
        qt_img = self.convert_cv_qt(cv_img)
        self.image_label.setPixmap(qt_img)

    def convert_cv_qt(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(convert_to_Qt_format).scaled(800, 480, Qt.KeepAspectRatio)

    def update_status(self, status):
        self.current_status = status
        
        # HP 감소 로직
        decay = status.get('hp_decay', 0)
        if decay > 0:
            self.hp = max(0, self.hp - decay)
            self.hp_bar.setValue(self.hp)
            
            # HP 바 색상 변경 (위험하면 빨강)
            if self.hp < 30:
                self.hp_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")
                # HP가 너무 낮으면 AI가 말을 걸도록 트리거 (여기서 빈도 조절 필요)
                # self.trigger_ai_warning() 

    def handle_input(self):
        user_text = self.input_box.text()
        self.input_box.clear()
        
        # UI에 내 말 표시
        self.chat_label.setText(f"나: {user_text}")
        
        # Brain 호출 (status 함께 전달)
        status_snapshot = self.current_status.copy()
        status_snapshot['hp'] = self.hp
        
        # 비동기 처리가 좋지만 예제 단순화를 위해 직접 호출
        ai_response = self.brain.chat(user_text, status_snapshot)
        
        # AI 응답 처리
        self.chat_label.setText(f"Dev-Gotchi: {ai_response.get('response', '...')}")
        
        # 액션 처리 (타이머 등)
        if ai_response.get('action') == 'timer_25min':
            print("타이머 시작 로직 실행")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())