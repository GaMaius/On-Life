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
    def chat(self, user_input, level, callback):
        # Run in a separate thread to avoid blocking the server
        t = threading.Thread(target=self._run, args=(user_input, level, callback))
        t.start()

    def _run(self, user_input, level, callback):
        system_prompt = "너는 사용자의 성장을 돕는 스마트 미러 AI야. 긍정적이고 활기찬 톤으로 짧게 대답해."
        
        try:
            client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
            
            full_prompt = f"""
            {system_prompt}
            
            [Context]
            User Input: "{user_input}"
            
            [Strict Output Rules]
            1. If User requests a schedule/task -> Return ONLY JSON.
            JSON Format: {{"type": "schedule", "content": "...", "time": "...", "location": "..."}}
            
            2. If General Chat -> Return ONLY the response text. 
            - Do NOT include reasoning.
            - Do NOT include the JSON structure if it's not a task.
            - Just say the response naturally.
            """

            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7
            )
            
            text = response.choices[0].message.content
            task_info = None
            
            # JSON Parse Attempt
            try:
                if "{" in text and "}" in text:
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    json_str = text[start:end]
                    data = json.loads(json_str)
                    if data.get("type") == "schedule":
                        task_info = data
                        text = f"알겠습니다. '{data.get('content')}' 일정을 등록할게요!"
            except:
                pass
            
            callback(text, task_info)

        except Exception as e:
            print(f"\n[Brain Error] {e}")
            error_msg = f"오류가 발생했습니다: {str(e)[:50]}..."
            if "401" in str(e):
                error_msg = "API 키 인증 실패 (401). .env 파일을 확인하세요."
            callback(error_msg, None)
