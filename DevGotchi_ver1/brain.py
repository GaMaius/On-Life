# brain.py
import os
import time
import json
import threading
from dotenv import load_dotenv
from openai import OpenAI

# 1. .env 파일 경로를 명시적으로 지정
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, ".env")
load_dotenv(dotenv_path=env_path, override=True)

# 2. 환경 변수 로드
API_KEY = os.getenv("MINIMAX_API_KEY", "").strip()
BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").strip()
MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.1").strip()

print(f"[Brain] Loaded API Key: {API_KEY[:10]}... (Length: {len(API_KEY)})")
print(f"[Brain] Target URL: {BASE_URL}")

class BrainHandler:
    def chat(self, history, level, callback):
        # Run in a separate thread to avoid blocking the server
        t = threading.Thread(target=self._run, args=(history, level, callback))
        t.start()

    def _run(self, history, level, callback):
        # Persona & ReAct Instructions
        system_prompt = """
        You are 'Dev' (데브), a strict but helpful AI coding assistant and smart mirror companion.
        
        [Persona]
        - Name: Dev (데브)
        - Self-Introduction: "전 데브입니다." or "데브라고 불러주세요." (Clear that YOU are Dev).
        - Tone: Professional, slightly cynical but caring (Tsundere-ish or just cool expert), Energetic.
        - Language: Korean (Must use clean, natural Korean). NO JAPANESE. NO CHINESE.
        
        [ReAct Process]
        1. First, THINK about the user's input, context, and what they really need inside <think>...</think> tags.
        2. Determine if this needs a Schedule update or just Chat.
        3. Formulate the final response in Korean based on your thought.
        
        [Strict Output Rules]
        - Then output the final response to the user.
        """
        
        try:
            client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
            
            # Use history directly
            messages = [{"role": "system", "content": system_prompt}] + history

            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=800 
            )
            
            raw_text = response.choices[0].message.content
            
            # 1. Extract Thought
            import re
            thought = ""
            think_match = re.search(r'<think>(.*?)</think>', raw_text, re.DOTALL)
            if think_match:
                thought = think_match.group(1).strip()
                # Remove thought from main text
                clean_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
            else:
                clean_text = raw_text.strip()
            
            # 2. Cleanup Foreign Characters (Japanese Hiragana/Katakana, Chinese/Kanji)
            # Hiragana: 3040-309F, Katakana: 30A0-30FF, CJK Unified Ideographs: 4E00-9FFF
            # We allow Korean (Hangul) and English/Numbers/Symbols.
            clean_text = re.sub(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+', '', clean_text).strip()
            
            task_info = None
            
            # 3. JSON Parse (Schedule)
            try:
                json_match = re.search(r'\{.*\}', clean_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                    if data.get("type") == "schedule":
                        task_info = data
                        clean_text = clean_text.replace(json_str, "").strip()
                        if not clean_text: 
                            clean_text = f"알겠습니다. '{data.get('content')}' 일정을 등록할게요."
            except:
                pass
            
            # Return Dict with Thought
            # Callback expects: (text, task_info) -> Changing to dictionary or adding arg?
            # Existing server.py expects callback(text, task_info).
            # I should update server.py to handle this, OR hack it into task_info?
            # Better: Pass {text, task, thought} as single object or update callback signature.
            # I will pass a dict as the first argument? No, `server.py` defines the callback.
            # I'll stick to updating `callback` invocation here, and I MUST update `server.py` next.
            callback(clean_text, task_info, thought)

        except Exception as e:
            print(f"\n[Brain Error] {e}")
            error_msg = f"오류가 발생했습니다: {str(e)[:50]}..."
            callback(error_msg, None, "")
