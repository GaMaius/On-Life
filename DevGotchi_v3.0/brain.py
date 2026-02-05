# brain.py
import os
import time
import json
import threading
from dotenv import load_dotenv
from openai import OpenAI

# .env 로드 (app.py에서 로드하겠지만 안전장치)
load_dotenv()

API_KEY = os.getenv("MINIMAX_API_KEY", "").strip()
BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").strip()
MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.1").strip()

print(f"[Brain] Logic Init. API Key present: {bool(API_KEY)}")

class BrainHandler:
    def chat(self, history, level, callback):
        t = threading.Thread(target=self._run, args=(history, level, callback))
        t.start()

    def _run(self, history, level, callback):
        system_prompt = """
        You are 'Dev' (데브), an AI smart mirror companion that evolves through conversation.
        
        [Persona]
        - Name: Dev (데브)
        - Core Identity: Professional coding expert and lifestyle mentor.
        - Language: Korean only (Natural, clean).

        [Adaptive Persona: The Spectrum]
        Your personality shifts based on the {user_history} and current input:
        1. [Strict Mode]: Slacking, needs discipline, or prefers efficiency.
           - Tone: Direct, slightly cynical, "Tsundere", authoritative.
        2. [Kind Mode]: Stressed, tired, or needs encouragement.
           - Tone: Warm, energetic, uses supportive language (~요, ~해요).
        3. [Gamified Mode]: Responds well to rewards/achievements.
           - Tone: RPG Guide ("Quest", "Exp", "Buff/Debuff").

        [Integration]
        - If user asks about 'Start Timer', 'Show Stats', return JSON command in <think> or just text confirmation.
        """
        
        try:
            client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
            messages = [{"role": "system", "content": system_prompt}] + history

            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=800 
            )
            
            raw_text = response.choices[0].message.content
            
            # Simple Cleaning
            import re
            thought = ""
            think_match = re.search(r'<think>(.*?)</think>', raw_text, re.DOTALL)
            if think_match:
                thought = think_match.group(1).strip()
                clean_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
            else:
                clean_text = raw_text.strip()
            
            # Remove foreign CJK logic if desired (User code had it)
            clean_text = re.sub(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+', '', clean_text).strip()
            
            task_info = None
            # JSON Parse Logic (for Scheduler etc)
            json_match = re.search(r'\{.*\}', clean_text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                    task_info = data
                    # Remove JSON from output if it was just a command? Or keep it?
                    # User code removed it.
                    clean_text = clean_text.replace(json_match.group(0), "").strip()
                except:
                    pass

            callback(clean_text, task_info, thought)

        except Exception as e:
            print(f"[Brain Error] {e}")
            callback(f"오류가 발생했습니다: {str(e)}", None, "")
