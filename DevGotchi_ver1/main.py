import sys
import cv2
import time
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from config import Config
from data_manager import DataManager
from vision_engine import VisionEngine
from brain import BrainHandler
from game_manager import GameManager

class ScheduleWindow(QDialog):
    """Separate window for displaying daily schedule"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📅 오늘의 일정")
        self.resize(600, 400)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Config.COLOR_BG};
            }}
            QLabel {{
                font-family: '{Config.FONT_FAMILY}';
                color: {Config.COLOR_TEXT_MAIN};
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4CC2FF, stop:1 #0099FF);
                color: white;
                border-radius: 20px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #66CEFF, stop:1 #33Aaff);
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Title
        title = QLabel("📅 오늘의 할 일")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        
        # Table
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(3)
        self.task_table.setHorizontalHeaderLabels(["시간", "장소", "내용"])
        self.task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setShowGrid(False)
        self.task_table.setStyleSheet(f"""
            QTableWidget {{ 
                background-color: rgba(0,0,0,0.2); 
                border: none; 
                border-radius: 12px;
                color: {Config.COLOR_TEXT_MAIN}; 
                gridline-color: rgba(255,255,255,0.1);
            }}
            QHeaderView::section {{ 
                background-color: rgba(0,0,0,0.3); 
                color: {Config.COLOR_TEXT_SUB}; 
                border: none;
                padding: 8px;
                font-weight: bold;
            }}
            QTableWidget::item {{ 
                padding: 12px; 
                border-bottom: 1px solid rgba(255,255,255,0.05); 
            }}
        """)
        self.task_table.setFocusPolicy(Qt.NoFocus)
        self.task_table.setSelectionMode(QAbstractItemView.NoSelection)
        layout.addWidget(self.task_table)
        
        # Close button
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

class QuestWindow(QDialog):
    """Separate window for quest selection and tracking"""
    def __init__(self, parent=None, game_manager=None):
        super().__init__(parent)
        self.game = game_manager
        self.parent_window = parent
        self.setWindowTitle("⚔️ 퀘스트")
        self.resize(700, 600)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #1E1E2E;
            }}
            QLabel {{
                font-family: '{Config.FONT_FAMILY}';
                color: #CDD6F4;
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4CC2FF, stop:1 #0099FF);
                color: white;
                border-radius: 20px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #66CEFF, stop:1 #33Aaff);
            }}
            QFrame {{
                background-color: #2B2B40;
                border-radius: 16px;
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(12)
        
        # Title
        title = QLabel("⚔️ 퀘스트")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)
        
        # Create scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0,0,0,0.2);
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.2);
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,0.3);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Content widget inside scroll area
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(0, 0, 10, 0)  # Right margin for scrollbar
        layout.setSpacing(20)
        
        # Available Quests Section
        available_label = QLabel("🎯 선택 가능한 퀘스트 (1개 선택)")
        available_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(available_label)
        
        self.available_container = QWidget()
        self.available_layout = QVBoxLayout(self.available_container)
        self.available_layout.setSpacing(12)
        layout.addWidget(self.available_container)
        
        # Active Quest Section
        active_label = QLabel("✅ 현재 진행중인 퀘스트")
        active_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(active_label)
        
        self.active_container = QWidget()
        self.active_layout = QVBoxLayout(self.active_container)
        layout.addWidget(self.active_container)
        
        layout.addStretch()
        
        # Set content widget to scroll area
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # Close button (outside scroll area, always visible)
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.close)
        main_layout.addWidget(btn_close)
        
        # Initial update
        self.update_quests()
    
    def update_quests(self):
        """Update quest displays"""
        # Clear available quests
        while self.available_layout.count():
            item = self.available_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Clear active quest
        while self.active_layout.count():
            item = self.active_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Show available quest options
        if self.game and len(self.game.available_quests) > 0:
            for i, quest in enumerate(self.game.available_quests):
                quest_card = self.create_quest_option_card(quest, i)
                self.available_layout.addWidget(quest_card)
        else:
            no_quests = QLabel("현재 선택 가능한 퀘스트가 없습니다.")
            no_quests.setStyleSheet("color: #888; font-style: italic; padding: 20px;")
            self.available_layout.addWidget(no_quests)
        
        # Show active quest
        if self.game:
            active_quests = [q for q in self.game.quests if not q.is_completed]
            if len(active_quests) > 0:
                for quest in active_quests:
                    quest_card = self.create_active_quest_card(quest)
                    self.active_layout.addWidget(quest_card)
            else:
                no_active = QLabel("진행중인 퀘스트가 없습니다. 위에서 퀘스트를 선택하세요!")
                no_active.setStyleSheet("color: #888; font-style: italic; padding: 20px;")
                self.active_layout.addWidget(no_active)
    
    def create_quest_option_card(self, quest, index):
        """Create a quest option card with accept button"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #2B2B40;
                border: 2px solid rgba(255,255,255,0.1);
                border-radius: 16px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        
        # Quest name and difficulty
        header = QHBoxLayout()
        name_label = QLabel(f"⚔️ {quest.name}")
        name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFF;")
        header.addWidget(name_label)
        
        diff_color = {"Easy": "#4CAF50", "Normal": "#2196F3", "Hard": "#FF5722"}.get(quest.difficulty, "#888")
        diff_label = QLabel(quest.difficulty)
        diff_label.setStyleSheet(f"color: {diff_color}; font-weight: bold; font-size: 12px;")
        header.addWidget(diff_label)
        header.addStretch()
        
        reward_label = QLabel(f"💎 {quest.reward_xp} XP")
        reward_label.setStyleSheet("color: #FFD700; font-weight: bold;")
        header.addWidget(reward_label)
        
        layout.addLayout(header)
        
        # Description
        desc_label = QLabel(quest.description)
        desc_label.setStyleSheet("color: #CCC; font-size: 13px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Clear condition
        condition_label = QLabel(f"📋 클리어 조건: {quest.clear_condition}")
        condition_label.setStyleSheet("color: #AAA; font-size: 12px; font-style: italic;")
        condition_label.setWordWrap(True)
        layout.addWidget(condition_label)
        
        # Accept button
        btn_accept = QPushButton("수락하기")
        btn_accept.clicked.connect(lambda: self.accept_quest(index))
        layout.addWidget(btn_accept)
        
        return frame
    
    def create_active_quest_card(self, quest):
        """Create display card for active quest with progress"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #2B2B40;
                border: 2px solid #89B4FA;
                border-radius: 16px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        
        # Quest name
        name_label = QLabel(f"⚔️ {quest.name}")
        name_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        layout.addWidget(name_label)
        
        # Description
        desc_label = QLabel(quest.description)
        desc_label.setStyleSheet("color: #CCC; font-size: 13px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Clear condition
        condition_label = QLabel(f"📋 클리어 조건: {quest.clear_condition}")
        condition_label.setStyleSheet("color: #AAA; font-size: 12px; font-style: italic;")
        condition_label.setWordWrap(True)
        layout.addWidget(condition_label)
        
        # Progress bar
        progress_pct = int((quest.progress / quest.target_duration) * 100)
        progress_label = QLabel(f"진행도: {progress_pct}%")
        progress_label.setStyleSheet("color: #DDD; font-weight: bold; margin-top: 8px;")
        layout.addWidget(progress_label)
        
        pbar = QProgressBar()
        pbar.setFixedHeight(12)
        pbar.setRange(0, 100)
        pbar.setValue(progress_pct)
        pbar.setStyleSheet(f"""
            QProgressBar {{ 
                background-color: rgba(0,0,0,0.3); 
                border-radius: 6px; 
                text-align: center;
            }}
            QProgressBar::chunk {{ 
                background-color: {Config.COLOR_ACCENT}; 
                border-radius: 6px; 
            }}
        """)
        layout.addWidget(pbar)
        
        return frame
    
    def accept_quest(self, index):
        """Accept a quest from available options"""
        if self.game and self.game.accept_quest(index):
            self.update_quests()
            # Notify parent to refresh if needed
            if hasattr(self.parent_window, 'chat_display'):
                self.parent_window.chat_display.append(
                    f"<span style='color:#4CC2FF'><b>시스템:</b> 퀘스트 '{self.game.quests[0].name}'을(를) 수락했습니다!</span>"
                )

class ModernMirror(QMainWindow):
    def __init__(self):
        super().__init__()
        # Data & Core Systems
        self.dm = DataManager()
        self.vision = VisionEngine()
        self.brain = BrainHandler()
        self.game = GameManager()
        self.tasks = [] 
        
        # Separate Windows
        self.schedule_window = None
        self.quest_window = None
        
        # State Tracking
        self.last_input_time = time.time()
        self.alarm_active = False
        self.alarm_start_time = 0
        
        self.init_ui()
        self.init_video()
        self.init_timers()
        
        # Alarm Timer (Every 50 mins)
        self.work_timer = QTimer()
        self.work_timer.timeout.connect(self.trigger_rest_alarm)
        self.work_timer.start(50 * 60 * 1000) # 50 mins

        self.dm.log_interaction("System", "Boot_Complete")

    def init_ui(self):
        self.setWindowTitle("Dev-Gotchi: Logic Master")
        self.resize(1200, 700)
        
        # Modern Gradient Background & Font
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {Config.COLOR_BG};
            }}
            QLabel {{
                font-family: '{Config.FONT_FAMILY}';
                color: {Config.COLOR_TEXT_MAIN};
            }}
            /* Soft Panel Style */
            QFrame {{
                background-color: {Config.COLOR_PANEL};
                border-radius: 20px;
                border: 1px solid rgba(255,255,255,0.05); /* Subtle rim */
            }}
            QProgressBar {{
                border: none;
                background-color: rgba(0,0,0,0.2);
                border-radius: 8px;
                text-align: center;
                color: transparent;
            }}
            QLineEdit {{
                background-color: rgba(0,0,0,0.2); 
                color: {Config.COLOR_TEXT_MAIN}; 
                padding: 15px; 
                border-radius: 15px; /* Pill shape-ish */
                border: 1px solid rgba(255,255,255,0.08);
                font-size: 14px;
                selection-background-color: {Config.COLOR_ACCENT};
            }}
            QTextEdit {{
                background-color: rgba(0,0,0,0.2);
                color: {Config.COLOR_TEXT_MAIN};
                border-radius: 15px;
                border: 1px solid rgba(255,255,255,0.05);
                padding: 15px;
                font-size: 13px;
                line-height: 1.4;
            }}
            /* Neumorphic / Glassy Button */
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4CC2FF, stop:1 #0099FF);
                color: white;
                border-radius: 20px; /* Fully rounded pill */
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #66CEFF, stop:1 #33Aaff);
                margin-top: -2px; /* Slight lift */
            }}
            QPushButton:pressed {{
                background-color: #0077CC;
                margin-top: 2px;
            }}
            /* Scrollbar Style */
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,255,255,0.1);
                min-height: 30px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)

        # === [Left] Character & Status ===
        left_panel = QFrame()
        left_panel.setStyleSheet(f"background-color: {Config.COLOR_PANEL}; border-radius: 24px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)

        # Level Badge
        self.lbl_level = QLabel(f"Lv.{self.game.level}")
        self.lbl_level.setStyleSheet("font-size: 28px; font-weight: bold; color: " + Config.COLOR_XP)
        self.lbl_level.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.lbl_level)
        
        # Title
        self.lbl_title = QLabel("")
        self.lbl_title.setStyleSheet("font-size: 14px; color: " + Config.COLOR_TEXT_SUB)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.lbl_title)

        # Character Image
        self.char_img = QLabel()
        self.char_img.setMinimumSize(180, 180) # Responsive min size
        self.char_img.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Allow grow
        self.char_img.setAlignment(Qt.AlignCenter)
        self.update_character_image() 
        self.char_img.setStyleSheet("border: 4px solid rgba(255,255,255,0.1); border-radius: 20px;") 
        left_layout.addWidget(self.char_img, alignment=Qt.AlignCenter)

        # Status Bars
        left_layout.addSpacing(20)
        left_layout.addWidget(QLabel("체력 (HP)"))
        self.hp_bar = QProgressBar()
        self.hp_bar.setRange(0, Config.MAX_HP)
        self.hp_bar.setValue(int(Config.MAX_HP))
        self.hp_bar.setFixedHeight(14)
        self.hp_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: rgba(0,0,0,0.3); border-radius: 7px; }}
            QProgressBar::chunk {{ background-color: {Config.COLOR_HP}; border-radius: 7px; }}
        """)
        left_layout.addWidget(self.hp_bar)

        left_layout.addSpacing(10)
        left_layout.addWidget(QLabel("경험치 (XP)"))
        self.xp_bar = QProgressBar()
        self.xp_bar.setRange(0, 100)
        self.xp_bar.setFixedHeight(10)
        self.xp_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: rgba(0,0,0,0.3); border-radius: 5px; }}
            QProgressBar::chunk {{ background-color: {Config.COLOR_XP}; border-radius: 5px; }}
        """)
        left_layout.addWidget(self.xp_bar)
        
        left_layout.addSpacing(20)
        
        # Window Buttons
        btn_schedule = QPushButton("📅 일정")
        btn_schedule.clicked.connect(self.show_schedule_window)
        left_layout.addWidget(btn_schedule)
        
        btn_quest = QPushButton("⚔️ 퀘스트")
        btn_quest.clicked.connect(self.show_quest_window)
        left_layout.addWidget(btn_quest)
        
        left_layout.addStretch()

        # === [Center] Vision & Chat ===
        center_layout = QVBoxLayout()
        
        # Camera Feed (Responsive)
        self.video_container = QLabel()
        self.video_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_container.setMinimumSize(400, 300) 
        self.video_container.setStyleSheet("background-color: #000; border-radius: 16px; border: 2px solid rgba(255,255,255,0.1);")
        self.video_container.setAlignment(Qt.AlignCenter) # Keep aspect ratio centered
        center_layout.addWidget(self.video_container, stretch=3)

        # Chat Area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        center_layout.addWidget(self.chat_display, stretch=1)

        # Input Area
        input_container = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("오늘 할 일을 입력하거나 대화를 나눠보세요...")
        self.input_field.returnPressed.connect(self.send_message)
        input_container.addWidget(self.input_field)
        
        center_layout.addLayout(input_container)

        # Add to Main
        main_layout.addWidget(left_panel, 25)
        main_layout.addLayout(center_layout, 75)

    def init_video(self):
        self.cap = cv2.VideoCapture(0)
        self.video_timer = QTimer()
        self.video_timer.timeout.connect(self.update_video)
        self.video_timer.start(30)

    def init_timers(self):
        self.game_timer = QTimer()
        self.game_timer.timeout.connect(self.update_game)
        self.game_timer.start(1000)

        self.game_timer.start(1000)

    def trigger_damage_effect(self):
        """HP 감소 시 메인 창 테두리가 붉게 깜빡임"""
        # Save original window style
        original_style = self.styleSheet()
        
        # Append red border to existing style to preserve other styling
        # (Avoids white flash by keeping original background/font settings)
        new_style = original_style + f"""
            QMainWindow {{
                border: 8px solid #FF6B6B;
            }}
        """
        self.setStyleSheet(new_style)
        
        # Restore after 200ms
        QTimer.singleShot(200, lambda: self.setStyleSheet(original_style))

    def update_video(self):
        ret, frame = self.cap.read()
        if not ret: return

        # Vision Analysis
        posture_score, is_drowsy, is_smiling, landmarks = self.vision.analyze_frame(frame)
        self.current_posture = posture_score
        self.current_drowsy = is_drowsy
        self.current_smiling = is_smiling
        self.current_frame = frame 

        # Convert to Qt and Scale to Container
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Scaling while keeping aspect ratio
        container_w = self.video_container.width()
        container_h = self.video_container.height()
        
        # Use simple scaling - fit to container
        scaled_pixmap = QPixmap.fromImage(qt_img).scaled(
            container_w, container_h, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_container.setPixmap(scaled_pixmap)

    def update_game(self):
        # 1. Input Check (Idle)
        now = time.time()
        has_input = (now - self.last_input_time) < 1.0 # Input event updated last_input_time
        
        # 2. Vision Check
        is_bad = getattr(self, 'current_posture', 0) > Config.POSTURE_THRESHOLD
        is_sleep = getattr(self, 'current_drowsy', False)
        
        # 3. Action Check (Stretching/Standing)
        is_active = False
        if hasattr(self, 'current_frame'):
            is_active = self.vision.check_action_movement(self.current_frame)
            
        self.game.update(is_bad, is_sleep, has_input, is_active)
        
        if self.game.hp < getattr(self, 'last_hp', self.game.hp):
            self.trigger_damage_effect()
        self.last_hp = self.game.hp

        # 4. Data Logging (Telemetry)
        self.dm.log_context(self.game.hp, getattr(self, 'current_posture', 0), is_sleep)
        
        # 5. Update Status UI
        self.hp_bar.setValue(int(self.game.hp))
        
        # XP Bar logic (Relative to level)
        next_xp = Config.MAX_XP_TABLE.get(self.game.level + 1, 9999)
        prev_xp = Config.MAX_XP_TABLE.get(self.game.level, 0)
        level_range = next_xp - prev_xp
        current_progress = self.game.xp - prev_xp
        
        if level_range > 0:
            percentage = int((current_progress / level_range) * 100)
            self.xp_bar.setValue(percentage)
        else:
            self.xp_bar.setValue(100) # Max level

        # Text Updates
        self.lbl_level.setText(f"Lv.{self.game.level}")
        
        if self.game.level >= 10:
            self.lbl_title.setText("✨ 전설의 개발자 ✨")
        elif self.game.level >= 5:
            self.lbl_title.setText("🔥 시니어 병아리")
        else:
            self.lbl_title.setText("🐣 주니어 병아리")

        # 6. Alarm Check
        if self.alarm_active:
             if now - self.alarm_start_time > 60: # 1 min to respond
                 self.game.report_alarm_ignored()
                 self.alarm_active = False # Reset
                 self.chat_display.append("<span style='color:#FF6B6B'><b>시스템:</b> 휴식 알람을 무시했습니다! (HP -5)</span>")
                 self.dm.log_interaction("Alarm", "Ignored")

        # Character Expression (Level 2+)
        if self.game.level >= 2:
            self.update_file_face()



    def trigger_rest_alarm(self):
        self.alarm_active = True
        self.alarm_start_time = time.time()
        self.chat_display.append("<span style='color:#FFD93D'><b>🔔 알람:</b> 쉬는 시간입니다! 스트레칭 버튼을 누르거나 휴식하세요!</span>")
        self.dm.log_interaction("Alarm", "Triggered")

    def do_stretch(self):
        # Now uses active movement detection mostly, but button remains as fallback or specific "I am doing it" signal
        # But user wants "Reaction to real movement".
        # We can say "Button pressed -> Please stand up now!"
        self.chat_display.append("<span style='color:#4CC2FF'><b>시스템:</b> 카메라 앞에서 크게 움직이거나 일어서세요!</span>")

    def show_schedule_window(self):
        """Open the schedule window"""
        if self.schedule_window is None:
            self.schedule_window = ScheduleWindow(self)
        
        # Sync tasks to the schedule window
        self.schedule_window.task_table.setRowCount(0)
        for task in self.tasks:
            row = self.schedule_window.task_table.rowCount()
            self.schedule_window.task_table.insertRow(row)
            self.schedule_window.task_table.setItem(row, 0, QTableWidgetItem(task.get('time', '-')))
            self.schedule_window.task_table.setItem(row, 1, QTableWidgetItem(task.get('location', '-')))
            self.schedule_window.task_table.setItem(row, 2, QTableWidgetItem(task.get('content', '-')))
        
        self.schedule_window.show()
        self.schedule_window.raise_()
        self.schedule_window.activateWindow()
    
    def show_quest_window(self):
        """Open the quest window"""
        if self.quest_window is None:
            self.quest_window = QuestWindow(self, self.game)
        
        # Update quests display
        self.quest_window.update_quests()
        self.quest_window.show()
        self.quest_window.raise_()
        self.quest_window.activateWindow()

    def update_file_face(self):
        # Level 2 Unlock: Character Expressions
        if self.game.level < 2:
            return

        status_text = ""
        border_color = "rgba(255,255,255,0.1)"
        
        if self.current_smiling:
            status_text = "😊 행복함"
            border_color = "#F9E2AF" 
        elif self.current_drowsy:
            status_text = "😴 졸림..."
            border_color = "#FF6B6B" 
        elif self.current_posture > Config.POSTURE_THRESHOLD:
            status_text = "🐢 거북목!"
            border_color = "#FF6B6B"
        else:
            status_text = "😐 집중중"
            border_color = Config.COLOR_ACCENT
            
        self.char_img.setStyleSheet(f"border: 4px solid {border_color}; border-radius: 110px;")
        
        if self.game.level < 10:
             self.lbl_title.setText(f"{status_text}")

    def update_character_image(self):
         try:
            pixmap = QPixmap(Config.IMAGE_PATH)
            if not pixmap.isNull():
                self.char_img.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.char_img.setText("🐣")
         except:
            self.char_img.setText("🐣")

    # --- Interaction Events ---
    def keyPressEvent(self, event):
        self.last_input_time = time.time()
        super().keyPressEvent(event)

    def mouseMoveEvent(self, event):
        self.last_input_time = time.time()
        super().mouseMoveEvent(event)

    def send_message(self):
        text = self.input_field.text()
        if not text: return
        
        self.chat_display.append(f"<b>나:</b> {text}")
        self.input_field.clear()
        self.last_input_time = time.time()
        self.dm.log_interaction("User_Input", text) # Log event
        
        # AI Call
        self.brain.chat(text, self.game.level, self.on_ai_response)

    def on_ai_response(self, text, task_info):
        if text:
            self.chat_display.append(f"<b>비서:</b> {text}")
        
        if task_info:
             # Store task
             self.tasks.append(task_info)
             
             # Update schedule window if it's open
             if self.schedule_window and self.schedule_window.isVisible():
                 row = self.schedule_window.task_table.rowCount()
                 self.schedule_window.task_table.insertRow(row)
                 self.schedule_window.task_table.setItem(row, 0, QTableWidgetItem(task_info.get('time', '-')))
                 self.schedule_window.task_table.setItem(row, 1, QTableWidgetItem(task_info.get('location', '-')))
                 self.schedule_window.task_table.setItem(row, 2, QTableWidgetItem(task_info.get('content', '-')))
              
             self.dm.log_interaction("Task_Added", task_info.get('content')) # Log event

    def closeEvent(self, event):
        self.game.save_game()
        self.cap.release()
        self.dm.log_interaction("System", "Shutdown")
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Global Font Setup
    font = QFont(Config.FONT_FAMILY)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)
    
    win = ModernMirror()
    win.show()
    sys.exit(app.exec_())