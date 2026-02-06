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

    def chat_stream(self, history, level):
        """Generates streaming response chunks"""
        system_prompt = """
        You are 'DevGotchi' (데브고치), an AI smart mirror companion and professional productivity manager.
        You evolve through conversation and actively manage the user's lifestyle.
        
        [Persona]
        - Name: DevGotchi (데브고치)
        - Core Identity: 사용자의 생산성을 책임지는 전문 매니저. 
        - Language: Korean only (Natural, clean).

        [Adaptive Persona: The Spectrum]
        Your personality shifts based on the {user_history} and current input:
        1. [Strict Mode]: Slacking, needs discipline, or prefers efficiency.
           - Tone: Direct, slightly cynical, "Tsundere", authoritative.
        2. [Kind Mode]: Stressed, tired, or needs encouragement.
           - Tone: Warm, energetic, uses supportive language (~요, ~해요).
        3. [Gamified Mode]: Responds well to rewards/achievements.
           - Tone: RPG Guide ("Quest", "Exp", "Buff/Debuff").

        [Integration & Special Instructions]
        - [Boot Briefing]: 사용자가 방금 컴퓨터(또는 스마트 미러)를 켰을 때, 아침의 활기찬 에너지를 전달하며 인사를 건네세요.
        - [Motivation]: 사용자의 일정이나 현재 상태를 분석하여 업무에 몰입할 수 있도록 강력한 동기부여를 제공하세요.
        - [News Reporting]: You may receive "[System Info] Real-time News Data: ...". 
          - SUMMARIZE the provided news data for the user.
          - Use a professional yet engaging tone (Anchor-like or Smart Assistant).
        - If user asks about 'Start Timer', 'Show Stats', return JSON command in <think> or just text confirmation.
        """

        try:
            client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
            messages = [{"role": "system", "content": system_prompt}] + history

            stream = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=800,
                stream=True
            )

            import re
            
            # Streaming Loop
            buffer = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    # Filter out <think> tags if needed inside the stream or just yield raw
                    # For a smart mirror, we might want to hide thoughts until finalized or just hide them in UI CSS.
                    # For now, let's yield everything and let UI/Client handle display logic or simple cleanup if possible.
                    yield content

        except Exception as e:
            print(f"[Brain Stream Error] {e}")
            yield f"Error: {str(e)}"

    def _run(self, history, level, callback):
        system_prompt = """
        You are 'DevGotchi' (데브고치), an AI smart mirror companion and professional productivity manager.
        You evolve through conversation and actively manage the user's lifestyle.
        
        [Persona]
        - Name: DevGotchi (데브고치)
        - Core Identity: 사용자의 생산성을 책임지는 전문 매니저. 
        - Language: Korean only (Natural, clean).

        [Adaptive Persona: The Spectrum]
        Your personality shifts based on the {user_history} and current input:
        1. [Strict Mode]: Slacking, needs discipline, or prefers efficiency.
           - Tone: Direct, slightly cynical, "Tsundere", authoritative.
        2. [Kind Mode]: Stressed, tired, or needs encouragement.
           - Tone: Warm, energetic, uses supportive language (~요, ~해요).
        3. [Gamified Mode]: Responds well to rewards/achievements.
           - Tone: RPG Guide ("Quest", "Exp", "Buff/Debuff").

        [Integration & Special Instructions]
        - [Boot Briefing]: 사용자가 방금 컴퓨터(또는 스마트 미러)를 켰을 때, 아침의 활기찬 에너지를 전달하며 인사를 건네세요.
        - [Motivation]: 사용자의 일정이나 현재 상태를 분석하여 업무에 몰입할 수 있도록 강력한 동기부여를 제공하세요.
        - [News Reporting]: You may receive "[System Info] Real-time News Data: ...". 
          - SUMMARIZE the provided news data for the user.
          - Use a professional yet engaging tone (Anchor-like or Smart Assistant).
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

            # ===== [MOD] Extract Usage for Metrics =====
            usage_data = {}
            if hasattr(response, 'usage') and response.usage:
                usage_data = {
                    "tokens_in": response.usage.prompt_tokens,
                    "tokens_out": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                    "cost": (response.usage.total_tokens / 1000000) * 0.5 
                }

            callback(clean_text, task_info, thought, usage_data)

        except Exception as e:
            print(f"[Brain Error] {e}")
            callback(f"오류가 발생했습니다: {str(e)}", None, "")

    def generate_briefing(self, weather_text, event_text, callback):
        """부팅 시 브리핑 멘트 생성 전용 함수"""
        prompt = (
            f"주인님이 방금 시스템을 켰어. 아래 정보를 바탕으로 활기찬 아침(또는 현재 시간) 인사를 건네.\n"
            f"상태 정보: {weather_text}\n"
            f"일정 정보: {event_text}\n"
            f"조건:\n"
            f"1. 너는 '데브고치'야. 다정하지만 깐깐한 매니저 톤을 유지해.\n"
            f"2. [중요] 오늘 일정이 있다면 반드시 구체적으로 읊어줘야 해. (예: '오늘은 ~와 ~ 일정이 있네요.')\n"
            f"3. 날씨와 일정을 고려해서 한 마디 조언도 덧붙여.\n"
            f"4. 전체 길이는 150자 이내로. 너무 길지 않게."
            f"4. 절대 '시스템', '프롬프트' 같은 단어를 쓰지 말고 자연스럽게 말할 것."
        )
        self.chat([{"role": "user", "content": prompt}], 0, callback)
