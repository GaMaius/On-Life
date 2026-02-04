
import cv2
import time
import threading
import base64
import queue
from flask import Flask, render_template, Response, jsonify, request
from config import Config
from game_manager import GameManager
from vision_engine import VisionEngine
from brain import BrainHandler

app = Flask(__name__)

# Core Systems
game = GameManager()
vision = VisionEngine()
brain = BrainHandler()

# Global State
current_frame = None
video_lock = threading.Lock()
running = True

# Vision Data shared with main thread
vision_state = {
    "is_bad_posture": False,
    "posture_score": 0,
    "is_drowsy": False,
    "is_smiling": False,
    "is_active_movement": False
}

def game_loop():
    global current_frame, running, vision_state
    cap = cv2.VideoCapture(0)
    
    while running:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue
            
        # 1. Vision Analysis
        posture_score, is_drowsy, is_smiling, is_eye_closed = vision.analyze_frame(frame)
        is_active_movement = vision.check_action_movement(frame)
        
        is_bad_posture = posture_score > Config.POSTURE_THRESHOLD
        
        # Update shared state
        vision_state = {
            "is_bad_posture": is_bad_posture,
            "posture_score": float(posture_score),
            "is_drowsy": bool(is_drowsy),
            "is_smiling": bool(is_smiling),
            "is_eye_closed": bool(is_eye_closed),
            "is_active_movement": bool(is_active_movement)
        }
        
        # 2. Game Update
        # Note: 'has_user_input' is hard to track via web without installing a system hook. 
        # For now, we'll assume web interaction counts as input, 
        # OR we just rely on camera movement for "presence" and specific API calls for "input".
        # Let's say: if is_active_movement or recent API call -> has_input.
        has_input = (time.time() - last_api_interaction) < 2.0 
        
        game.update(is_bad_posture, is_drowsy, has_input, is_active_movement)
        
        # 3. Draw Debug Info on Frame (Optional, for video feed)
        if is_bad_posture:
            cv2.rectangle(frame, (0,0), (frame.shape[1], frame.shape[0]), (0,0,255), 10)
        
        with video_lock:
            current_frame = frame
            
        time.sleep(0.03) # ~30 FPS
        
    cap.release()

# Track API interaction time for "Idle" detection
last_api_interaction = time.time()

@app.before_request
def update_interaction():
    global last_api_interaction
    last_api_interaction = time.time()

@app.route('/')
def index():
    return render_template('index.html')

def generate_frames():
    global current_frame
    while True:
        with video_lock:
            if current_frame is None:
                time.sleep(0.1)
                continue
            
            # Encode frame
            ret, buffer = cv2.imencode('.jpg', current_frame)
            frame = buffer.tobytes()
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.04)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def get_status():
    # Return Game State
    active_quests = [q.to_dict() for q in game.quests if not q.is_completed]
    available_quests = [q.to_dict() for q in game.available_quests]
    
    # Check if damage is actually happening (if bad posture lasts long enough)
    is_taking_damage = False
    if game.bad_posture_duration > 180: # 3 min
        is_taking_damage = True
    
    return jsonify({
        "hp": game.hp, # Send full precision for smooth bar
        "max_hp": Config.MAX_HP,
        "xp": game.xp,
        "level": game.level,
        "level_progress": get_level_progress(),
        "next_level_xp": Config.MAX_XP_TABLE.get(game.level+1, 9999),
        "posture_score": vision_state['posture_score'],
        "is_bad_posture": vision_state['is_bad_posture'],
        "is_taking_damage": is_taking_damage,
        "is_eye_closed": vision_state.get('is_eye_closed', False),
        "is_smiling": vision_state.get('is_smiling', False),
        "is_drowsy": vision_state.get('is_drowsy', False),
        "active_quests": active_quests,
        "available_quests": available_quests
    })

def get_level_progress():
    prev_xp = Config.MAX_XP_TABLE.get(game.level, 0)
    next_xp = Config.MAX_XP_TABLE.get(game.level + 1, 9999)
    if next_xp == 9999: return 100
    
    curr = game.xp - prev_xp
    total = next_xp - prev_xp
    return int((curr / total) * 100) if total > 0 else 100

@app.route('/api/quest/accept', methods=['POST'])
def accept_quest():
    data = request.json
    index = data.get('index')
    success = game.accept_quest(index)
    return jsonify({"success": success})

# Chat History (In-Memory for now)
CHAT_HISTORY = []

@app.route('/api/chat', methods=['POST'])
def chat():
    global CHAT_HISTORY
    data = request.json
    user_msg = data.get('message')
    
    # Add User Message to History
    CHAT_HISTORY.append({"role": "user", "content": user_msg})
    # Keep last 10 turns (20 messages) to manage context window
    if len(CHAT_HISTORY) > 20:
        CHAT_HISTORY = CHAT_HISTORY[-20:]
    
    # Process AI Chat synchronously for the API response
    result_queue = queue.Queue()
    
    def callback(text, task_info, thought=""):
        # Add AI Message to History
        CHAT_HISTORY.append({"role": "assistant", "content": text})
        result_queue.put({"text": text, "task": task_info, "thought": thought})
        
    brain.chat(CHAT_HISTORY, game.level, callback)
    
    # Wait for response with timeout
    try:
        result = result_queue.get(timeout=30) # Increased timeout for ReAct
        return jsonify({
            "response": result["text"],
            "task": result["task"],
            "thought": result["thought"]
        })
    except queue.Empty:
        return jsonify({
            "response": "AI 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.",
            "task": None,
            "thought": "시간 초과"
        })

if __name__ == '__main__':
    # Start Game Loop Thread
    t = threading.Thread(target=game_loop)
    t.daemon = True
    t.start()
    
    # Start Server
    app.run(host='0.0.0.0', port=5000, debug=False)
