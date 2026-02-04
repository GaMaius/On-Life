import os
import time
import io
import speech_recognition as sr
from gtts import gTTS
import pygame
import google.generativeai as genai
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner
from dotenv import load_dotenv

# 1. 초기화
load_dotenv(override=True)
API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
MODEL_NAME = "gemini-2.5-flash"

console = Console()

# Google GenAI 설정
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    console.print("[bold red]❌ .env 파일에 GOOGLE_API_KEY가 없습니다![/bold red]")

pygame.mixer.init()

# 2. 음성 출력 함수 (배속 재생)
def speak(text):
    if not text.strip(): return
    # 사족 필터링
    forbidden = ["싱크", "부드럽게", "규칙", "분석", "스타일", "상황"]
    clean_text = " ".join([l for l in text.split('\n') if not any(k in l for k in forbidden)]).strip()
    
    try:
        tts = gTTS(text=clean_text if clean_text else text, lang='ko')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        
        # 주파수를 높여 1.5배속 효과 (44100Hz)
        pygame.mixer.quit()
        pygame.mixer.init(frequency=44100) 
        pygame.mixer.music.load(fp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
    except Exception as e:
        console.print(f"[red]음성 에러: {e}[/red]")

# 3. 마이크 인식 함수
def listen(r, source, mode="WAKE"):
    r.adjust_for_ambient_noise(source, duration=1.0)
    try:
        audio = r.listen(source, timeout=(None if mode == "WAKE" else 7), phrase_time_limit=5)
        return r.recognize_google(audio, language="ko-KR")
    except:
        return ""

def main():
    r = sr.Recognizer()
    r.energy_threshold = 400 
    r.dynamic_energy_threshold = True

    console.print(Panel("[bold cyan]👾 데브고치(Gemini) 가동 중! 호출 후 바로 질문하세요.[/bold cyan]"))

    # Chat history is managed by the model session if needed, but here we use single turn or new chat per loop
    # If maintaining history is required, we need a persistent chat object.
    # Given the previous logic used a "system prompt" renewed each time, we'll re-init the model to apply the prompt.
    
    chat_history = []

    while True:
        # 시스템 명령 (시스템 명령어를 별도 인자로 넣지 않고 contents에 포함하여 안정성 확보)
        sys_instr = "당신은 '데브고치'입니다. '네 듣고있어요' 같은 사족 없이 본론만 한 문장으로 대답하세요. '싱크', '규칙' 단어 금지."
        
        # 모델 초기화 (System Instruction 적용)
        try:
             # system_instruction is supported in newer versions of google-generativeai
            model = genai.GenerativeModel(MODEL_NAME, system_instruction=sys_instr)
            chat = model.start_chat(history=chat_history)
        except:
            # Fallback for older versions if system_instruction param fails
             model = genai.GenerativeModel(MODEL_NAME)
             chat = model.start_chat(history=chat_history)
             # If system instruction can't be passed to init, we prepend it to the message or history 
             # But let's assume valid version first.

        with sr.Microphone() as source:
            console.print("[bold white]● 대기 중...[/bold white]", end="\r")
            wake_text = listen(r, source, mode="WAKE")
            
            if wake_text:
                console.print(f"[dim]인식됨: {wake_text}[/dim]", end="\r")

            if any(word in wake_text for word in ["데브", "고치", "데이브", "대부", "배부"]):
                console.print(f"\n[bold yellow]✨ 호출 성공![/bold yellow]")
                speak("네, 듣고 있어요.") 
                
                user_input = listen(r, source, mode="CHAT")
                if user_input:
                    console.print(f"[bold green]You>[/bold green] {user_input}")
                    
                    full_answer = ""
                    with Live(Spinner("dots", text="Thinking..."), console=console, transient=True) as live:
                        try:
                            # [수정] 표준 google-generativeai 방식
                            response = chat.send_message(user_input, stream=True)
                            for chunk in response:
                                full_answer += chunk.text
                                live.update(Markdown(full_answer))
                            
                            speak(full_answer)
                            console.print(f"[bold blue]Bot>[/bold blue] {full_answer.strip()}")
                            
                            # Update history
                            chat_history = chat.history
                            
                        except Exception as e:
                            console.print(f"[red]에러: {e}[/red]")
            
            time.sleep(0.5)

if __name__ == "__main__":
    main()
