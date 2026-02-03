import requests
import json
import time

class BrainAgent:
    def __init__(self, api_key, data_manager):
        self.api_key = api_key.strip()
        self.logger = data_manager # 데이터 매니저 연결
        
        # OpenAI 모드로 설정
        self.url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-4o-mini" # 또는 gpt-3.5-turbo

        self.history = []
        self.system_prompt = {
            "role": "system",
            "content": "당신은 '데브고치'입니다. 사용자의 일정과 건강을 관리하는 스마트 미러 AI입니다. 짧고 명확하게 대답하세요."
        }

    def chat(self, user_input):
        start_time = time.time() # 시작 시간 측정 (Telemetry)
        success = False
        
        self.history.append({"role": "user", "content": user_input})
        messages = [self.system_prompt] + self.history[-6:] # 최근 6턴만 유지

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=5)
            
            # 응답 시간 계산 (ms)
            latency = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                result_text = data['choices'][0]['message']['content']
                tokens = data.get('usage', {}).get('total_tokens', 0)
                
                # 성공 로그 (Type C, D)
                self.logger.log_telemetry(latency, True)
                self.logger.log_llm(tokens, "Chat_Response")
                
                self.history.append({"role": "assistant", "content": result_text})
                return result_text
            else:
                # 실패 로그 (Type C)
                self.logger.log_telemetry(latency, False, f"HTTP {response.status_code}")
                return "AI 서버 상태가 좋지 않아요."

        except Exception as e:
            latency = int((time.time() - start_time) * 1000)
            self.logger.log_telemetry(latency, False, str(e))
            return "인터넷 연결을 확인해주세요."