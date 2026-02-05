from flask import Flask, render_template, jsonify, request
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from flask import Flask, render_template, jsonify, request
import os
import requests
from dotenv import load_dotenv
from game_logic import GameManager

# Load environment variables
load_dotenv()

from flask import Flask, render_template, jsonify, request
import os
import requests
import queue
from dotenv import load_dotenv
from game_logic import GameManager
from brain import BrainHandler

# Load environment variables
load_dotenv()

app = Flask(__name__)

# --- Configuration ---
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# --- Managers ---
gm = GameManager()
brain = BrainHandler()
chat_history = [] # In-memory history for demo

# --- Routes ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/weather', methods=['GET'])
def get_weather():
    lat = 37.5665
    lon = 126.9780
    api_key = OPENWEATHER_API_KEY or "f83c5f76153571e5cbd97d300cfdeea3"

    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=kr"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        weather_data = {
            "location": data['name'],
            "desc": data['weather'][0]['description'],
            "temp": data['main']['temp'],
            "feels_like": data['main']['feels_like'],
            "temp_min": data['main']['temp_min'],
            "temp_max": data['main']['temp_max'],
            "icon": data['weather'][0]['icon']
        }
        return jsonify(weather_data)
    except Exception as e:
        print(f"Weather API Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status', methods=['GET', 'POST'])
def status():
    if request.method == 'POST':
        data = request.json
        status_val = data.get('status', 'idle')
        
        if 'happiness' in data:
            gm.happiness = data['happiness']
            
        is_bad = data.get('isBadPosture', False)
        
        gm.update_state(status_val, is_bad_posture=is_bad)
        gm.save_data()
        
        return jsonify({"msg": "Updated", "state": gm.get_state()})
    
    return jsonify(gm.get_state())

@app.route('/api/ai', methods=['POST'])
def chat_ai():
    data = request.json
    user_msg = data.get('message', '')
    
    # Update History
    chat_history.append({"role": "user", "content": user_msg})
    if len(chat_history) > 10: chat_history.pop(0)
    
    # Callback Wrapper
    result_q = queue.Queue()
    
    def on_complete(text, task_info, thought):
        result_q.put({
            "response": text,
            "task_info": task_info,
            "thought": thought
        })
    
    # Use Level from GameManager
    level = gm.level
    
    # Call Brain
    brain.chat(chat_history, level, on_complete)
    
    try:
        # Wait for response (up to 30s)
        result = result_q.get(timeout=30)
        
        # Append Assistant message to history
        chat_history.append({"role": "assistant", "content": result['response']})
        
        return jsonify(result)
    except queue.Empty:
        return jsonify({"response": "생각이 너무 오래 걸리네요... 다시 말해주세요."}), 504


if __name__ == '__main__':
    app.run(debug=True, port=5000)
