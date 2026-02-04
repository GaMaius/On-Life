# config.py

class Config:
    # --- Vision Thresholds ---
    EAR_THRESHOLD = 0.18        # 눈 감음 판정
    POSTURE_THRESHOLD = 0.15    # 거북목 판정
    POSTURE_OFFSET_Y = 0.05     # 대각선/측면 뷰 보정값
    SMILE_THRESHOLD = 0.04      
    
    # --- Game Mechanics ---
    MAX_HP = 100
    # 레벨 구조: Lv.1(0), Lv.2(100), Lv.3(300), Lv.5(800), Lv.10(2000)
    MAX_XP_TABLE = {1: 0, 2: 100, 3: 300, 4: 550, 5: 800, 6: 1050, 7: 1300, 8: 1550, 9: 1800, 10: 2000} 
    
    # HP 감소 조건 (패널티)
    # 거북목 지속 3분 이상: -2 / 분
    # 심각한 거북목 7분 이상: -5 / 분
    HP_PENALTY_POSTURE_3MIN = 2.0  
    HP_PENALTY_POSTURE_7MIN = 5.0  
    
    # 몰컴 감지 (입력/집중 없음 5분): -3
    HP_PENALTY_IDLE_5MIN = 3.0     
    
    # 알람 무시 2회 연속: -5
    HP_PENALTY_IGNORE_ALARM = 5.0  
    
    # 휴식 없이 연속 작업 90분 초과: -10
    HP_PENALTY_OVERWORK_90MIN = 10.0 
    
    # HP 회복 조건
    HP_HEAL_STRETCH = 10.0         # 스트레칭 가이드 완료
    HP_HEAL_POSTURE_10MIN = 3.0    # 10분 연속 바른 자세
    HP_HEAL_REST_5MIN = 8.0        # 5분 휴식 퀘스트 완료
    HP_HEAL_FOCUS_25MIN = 5.0      # 집중 세션 성공 (25분)
    
    # UI Colors (Neumorphism / Modern)
    COLOR_BG = "#E0E5EC"           # Light Grey-ish for Neumorphism
    COLOR_SHADOW_LIGHT = "#FFFFFF"
    COLOR_SHADOW_DARK = "#A3B1C6"
    COLOR_ACCENT = "#6D5DFC"       # Purple/Blue accent
    COLOR_TEXT_MAIN = "#4A4A4A"
    COLOR_TEXT_SUB = "#888888"
    
    FONT_FAMILY = "Inter, Malgun Gothic, sans-serif"
    IMAGE_PATH = "assets/chick.jpg"