import time
import json
import os
import random

# Simplified Config
class Config:
    MAX_HP = 100
    MAX_XP_TABLE = {1: 100, 2: 200, 3: 400, 4: 800, 5: 1600}
    HP_PENALTY_IDLE_5MIN = 5
    HP_PENALTY_IS_BAD_POSTURE = 0.5 # Per tick (simulated)
    HP_HEAL_POSTURE_10MIN = 10
    
class Quest:
    def __init__(self, name, type, duration, xp, desc):
        self.name = name
        self.type = type
        self.duration = duration
        self.xp = xp
        self.desc = desc
        self.progress = 0
        self.is_completed = False

    def to_dict(self):
        return self.__dict__

class GameManager:
    def __init__(self):
        self.data_file = "user_data.json"
        self.load_data()
        self.last_update = time.time()
        
        # Runtime
        self.bad_posture_timer = 0
        self.good_posture_timer = 0
        self.idle_timer = 0
        
        # Current Active Quest (Simplified to 1 at a time for v3.0 initial)
        self.current_quest = None
        
    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.hp = data.get('hp', 100)
                self.xp = data.get('xp', 0)
                self.level = data.get('level', 1)
                self.happiness = data.get('happiness', 80)
        else:
            self.hp = 100
            self.xp = 0
            self.level = 1
            self.happiness = 80
            
    def save_data(self):
        data = {
            "hp": self.hp,
            "xp": self.xp,
            "level": self.level,
            "happiness": self.happiness
        }
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f)
            
    def update_state(self, status, is_bad_posture=False):
        now = time.time()
        dt = now - self.last_update
        self.last_update = now
        
        # Only update logic if in Work Mode
        if status == '업무중':
            if is_bad_posture:
                self.bad_posture_timer += dt
                self.good_posture_timer = 0
                if self.bad_posture_timer > 3: # 3 sec grace
                    self.hp -= Config.HP_PENALTY_IS_BAD_POSTURE * dt
            else:
                self.bad_posture_timer = 0
                self.good_posture_timer += dt
                if self.good_posture_timer > 600: # 10 min good
                    self.hp += Config.HP_HEAL_POSTURE_10MIN
                    self.good_posture_timer = 0
            
            # Quest Logic
            if self.current_quest and not self.current_quest.is_completed:
                if self.current_quest.type == 'focus' and not is_bad_posture:
                    self.current_quest.progress += dt
                elif self.current_quest.type == 'posture' and not is_bad_posture:
                     self.current_quest.progress += dt
                     
                if self.current_quest.progress >= self.current_quest.duration:
                    self.complete_quest()
                    
        # Clamp Values
        self.hp = max(0, min(100, self.hp))
        self.happiness = max(0, min(100, self.happiness))
        
        # Level Up Check
        req_xp = Config.MAX_XP_TABLE.get(self.level, 1000 * self.level)
        if self.xp >= req_xp:
            self.xp -= req_xp
            self.level += 1
            
        self.save_data()
        
    def start_quest(self, type):
        if type == 'focus':
            self.current_quest = Quest("집중 모드", "focus", 25*60, 50, "25분간 집중하기")
        elif type == 'posture':
            self.current_quest = Quest("바른 자세", "posture", 10*60, 30, "10분간 바른 자세 유지")
            
    def complete_quest(self):
        if self.current_quest:
            self.current_quest.is_completed = True
            self.xp += self.current_quest.xp
            self.happiness += 5
            self.current_quest = None

    def get_state(self):
        return {
            "hp": int(self.hp),
            "xp": int(self.xp),
            "level": self.level,
            "happiness": int(self.happiness),
            "max_xp": Config.MAX_XP_TABLE.get(self.level, 1000 * self.level),
            "current_quest": self.current_quest.to_dict() if self.current_quest else None
        }
