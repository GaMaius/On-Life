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
current_status = "업무중" 
is_work_mode = False 

def get_weather():
    api_key = os.getenv("WEATHER_API_KEY")
    lat, lon = 35.0471, 127.9915 
    
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
    global current_status
    data = request.json
    current_status = data.get('status', current_status)
    return jsonify({"status": current_status})

@app.route('/api/mode/toggle', methods=['POST'])
def toggle_mode():
    global is_work_mode
    data = request.json
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
    
    return jsonify(result)

def vision_loop():
    global video_capture
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(1)
            continue
            
        score, drowsy, smile, closed, landmarks = vision.analyze_frame(frame)
        is_bad = score > 20
        gm.update(is_bad, drowsy, True) 
        
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
    t = threading.Thread(target=vision_loop, daemon=True)
    t.start()
    app.run(debug=True, port=5000, use_reloader=False)
