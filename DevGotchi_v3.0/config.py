
import os

class Config:
    # App Config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'devgotchi-secret-key'
    
    # Game Config
    MAX_HP = 100
    MAX_EXP_TABLE = {
        1: 2000, 2: 5000, 3: 10000, 4: 20000, 5: 50000
    }
    
    # Penalties
    HP_PENALTY_POSTURE_INSTANT = 0.5 # per second after 3s
    HP_PENALTY_POSTURE_3MIN = 30 # absolute damage or rate? Game logic uses logic.
    HP_PENALTY_POSTURE_7MIN = 50
    HP_PENALTY_IDLE_5MIN = 10
    HP_PENALTY_OVERWORK_90MIN = 20
    HP_PENALTY_IGNORE_ALARM = 5
    
    # Heals
    HP_HEAL_POSTURE_10MIN = 5
    HP_HEAL_FOCUS_25MIN = 10
    HP_HEAL_REST_5MIN = 5
    HP_HEAL_STRETCH = 15
    
    # Vision Config
    EAR_THRESHOLD = 0.18
    POSTURE_OFFSET_Y = 0.1 # Calibration