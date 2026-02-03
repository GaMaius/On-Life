from openai import OpenAI
import json

class BrainAgent:
    def __init__(self, api_key):
        # MiniMax API Base URL (공식 문서 확인 필요, 보통 /v1)
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.minimax.chat/v1" 
        )
        self.history = []
        
        # 시스템 프롬프트: 에이전트의 성격과 행동 규칙 정의
        self.system_prompt = {
            "role": "system",
            "content": """
            당신은 '데브고치'입니다. 사용자의 업무/학업을 돕는 게임 캐릭터 같은 AI 비서입니다.
            
            [규칙]
            1. 말투: 친근하고 약간 장난기 있게 (예: "가람아, 허리 좀 펴!", "HP가 위험해!")
            2. 입력으로 사용자의 상태(Status)와 말(Input)이 주어집니다.
            3. 사용자가 졸거나 자세가 나쁘면 경고를, 잘하면 칭찬을 하세요.
            4. 답변은 반드시 JSON 형식으로 하세요.
            
            [JSON 형식]
            {
                "response": "사용자에게 할 말 (TTS용)",
                "emotion": "happy" | "angry" | "sleepy" | "worried",
                "action": "none" | "timer_25min" | "stretching_guide"
            }
            """
        }

    def chat(self, user_input, user_status):
        # 컨텍스트 조립
        status_desc = f"현재상태: 자세={user_status['bad_posture']}, 졸음={user_status['is_drowsy']}, HP={user_status['hp']}"
        full_prompt = f"{status_desc}\n사용자 입력: {user_input}"
        
        # 메시지 기록 관리 (최근 10개 유지 - M1 요구사항 [cite: 18])
        self.history.append({"role": "user", "content": full_prompt})
        if len(self.history) > 10:
            self.history.pop(0)

        messages = [self.system_prompt] + self.history

        try:
            completion = self.client.chat.completions.create(
                model="abab5.5-chat", # MiniMax 모델명 (문서 확인 필요)
                messages=messages,
                temperature=0.7,
            )
            
            result_text = completion.choices[0].message.content
            self.history.append({"role": "assistant", "content": result_text})
            
            # JSON 파싱 시도 (LLM이 가끔 마크다운 ```json ... ``` 을 붙일 때 처리)
            clean_text = result_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
            
        except Exception as e:
            print(f"Brain Error: {e}")
            return {"response": "서버랑 통신이 잘 안 돼요 ㅠㅠ", "emotion": "worried", "action": "none"}