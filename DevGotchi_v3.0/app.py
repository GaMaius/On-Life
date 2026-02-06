import os
# MediaPipe 로그 숨기기 (반드시 import mediapipe 전에 설정해야 함)
os.environ['GLOG_minloglevel'] = '3'  # 0: INFO, 1: WARNING, 2: ERROR, 3: FATAL

from flask import Flask, render_template, Response, jsonify, request
# import os # Removed duplicate import
from dotenv import load_dotenv # .env 사용을 위해 추가

import cv2
import threading
import time
import json
import random
from config import Config
from game_manager import GameManager
from vision_engine import VisionEngine
from brain import BrainHandler
from data_manager import DataManager
from posture_logger import PostureLogger
from activity_logger import ActivityLogger
import requests
import threading
from say_miniMax import main as voice_main

# .env 파일 로드
load_dotenv()

app = Flask(__name__)

# Singletons A
gm = GameManager()
vision = None # 일단 None으로 설정하여 서버를 먼저 띄웁니다.
brain = BrainHandler()
dm = DataManager()
# Global State for Vision Thread
video_capture = None
latest_frame = None
vision_lock = threading.Lock()

# Posture Status (for frontend UI)
current_posture_score = 0
current_is_eye_closed = False
posture_status_lock = threading.Lock()

# Status State
current_status = "퇴근" # "업무중", "자리비움", "회의중", "퇴근"
is_work_mode = False # Toggle between Idle and Work UI

# Voice Chat Buffer for UI Sync
voice_buffer = []
voice_buffer_lock = threading.Lock()

# Persistent History for the current session
# Persistent History loaded from data_manager
_history_data = dm.load_chat_history()
global_chat_history = _history_data["history"]
current_session_id = _history_data["current_session_id"]
pinned_sessions = set(_history_data["pinned_sessions"])

# Persistent Schedules
global_schedules = dm.load_schedules()
history_lock = threading.Lock()

# 음성 타이머 명령 저장용
pending_timer_command = None  # {"minutes": 5, "auto_start": True}
timer_command_lock = threading.Lock()

# 음성 일정 명령 저장용
pending_schedule_command = None
schedule_command_lock = threading.Lock()

# 최신 날씨 데이터 저장용 (음성 명령으로 업데이트 시 대비)
latest_weather_data = None
weather_data_lock = threading.Lock()

# --- 네이버 뉴스 검색 기능 추가 ---
def get_naver_news(query="오늘의 주요 뉴스"):
    """네이버 API를 사용하여 실시간 뉴스 검색"""
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        return "네이버 API 키가 설정되지 않았습니다."

    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=3&sort=sim"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    
    try:
        res = requests.get(url, timeout=5, headers=headers)
        if res.status_code == 200:
            data = res.json()
            items = data.get('items', [])
            if not items:
                return "관련 뉴스를 찾지 못했습니다."
            
            # HTML 태그 제거 및 제목 추출
            titles = [item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"') for item in items]
            return "최신 뉴스 소식입니다. " + ". ".join(titles)
    except Exception as e:
        print(f"News API Error: {e}")
    
    return "뉴스를 가져오는 중에 오류가 발생했습니다."

@app.route('/api/news/get')
def api_get_news_raw():
    """음성 비서(say_miniMax) 등에서 호출할 수 있는 뉴스 API"""
    news_text = get_naver_news()
    return jsonify({"result": news_text})
# ------------------------------

def add_voice_message(text, sender):
    global current_session_id
    if not text: return # 빈 메시지 방지
    
    # 만약 사용자가 '뉴스'를 물어본다면 자동으로 답변 생성 (선택 사항)
    # 이 로직은 brain.py에서 처리하게 할 수도 있지만, 여기서 직접 가로챌 수도 있습니다.
    
    with voice_buffer_lock:
        voice_buffer.append({"text": text, "type": sender})
    
    with history_lock:
        global_chat_history.append({
            "text": text, 
            "type": sender, 
            "time": time.strftime("%H:%M"),
            "session_id": current_session_id
        })
        dm.save_chat_history(global_chat_history, current_session_id, pinned_sessions)

# 초기 상태: 퇴근
current_status = "퇴근" 
# is_work_mode는 current_status에 따라 동적으로 결정됨

def get_weather():
    """weather_test.py의 정확한 구현 (API 키는 .env에서 로드)"""
    # .env에서 API 키 로드
    api_key = os.getenv("WEATHER_API_KEY")
    
    # 서울 시청 좌표 (weather_test.py와 동일)
    lat = float(os.getenv("WEATHER_LAT", "37.5665"))
    lon = float(os.getenv("WEATHER_LON", "126.9780"))
    
    if not api_key:
        print("[Weather] No API Key found in .env (WEATHER_API_KEY)")
        return {"temp": 0, "condition": "No API Key", "min": 0, "max": 0, "feels_like": 0}
    
    # weather_test.py와 동일한 API 엔드포인트
    # units=metric: 섭씨 온도(°C) 사용
    # lang=kr: 한국어로 결과 받기
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=kr"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # 오류 발생 시 예외 처리
        
        # JSON 데이터 파싱
        data = response.json()
        
        # 필요한 정보 추출 (weather_test.py와 동일)
        location = data['name']  # 지역 이름
        weather_desc = data['weather'][0]['description']  # 날씨 상태
        
        # main 딕셔너리에 기온 정보가 들어있습니다
        temp_current = data['main']['temp']        # 현재 기온
        temp_feels = data['main']['feels_like']    # 체감 온도
        temp_min = data['main']['temp_min']        # 최저 기온
        temp_max = data['main']['temp_max']        # 최고 기온
        
        # 콘솔 출력 (weather_test.py와 동일한 형식)
        print(f"=== {location}의 현재 날씨 ===")
        print(f"날씨 상태: {weather_desc}")
        print(f"현재 기온: {temp_current}°C")
        print(f"체감 온도: {temp_feels}°C")
        print(f"최저/최고: {temp_min}°C / {temp_max}°C")
        
        # API 응답 데이터 반환
        return {
            "temp": int(temp_current),
            "condition": weather_desc,
            "min": int(temp_min),
            "max": int(temp_max),
            "feels_like": int(temp_feels)
        }
        
    except requests.exceptions.RequestException as e:
        print(f"연결 오류 발생: {e}")
        return {"temp": 0, "condition": "연결 오류", "min": 0, "max": 0, "feels_like": 0}
    except KeyError:
        print("데이터를 찾을 수 없습니다. 좌표나 API 키를 확인해주세요.")
        return {"temp": 0, "condition": "데이터 없음", "min": 0, "max": 0, "feels_like": 0}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/status/update', methods=['POST'])
def update_status_btn():
    global current_status
    data = request.json
    current_status = data.get('status', current_status)
    return jsonify({"status": current_status})
    
# toggle_mode endpoint removed (logic unified)

@app.route('/api/weather/update', methods=['POST'])
def update_weather():
    """음성 명령에서 날씨 정보 업데이트"""
    global latest_weather_data
    data = request.json
    with weather_data_lock:
        latest_weather_data = {
            **data,
            "timestamp": time.time()
        }
    print(f"[WEATHER] 음성에서 날씨 업데이트됨: {data.get('city')}")
    return jsonify({"status": "success"})

@app.route('/api/gamestate')
def get_gamestate():
    global latest_weather_data
    
    weather_info = None
    # 5분 이내에 음성으로 업데이트된 최신 날씨가 있으면 사용
    with weather_data_lock:
        if latest_weather_data and time.time() - latest_weather_data.get('timestamp', 0) < 300:
            weather_info = latest_weather_data
            
    if not weather_info:
        weather_info = get_weather()

    # Get posture status
    with posture_status_lock:
        posture_score = current_posture_score
        is_eye_closed = current_is_eye_closed
    
    return jsonify({
        "hp": gm.hp,
        "max_hp": Config.MAX_HP,
        "xp": gm.xp,
        "level": gm.level,
        "happiness": gm.happiness,
        "quests": [q.to_dict() for q in gm.quests],
        "available_quests": [q.to_dict() for q in gm.available_quests],
        "work_mode": (current_status == "업무중"),
        "status": current_status,
        "weather": weather_info,
        "schedules": global_schedules,
        "pinned_sessions": list(pinned_sessions),
        "posture_score": posture_score,
        "is_eye_closed": is_eye_closed
    })

@app.route('/api/quest/accept', methods=['POST'])
def accept_quest():
    """퀘스트 수락 API"""
    data = request.json
    quest_index = data.get('index')
    
    if quest_index is not None:
        accepted = gm.accept_quest(quest_index)
        if accepted:
            return jsonify({"status": "success", "message": "퀘스트 수락됨"})
    
    return jsonify({"status": "fail"}), 400

# Singletons for logging
posture_log_instance = PostureLogger()
activity_log_instance = ActivityLogger()
gm.set_activity_logger(activity_log_instance)

@app.route('/api/posture/stats')
def posture_stats():
    """오늘의 자세 통계"""
    stats = posture_log_instance.get_today_stats()
    return jsonify(stats)

@app.route('/api/posture/history')
def posture_history():
    """날짜별 기록 조회"""
    date = request.args.get('date')
    if date:
        data = posture_log_instance.get_date_data(date)
        return jsonify(data) if data else jsonify({"error": "No data"}), 404
    dates = posture_log_instance.get_all_dates()
    return jsonify({"dates": dates})

@app.route('/api/voice_messages')
def get_voice_messages():
    global voice_buffer
    with voice_buffer_lock:
        messages = list(voice_buffer)
        voice_buffer.clear()
    return jsonify(messages)

# 타이머 API - 음성에서 설정한 타이머를 프론트엔드로 전달
@app.route('/api/timer/set', methods=['POST'])
def set_timer():
    """음성 명령에서 타이머 설정"""
    global pending_timer_command
    data = request.json
    minutes = data.get('minutes', 0)
    auto_start = data.get('auto_start', True)
    mode = data.get('mode', 'down')
    
    with timer_command_lock:
        pending_timer_command = {
            "minutes": minutes,
            "auto_start": auto_start,
            "mode": mode,
            "timestamp": time.time()
        }
    
    print(f"[TIMER] 음성에서 {minutes}분 타이머 설정됨 (mode: {mode}, auto_start: {auto_start})")
    return jsonify({"status": "success", "minutes": minutes})

@app.route('/api/timer/pending')
def get_pending_timer():
    """프론트엔드에서 폴링하여 대기중인 타이머 명령 확인"""
    global pending_timer_command
    with timer_command_lock:
        if pending_timer_command:
            cmd = pending_timer_command
            pending_timer_command = None  # 한 번 읽으면 초기화
            return jsonify({"has_command": True, **cmd})
        return jsonify({"has_command": False})

# 일정 등록 API
@app.route('/api/schedule/set', methods=['POST'])
def set_schedule():
    """음성 명령에서 일정 등록"""
    global pending_schedule_command
    data = request.json
    date_str = data.get('date', time.strftime("%Y-%m-%d"))
    title = data.get('title', '새 일정')
    schedule_time = data.get('time', '')  # 시간 추가
    location = data.get('location', '')  # 장소 추가
    description = data.get('description', '')  # 내용 추가
    
    with schedule_command_lock:
        new_entry = {
            "date": date_str,
            "title": title,
            "type": random.randint(1, 3),
            "time": schedule_time,
            "location": location,
            "description": description
        }
        pending_schedule_command = {
            **new_entry,
            "mode": "add"
        }
    
    # 영구 저장
    global_schedules.append(new_entry)
    dm.save_schedules(global_schedules)
    
    print(f"[SCHEDULE] 음성에서 일정 등록됨: {date_str} - {title}")
    return jsonify({"status": "success"})

@app.route('/api/schedule/delete', methods=['POST'])
def delete_schedule():
    """음성 명령에서 일정 삭제"""
    global pending_schedule_command, global_schedules
    data = request.json
    date_str = data.get('date')
    
    if not date_str:
        return jsonify({"status": "fail", "message": "date is required"}), 400
        
    with schedule_command_lock:
        pending_schedule_command = {
            "date": date_str,
            "mode": "delete"
        }
    
    # 영구 데이터에서 삭제 (날짜 기준)
    original_count = len(global_schedules)
    global_schedules = [s for s in global_schedules if s.get('date') != date_str]
    dm.save_schedules(global_schedules)
    
    print(f"[SCHEDULE] 음성에서 일정 삭제됨: {date_str}")
    return jsonify({"status": "success"})

@app.route('/api/calendar')
def get_calendar():
    """캘린더 데이터 반환 (YYYY-MM-DD 키로 그룹화)"""
    global global_schedules
    
    # 딕셔너리 형태로 변환: "2024-03-15": [{"title": "...", "type": 1, "time": "...", "location": "...", "description": "..."}, ...]
    events_map = {}
    for item in global_schedules:
        d = item['date']
        if d not in events_map:
            events_map[d] = []
        events_map[d].append({
            "title": item.get('title', '제목 없음'),
            "type": item.get('type', 1),  # 1, 2, 3 (color index)
            "time": item.get('time', ''),
            "location": item.get('location', ''),
            "description": item.get('description', '')
        })
        
    return jsonify(events_map)

@app.route('/api/schedule/pending')
def get_pending_schedule():
    """프론트엔드에서 폴링하여 대기중인 일정 명령 확인"""
    global pending_schedule_command
    with schedule_command_lock:
        if pending_schedule_command:
            cmd = pending_schedule_command
            pending_schedule_command = None
            return jsonify({"has_command": True, **cmd})
        return jsonify({"has_command": False})

@app.route('/api/weather/update', methods=['POST'])
def update_weather_voice():
    """음성 명령에서 조회한 최신 날씨 정보를 수신"""
    global latest_weather_data
    data = request.json
    if not data:
        return jsonify({"status": "fail", "message": "no data"}), 400
        
    with weather_data_lock:
        latest_weather_data = {
            "temp": data.get('temp'),
            "condition": data.get('condition'),
            "min": data.get('min'),
            "max": data.get('max'),
            "feels_like": data.get('feels_like'),
            "timestamp": time.time()
        }
    
    print(f"[WEATHER] 최신 날씨 정보 수신 완료: {data.get('temp')}°C")
    return jsonify({"status": "success"})

@app.route('/api/history')
def get_history():
    """세션별로 그룹화된 히스토리 목록과 현재 세션의 메시지 반환"""
    # 1. Group by session_id
    grouped = {}
    
    # 세션 메타데이터 수집 (messages를 순회하며)
    for msg in global_chat_history:
        sid = msg.get('session_id')
        if not sid: continue
        
        if sid not in grouped:
            grouped[sid] = {
                "id": sid,
                "startTime": msg.get('time', ''),
                "preview": msg.get('text', '')[:20] + "..." if msg.get('text') else "내용 없음",
                "isPinned": sid in pinned_sessions, 
                "messages": []
            }
        grouped[sid]["messages"].append(msg)

    # 2. Convert to list for sidebar
    sidebar_list = []
    if current_session_id not in grouped:
         sidebar_list.append({
            "id": current_session_id,
            "startTime": time.strftime("%H:%M"),
            "preview": "새로운 대화",
            "isPinned": current_session_id in pinned_sessions,
            "isActive": True
        })
    
    for sid, data in grouped.items():
        sidebar_list.append({
            "id": sid,
            "startTime": data['startTime'],
            "preview": data['preview'],
            "isPinned": sid in pinned_sessions,
            "isActive": (sid == current_session_id)
        })
    
    # 3. Sort: Pinned first, then Newest ID first
    def sort_key(item):
        return (
            0 if item['isPinned'] else 1, 
            -item['id'] 
        )
    sidebar_list.sort(key=sort_key)

    # 4. Get Current Session Messages for Main View
    current_messages = grouped.get(current_session_id, {}).get('messages', [])

    return jsonify({
        "sidebar": sidebar_list,
        "current_messages": current_messages,
        "current_session_id": current_session_id
    })

@app.route('/api/history/delete', methods=['POST'])
def delete_history():
    """특정 세션의 히스토리를 삭제"""
    global global_chat_history, pinned_sessions
    data = request.json
    session_id = data.get('session_id')
    
    if session_id is None:
        return jsonify({"error": "session_id required"}), 400
    
    with history_lock:
        global_chat_history = [msg for msg in global_chat_history if msg.get('session_id') != session_id]
        pinned_sessions.discard(session_id)
        dm.save_chat_history(global_chat_history, current_session_id, pinned_sessions)
    
    return jsonify({"status": "success", "deleted_session_id": session_id})

@app.route('/api/history/pin', methods=['POST'])
def pin_history():
    """특정 세션을 고정/고정해제"""
    global pinned_sessions
    data = request.json
    session_id = data.get('session_id')
    pin = data.get('pin', True)  
    
    if session_id is None:
        return jsonify({"error": "session_id required"}), 400
    
    with history_lock:
        if pin:
            pinned_sessions.add(session_id)
        else:
            pinned_sessions.discard(session_id)
        dm.save_chat_history(global_chat_history, current_session_id, pinned_sessions)
    
    return jsonify({"status": "success", "session_id": session_id, "pinned": pin})

@app.route('/api/chat/reset', methods=['POST', 'GET'])
def reset_chat():
    global current_session_id
    print("\n" + "="*30)
    print(f"[DEBUG] /api/chat/reset 호출됨!")
    
    try:
        with voice_buffer_lock:
            voice_buffer.clear()
        
        with history_lock:
            current_session_id += 1
            print(f"[DEBUG] 새 세션 ID 할당: {current_session_id}")
            dm.save_chat_history(global_chat_history, current_session_id, pinned_sessions)

        print("="*30 + "\n")
        return jsonify({
            "status": "success", 
            "new_session_id": current_session_id
        })
    except Exception as e:
        print(f"[ERROR] 리셋 중 오류 발생: {e}") 
        return jsonify({"error": str(e)}), 500

@app.route('/api/session/switch', methods=['POST'])
def switch_session():
    global current_session_id
    data = request.json
    target_id = data.get('session_id')
    
    if target_id is None:
        return jsonify({"error": "session_id required"}), 400
        
    with history_lock:
        current_session_id = int(target_id)
    
    print(f"[DEBUG] 세션 전환됨: {current_session_id}")
    return jsonify({"status": "success", "current_session_id": current_session_id})

# AI Chat Endpoint
@app.route('/api/chat', methods=['POST'])
def chat():
    global current_session_id
    data = request.json
    user_msg = data.get('message', '')
    history = data.get('history', []) 
    
    # --- 뉴스 질의 확인 로직 추가 ---
    # --- 뉴스 질의 확인 로직 (LLM Context Injection) ---
    if "뉴스" in user_msg or "소식" in user_msg:
        print("[App] News keyword detected. Fetching Naver News...")
        news_data = get_naver_news() # Returns string "최신 뉴스 소식입니다. ..."
        
        # LLM에게 주입할 시스템 메시지 생성
        system_injection = f"[System Info] Real-time News Data: {news_data}. Please explain this to the user."
        
        # History에 기록 (User msg는 보여주되, System Info는 내부적으로 처리하거나 History에 포함)
        # 여기서는 History에 포함하여 문맥 유지
        updated_history = history + [
            {"role": "user", "content": user_msg},
            {"role": "system", "content": system_injection}
        ]
        
        # 일반 Chat 로직으로 위임 (단, history를 조작함)
        result = {}
        event = threading.Event()
        
        def cb(text, task, thought):
            result['text'] = text
            result['task'] = task
            result['thought'] = thought
            event.set()
            
        brain.chat(updated_history, gm.level, cb)
        event.wait(timeout=30)
        
        if result.get('text'):
             with history_lock:
                global_chat_history.append({"text": user_msg, "type": "user", "time": time.strftime("%H:%M"), "session_id": current_session_id})
                global_chat_history.append({"text": result['text'], "type": "ai", "time": time.strftime("%H:%M"), "session_id": current_session_id})
                dm.save_chat_history(global_chat_history, current_session_id, pinned_sessions)
        
        return jsonify(result)
    # -----------------------------
    # -----------------------------

    user_msg = data.get('message')
    history = data.get('history', []) 
    
    result = {}
    event = threading.Event()
    
    def cb(text, task, thought):
        result['text'] = text
        result['task'] = task
        result['thought'] = thought
        event.set()
        
    brain.chat(history + [{"role": "user", "content": user_msg}], gm.level, cb)
    event.wait(timeout=30)
    
    if result.get('text'):
        with history_lock:
            global_chat_history.append({
                "text": user_msg, 
                "type": "user", 
                "time": time.strftime("%H:%M"),
                "session_id": current_session_id
            })
            global_chat_history.append({
                "text": result['text'],
                "type": "ai",
                "time": time.strftime("%H:%M"),
                "session_id": current_session_id
            })
            dm.save_chat_history(global_chat_history, current_session_id, pinned_sessions)
        
    return jsonify(result)

@app.route('/api/activity/stats')
def activity_stats():
    """오늘의 활동 통계"""
    stats = activity_log_instance.get_today_stats()
    return jsonify(stats)

@app.route('/api/activity/insights')
def activity_insights():
    """활동 인사이트"""
    insights = activity_log_instance.get_today_insights()
    return jsonify(insights)

@app.route('/api/activity/log_timer', methods=['POST'])
def log_timer():
    """타이머 이벤트 로깅"""
    data = request.json
    event_type = data.get('type')
    duration = data.get('duration', 0)
    activity_log_instance.log_timer_event(event_type, duration)
    return jsonify({"status": "success"})

@app.route('/api/activity/full_log')
def activity_full_log():
    """오늘의 전체 활동 로그 (상세)"""
    # Force save/update before reading to get latest in-memory events
    activity_log_instance._save_data() 
    return jsonify(activity_log_instance.today_data)

@app.route('/stats')
def stats_page():
    return render_template('stats.html')

def vision_loop():
    global video_capture, vision, current_posture_score, current_is_eye_closed
    cap = cv2.VideoCapture(0)
    posture_log = PostureLogger()
    activity_log = activity_log_instance  # 전역 인스턴스 사용 (데이터 공유)
    
    # 중복 로깅 방지용 쿨다운
    last_turtle_log = 0
    last_eye_log = 0
    LOG_COOLDOWN = 3  # 3초 쿨다운
    
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(1)
            continue
            
        if vision:
            score, drowsy, smile, closed, landmarks = vision.analyze_frame(frame)
            # Config.POSTURE_THRESHOLD (0.18) 사용
            is_bad = score > Config.POSTURE_THRESHOLD
            gm.update(is_bad, drowsy, True)
            
            # Update global posture status for frontend
            with posture_status_lock:
                current_posture_score = score
                current_is_eye_closed = closed
            
            # 업무중 상태일 때만 로깅
            if current_status == "업무중":
                current_time = time.time()
                
                # 거북목 감지 로깅 (Config.POSTURE_THRESHOLD 사용)
                if is_bad and (current_time - last_turtle_log) > LOG_COOLDOWN:
                    posture_log.log_turtle_neck()
                    activity_log.log_turtle_neck()  # 통합 로깅
                    last_turtle_log = current_time
                
                # 눈감음 감지 로깅
                if closed and (current_time - last_eye_log) > LOG_COOLDOWN:
                    posture_log.log_eye_closed()
                    activity_log.log_eye_closed()  # 통합 로깅
                    last_eye_log = current_time
        
        with vision_lock:
            global latest_frame
            flag, encoded_image = cv2.imencode(".jpg", frame)
            if flag:
                latest_frame = encoded_image.tobytes()
        
        time.sleep(0.03)

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            with vision_lock:
                if latest_frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')
            time.sleep(0.1)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # 1. Vision Thread Start
    if vision is None:
        try:
            vision = VisionEngine()
        except Exception as e:
            print(f"[ERROR] Vision Init Failed: {e}")

    t_vision = threading.Thread(target=vision_loop, daemon=True)
    t_vision.start()
    print("[SYSTEM] 비전 엔진 스레드 시작됨")
    
    # 2. Voice Thread Start
    t_voice = threading.Thread(target=voice_main, args=(add_voice_message,), daemon=True)
    t_voice.start()
    print("[SYSTEM] 음성 인식(MiniMax) 스레드 시작됨")
    
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
