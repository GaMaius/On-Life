import os
# MediaPipe 로그 숨기기 - Removed as Vision is removed
# os.environ['GLOG_minloglevel'] = '3' 

from flask import Flask, render_template, Response, jsonify, request
from dotenv import load_dotenv 

import threading
import time
import json
import random
from config import Config
from game_manager import GameManager
# from vision_engine import VisionEngine # Removed
from brain import BrainHandler
from data_manager import DataManager
import requests
from say_miniMax import main as voice_main, speak

# .env 파일 로드
load_dotenv()

app = Flask(__name__)

# Singletons A
gm = GameManager()
# vision = None # Removed
brain = BrainHandler()
dm = DataManager()
# Global State for Vision Thread - Removed
# video_capture = None
# latest_frame = None
# vision_lock = threading.Lock()

# Status State
current_status = "업무중" # "업무중", "자리비움", "회의중", "퇴근"
is_work_mode = False # Toggle between Idle and Work UI

# Voice Chat Buffer for UI Sync
voice_buffer = []
voice_buffer_lock = threading.Lock()

# Persistent History for the current session
_history_data = dm.load_chat_history()
global_chat_history = _history_data["history"]
current_session_id = _history_data["current_session_id"]
pinned_sessions = set(_history_data["pinned_sessions"])

# Persistent Schedules
global_schedules = dm.load_schedules()
history_lock = threading.Lock()

# 음성 타이머 명령 저장용
pending_timer_command = None  
timer_command_lock = threading.Lock()

# 음성 일정 명령 저장용
pending_schedule_command = None
schedule_command_lock = threading.Lock()

# 최신 날씨 데이터 저장용 (음성 명령으로 업데이트 시 대비)
latest_weather_data = None
weather_data_lock = threading.Lock()

# --- 네이버 뉴스 검색 기능 ---
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
    if not text: return 
    
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

def get_weather():
    api_key = os.getenv("WEATHER_API_KEY")
    lat, lon = 37.5665, 126.9780 
    
    if not api_key:
        return {"temp": 0, "condition": "No Key", "comparison": 0}

    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=kr"
    
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return {
                "temp": int(data['main']['temp']),
                "condition": data['weather'][0]['description'],
                "min": int(data['main']['temp_min']),
                "max": int(data['main']['temp_max']),
                "feels_like": int(data['main']['feels_like'])
            }
    except Exception as e:
        print(f"Weather Error: {e}")
    
    return {"temp": 0, "condition": "Error", "comparison": 0}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/status/update', methods=['POST'])
def update_status_btn():
    global current_status, is_work_mode
    data = request.json
    current_status = data.get('status', current_status)
    
    # [수정] 상태에 따라 work_mode 동기화 
    is_work_mode = (current_status == "업무중")
    
    return jsonify({"status": current_status, "work_mode": is_work_mode})

# Removed auto_calibrate_after_delay (Vision dependency)

@app.route('/api/mode/toggle', methods=['POST'])
def toggle_mode():
    global is_work_mode
    data = request.json
    old_mode = is_work_mode
    is_work_mode = data.get('work_mode', False)
    
    # Removed calibration trigger
        
    return jsonify({"work_mode": is_work_mode})

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

    return jsonify({
        "hp": gm.hp,
        "max_hp": Config.MAX_HP,
        "xp": gm.xp,
        "level": gm.level,
        "happiness": gm.happiness,
        "quests": [q.to_dict() for q in gm.quests],
        "work_mode": is_work_mode,
        "status": current_status,
        "weather": weather_info,
        "schedules": global_schedules,
        "pinned_sessions": list(pinned_sessions),
        "is_calibrating": False # Removed vision calibration
    })

@app.route('/api/voice_messages')
def get_voice_messages():
    global voice_buffer
    with voice_buffer_lock:
        messages = list(voice_buffer)
        voice_buffer.clear()
    return jsonify(messages)

# 타이머 API 
@app.route('/api/timer/set', methods=['POST'])
def set_timer():
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
    global pending_timer_command
    with timer_command_lock:
        if pending_timer_command:
            cmd = pending_timer_command
            pending_timer_command = None  
            return jsonify({"has_command": True, **cmd})
        return jsonify({"has_command": False})

# 일정 등록 API
@app.route('/api/schedule/set', methods=['POST'])
def set_schedule():
    global pending_schedule_command
    data = request.json
    date_str = data.get('date', time.strftime("%Y-%m-%d"))
    title = data.get('title', '새 일정')
    
    with schedule_command_lock:
        new_entry = {
            "date": date_str,
            "title": title,
            "type": random.randint(1, 3)
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
    global global_schedules
    
    events_map = {}
    for item in global_schedules:
        d = item['date']
        if d not in events_map:
            events_map[d] = []
        events_map[d].append({
            "title": item['title'],
            "type": item['type'] 
        })
        
    return jsonify(events_map)

@app.route('/api/schedule/pending')
def get_pending_schedule():
    global pending_schedule_command
    with schedule_command_lock:
        if pending_schedule_command:
            cmd = pending_schedule_command
            pending_schedule_command = None
            return jsonify({"has_command": True, **cmd})
        return jsonify({"has_command": False})

@app.route('/api/weather/update_voice', methods=['POST']) # Endpoint name fix to avoid conflict if any
def update_weather_voice():
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
    # 1. Group by session_id
    grouped = {}
    
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
    
    # 3. Sort
    def sort_key(item):
        return (
            0 if item['isPinned'] else 1, 
            -item['id'] 
        )
    sidebar_list.sort(key=sort_key)

    # 4. Get Current Session Messages
    current_messages = grouped.get(current_session_id, {}).get('messages', [])

    return jsonify({
        "sidebar": sidebar_list,
        "current_messages": current_messages,
        "current_session_id": current_session_id
    })

@app.route('/api/history/delete', methods=['POST'])
def delete_history():
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
    
    if "뉴스" in user_msg or "소식" in user_msg:
        print("[App] News keyword detected. Fetching Naver News...")
        news_data = get_naver_news() 
        
        system_injection = f"[System Info] Real-time News Data: {news_data}. Please explain this to the user."
        
        updated_history = history + [
            {"role": "user", "content": user_msg},
            {"role": "system", "content": system_injection}
        ]
        
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

# Vision Loop Removed

# --- 자동 브리핑 로직 ---
def run_boot_briefing():
    """부팅 10초 후 날씨와 일정을 분석하여 음성으로 브리핑"""
    print("[SYSTEM] 부팅 브리핑 대기 중 (10초)...")
    time.sleep(10)  # 시스템 안정화를 위한 10초 대기
    
    # 1. 오늘 날짜 및 일정 데이터 추출
    today_str = time.strftime("%Y-%m-%d")
    todays_events = [s['title'] for s in global_schedules if s['date'] == today_str]
    
    # 2. 날씨 정보 가져오기
    weather = get_weather()
    weather_text = f"현재 기온 {weather['temp']}도, {weather['condition']}"
    
    # 3. 일정 텍스트 정리
    if todays_events:
        event_text = f"오늘 일정: {', '.join(todays_events)}"
    else:
        event_text = "오늘 일정 없음"

    # 4. Brain에게 위임 (프롬프트는 Brain.py에서 관리)
    result = {}
    event = threading.Event()
    
    def cb(text, task, thought):
        result['text'] = text
        event.set()

    brain.generate_briefing(weather_text, event_text, cb)
    event.wait(timeout=15)
    
    final_text = result.get('text', "시스템 준비가 완료되었습니다. 오늘도 화이팅하세요!")
    
    # 5. 음성 출력 및 UI 메시지 기록
    print(f"[SYSTEM] 자동 브리핑: {final_text}")
    speak(final_text) # TTS 출력
    add_voice_message(final_text, "ai") # UI에 기록

if __name__ == '__main__':
    # Vision Init Removed
    
    # 1. Vision Thread Removed
    
    # 2. Voice Thread Start
    t_voice = threading.Thread(target=voice_main, args=(add_voice_message,), daemon=True)
    t_voice.start()
    print("[SYSTEM] 음성 인식(MiniMax) 스레드 시작됨")
    
    # 3. Boot Briefing Thread Start
    t_boot = threading.Thread(target=run_boot_briefing, daemon=True)
    t_boot.start()
    print("[SYSTEM] 부팅 브리핑 스레드 예약됨 (10초 후)")

    # 4. Flask Server Start (Blocking)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)