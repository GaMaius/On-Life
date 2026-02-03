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
    def log_interaction(self, event, detail):
        self._save({
            "type": "A_Interaction",
            "ts": datetime.now().isoformat(),
            "session": self.session_id,
            "event": event,
            "detail": detail
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