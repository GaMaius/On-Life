import os
import time
import io
import json
import speech_recognition as sr
from gtts import gTTS
import pygame
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner
from dotenv import load_dotenv

# 1. 환경 설정 및 초기화
load_dotenv(override=True)
API_KEY = os.getenv("MINIMAX_API_KEY", "").strip()
BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").strip()
MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.1").strip()

console = Console()
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
pygame.mixer.init()

MEMORY_FILE = "dev_memory.json"

# 2. 개인화 데이터 관리
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"context_summary": "아직 축적된 데이터가 없는 새 사용자입니다."}

def save_memory(summary):
    memory = {"context_summary": summary}
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

def update_personalization(conversation):
    try:
        extract_prompt = "이 대화에서 사용자에 대해 새로 알게 된 사실이나 업무 스타일을 한 문장으로 업데이트해줘."
        messages = conversation + [{"role": "user", "content": extract_prompt}]
        response = client.chat.completions.create(model=MODEL, messages=messages)
        new_summary = response.choices[0].message.content
        save_memory(new_summary)
        console.print(f"[dim blue]💾 메모리 업데이트 완료: {new_summary}[/dim blue]")
    except Exception as e:
        console.print(f"[dim red]메모리 갱신 에러: {e}[/dim red]")

# 3. 음성 관련 함수 (필터링 강화)
def speak(text):
    """텍스트를 음성으로 출력 (AI의 내부 사고 과정 필터링)"""
    if not text.strip(): return
    
    lines = text.split('\n')
    filtered_lines = []
    # AI가 스스로 내리는 지시나 상황 분석 문구들을 필터링합니다.
    stop_keywords = ["사용자가", "해야 한다", "분석", "프롬프트", "상황:", "전략:"]
    
    for line in lines:
        if any(keyword in line for keyword in stop_keywords):
            continue
        filtered_lines.append(line)
    
    clean_text = " ".join(filtered_lines).strip()
    clean_text = clean_text.replace("*", "").replace("#", "").replace("`", "").strip()

    try:
        final_out = clean_text if clean_text else text
        tts = gTTS(text=final_out, lang='ko')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        pygame.mixer.music.load(fp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        console.print(f"[red]TTS 출력 에러: {e}[/red]")

def listen_with_debug(r, source, mode="WAKE"):
    """디버깅 정보를 출력하며 음성을 인식함"""
    r.adjust_for_ambient_noise(source, duration=0.8)
    current_threshold = int(r.energy_threshold)
    console.print(f"[dim]  > [DEBUG] 현재 에너지 임계값: {current_threshold}[/dim]", end="\r")
    
    try:
        timeout = None if mode == "WAKE" else 7
        audio = r.listen(source, timeout=timeout, phrase_time_limit=10)
        recognized = r.recognize_google(audio, language="ko-KR")
        console.print(f"[bold magenta]  > [인식 결과]: {recognized}[/bold magenta]")
        return recognized
    except:
        return ""

# 4. 메인 실행 루프
def main():
    r = sr.Recognizer() # [수정] 변수 r을 여기서 정확히 선언합니다.
    r.energy_threshold = 600 #
    r.dynamic_energy_threshold = False 

    console.print(Panel("[bold green]🤖 스마트 미러 '데브' 가동 중... '데브야'라고 불러주세요.[/bold green]"))

    while True:
        memory = load_memory()
        # [수정] AI가 답변 본론만 말하도록 강력한 시스템 프롬프트를 설정합니다.
        system_content = f"""
        당신은 스마트 미러 비서 '데브'입니다.
        [기억 중인 사용자 정보]: {memory['context_summary']}
        
        [응답 규칙 - 절대 준수]
        1. 당신의 생각, 분석 과정, 전략을 절대 텍스트로 출력하지 마세요.
        2. "안녕하세요" 또는 본론으로 즉시 대화를 시작하세요.
        3. 오직 사용자에게 전달할 최종 답변만 한글로 출력하세요.
        """
        conversation = [{"role": "system", "content": system_content}]

        with sr.Microphone() as source:
            console.print("[bold white]● 대기 중...[/bold white]", end="\r")
            
            # 호출어 인식
            wake_text = listen_with_debug(r, source, mode="WAKE")
            
            if any(word in wake_text for word in ["데브야", "대부야", "데브", "대부", "거기는", "전기"]):
                console.print(f"\n[bold cyan]✨ 호출 성공! (인식: {wake_text})[/bold cyan]")
                speak("네, 말씀하세요.")
                
                # 질문 인식
                user_input = listen_with_debug(r, source, mode="CHAT")
                
                if user_input:
                    console.print(f"[bold green]You>[/bold green] {user_input}")
                    conversation.append({"role": "user", "content": user_input})
                    
                    full_answer = ""
                    console.print("[bold blue]Bot>[/bold blue] ", end="")
                    
                    with Live(Spinner("dots", text="Thinking..."), console=console, transient=True) as live:
                        try:
                            stream = client.chat.completions.create(model=MODEL, messages=conversation, stream=True)
                            for chunk in stream:
                                token = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ""
                                full_answer += token
                                live.update(Markdown(full_answer))
                            
                            console.print(Markdown(full_answer))
                            speak(full_answer) # 필터링된 음성 출력
                            conversation.append({"role": "assistant", "content": full_answer})
                            update_personalization(conversation)
                        except Exception as e:
                            console.print(f"[red]API 에러: {e}[/red]")
                else:
                    console.print("[yellow]질문을 인식하지 못했습니다.[/yellow]")
            
            time.sleep(0.5)

if __name__ == "__main__":
    main()
