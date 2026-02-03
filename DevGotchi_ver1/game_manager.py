import time
import random
from config import Config
from data_manager import DataManager

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
        q.progress = data['progress']
        q.is_completed = data['is_completed']
        return q

class GameManager:
    def __init__(self):
        self.dm = DataManager()
        self.load_game()
        
        # Runtime State (Reset on restart)
        self.reset_runtime_state()
        
        # Quest Selection System
        self.available_quests = []  # 3 options for user to choose from

    def reset_runtime_state(self):
        self.bad_posture_duration = 0
        self.good_posture_duration = 0
        self.idle_duration = 0
        self.continuous_work_duration = 0
        self.alarm_ignore_count = 0
        self.last_update_time = time.time()

    def load_game(self):
        data = self.dm.load_user_data()
        if data:
            self.hp = data.get("hp", Config.MAX_HP)
            self.xp = data.get("xp", 0)
            self.level = data.get("level", 1)
            self.quests = [Quest.from_dict(q) for q in data.get("quests", [])]
            self.quest_streak = data.get("quest_streak", 0) # + for success, - for failure
        else:
            self.hp = Config.MAX_HP
            self.xp = 0
            self.level = 1
            self.quests = []
            self.quest_streak = 0
        
        # Ensure HP is valid
        self.hp = max(0, min(Config.MAX_HP, self.hp))

    def save_game(self):
        data = {
            "hp": self.hp,
            "xp": self.xp,
            "level": self.level,
            "quests": [q.to_dict() for q in self.quests],
            "quest_streak": self.quest_streak
        }
        self.dm.save_user_data(data)

    def update(self, is_bad_posture, is_drowsy, has_user_input, is_active_movement=False):
        now = time.time()
        dt = now - self.last_update_time
        self.last_update_time = now

        # --- 2. Quest Progress & Protection Check ---
        active_quests = [q for q in self.quests if not q.is_completed]
        
        # Check if we are in a "protected" mode (Stretch/Rest quest active)
        # User requested: No HP reduction during 'Stretch' (Stress) type quests.
        # Focus/Posture quests SHOULD have HP reduction.
        is_protected_mode = any(q.type in ['stretch', 'rest'] for q in active_quests)

        # --- 1. HP Penalty Logic ---
        if not is_protected_mode:
            # 1.1 Posture (3min / 7min)
            if is_bad_posture:
                self.bad_posture_duration += dt
                self.good_posture_duration = 0 # Reset good streak
                
                if self.bad_posture_duration > 420: # 7 min
                    self.hp -= (Config.HP_PENALTY_POSTURE_7MIN / 60) * dt
                elif self.bad_posture_duration > 180: # 3 min
                    self.hp -= (Config.HP_PENALTY_POSTURE_3MIN / 60) * dt
            else:
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
            
            # 1.4 Sleep (Drowsy) - Sleep might still be penalized? 
            # Assuming 'Rest' allows sleep, but 'Stretch' implies activity. 
            # For now, disable sleep penalty too if protected.
            if is_drowsy:
                self.hp -= Config.HP_PENALTY_SLEEP * dt
        else:
            # In protected mode, reset bad counters to prevent instant penalty upon finishing quest
            self.bad_posture_duration = 0
            self.idle_duration = 0
        
        # Generate quest options if no active quest and no available options
        if len(active_quests) == 0 and len(self.available_quests) == 0:
            self.generate_quest_options()

        for q in active_quests:
            if q.type == 'focus':
                if not is_bad_posture and not is_drowsy:
                    q.progress += dt
            elif q.type == 'posture':
                if not is_bad_posture:
                    q.progress += dt
            elif q.type == 'rest':
                # Rest quest: User should be away/idle or MOVING (stretching)
                if self.idle_duration > 10 or is_active_movement: 
                    q.progress += dt
            elif q.type == 'stretch':
                # Active movement needed
                if is_active_movement:
                    q.progress += dt 
                    # Bonus speed for stretching
                    q.progress += dt * 2 
            if q.progress >= q.target_duration:
                self.complete_quest(q)

        # Level Up Check
        self.check_level_up()

        # Clamp HP
        self.hp = max(0, min(Config.MAX_HP, self.hp))

    def get_quest_capacity(self):
        return 2 if self.level >= 3 else 1

    def generate_quest_options(self):
        """Generate 3 random quest options for user to choose from"""
        # Quest Types
        # 1. Focus: 25m (Normal), 50m (Hard)
        # 2. Posture: 10m (Easy), 30m (Normal)
        # 3. Recovery: Rest 5m (Normal)
        # 4. Stretch: Active movement (Normal)
        
        # Difficulty Adjustment
        difficulty_mod = self.quest_streak # +2 (Harder), -2 (Easier)
        
        pool = []
        
        # Focus Quests
        pool.append(Quest(
            "집중 세션 (25분)", 
            "focus", 
            25*60, 
            50, 
            "Normal",
            "25분 동안 집중 작업을 수행하세요.",
            "바른 자세 유지 + 졸음 없이 25분 작업"
        ))
        if difficulty_mod > 2:
            pool.append(Quest(
                "딥 워크 (50분)", 
                "focus", 
                50*60, 
                120, 
                "Hard",
                "50분 동안 중단 없이 깊은 집중 작업을 수행하세요.",
                "바른 자세 + 졸음 없이 50분 연속 작업"
            ))
        
        # Posture Quests
        pool.append(Quest(
            "바른 자세 (10분)", 
            "posture", 
            10*60, 
            30, 
            "Easy",
            "10분 동안 바른 자세를 유지하세요.",
            "거북목 없이 10분 유지"
        ))
        if difficulty_mod > 1:
            pool.append(Quest(
                "거북목 금지 (30분)", 
                "posture", 
                30*60, 
                80, 
                "Normal",
                "30분 동안 거북목 없이 작업하세요.",
                "거북목 자세 없이 30분 유지"
            ))
            
        # Recovery Quests
        pool.append(Quest(
            "잠시 휴식 (5분)", 
            "rest", 
            5*60, 
            40, 
            "Normal",
            "5분간 자리를 비우거나 스트레칭하며 휴식을 취하세요.",
            "5분간 입력 없음 또는 움직임 감지"
        ))
        
        # Stretch Quest
        pool.append(Quest(
            "스트레칭 (3분)",
            "stretch",
            3*60,
            60,
            "Normal",
            "3분 동안 카메라 앞에서 활발하게 움직이세요.",
            "카메라가 큰 움직임을 3분간 감지"
        ))

        # Select 3 unique quests
        if len(pool) >= 3:
            self.available_quests = random.sample(pool, 3)
        else:
            self.available_quests = pool
            
    def accept_quest(self, quest_index):
        """User accepts one of the available quests"""
        if 0 <= quest_index < len(self.available_quests):
            selected_quest = self.available_quests[quest_index]
            # Clear current active quests and add the selected one
            self.quests = [selected_quest]
            # Clear available options
            self.available_quests = []
            self.save_game()
            return True
        return False

    def complete_quest(self, quest):
        quest.is_completed = True
        self.gain_xp(quest.reward_xp)
        self.quest_streak += 1
        
        # HP Rewards
        if quest.type == 'focus':
            self.gain_hp(Config.HP_HEAL_FOCUS_25MIN)
        elif quest.type == 'posture':
            self.gain_hp(Config.HP_HEAL_POSTURE_10MIN)
        elif quest.type == 'rest':
            self.gain_hp(Config.HP_HEAL_REST_5MIN)
            self.continuous_work_duration = 0 # Reset overwork timer
            
        self.save_game()

    def report_alarm_ignored(self):
        self.alarm_ignore_count += 1
        if self.alarm_ignore_count >= 2:
            self.hp -= Config.HP_PENALTY_IGNORE_ALARM
            self.alarm_ignore_count = 0 

    def fail_quest(self, quest):
        # Manually fail or timeout logic (not implemented yet, but for streak)
        self.quest_streak = max(-5, self.quest_streak - 1)

    def perform_stretch(self):
        # Called when Stretch Guide is completed
        self.gain_hp(Config.HP_HEAL_STRETCH)
        self.gain_xp(15)
        # Also complete any stretch quest if exists (though we didn't add one to pool)
        self.save_game()

    def gain_xp(self, amount):
        # Level 5+ Reward Boost
        if self.level >= 5:
            amount = int(amount * 1.2)
        self.xp += amount
        self.check_level_up()

    def gain_hp(self, amount):
        self.hp += amount
        self.hp = min(Config.MAX_HP, self.hp)

    def check_level_up(self):
        # Check next level
        next_xp = Config.MAX_XP_TABLE.get(self.level + 1)
        if next_xp and self.xp >= next_xp:
            self.level += 1
            # Recurse for multi-level up
            self.check_level_up()
            self.save_game()