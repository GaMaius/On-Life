import time
from config import Config

class Quest:
    def __init__(self, name, type, target_duration, reward_xp):
        self.name = name
        self.type = type # 'focus', 'posture', 'rest'
        self.target_duration = target_duration
        self.reward_xp = reward_xp
        self.start_time = time.time()
        self.progress = 0
        self.is_completed = False

class GameManager:
    def __init__(self):
        self.hp = Config.MAX_HP
        self.xp = 0
        self.level = 1
        self.quests = []
        
        # 상태 추적용 타이머 변수
        self.last_good_posture_time = time.time()
        self.bad_posture_start_time = None
        self.focus_start_time = time.time()
        self.last_input_time = time.time() # 몰컴 감지용

    def update(self, is_bad_posture, is_drowsy, has_user_input):
        now = time.time()
        dt = 1.0 # 1초 단위 업데이트 가정

        # 1. 거북목 패널티 로직 (3분/7분)
        if is_bad_posture:
            if self.bad_posture_start_time is None:
                self.bad_posture_start_time = now
            
            duration = now - self.bad_posture_start_time
            if duration > 420: # 7분
                self.hp -= (Config.HP_PENALTY_POSTURE_7MIN / 60) * dt
            elif duration > 180: # 3분
                self.hp -= (Config.HP_PENALTY_POSTURE_3MIN / 60) * dt
        else:
            self.bad_posture_start_time = None

        # 2. 졸음 패널티 (지속적인 감소)
        if is_drowsy:
             self.hp -= 0.5 * dt # 졸면 HP 빠르게 감소

        # 3. 퀘스트 진행 체크
        active_quests = [q for q in self.quests if not q.is_completed]
        for q in active_quests:
            if q.type == 'focus':
                # 거북목이 아니고 졸지 않아야 집중 인정
                if not is_bad_posture and not is_drowsy:
                    q.progress += dt
            elif q.type == 'posture':
                if not is_bad_posture:
                    q.progress += dt
            elif q.type == 'stretch':
                # 스트레칭은 즉시 완료되는 타입
                pass
            
            # 퀘스트 완료 체크
            if q.progress >= q.target_duration:
                q.is_completed = True
                self.gain_xp(q.reward_xp)
                # 집중 성공 시 HP 회복
                if q.type == 'focus':
                    self.gain_hp(Config.HP_HEAL_FOCUS_25MIN)
                elif q.type == 'posture':
                    self.gain_hp(Config.HP_HEAL_POSTURE_10MIN)

        # 4. 레벨업 체크
        next_level_xp = Config.MAX_XP_TABLE.get(self.level + 1, 99999)
        if self.xp >= next_level_xp:
            self.level += 1
            # 레벨업 효과는 UI에서 처리

        # HP 범위 제한
        self.hp = max(0, min(Config.MAX_HP, self.hp))

    def add_quest(self, quest_type):
        if quest_type == "focus_25m":
            # 이미 있는지 확인
            if not any(q.type == 'focus' and not q.is_completed for q in self.quests):
                self.quests.append(Quest("25분 집중", "focus", 25*60, 100))
        elif quest_type == "posture_10m":
            if not any(q.type == 'posture' and not q.is_completed for q in self.quests):
                self.quests.append(Quest("바른자세 10분", "posture", 10*60, 50))
        elif quest_type == "stretch":
            # 스트레칭은 즉시 완료 처리 (감지 로직이 복잡하므로 버튼 클릭 시 성공으로 간주)
            self.gain_hp(Config.HP_HEAL_STRETCH)
            self.gain_xp(30)
            # 완료된 퀘스트 기록 남기기 (UI 표시용)
            q = Quest("스트레칭", "stretch", 0, 30)
            q.is_completed = True
            self.quests.append(q)

    def gain_xp(self, amount):
        self.xp += amount

    def gain_hp(self, amount):
        self.hp += amount