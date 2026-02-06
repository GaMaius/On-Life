# data_manager.py
import json
import os
from datetime import datetime
from collections import Counter

LOG_FILE = "dev_gotchi_logs.json"

class DataManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataManager, cls).__new__(cls)
            cls._instance._init_logger()
        return cls._instance

    def _init_logger(self):
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
        self.session_id = f"sess_{int(datetime.now().timestamp())}"

    def _save(self, entry):
        try:
            with open(LOG_FILE, 'r+', encoding='utf-8') as f:
                try:
                    logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
                logs.append(entry)
                f.seek(0)
                json.dump(logs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Data Error] {e}")

    # --- Type A: Interaction ---
    def log_interaction(self, event, metadata=None):
        self._save({
            "type": "A_Interaction",
            "ts": datetime.now().isoformat(),
            "session": self.session_id,
            "device_id": "mirror_prototype_01", # Fixed ID for prototype
            "event_name": event,
            "metadata": metadata or {}
        })

    # --- Type B: Context ---
    def log_context(self, hp, posture_score, is_drowsy):
        self._save({
            "type": "B_Context",
            "ts": datetime.now().isoformat(),
            "hp": round(hp, 1),
            "posture_score": round(posture_score, 3),
            "is_drowsy": is_drowsy
        })

    # --- Type C: Telemetry ---
    def log_telemetry(self, latency_ms, fps=0):
        self._save({
            "type": "C_Telemetry",
            "ts": datetime.now().isoformat(),
            "latency_ms": latency_ms,
            "fps": fps
        })

    # --- Type D: LLM Usage ---
    def log_llm(self, tokens, task):
        self._save({
            "type": "D_LLM",
            "ts": datetime.now().isoformat(),
            "tokens": tokens,
            "task": task
        })

    def get_stats(self):
        """인포그래픽용 통계 데이터 추출"""
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            # 퀘스트 완료 횟수
            quests = len([l for l in logs if l.get('event') == 'Quest_Complete'])
            # 평균 API 지연시간
            latencies = [l['latency_ms'] for l in logs if l['type'] == 'C_Telemetry']
            avg_latency = sum(latencies) // len(latencies) if latencies else 0
            
            return {"quests": quests, "avg_latency": avg_latency}
        except:
            return {"quests": 0, "avg_latency": 0}

    # --- User Data Persistence ---
    def save_user_data(self, data):
        """사용자 데이터(레벨, 경험치, 퀘스트 기록 등) 저장"""
        try:
            with open("user_data.json", 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Save Error] {e}")

    def load_user_data(self):
        """사용자 데이터 불러오기"""
        if not os.path.exists("user_data.json"):
            return None
        try:
            with open("user_data.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Load Error] {e}")
            return None

    # --- Chat History & Schedule Persistence (Added for app.py compatibility) ---
    def load_chat_history(self):
        """채팅 기록 및 세션 정보 로드"""
        default_data = {
            "history": [],
            "current_session_id": 1,
            "pinned_sessions": []
        }
        if not os.path.exists("chat_history.json"):
            return default_data
        
        try:
            with open("chat_history.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 필수 키 보장
                for key in default_data:
                    if key not in data:
                        data[key] = default_data[key]
                # pinned_sessions가 list여야 함 (app.py에서 set으로 변환)
                if not isinstance(data.get("pinned_sessions"), list):
                    data["pinned_sessions"] = []
                return data
        except Exception as e:
            print(f"[History Load Error] {e}")
            return default_data

    def save_chat_history(self, history, current_session_id, pinned_sessions):
        """채팅 기록 저장"""
        try:
            data = {
                "history": history,
                "current_session_id": current_session_id,
                "pinned_sessions": list(pinned_sessions) if isinstance(pinned_sessions, set) else pinned_sessions
            }
            with open("chat_history.json", 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[History Save Error] {e}")

    def load_schedules(self):
        """일정 데이터 로드"""
        if not os.path.exists("schedules.json"):
            return []
        try:
            with open("schedules.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Schedule Load Error] {e}")
            return []

    def save_schedules(self, schedules):
        """일정 데이터 저장"""
        try:
            with open("schedules.json", 'w', encoding='utf-8') as f:
                json.dump(schedules, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Schedule Save Error] {e}")