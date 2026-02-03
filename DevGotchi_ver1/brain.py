# brain.py
import os
import time
import json
from dotenv import load_dotenv
from openai import OpenAI
from PyQt5.QtCore import QThread, pyqtSignal

# 1. .env 파일 경로를 명시적으로 지정 (파일 못 찾는 문제 방지)
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, ".env")
load_dotenv(dotenv_path=env_path, override=True)

# 2. 환경 변수 로드 및 공백 제거
API_KEY = os.getenv("MINIMAX_API_KEY", "").strip()
BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").strip()
MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.1").strip()

# [디버깅] 키가 제대로 로드되었는지 콘솔에 출력
print(f"[Brain] Loaded API Key: {API_KEY[:10]}... (Length: {len(API_KEY)})")
print(f"[Brain] Target URL: {BASE_URL}")

class BrainWorker(QThread):
    # [수정 1] dict 대신 object로 변경하여 None이 와도 튕기지 않게 함
    response_received = pyqtSignal(str, object) 

    def __init__(self, user_input, system_prompt):
        super().__init__()
        self.client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
        self.user_input = user_input
        self.system_prompt = system_prompt

    def run(self):
        try:
            full_prompt = f"""
            {self.system_prompt}
            
            [사용자 입력]: "{self.user_input}"
            
            사용자가 일정/할일을 등록하려 하면 JSON으로 출력해. 아니면 그냥 대답해.
            JSON 형식: {{"type": "schedule", "content": "일정내용", "time": "시간"}}
            일정이 아니면 JSON 형식을 쓰지 말고 평범하게 한국어로 대답해.
            """

            # API 호출
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": full_prompt}],
                temperature=0.7
            )
            
            text = response.choices[0].message.content
            
            # JSON 파싱 (일정 등록 확인)
            task_info = None
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
            
            # 성공 시 결과 전송
            self.response_received.emit(text, task_info)

        except Exception as e:
            # 오류 내용 콘솔 출력
            print(f"\n[Brain Error] {e}")
            
            # [수정 2] 에러 발생 시 None을 보내도 앱이 죽지 않음 (위에서 object로 바꿨기 때문)
            error_msg = f"오류가 발생했습니다: {str(e)[:50]}..."
            if "401" in str(e):
                error_msg = "API 키 인증 실패 (401). .env 파일을 확인하세요."
            
            self.response_received.emit(error_msg, None)

class BrainHandler:
    def chat(self, user_input, level, callback):
        persona = "당신은 사용자의 업무를 돕는 AI 병아리 비서입니다."
        if level == 1:
            persona += " 갓 태어난 병아리처럼 '삐약'을 붙이며 귀엽게 말하세요."
        elif level >= 5:
            persona += " 늠름한 닭처럼 든든하고 전문적으로 말하세요."

        self.worker = BrainWorker(user_input, persona)
        self.worker.response_received.connect(callback)
        self.worker.start()
