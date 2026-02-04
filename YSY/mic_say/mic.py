import os
import time
import io
import uuid  # [추가] request_id 생성을 위함
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

# 1. 초기화 및 설정
load_dotenv(override=True)
API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
MODEL_NAME = "gemini-2.0-flash" # 최신 모델명 확인 필요

console = Console()
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    console.print("[bold red]❌ .env 파일에 GOOGLE_API_KEY가 없습니다![/bold red]")

pygame.mixer.init()

# [메모리 로그 저장소] 사진의 C, D 항목을 모두 담는 리스트
telemetry_logs = []

def speak(text):
    if not text.strip(): return
    forbidden = ["싱크", "부드럽게", "규칙", "분석", "스타일", "상황"]
    clean_text = " ".join([l for l in text.split('\n') if not any(k in l for k in forbidden)]).strip()
    
    try:
        tts = gTTS(text=clean_text if clean_text else text, lang='ko')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        
        pygame.mixer.quit()
        pygame.mixer.init(frequency=44100) 
        pygame.mixer.music.load(fp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
    except Exception as e:
        console.print(f"[red]음성 에러: {e}[/red]")

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

    console.print(Panel("[bold cyan]👾 데브고치(Gemini) 시스템 가동! (Telemetry 로깅 활성화)[/bold cyan]"))

    chat_history = []
    
    # 모델 인스턴스 미리 생성 (토큰 계산 등 활용)
    sys_instr = "당신은 '데브고치'입니다. '네 듣고있어요' 같은 사족 없이 본론만 한 문장으로 대답하세요. '싱크', '규칙' 단어 금지."
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=sys_instr)
    chat = model.start_chat(history=chat_history)

    while True:
        with sr.Microphone() as source:
            console.print("[bold white]● 대기 중...[/bold white]", end="\r")
            wake_text = listen(r, source, mode="WAKE")
            
            if any(word in wake_text for word in ["데브", "고치", "데이브", "대부", "배부"]):
                console.print(f"\n[bold yellow]✨ 호출 성공![/bold yellow]")
                speak("네, 듣고 있어요.") 
                
                user_input = listen(r, source, mode="CHAT")
                if user_input:
                    # --- [Telemetry & Log 데이터 준비] ---
                    req_id = str(uuid.uuid4())[:8]  # 고유 요청 ID
                    start_time = time.time()
                    success = False
                    error_code = "N/A"
                    full_answer = ""
                    token_count = 0
                    
                    # 요청 시점의 토큰 계산 (D 항목: 토큰/비용 추적용)
                    try:
                        token_count = model.count_tokens(user_input).total_tokens
                    except: pass

                    console.print(f"[bold green]You>[/bold green] {user_input}")
                    
                    with Live(Spinner("dots", text="Thinking..."), console=console, transient=True) as live:
                        try:
                            # 실제 API 호출
                            response = chat.send_message(user_input, stream=True)
                            for chunk in response:
                                full_answer += chunk.text
                                live.update(Markdown(full_answer))
                            
                            success = True
                        except Exception as e:
                            success = False
                            error_code = type(e).__name__ # 에러 유형(예: DeadlineExceeded)
                            console.print(f"[red]❌ API 실패: {e}[/red]")
                    
                    # --- [Telemetry 데이터 기록] ---
                    latency_ms = int((time.time() - start_time) * 1000)
                    
                    # 사진 속 요구사항 정리
                    log_data = {
                        "request_id": req_id,           # C 항목
                        "latency_ms": latency_ms,       # C 항목: 응답 지연
                        "retry_count": 0,               # C 항목 (단일 호출이므로 0)
                        "success": success,             # C 항목: API 성공여부
                        "error_code": error_code,       # C 항목: 오류 로그
                        "req_type": "CHAT",             # D 항목: 요청 유형
                        "input_tokens": token_count,    # D 항목: 토큰
                        "resp_len": len(full_answer)    # D 항목: 응답 길이
                    }
                    telemetry_logs.append(log_data)
                    
                    # 실시간 로그 요약 출력
                    console.print(f"[dim]📊 [Log] ID:{req_id} | 지연:{latency_ms}ms | 성공:{success} | 토큰:{token_count}[/dim]")
                    
                    if success:
                        speak(full_answer)
                        console.print(f"[bold blue]Bot>[/bold blue] {full_answer.strip()}")
                        chat_history = chat.history
            
            time.sleep(0.5)

if __name__ == "__main__":
    main()
