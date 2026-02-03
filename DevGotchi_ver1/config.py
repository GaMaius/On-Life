# config.py

class Config:
    # --- Vision Thresholds ---
    EAR_THRESHOLD = 0.22        # 눈 감음 판정
    POSTURE_THRESHOLD = 0.15    # 거북목 판정 (값이 클수록 거북목)
    SMILE_THRESHOLD = 0.04      
    
    # --- Game Mechanics (User Defined) ---
    MAX_HP = 100
    MAX_XP_TABLE = {1: 0, 2: 100, 3: 300, 5: 800, 10: 2000} # 레벨별 필요 XP
    
    # 패널티 규칙
    HP_PENALTY_POSTURE_3MIN = 2.0  # 분당 감소
    HP_PENALTY_POSTURE_7MIN = 5.0  # 분당 감소 (심각)
    HP_PENALTY_AFK_5MIN = 3.0      # 몰컴/부재
    HP_PENALTY_IGNORE_ALARM = 5.0  
    HP_PENALTY_OVERWORK_90MIN = 10.0

    # 회복 규칙
    HP_HEAL_STRETCH = 10.0
    HP_HEAL_POSTURE_10MIN = 3.0
    HP_HEAL_REST_5MIN = 8.0
    HP_HEAL_FOCUS_25MIN = 5.0
    
    XP_REWARD_NORMAL = 50
    XP_REWARD_HARD = 150

    # --- UI Colors (Modern Desk Style) ---
    COLOR_BG = "#121212"           # 딥 다크 그레이
    COLOR_PANEL = "rgba(255, 255, 255, 0.08)" # 반투명 글래스 효과
    COLOR_ACCENT = "#4CC2FF"       # 소프트 블루 (포인트)
    COLOR_TEXT_MAIN = "#FFFFFF"
    COLOR_TEXT_SUB = "#AAAAAA"
    COLOR_HP = "#FF6B6B"           # 소프트 레드
    COLOR_XP = "#FFD93D"           # 소프트 옐로우
    
    FONT_FAMILY = "Malgun Gothic"  # 윈도우 기본 폰트 (한글 깨짐 방지)
    IMAGE_PATH = "assets/chick.jpg" # 병아리 이미지 경로