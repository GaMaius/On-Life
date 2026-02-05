# app.py
from flask import Flask, render_template, Response, jsonify, request
import os
import cv2
import threading
import time
import json
import random
from config import Config
from game_manager import GameManager
from vision_engine import VisionEngine
from brain import BrainHandler
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Singletons A
gm = GameManager()
vision = VisionEngine()
brain = BrainHandler()

# Global State for Vision Thread
video_capture = None
latest_frame = None
vision_lock = threading.Lock()

# Status State
current_status = "업무중" # "업무중", "자리비움", "회의중", "퇴근"
is_work_mode = False # Toggle between Idle and Work UI

# Weather Cache
last_weather_update = 0
cached_weather = None

def get_weather():
    global last_weather_update, cached_weather
    now = time.time()
    
    # Cache for 10 minutes (600s), but ONLY if cache is valid data
    if cached_weather and cached_weather.get("temp") != 0 and (now - last_weather_update < 600):
        return cached_weather

    api_key = os.getenv("WEATHER_API_KEY")
    lat, lon = 37.5665, 126.9780 # Seoul (Hardcoded or Config)
    
    if not api_key:
        print("[Weather] No API Key found.")
        return {"temp": 0, "condition": "No Key", "comparison": 0}

    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=kr"
    
    try:
        print(f"[Weather] Requesting: {url}")
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            weather_data = {
                "temp": int(data['main']['temp']),
                "condition": data['weather'][0]['description'],
                "min": int(data['main']['temp_min']),
                "max": int(data['main']['temp_max']),
                "feels_like": int(data['main']['feels_like'])
            }
            cached_weather = weather_data
            last_weather_update = now
            print(f"[Weather] Success: {weather_data}")
            return weather_data
        else:
            print(f"[Weather] API Error: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"[Weather] Exception: {e}")
    
    # Return placeholder or last known bad state, but DO NOT CACHE IT logic effectively (since we check != 0 above)
    return {"temp": 0, "condition": "Error", "comparison": 0}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/status/update', methods=['POST'])
def update_status_btn():
    global current_status, is_work_mode
    data = request.json
    new_status = data.get('status')
    if new_status:
        current_status = new_status
        # Logic: If 'Work', enable Work UI. Else Idle.
        # Check stripping to ensure match
        if current_status.strip() == "업무중":
            is_work_mode = True
        else:
            is_work_mode = False
        print(f"[Status] Updated to: {current_status} (WorkMode: {is_work_mode})")
    return jsonify({"success": True, "status": current_status})

@app.route('/api/mode/toggle', methods=['POST'])
def toggle_mode():
    global is_work_mode
    data = request.json
    # This might be deprecated if update_status handles it, but kept for direct toggle
    is_work_mode = data.get('work_mode', False)
    return jsonify({"work_mode": is_work_mode})



@app.route('/api/gamestate')
def get_gamestate():
    return jsonify({
        "hp": gm.hp,
        "max_hp": Config.MAX_HP,
        "xp": gm.xp,
        "level": gm.level,
        "happiness": gm.happiness,
        "quests": [q.to_dict() for q in gm.quests],
        "available_quests": [q.to_dict() for q in gm.available_quests],
        "work_mode": is_work_mode,
        "status": current_status,
        "weather": get_weather(),
        "posture_score": vision.last_posture if hasattr(vision, 'last_posture') else 0,
        "bad_posture_duration": gm.bad_posture_duration,
        "todays_events": gm.get_todays_events()
    })

@app.route('/api/quest/accept', methods=['POST'])
def accept_quest():
    data = request.json
    idx = data.get('index', -1)
    if gm.accept_quest(idx):
        return jsonify({"success": True, "message": "Quest accepted"})
    return jsonify({"success": False, "message": "Could not accept quest"})

@app.route('/api/calendar/add', methods=['POST'])
def add_calendar_event():
    data = request.json
    date = data.get('date')
    title = data.get('title')
    color = data.get('color', '#bb86fc')
    if date and title:
        gm.add_calendar_event(date, title, color)
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/api/calendar', methods=['GET'])
def get_calendar():
    return jsonify(gm.calendar)

# AI Chat Endpoint
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_msg = data.get('message')
    history = data.get('history', []) # list of {role, content}
    
    def on_complete(response, task, thought):
        # This callback is running in thread, we can't return HTTP response here directly
        # But for 'stream', we might need SSE. For simple request, we wait?
        # Brain runs in thread. We should make this synchronous for the web API 
        # OR use a Future. 
        # For simplicity in V3, let's make it blocking or use a queue.
        pass

    # For web integration, we'll wrap brain call synchronously or use a specialized route
    # Adapting brain.py: It uses threading. 
    # Let's modify usage:
    result = {}
    event = threading.Event()
    
    def cb(text, task, thought):
        result['text'] = text
        result['task'] = task
        result['thought'] = thought
        event.set()
        
    brain.chat(history + [{"role": "user", "content": user_msg}], gm.level, cb)
    event.wait(timeout=30)
    
    return jsonify(result)

# Vision Streaming & Logic Loop
def vision_loop():
    global video_capture
    # Use 0 for webcam
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(1)
            continue
            
        # Analysis
        score, drowsy, smile, closed, landmarks = vision.analyze_frame(frame)
        
        # Game Update
        # Determine strict "Bad Posture" based on score
        # Heuristic: Score > 15 ? (Need calibration)
        # Let's assume score > 20 is bad
        is_bad = score > 20
        
        # Drowsy check logic (Vision Engine returns boolean)
        
        gm.update(is_bad, drowsy, True) # Active input simulated
        
        # Draw Visuals (Optional, for debug stream)
        # ...
        
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
    # Start Vision Thread
    t = threading.Thread(target=vision_loop, daemon=True)
    t.start()
    
    app.run(debug=True, port=5000, use_reloader=False)
