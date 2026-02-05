# game_manager.py
import time
import random
from config import Config
# data_manager will be implemented later or mock for now
import json
import os

class DataManager:
    def __init__(self, filepath="user_data.json"):
        self.filepath = filepath

    def load_user_data(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_user_data(self, data):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

class Quest:
    def __init__(self, name, type, target_duration, reward_xp, difficulty="Normal", description="", clear_condition=""):
        self.name = name
        self.type = type 
        self.target_duration = target_duration 
        self.reward_xp = reward_xp
        self.difficulty = difficulty 
        self.description = description
        self.clear_condition = clear_condition
        self.progress = 0
        self.is_completed = False

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(data):
        q = Quest(
            data['name'], data['type'], data['target_duration'], data['reward_xp'], 
            data['difficulty'], data.get('description',''), data.get('clear_condition','')
        )
        q.progress = data.get('progress', 0)
        q.is_completed = data.get('is_completed', False)
        return q

class GameManager:
    def __init__(self):
        self.dm = DataManager()
        self.load_game()
        self.reset_runtime_state()
        self.available_quests = []

    def reset_runtime_state(self):
        self.bad_posture_duration = 0
        self.good_posture_duration = 0
        self.idle_duration = 0
        self.continuous_work_duration = 0
        self.last_update_time = time.time()

    def load_game(self):
        data = self.dm.load_user_data()
        self.hp = data.get("hp", Config.MAX_HP)
        self.xp = data.get("xp", 0)
        self.level = data.get("level", 1)
        self.quests = [Quest.from_dict(q) for q in data.get("quests", [])]
        self.happiness = data.get("happiness", 100)

    def save_game(self):
        data = {
            "hp": self.hp,
            "xp": self.xp,
            "level": self.level,
            "quests": [q.to_dict() for q in self.quests],
            "happiness": self.happiness
        }
        self.dm.save_user_data(data)

    def update(self, is_bad_posture, is_drowsy, has_user_input, is_active_movement=False):
        now = time.time()
        dt = now - self.last_update_time
        self.last_update_time = now

        # 1. HP Penalty Logic (Simplified for V3 Migration)
        if is_bad_posture:
            self.bad_posture_duration += dt
            if self.bad_posture_duration > 3:
                 self.hp -= Config.HP_PENALTY_POSTURE_INSTANT * dt
        else:
            self.bad_posture_duration = 0
            # Good posture healing
            self.good_posture_duration += dt
            if self.good_posture_duration > 600:
                self.hp = min(Config.MAX_HP, self.hp + Config.HP_HEAL_POSTURE_10MIN)
                self.good_posture_duration = 0

        # Updates quests... (Simplified)
        active_quests = [q for q in self.quests if not q.is_completed]
        for q in active_quests:
            if q.type == 'focus' and not is_bad_posture:
                q.progress += dt
            elif q.type == 'posture' and not is_bad_posture:
                q.progress += dt
            
            if q.progress >= q.target_duration:
                q.is_completed = True
                self.xp += q.reward_xp
                self.save_game()

        self.hp = max(0, self.hp)