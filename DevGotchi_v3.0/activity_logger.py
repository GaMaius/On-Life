# activity_logger.py
"""통합 활동 로깅 시스템 - 자세, 퀘스트, HP, 세션 정보 통합 기록"""

import os
import json
from datetime import datetime
from collections import defaultdict

class ActivityLogger:
    def __init__(self, data_dir="./data/activity_logs"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.session_data = self._init_session()
        self.today_data = self._load_today_data()
    
    def _init_session(self):
        """현재 세션 초기화"""
        return {
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration_minutes": 0,
            "events": []
        }
    
    def _get_today_filename(self):
        """오늘 날짜의 파일명 반환"""
        today = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.data_dir, f"activity_{today}.json")
    
    def _load_today_data(self):
        """오늘의 데이터 로드 또는 초기화"""
        filepath = self._get_today_filename()
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # 초기 데이터 구조
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "sessions": [],
            "posture_detections": {
                "turtle_neck": {
                    "count": 0,
                    "events": [],
                    "hourly_freq": {}
                },
                "eye_closed": {
                    "count": 0,
                    "events": [],
                    "hourly_freq": {}
                }
            },
            "quests": {
                "accepted": [],
                "completed": [],
                "failed": []
            },
            "hp_changes": [],
            "summary": {
                "total_work_time_minutes": 0,
                "total_detections": 0,
                "quests_completed": 0,
                "avg_hp": 0,
                "peak_activity_hour": None
            }
        }
    
    def _save_data(self):
        """데이터 저장"""
        # 날짜가 바뀌었으면 새로 시작
        today = datetime.now().strftime("%Y-%m-%d")
        if self.today_data["date"] != today:
            self._end_session()
            self.today_data = self._load_today_data()
            self.session_data = self._init_session()
        
        # 통계 업데이트
        self._update_summary()
        
        filepath = self._get_today_filename()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.today_data, f, ensure_ascii=False, indent=2)
    
    def _update_summary(self):
        """통계 요약 업데이트"""
        posture = self.today_data["posture_detections"]
        turtle_count = posture["turtle_neck"]["count"]
        eye_count = posture["eye_closed"]["count"]
        
        # 시간대별 빈도 합산
        combined_freq = defaultdict(int)
        for hour, count in posture["turtle_neck"]["hourly_freq"].items():
            combined_freq[hour] += count
        for hour, count in posture["eye_closed"]["hourly_freq"].items():
            combined_freq[hour] += count
        
        # 피크 시간대
        peak_hour = None
        if combined_freq:
            peak_hour = max(combined_freq, key=combined_freq.get)
        
        # 총 업무 시간
        total_minutes = sum(s.get("duration_minutes", 0) for s in self.today_data["sessions"])
        
        # 평균 HP (HP 변경 이벤트 기반)
        hp_values = [e["hp_after"] for e in self.today_data["hp_changes"] if "hp_after" in e]
        avg_hp = round(sum(hp_values) / len(hp_values), 1) if hp_values else 0
        
        self.today_data["summary"] = {
            "total_work_time_minutes": total_minutes,
            "total_detections": turtle_count + eye_count,
            "turtle_neck_count": turtle_count,
            "eye_closed_count": eye_count,
            "quests_completed": len(self.today_data["quests"]["completed"]),
            "quests_failed": len(self.today_data["quests"]["failed"]),
            "avg_hp": avg_hp,
            "peak_activity_hour": peak_hour,
            "hourly_distribution": dict(combined_freq)
        }
    
    # ========== 자세 감지 로깅 ==========
    def log_turtle_neck(self, duration_sec=None):
        """거북목 감지 기록"""
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        hour = now.strftime("%H")
        
        event = {
            "time": time_str,
            "duration_sec": duration_sec
        }
        
        self.today_data["posture_detections"]["turtle_neck"]["count"] += 1
        self.today_data["posture_detections"]["turtle_neck"]["events"].append(event)
        
        freq = self.today_data["posture_detections"]["turtle_neck"]["hourly_freq"]
        freq[hour] = freq.get(hour, 0) + 1
        
        # 세션 이벤트 추가
        self.session_data["events"].append({
            "type": "turtle_neck",
            "time": time_str,
            "data": event
        })
        
        self._save_data()
        print(f"[ActivityLog] 거북목 감지: {time_str}")
    
    def log_eye_closed(self, duration_sec=None):
        """눈감음 감지 기록"""
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        hour = now.strftime("%H")
        
        event = {
            "time": time_str,
            "duration_sec": duration_sec
        }
        
        self.today_data["posture_detections"]["eye_closed"]["count"] += 1
        self.today_data["posture_detections"]["eye_closed"]["events"].append(event)
        
        freq = self.today_data["posture_detections"]["eye_closed"]["hourly_freq"]
        freq[hour] = freq.get(hour, 0) + 1
        
        # 세션 이벤트 추가
        self.session_data["events"].append({
            "type": "eye_closed",
            "time": time_str,
            "data": event
        })
        
        self._save_data()
        print(f"[ActivityLog] 눈감음 감지: {time_str}")
    
    # ========== 퀘스트 로깅 ==========
    def log_quest_accepted(self, quest_name, quest_type, target_duration, reward_xp):
        """퀘스트 수락 기록"""
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        
        quest_data = {
            "name": quest_name,
            "type": quest_type,
            "target_duration": target_duration,
            "reward_xp": reward_xp,
            "accepted_at": time_str
        }
        
        self.today_data["quests"]["accepted"].append(quest_data)
        
        # 세션 이벤트
        self.session_data["events"].append({
            "type": "quest_accepted",
            "time": time_str,
            "data": quest_data
        })
        
        self._save_data()
        print(f"[ActivityLog] 퀘스트 수락: {quest_name} at {time_str}")
    
    def log_quest_completed(self, quest_name, quest_type, actual_duration, reward_xp):
        """퀘스트 완료 기록"""
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        
        quest_data = {
            "name": quest_name,
            "type": quest_type,
            "actual_duration": actual_duration,
            "reward_xp": reward_xp,
            "completed_at": time_str
        }
        
        self.today_data["quests"]["completed"].append(quest_data)
        
        # 세션 이벤트
        self.session_data["events"].append({
            "type": "quest_completed",
            "time": time_str,
            "data": quest_data
        })
        
        self._save_data()
        print(f"[ActivityLog] 퀘스트 완료: {quest_name} at {time_str}")
    
    def log_quest_failed(self, quest_name, quest_type, reason="timeout"):
        """퀘스트 실패 기록"""
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        
        quest_data = {
            "name": quest_name,
            "type": quest_type,
            "reason": reason,
            "failed_at": time_str
        }
        
        self.today_data["quests"]["failed"].append(quest_data)
        
        self._save_data()
        print(f"[ActivityLog] 퀘스트 실패: {quest_name} ({reason})")
    
    # ========== 타이머 로깅 ==========
    def log_timer_event(self, event_type, duration_seconds=0):
        """타이머 이벤트 기록 (start, complete, cancel)"""
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        
        event = {
            "type": event_type,  # 'start', 'complete', 'cancel'
            "time": time_str,
            "duration_seconds": duration_seconds
        }
        
        if "timer_usage" not in self.today_data:
            self.today_data["timer_usage"] = []
            
        self.today_data["timer_usage"].append(event)
        
        # 세션 이벤트
        self.session_data["events"].append({
            "type": "timer_event",
            "time": time_str,
            "data": event
        })
        
        self._save_data()
        print(f"[ActivityLog] 타이머 이벤트: {event_type} ({duration_seconds}s)")
    
    # ========== HP 변화 로깅 ==========
    def log_hp_change(self, hp_before, hp_after, reason, amount):
        """HP 변화 기록"""
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        
        hp_event = {
            "time": time_str,
            "hp_before": round(hp_before, 1),
            "hp_after": round(hp_after, 1),
            "change": round(amount, 1),
            "reason": reason
        }
        
        self.today_data["hp_changes"].append(hp_event)
        
        # 세션 이벤트
        self.session_data["events"].append({
            "type": "hp_change",
            "time": time_str,
            "data": hp_event
        })
        
        self._save_data()
        # HP 변화는 너무 자주 발생하므로 터미널 출력 생략
    
    # ========== 세션 관리 ==========
    def _end_session(self):
        """현재 세션 종료 및 저장"""
        if self.session_data["events"]:
            start = datetime.fromisoformat(self.session_data["start_time"])
            end = datetime.now()
            self.session_data["end_time"] = end.isoformat()
            self.session_data["duration_minutes"] = round((end - start).total_seconds() / 60, 1)
            
            self.today_data["sessions"].append(self.session_data.copy())
            print(f"[ActivityLog] 세션 종료: {self.session_data['duration_minutes']}분")
    
    # ========== 통계 조회 ==========
    def get_today_stats(self):
        """오늘의 통계 반환"""
        self._update_summary()
        return self.today_data["summary"]
    
    def get_today_insights(self):
        """오늘의 인사이트 생성"""
        self._update_summary()
        summary = self.today_data["summary"]
        
        insights = []
        
        # 자세 관련 인사이트
        if summary["turtle_neck_count"] > 10:
            insights.append({
                "type": "warning",
                "icon": "🐢",
                "message": f"오늘 거북목이 {summary['turtle_neck_count']}회 감지되었습니다. 모니터 높이를 조정해보세요."
            })
        
        if summary["eye_closed_count"] > 5:
            insights.append({
                "type": "warning",
                "icon": "😴",
                "message": f"졸음 감지 {summary['eye_closed_count']}회. 충분한 휴식이 필요합니다."
            })
        
        # 퀘스트 관련 인사이트
        if summary["quests_completed"] > 0:
            insights.append({
                "type": "success",
                "icon": "🎯",
                "message": f"오늘 {summary['quests_completed']}개의 퀘스트를 완료했습니다!"
            })
        
        # 피크 시간대
        if summary["peak_activity_hour"]:
            insights.append({
                "type": "info",
                "icon": "📊",
                "message": f"{summary['peak_activity_hour']}시에 가장 많은 활동이 감지되었습니다."
            })
        
        # HP 관련
        if summary["avg_hp"] < 50:
            insights.append({
                "type": "danger",
                "icon": "💔",
                "message": f"평균 HP가 {summary['avg_hp']}로 낮습니다. 휴식이 필요합니다!"
            })
        
        return insights
    
    def get_all_dates(self):
        """기록된 모든 날짜 목록 반환"""
        files = os.listdir(self.data_dir)
        dates = []
        for f in files:
            if f.startswith("activity_") and f.endswith(".json"):
                date = f.replace("activity_", "").replace(".json", "")
                dates.append(date)
        return sorted(dates, reverse=True)
    
    def get_date_data(self, date_str):
        """특정 날짜의 데이터 반환"""
        filepath = os.path.join(self.data_dir, f"activity_{date_str}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
