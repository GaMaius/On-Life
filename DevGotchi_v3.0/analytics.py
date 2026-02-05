# analytics.py
import time
from collections import defaultdict, deque
import json

class Analytics:
    """데이터 수집 및 분석 (Event/Context/Telemetry)"""
    
    def __init__(self):
        # A. 사용자 상호작용 이벤트 (Event)
        self.events = deque(maxlen=1000)  # Last 1000 events
        
        # B. 컨텍스트 데이터 (Context)
        self.context_snapshots = deque(maxlen=500)
        
        # C. 시스템 상태/품질 (Telemetry)
        self.telemetry = {
            "api_calls": deque(maxlen=100),
            "errors": deque(maxlen=50)
        }
        
        # D. LLM 사용 로그 (Currently minimal)
        self.llm_logs = deque(maxlen=100)
        
        # Session tracking
        self.session_start = time.time()
        self.session_id = str(int(self.session_start))
        
    # --- A. Event Tracking ---
    def log_event(self, event_name, metadata=None):
        """사용자 행동 로그 (버튼 클릭, 퀘스트 수락 등)"""
        event = {
            "event_name": event_name,
            "timestamp": time.time(),
            "session_id": self.session_id,
            "metadata": metadata or {}
        }
        self.events.append(event)
    
    # --- B. Context Tracking ---
    def log_context(self, posture_state, hp, level, time_bucket=None):
        """실시간 컨텍스트 스냅샷 (자세, HP, 시간대 등)"""
        if time_bucket is None:
            hour = time.localtime().tm_hour
            if 6 <= hour < 12:
                time_bucket = "morning"
            elif 12 <= hour < 18:
                time_bucket = "afternoon"
            elif 18 <= hour < 22:
                time_bucket = "evening"
            else:
                time_bucket = "night"
        
        snapshot = {
            "timestamp": time.time(),
            "time_bucket": time_bucket,
            "posture_state": posture_state,  # "good" or "bad"
            "hp": hp,
            "level": level
        }
        self.context_snapshots.append(snapshot)
    
    # --- C. Telemetry (API/System) ---
    def log_api_call(self, request_id, latency_ms, success=True, error_msg=None):
        """API 호출 로그 (주로 LLM Chat)"""
        log = {
            "request_id": request_id,
            "timestamp": time.time(),
            "latency_ms": latency_ms,
            "success": success,
            "error_message": error_msg
        }
        self.telemetry["api_calls"].append(log)
        if not success:
            self.telemetry["errors"].append(log)
    
    # --- D. LLM Usage ---
    def log_llm_usage(self, prompt_tokens, completion_tokens, response_time_ms):
        """LLM 사용량 로그"""
        log = {
            "timestamp": time.time(),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "response_time_ms": response_time_ms
        }
        self.llm_logs.append(log)
    
    # --- Analytics Queries ---
    def get_posture_timeline(self, hours=1):
        """최근 N시간 동안 자세 상태 타임라인"""
        now = time.time()
        cutoff = now - (hours * 3600)
        
        timeline = [s for s in self.context_snapshots if s["timestamp"] > cutoff]
        
        # 시간대별 그룹화 (10분 단위)
        buckets = defaultdict(lambda: {"good": 0, "bad": 0})
        for snap in timeline:
            t = snap["timestamp"]
            bucket_key = int((t - cutoff) // 600)  # 10-min buckets
            state = snap["posture_state"]
            buckets[bucket_key][state] += 1
        
        return dict(buckets)
    
    def get_event_counts(self):
        """이벤트 유형별 카운트"""
        counts = defaultdict(int)
        for event in self.events:
            counts[event["event_name"]] += 1
        return dict(counts)
    
    def get_api_stats(self):
        """API 성능 통계"""
        if not self.telemetry["api_calls"]:
            return {"avg_latency": 0, "success_rate": 1.0, "total_calls": 0}
        
        calls = list(self.telemetry["api_calls"])
        latencies = [c["latency_ms"] for c in calls]
        successes = sum(1 for c in calls if c["success"])
        
        return {
            "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
            "success_rate": successes / len(calls) if calls else 1.0,
            "total_calls": len(calls)
        }
    
    def get_session_duration(self):
        """현재 세션 시간 (분)"""
        return (time.time() - self.session_start) / 60.0
    
    def to_json(self):
        """전체 분석 데이터를 JSON으로"""
        return {
            "posture_timeline": self.get_posture_timeline(),
            "event_counts": self.get_event_counts(),
            "api_stats": self.get_api_stats(),
            "session_duration_minutes": self.get_session_duration(),
            "total_events": len(self.events)
        }
