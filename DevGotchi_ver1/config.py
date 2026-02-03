# config.py

class Config:
    # --- Vision Thresholds ---
    # --- Vision Thresholds ---
    EAR_THRESHOLD = 0.18        # 눈 감음 판정 (기본 0.22 -> 0.18로 완화)
    POSTURE_THRESHOLD = 0.15    # 거북목 판정 (값이 클수록 거북목)
    POSTURE_OFFSET_Y = 0.05     # 대각선/측면 뷰 보정값 (필요시 조정)
    SMILE_THRESHOLD = 0.04      
    
    # --- Game Mechanics (User Defined) ---
    MAX_HP = 100
    MAX_XP_TABLE = {1: 0, 2: 100, 3: 300, 5: 800, 10: 2000} # 레벨별 필요 XP
    
    # 패널티 규칙
    HP_PENALTY_POSTURE_3MIN = 2.0  # 분당 감소
    HP_PENALTY_POSTURE_7MIN = 5.0  # 분당 감소 (심각)
    HP_PENALTY_IDLE_5MIN = 3.0     # 몰컴/부재 (5분마다)
    HP_PENALTY_IGNORE_ALARM = 5.0  # 2회 연속 무시
    HP_PENALTY_OVERWORK_90MIN = 10.0 # 휴식 없이 90분 초과
    HP_PENALTY_SLEEP = 2.0         # 졸음 시 초당 감소량 (조정됨)

    # 회복 규칙
    HP_HEAL_STRETCH = 10.0
    HP_HEAL_POSTURE_10MIN = 3.0
    HP_HEAL_REST_5MIN = 8.0
    HP_HEAL_FOCUS_25MIN = 5.0
    
    XP_REWARD_NORMAL = 50
    XP_REWARD_HARD = 150

    # --- UI Colors (Modern Desk Style) ---
    COLOR_BG = "#1E1E2E"           # 모던 다크 블루 그레이
    COLOR_PANEL = "rgba(255, 255, 255, 0.05)" # 더 투명한 글래스
    COLOR_ACCENT = "#89B4FA"       # 파스텔 블루
    COLOR_TEXT_MAIN = "#CDD6F4"
    COLOR_TEXT_SUB = "#A6ADC8"
    COLOR_HP = "#F38BA8"           # 파스텔 레드
    COLOR_XP = "#F9E2AF"           # 파스텔 옐로우
    
    FONT_FAMILY = "Malgun Gothic"  # 윈도우 기본 폰트 (한글 깨짐 방지)
    IMAGE_PATH = "assets/chick.jpg" # 병아리 이미지 경로