# posture_logger.py
"""거북목/눈감음 인식 기록 및 통계 모듈"""

import os
import json
from datetime import datetime
from collections import defaultdict

class PostureLogger:
    def __init__(self, data_dir="./data/posture_logs"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.today_data = self._load_today_data()
    
    def _get_today_filename(self):
        """오늘 날짜의 파일명 반환"""
        today = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.data_dir, f"posture_{today}.json")
    
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
            "turtle_neck": {
                "count": 0,
                "events": [],  # [{"time": "10:30:15", "duration_sec": 5}]
                "hourly_freq": {}  # {"10": 3, "11": 5}
            },
            "eye_closed": {
                "count": 0,
                "events": [],
                "hourly_freq": {}
            },
            "summary": {
                "total_detections": 0,
                "peak_hour": None,
                "avg_per_hour": 0
            }
        }
    
    def _save_data(self):
        """데이터 저장"""
        # 날짜가 바뀌었으면 새로 시작
        today = datetime.now().strftime("%Y-%m-%d")
        if self.today_data["date"] != today:
            self.today_data = self._load_today_data()
        
        # 통계 업데이트
        self._update_summary()
        
        filepath = self._get_today_filename()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.today_data, f, ensure_ascii=False, indent=2)
    
    def _update_summary(self):
        """통계 요약 업데이트"""
        turtle_count = self.today_data["turtle_neck"]["count"]
        eye_count = self.today_data["eye_closed"]["count"]
        total = turtle_count + eye_count
        
        # 시간대별 빈도 합산
        combined_freq = defaultdict(int)
        for hour, count in self.today_data["turtle_neck"]["hourly_freq"].items():
            combined_freq[hour] += count
        for hour, count in self.today_data["eye_closed"]["hourly_freq"].items():
            combined_freq[hour] += count
        
        # 피크 시간대 찾기
        peak_hour = None
        if combined_freq:
            peak_hour = max(combined_freq, key=combined_freq.get)
        
        # 평균 시간당 감지 횟수
        hours_active = len(combined_freq) if combined_freq else 1
        avg_per_hour = round(total / hours_active, 2)
        
        self.today_data["summary"] = {
            "total_detections": total,
            "turtle_neck_count": turtle_count,
            "eye_closed_count": eye_count,
            "peak_hour": peak_hour,
            "avg_per_hour": avg_per_hour,
            "hourly_distribution": dict(combined_freq)
        }
    
    def log_turtle_neck(self, duration_sec=None):
        """거북목 감지 기록"""
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        hour = now.strftime("%H")
        
        self.today_data["turtle_neck"]["count"] += 1
        self.today_data["turtle_neck"]["events"].append({
            "time": time_str,
            "duration_sec": duration_sec
        })
        
        # 시간대별 빈도 업데이트
        freq = self.today_data["turtle_neck"]["hourly_freq"]
        freq[hour] = freq.get(hour, 0) + 1
        
        self._save_data()
        print(f"[PostureLog] 거북목 감지 기록: {time_str}")
    
    def log_eye_closed(self, duration_sec=None):
        """눈감음 감지 기록"""
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        hour = now.strftime("%H")
        
        self.today_data["eye_closed"]["count"] += 1
        self.today_data["eye_closed"]["events"].append({
            "time": time_str,
            "duration_sec": duration_sec
        })
        
        # 시간대별 빈도 업데이트
        freq = self.today_data["eye_closed"]["hourly_freq"]
        freq[hour] = freq.get(hour, 0) + 1
        
        self._save_data()
        print(f"[PostureLog] 눈감음 감지 기록: {time_str}")
    
    def get_today_stats(self):
        """오늘의 통계 반환"""
        self._update_summary()
        return self.today_data["summary"]
    
    def get_all_dates(self):
        """기록된 모든 날짜 목록 반환"""
        files = os.listdir(self.data_dir)
        dates = []
        for f in files:
            if f.startswith("posture_") and f.endswith(".json"):
                date = f.replace("posture_", "").replace(".json", "")
                dates.append(date)
        return sorted(dates, reverse=True)
    
    def get_date_data(self, date_str):
        """특정 날짜의 데이터 반환"""
        filepath = os.path.join(self.data_dir, f"posture_{date_str}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
