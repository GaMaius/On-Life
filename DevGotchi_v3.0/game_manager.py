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
        self.type = type # 'focus', 'posture', 'rest', 'stretch'
        self.target_duration = target_duration # seconds
        self.reward_xp = reward_xp
        self.difficulty = difficulty # 'Easy', 'Normal', 'Hard'
        self.description = description
        self.clear_condition = clear_condition
        self.progress = 0
        self.is_completed = False
        self.start_time = time.time()

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "target_duration": self.target_duration,
            "reward_xp": self.reward_xp,
            "difficulty": self.difficulty,
            "description": self.description,
            "clear_condition": self.clear_condition,
            "progress": self.progress,
            "is_completed": self.is_completed
        }

    @staticmethod
    def from_dict(data):
        q = Quest(
            data['name'], 
            data['type'], 
            data['target_duration'], 
            data['reward_xp'], 
            data['difficulty'],
            data.get('description', ''),
            data.get('clear_condition', '')
        )
        q.progress = data.get('progress', 0)
        q.is_completed = data.get('is_completed', False)
        return q

class GameManager:
    def __init__(self):
        self.dm = DataManager()
        self.load_game()
        
        # Runtime State (Reset on restart)
        self.reset_runtime_state()
        
        # Quest Selection System
        self.available_quests = [] 

    def reset_runtime_state(self):
        self.bad_posture_duration = 0
        self.good_posture_duration = 0
        self.idle_duration = 0
        self.continuous_work_duration = 0
        self.alarm_ignore_count = 0
        self.last_update_time = time.time()

    def load_game(self):
        data = self.dm.load_user_data()
        self.hp = data.get("hp", Config.MAX_HP)
        self.xp = data.get("xp", 0)
        self.level = data.get("level", 1)
        self.quests = [Quest.from_dict(q) for q in data.get("quests", [])]
        self.quest_streak = data.get("quest_streak", 0)
        self.happiness = data.get("happiness", 100)
        
        # Ensure HP is valid
        self.hp = max(0, min(Config.MAX_HP, self.hp))

    def save_game(self):
        data = {
            "hp": self.hp,
            "xp": self.xp,
            "level": self.level,
            "quests": [q.to_dict() for q in self.quests],
            "quest_streak": self.quest_streak,
            "happiness": self.happiness
        }
        self.dm.save_user_data(data)


    def update(self, is_bad_posture, is_drowsy, has_user_input, is_active_movement=False):
        now = time.time()
        dt = now - self.last_update_time
        self.last_update_time = now

        # --- 2. Quest Progress & Protection Check ---
        active_quests = [q for q in self.quests if not q.is_completed]
        
        # Check if we are in a "protected" mode (Stretch/Rest quest active)
        is_protected_mode = any(q.type in ['stretch', 'rest', 'recovery'] for q in active_quests)

        # --- 1. HP Penalty Logic ---
        if not is_protected_mode:
            # 1.1 Posture Penalty (Debounced)
            if not hasattr(self, 'good_posture_buffer'):
                self.good_posture_buffer = 0

            if is_bad_posture:
                self.bad_posture_duration += dt
                self.good_posture_buffer = 0 
                
                # Instant penalty (after 3s)
                if self.bad_posture_duration > 3:
                    damage = Config.HP_PENALTY_POSTURE_INSTANT * dt
                    self.hp -= damage
                    
                # Additional penalty: 3min+
                if self.bad_posture_duration > 180:
                    self.hp -= (Config.HP_PENALTY_POSTURE_3MIN / 60) * dt
                    
                # Additional penalty: 7min+
                if self.bad_posture_duration > 420:
                    self.hp -= (Config.HP_PENALTY_POSTURE_7MIN / 60) * dt
                    
            else:
                # 1.2 Good Posture (Debounce Reset)
                self.good_posture_buffer += dt
                if self.good_posture_buffer > 1.0: 
                     self.bad_posture_duration = 0
                
                self.good_posture_duration += dt
                
                # Posture Recovery (10 min good posture)
                if self.good_posture_duration >= 600: # 10 min
                    self.gain_hp(Config.HP_HEAL_POSTURE_10MIN)
                    self.good_posture_duration = 0 

            # 1.2 Idle / MolCom (5 min no input/focus)
            if not has_user_input and not is_bad_posture and not is_active_movement: 
                self.idle_duration += dt
            else:
                self.idle_duration = 0
                
            if self.idle_duration >= 300: # 5 min
                self.hp -= Config.HP_PENALTY_IDLE_5MIN
                self.idle_duration = 0 

            # 1.3 Overwork (90 min continuous)
            self.continuous_work_duration += dt
            if self.continuous_work_duration > 5400: # 90 min
                self.hp -= Config.HP_PENALTY_OVERWORK_90MIN
                self.continuous_work_duration = 0 
        else:
            # In protected mode, reset bad counters
            self.bad_posture_duration = 0
            self.idle_duration = 0
            
        # Check for Level Down (HP Depleted)
        if self.hp <= 0:
            print(f"[Game] HP Depleted! Level Down from {self.level} -> {max(1, self.level - 1)}")
            self.level = max(1, self.level - 1)
            self.hp = Config.MAX_HP / 2
            self.xp = 0 
        
        # Generator quest options if needed
        capacity = self.get_quest_capacity()
        if len(active_quests) < capacity and len(self.available_quests) == 0:
            self.generate_quest_options()

        for q in active_quests:
            if q.type == 'focus':
                # Rule: "25분 집중 유지하기"
                if not is_bad_posture and not is_drowsy:
                    q.progress += dt
            elif q.type == 'posture':
                # Rule: "10분간 바른 자세 유지"
                if not is_bad_posture:
                    q.progress += dt
                else:
                    # Reset progress for "continuous" quests
                    if "연속" in q.name or "Consectuive" in q.name:
                        q.progress = 0
            elif q.type == 'rest':
                if self.idle_duration > 10 or is_active_movement: 
                    q.progress += dt
            elif q.type == 'recovery': # Stretch or Rest
                 if is_active_movement or self.idle_duration > 10:
                    q.progress += dt

            if q.progress >= q.target_duration:
                self.complete_quest(q)

        self.check_level_up()
        self.hp = max(0, min(Config.MAX_HP, self.hp))

    def get_quest_capacity(self):
        return 2 if self.level >= 3 else 1

    def generate_quest_options(self):
        """Generate 3 random quest options (1 Focus, 1 Posture, 1 Recovery)"""
        difficulty_mod = self.quest_streak 
        is_hard = difficulty_mod >= 2
        is_easy = difficulty_mod < -1
        
        pool_focus = []
        pool_posture = []
        pool_recovery = []
        
        # 1. Focus Quests
        pool_focus.append(Quest("집중 퀘스트: 25분 집중 유지", "focus", 25*60, 50, "Normal", "25분 동안 집중 상태(바른 자세)를 유지하세요.", "바른 자세 + 졸음 없음 25분"))
        if is_hard:
             pool_focus.append(Quest("집중 퀘스트: 50분 딥워크", "focus", 50*60, 100, "Hard", "50분 동안 집중하세요.", "바른 자세 + 졸음 없음 50분"))

        # 2. Posture Quests
        pool_posture.append(Quest("자세 퀘스트: 10분 바른 자세", "posture", 10*60, 30, "Easy", "10분간 바른 자세를 연속 유지하세요.", "바른 자세 10분"))
        if not is_easy:
             pool_posture.append(Quest("자세 퀘스트: 1시간 거북목 없이", "posture", 60*60, 80, "Hard", "1시간 동안 거북목 경고 없이 작업하세요.", "거북목 감지 없음 1시간"))

        # 3. Recovery Quests
        pool_recovery.append(Quest("회복 퀘스트: 5분 휴식", "recovery", 5*60, 40, "Easy", "5분간 화면을 보지 말고 휴식하세요.", "입력 없음/부재 5분"))
        pool_recovery.append(Quest("회복 퀘스트: 스트레칭 1회", "recovery", 60, 60, "Normal", "1분간 스트레칭 가이드를 따라하세요.", "스트레칭 동작 감지"))

        q1 = random.choice(pool_focus)
        q2 = random.choice(pool_posture)
        q3 = random.choice(pool_recovery)
        
        self.available_quests = [q1, q2, q3]

    def accept_quest(self, quest_index):
        """User accepts one of the available quests"""
        capacity = self.get_quest_capacity()
        active_count = len([q for q in self.quests if not q.is_completed])
        
        if active_count >= capacity:
            return False 
            
        if 0 <= quest_index < len(self.available_quests):
            selected_quest = self.available_quests[quest_index]
            self.quests.append(selected_quest)
            self.available_quests.pop(quest_index)
            self.save_game()
            return True
        return False

    def complete_quest(self, quest):
        quest.is_completed = True
        self.gain_xp(quest.reward_xp)
        self.quest_streak += 1
        
        if quest.type == 'focus':
            self.gain_hp(Config.HP_HEAL_FOCUS_25MIN)
        elif quest.type == 'posture':
            self.gain_hp(Config.HP_HEAL_POSTURE_10MIN)
        elif quest.type == 'rest':
            self.gain_hp(Config.HP_HEAL_REST_5MIN)
            self.continuous_work_duration = 0 
            
        self.save_game()

    def gain_xp(self, amount):
        if self.level >= 5:
            amount = int(amount * 1.2)
        self.xp += amount
        self.check_level_up()

    def gain_hp(self, amount):
        self.hp += amount
        self.hp = min(Config.MAX_HP, self.hp)

    def check_level_up(self):
        next_xp = Config.MAX_EXP_TABLE.get(self.level + 1)
        if next_xp and self.xp >= next_xp:
            self.level += 1
            self.check_level_up()
            self.save_game()