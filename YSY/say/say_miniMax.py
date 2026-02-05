import os
import time
import io
import uuid
import requests
import json  # 추가
import re    # 추가
import speech_recognition as sr
from gtts import gTTS
import pygame
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner
from rich.align import Align
from dotenv import load_dotenv

# 1. 초기화 및 설정
load_dotenv(override=True)

API_KEY = os.getenv("MINIMAX_API_KEY", "").replace('"', '').replace("'", "").strip()
BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").strip()
MODEL_NAME = os.getenv("MINIMAX_MODEL", "MiniMax-M2.1").strip()

console = Console()
pygame.mixer.init()

telemetry_logs = []

def speak(text):
    if not text.strip(): return
    forbidden = ["싱크", "부드럽게", "규칙", "분석", "스타일", "상황", "payload", "API"]
    clean_text = " ".join([l for l in text.split('\n') if not any(k in l for k in forbidden)]).strip()
    
    try:
        tts = gTTS(text=clean_text if clean_text else text, lang='ko')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        pygame.mixer.music.load(fp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
    except Exception as e:
        console.print(f"[red]음성 에러: {e}[/red]")

def listen(r, source, mode="WAKE"):
    timeout = None if mode == "WAKE" else 5
    phrase_limit = 5 if mode == "WAKE" else 8
    try:
        if mode == "WAKE":
            r.adjust_for_ambient_noise(source, duration=0.5)
        audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
        return r.recognize_google(audio, language="ko-KR")
    except:
        return ""

# [추가] UI에 타이머/알림을 추가하기 위한 브릿지 함수
def update_ui_function(task_type, content, target_time):
    """
    이 함수는 나중에 메인 UI의 리스트나 타이머 객체에 데이터를 전달하는 역할을 합니다.
    """
    if task_type == "TIMER":
        console.print(f"[bold magenta]⏳ [UI 연동] {target_time} 타이머 가동![/bold magenta]")
    elif task_type == "REMINDER":
        console.print(f"[bold blue]📌 [UI 연동] 업무 추가: {content} ({target_time})[/bold blue]")

def call_minimax_standard(user_input, history):
    url = f"{BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # [수정] 시스템 프롬프트에 타이머/알림 추출 규칙 추가
    system_instruction = (
        "당신은 스마트 미러 비서 '데브고치'입니다. 사족 없이 한 문장으로 답변하세요. "
        "사용자가 타이머나 업무(알림) 설정을 요청하면 답변 끝에 반드시 아래 형식을 포함하세요.\n"
        "타이머일 경우: [COMMAND:TIMER:시간]\n"
        "업무 알림일 경우: [COMMAND:REMINDER:시간:내용]"
    )

    formatted_messages = [{"role": "system", "content": system_instruction}]
    for h in history:
        role = "assistant" if h["sender_type"] == "BOT" else "user"
        formatted_messages.append({"role": role, "content": h["text"]})
    formatted_messages.append({"role": "user", "content": user_input})
    
    payload = {
        "model": MODEL_NAME,
        "messages": formatted_messages,
        "max_tokens": 512,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        res_json = response.json()

        if response.status_code == 200:
            raw_content = res_json['choices'][0]['message']['content']
            tokens = res_json.get('usage', {}).get('total_tokens', 0)
            
            # [추가] 명령어 패턴 파싱 로직
            # 예: "5분 타이머 설정했습니다. [COMMAND:TIMER:5분]"
            command_pattern = r"\[COMMAND:(\w+):(.*?)\]"
            match = re.search(command_pattern, raw_content)
            
            clean_answer = raw_content
            if match:
                cmd_type = match.group(1)
                cmd_data = match.group(2).split(':')
                
                if cmd_type == "TIMER":
                    update_ui_function("TIMER", "", cmd_data[0])
                elif cmd_type == "REMINDER":
                    # cmd_data[0]은 시간, cmd_data[1]은 내용
                    time_val = cmd_data[0] if len(cmd_data) > 0 else "미정"
                    text_val = cmd_data[1] if len(cmd_data) > 1 else "업무"
                    update_ui_function("REMINDER", text_val, time_val)
                
                # 음성으로 읽어줄 때는 명령어 부분 제거
                clean_answer = re.sub(command_pattern, "", raw_content).strip()

            return clean_answer, tokens
        else:
            error_msg = res_json.get('error', {}).get('message', 'Unknown API Error')
            console.print(f"[bold red]❌ API 오류:[/bold red] {error_msg}")
            return f"오류가 발생했습니다: {error_msg}", 0
            
    except Exception as e:
        console.print(f"[bold red]❌ 네트워크 에러:[/bold red] {e}")
        return "연결 실패", 0

def main():
    r = sr.Recognizer()
    r.energy_threshold = 400
    r.dynamic_energy_threshold = True

    console.print(Panel("[bold cyan]👾 데브고치(MiniMax M2.1) 시스템 가동[/bold cyan]", 
                        subtitle="Standard API Mode (Timer/Task Enabled)", border_style="cyan"))
    
    chat_history = []
    
    while True:
        with sr.Microphone() as source:
            console.print("[dim white]● 대기 중...[/dim white]", end="\r")
            wake_text = listen(r, source, mode="WAKE")
            
            if any(word in wake_text for word in ["데브", "고치", "데이브", "대부"]):
                console.print("\n")
                console.print(Panel(
                    Align.center("[bold yellow]✨ CALL SIGN DETECTED ✨[/bold yellow]\n[white]인식 성공: 데브고치가 대기 중입니다[/white]"),
                    border_style="yellow", expand=False
                ))
                
                speak("네, 듣고 있어요.") 
                console.print("[bold green]🎤 말씀해 주세요...[/bold green]")
                user_input = listen(r, source, mode="CHAT")
                
                if user_input:
                    req_id = str(uuid.uuid4())[:8]
                    start_time = time.time()
                    
                    console.print(f"[bold cyan]You>[/bold cyan] {user_input}")
                    
                    with Live(Spinner("dots", text="MiniMax 응답 생성 중..."), console=console, transient=True) as live:
                        full_answer, token_count = call_minimax_standard(user_input, chat_history)
                        live.update(Markdown(full_answer))
                    
                    latency_ms = int((time.time() - start_time) * 1000)
                    log_entry = {"id": req_id, "latency": latency_ms, "tokens": token_count, "success": True}
                    telemetry_logs.append(log_entry)
                    
                    console.print(f"[dim]📊 [Log] ID:{req_id} | Latency:{latency_ms}ms | Tokens:{token_count}[/dim]")
                    
                    speak(full_answer)
                    console.print(f"[bold blue]데브고치>[/bold blue] {full_answer.strip()}")
                    
                    chat_history.append({"sender_type": "USER", "text": user_input})
                    chat_history.append({"sender_type": "BOT", "text": full_answer})
                    if len(chat_history) > 10: chat_history = chat_history[-10:]
                else:
                    console.print("[red]⚠ 입력이 없어 대기를 종료합니다.[/red]")
            
            time.sleep(0.3)

if __name__ == "__main__":
    main()
