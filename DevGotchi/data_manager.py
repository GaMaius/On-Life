import json
import os
from datetime import datetime
from collections import Counter

LOG_FILE = "user_behavior_logs.json"

class DataManager:
    def __init__(self):
        # 로그 파일이 없으면 초기화
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
        self.session_id = f"session_{int(datetime.now().timestamp())}"

    def _save_log(self, entry):
        """로그를 JSON 파일에 저장"""
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            logs.append(entry)
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Log Error] {e}")

    # --- [가이드라인 데이터 유형 구현] ---

    def log_interaction(self, event_name, detail, page):
        """Type A. 사용자 상호작용 (User Interaction)"""
        entry = {
            "type": "A_Interaction",
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "event_name": event_name, # 예: Button_Click
            "detail": detail,         # 예: Schedule_Check
            "page": page,
            "device_id": "mirror_dev_01"
        }
        self._save_log(entry)

    def log_context(self, environment_data):
        """Type B. 컨텍스트 데이터 (Context)"""
        entry = {
            "type": "B_Context",
            "timestamp": datetime.now().isoformat(),
            "time_bucket": datetime.now().strftime("%H"), # 시간대 분석용
            "environment": environment_data # 예: {"weather": "Sunny", "posture": "Good"}
        }
        self._save_log(entry)

    def log_telemetry(self, latency_ms, success, error_msg=""):
        """Type C. 시스템 상태/품질 (Telemetry)"""
        entry = {
            "type": "C_Telemetry",
            "timestamp": datetime.now().isoformat(),
            "latency_ms": latency_ms,
            "success": success,
            "error_msg": error_msg
        }
        self._save_log(entry)

    def log_llm(self, tokens, task_type):
        """Type D. LLM 사용 로그"""
        entry = {
            "type": "D_LLM_Log",
            "timestamp": datetime.now().isoformat(),
            "tokens": tokens,
            "task_type": task_type # 예: Conversation, Coaching
        }
        self._save_log(entry)

    # --- [인포그래픽용 데이터 분석] ---
    def get_analysis(self):
        """저장된 로그를 분석하여 그래프용 데이터로 변환"""
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except:
            return {}, [], []

        # 1. 페이지 방문 통계 (Bar Chart)
        page_visits = [log['page'] for log in logs if log['type'] == 'A_Interaction']
        page_counts = dict(Counter(page_visits))

        # 2. 시스템 지연 시간 추이 (Line Chart)
        latencies = [log['latency_ms'] for log in logs if log['type'] == 'C_Telemetry']
        
        # 3. 시간대별 활동량 (Pie/Text)
        active_hours = [log['time_bucket'] for log in logs if 'time_bucket' in log]
        
        return page_counts, latencies, active_hours