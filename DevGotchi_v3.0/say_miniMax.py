import os
import time
import io
import uuid
import requests
import json
import re
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
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()

console = Console()
pygame.mixer.init()

telemetry_logs = []

# [추가] 날씨 정보 가져오기 함수
def get_weather(city="Sacheon-si"):
    if not WEATHER_API_KEY:
        return {"error": "날씨 API 키가 설정되지 않았습니다."}
    
    # 한국어 출력을 위해 lang=kr 사용
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=kr"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get("cod") == 200:
            return {
                "temp": int(data['main']['temp']),
                "condition": data['weather'][0]['description'],
                "min": int(data['main']['temp_min']),
                "max": int(data['main']['temp_max']),
                "feels_like": int(data['main']['feels_like']),
                "city": city
            }
        else:
            return {"error": "도시를 찾을 수 없습니다."}
    except Exception as e:
        return {"error": str(e)}

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
        # Loop 내에서 매번 ambient_noise를 조정하면 인식이 늦어질 수 있으므로 제거하거나 필요시에만 호출
        # r.adjust_for_ambient_noise(source, duration=0.5) 
        
        audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
        text = r.recognize_google(audio, language="ko-KR")
        return text
    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
        # 인식이 안 된 경우 조용히 빈 값 반환
        return ""
    except sr.RequestError as e:
        console.print(f"[red]Google Speech Recognition 에러: {e}[/red]")
        return ""
    except Exception as e:
        if mode != "WAKE": # WAKE 모드일 때는 너무 잦은 출력을 피함
            console.print(f"[dim]인식 오류: {e}[/dim]")
        return ""

def update_ui_function(task_type, content, target_time):
    if task_type == "TIMER":
        console.print(f"[bold magenta]⏳ [UI 연동] {target_time} 타이머 가동![/bold magenta]")
        # 시간 문자열 파싱 (예: "5분", "10분", "30초")
        try:
            minutes = parse_time_to_minutes(target_time)
            mode = "down" # Default
            
            clean_content = content.upper().strip()
            if clean_content == "UP": mode = "up"
            elif clean_content == "RESET": mode = "reset"
            
            console.print(f"[bold yellow][DEBUG] 파싱된 분: {minutes}, 모드: {mode}[/bold yellow]")
            
            # Flask 서버에 타이머 설정 요청
            resp = requests.post("http://127.0.0.1:5000/api/timer/set", 
                         json={"minutes": minutes, "auto_start": True, "mode": mode}, 
                         timeout=3)
            console.print(f"[bold yellow][DEBUG] Flask 응답: {resp.status_code}, {resp.text}[/bold yellow]")
            
            if mode == "reset":
                console.print(f"[bold green]✓ 타이머 초기화 요청 성공![/bold green]")
            else:
                mode_str = "카운트다운" if mode == "down" else "카운트업"
                console.print(f"[bold magenta]⏳ [UI 연동] {minutes}분 {mode_str} 가동![/bold magenta]")
        except Exception as e:
            console.print(f"[red]타이머 설정 오류: {e}[/red]")
    elif task_type == "REMINDER":
        console.print(f"[bold blue]📌 [UI 연동] 일정 등록 요청: '{content}' (날짜: {target_time})[/bold blue]")
        try:
            # 날짜 및 제목 파싱
            date_val = parse_reminder_time(target_time)
            console.print(f"[dim blue]   -> 파싱된 최종 날짜: {date_val}[/dim blue]")
            requests.post("http://127.0.0.1:5000/api/schedule/set", 
                         json={"date": date_val, "title": content}, 
                         timeout=3)
            console.print(f"[bold green]✓ {date_val} 일정 '{content}' 등록 완료![/bold green]")
        except Exception as e:
            console.print(f"[red]일정 등록 오류: {e}[/red]")
    elif task_type == "SCHEDULE_DELETE":
        console.print(f"[bold red]🗑️ [UI 연동] 일정 삭제 요청: {content}일[/bold red]")
        try:
            date_val = parse_reminder_time(content)
            requests.post("http://127.0.0.1:5000/api/schedule/delete", 
                         json={"date": date_val}, 
                         timeout=3)
            console.print(f"[bold green]✓ {date_val} 일정 삭제 완료![/bold green]")
        except Exception as e:
            console.print(f"[red]일정 삭제 오류: {e}[/red]")
    elif task_type == "WEATHER":
        console.print(f"[bold yellow]☀️ [UI 연동] 날씨 정보 업데이트 완료[/bold yellow]")

def parse_reminder_time(time_str):
    """'오후 2시', '내일', '2월 8일', '2026-02-10' 등의 문자열을 YYYY-MM-DD 포맷으로 변환"""
    import datetime
    now = datetime.datetime.now()
    
    # 공백 제거 및 분석
    clean_str = str(time_str).replace(" ", "")
    console.print(f"[dim yellow][DEBUG] 날짜 파싱 시도: '{time_str}'[/dim yellow]")
    
    # 1. "X월 Y일" 형식 처리
    month_day_match = re.search(r'(\d+)월(\d+)일', clean_str)
    if month_day_match:
        m = int(month_day_match.group(1))
        d = int(month_day_match.group(2))
        try:
            target_date = datetime.date(now.year, m, d)
            return target_date.strftime("%Y-%m-%d")
        except: pass

    # 2. 키워드 처리
    if "오늘" in clean_str: return now.strftime("%Y-%m-%d")
    if "내일" in clean_str: return (now + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    if "모레" in clean_str: return (now + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
    
    # 3. 이미 날짜 형식인 경우 (YYYY-MM-DD)
    iso_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', clean_str)
    if iso_match: return iso_match.group(0)
    
    # 4. 숫자만 있는 경우 "일"로 간주 (이번 달의 해당 일)
    if clean_str.isdigit():
        d_val = int(clean_str)
        if 1 <= d_val <= 31:
            try:
                target_date = datetime.date(now.year, now.month, d_val)
                return target_date.strftime("%Y-%m-%d")
            except: pass

    console.print(f"[bold red]⚠ 날짜 파싱 실패: '{time_str}' -> 오늘 날짜로 기본값 설정[/bold red]")
    return now.strftime("%Y-%m-%d")

def korean_to_number(text):
    """'십삼', '이십오', '백' 등의 한글 숫자를 정수로 변환"""
    units = {
        '일': 1, '이': 2, '삼': 3, '사': 4, '오': 5,
        '육': 6, '칠': 7, '팔': 8, '구': 9,
    }
    tens = {'십': 10, '백': 100, '천': 1000}
    
    # 숫자만 있거나 이미 숫자로 된 경우 패스
    if text.isdigit(): return int(text)
    
    total = 0
    current = 0
    for char in text:
        if char in units:
            current = units[char]
        elif char in tens:
            if current == 0: current = 1
            total += current * tens[char]
            current = 0
        else:
            return None # 숫자가 아닌 문자가 섞임
            
    total += current
    return total

def parse_time_to_minutes(time_str):
    """시간 문자열을 분으로 변환 (예: '5분' -> 5, '30초' -> 0.5, '1시간 반' -> 90)"""
    import re
    time_str = str(time_str).strip().replace(" ", "")
    console.print(f"[dim yellow][DEBUG] 시간 파싱 시작: '{time_str}'[/dim yellow]")
    
    # 0. '반' 처리 logic (예: 1시간반 -> 1시간30분)
    if "반" in time_str:
        time_str = time_str.replace("반", "30분")
        
    # [추가] 한글 숫자 변환 (예: '십삼분' -> '13분')
    # '분', '시간', '초' 앞의 한글 숫자를 찾아서 변환
    def replace_korean_num(match):
        kor_num = match.group(1)
        num = korean_to_number(kor_num)
        if num is not None:
            return str(num) + match.group(2) # 예: "13" + "분"
        return match.group(0)

    # 일~구, 십~천이 포함된 패턴 찾기
    kor_pattern = r'([일이삼사오육칠팔구십백천]+)(분|시간|초)'
    time_str = re.sub(kor_pattern, replace_korean_num, time_str)
    console.print(f"[dim yellow][DEBUG] 한글 변환 후: '{time_str}'[/dim yellow]")
    
    # 1. 00:05:00 또는 05:00 형식 처리
    colon_match = re.match(r'(?:(\d+):)?(\d+):(\d+)', time_str)
    if colon_match:
        h = int(colon_match.group(1)) if colon_match.group(1) else 0
        m = int(colon_match.group(2))
        s = int(colon_match.group(3))
        total = h * 60 + m + s / 60
        return total

    # 2. 숫자만 있는 경우 분으로 간주
    if time_str.replace('.', '', 1).isdigit():
        total = float(time_str)
        return total
    
    # 3. 시간 패턴 매칭 (순서대로 합산)
    total_minutes = 0
    
    # 시간 추출
    hour_match = re.search(r'(\d+)\s*시간', time_str)
    if hour_match:
        total_minutes += int(hour_match.group(1)) * 60
        
    # 분 추출
    min_match = re.search(r'(\d+)\s*분', time_str)
    if min_match:
        total_minutes += int(min_match.group(1))
        
    # 초 추출
    sec_match = re.search(r'(\d+)\s*초', time_str)
    if sec_match:
        total_minutes += int(sec_match.group(1)) / 60
        
    if total_minutes > 0:
        return total_minutes

    # 4. "1시간" 같이 분 단위가 없을 때 처리
    if "시간" in time_str and not "분" in time_str:
         hour_only_match = re.search(r'(\d+)\s*시간', time_str)
         if hour_only_match:
             return int(hour_only_match.group(1)) * 60
             
    console.print(f"[dim yellow][DEBUG] 시간 파싱 실패: '{time_str}' -> None 반환[/dim yellow]")
    return None

def call_minimax_standard(user_input, history):
    url = f"{BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # [수정] 페르소나 및 응답 규칙 극단적 강화
    system_instruction = (
        "당신은 스마트 미러 비서 '데브고치'입니다. "
        "규칙 1: 절대 '명령어', '커맨드', '[COMMAND...]', '시스템' 등 내부 작동 방식을 설명하거나 언급하지 마세요.\n"
        "규칙 2: 사용자의 요청에 대해 친절하고 자연스럽게 대답만 하세요. (예: '네, 5분 타이머 시작하겠습니다!')\n"
        "규칙 3: 모든 특수 기능은 아래의 형식을 '답변 끝에' 조용히 포함하되, 말로 내뱉지는 마세요.\n"
        "- 날씨 조회: [COMMAND:WEATHER:도시명]\n"
        "- 카운트다운: [COMMAND:TIMER:시간:DOWN]\n"
        "- 카운트업: [COMMAND:TIMER:시간:UP]\n"
        "- 타이머 종료: [COMMAND:TIMER:0:RESET]\n"
        "- 일정 등록: [COMMAND:REMINDER:날짜:내용]\n"
        "- 일정 삭제: [COMMAND:DELETE_REMINDER:날짜]\n"
        "🚨필독🚨: 명령어 대괄호[] 안에 '날짜', '내용', '할일', '도시명' 같은 예시 단어를 쓰면 절대 안 됩니다. \n"
        "반드시 사용자가 말한 실제 도시(예: Seoul, Busan)나 실제 내용(예: 치과 가기)을 넣으세요.\n"
        "당신의 가장 큰 실수는 [COMMAND:WEATHER:도시명]과 같이 적는 것입니다. 반드시 [COMMAND:WEATHER:Busan]과 같이 실제 도시를 넣으세요."
    )
    
    # [News Injection Check]
    if "뉴스" in user_input or "소식" in user_input:
        try:
            # Fetch from local Flask API
            news_res = requests.get(f"http://127.0.0.1:5000/api/news/get", timeout=3)
            if news_res.status_code == 200:
                news_text = news_res.json().get("result", "")
                system_instruction += f"\n\n[SYSTEM INFO] Real-time News: {news_text}\nUser asks for news. Summarize this briefly and professionally."
                print(f"[Voice] News injected: {news_text[:30]}...")
        except Exception as e:
            print(f"[Voice] Failed to fetch news: {e}")


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
            
            # [수정] 명령어 패턴 파싱 로직을 먼저 수행하여 match 변수 정의
            command_pattern = r"\[COMMAND:(\w+):(.*?)\]"
            match = re.search(command_pattern, raw_content)

            # [강력 수정] AI가 명령어를 빼먹어도 키워드 기반으로 강제 처리 (Heuristic)
            u_clean = user_input.replace(" ", "")
            is_timer_req = "타이머" in u_clean or "카운트" in u_clean
            
            # 사용자 발화에서 시간 추출 시도 (가장 최우선)
            extracted_mins = parse_time_to_minutes(user_input)
            
            if is_timer_req:
                if any(k in u_clean for k in ["종료", "중지", "꺼", "멈춰", "리셋", "초기화", "그만", "끝내"]):
                    console.print("[bold yellow]⚠ 키워드 감지: 타이머 종료 실행[/bold yellow]")
                    update_ui_function("TIMER", "RESET", "0")
                elif any(k in u_clean for k in ["카운트업", "숫자커지게", "숫자늘려", "올려줘"]):
                    # 이미 match가 있는 경우는 아래 match 로직에서 처리됨 (단, 시간 override 필요)
                    if not match:
                        t_val = str(extracted_mins) if extracted_mins is not None else "5"
                        console.print(f"[bold yellow]⚠ 키워드 감지: 카운트업 실행 ({t_val}분)[/bold yellow]")
                        update_ui_function("TIMER", "UP", t_val)
            
            # [추가] 일정 삭제 키워드 직접 감지
            if "일정" in u_clean and any(k in u_clean for k in ["지워", "제거", "없애", "삭제", "취소"]):
                # 날짜 추측 (오늘이 기본)
                date_hint = "오늘"
                if "내일" in u_clean: date_hint = "내일"
                elif "어제" in u_clean: date_hint = "어제"
                month_day = re.search(r'(\d+)월(\d+)일', u_clean)
                if month_day:
                    date_hint = f"{month_day.group(1)}월{month_day.group(2)}일"
                
                console.print(f"[bold red]🗑️ 키워드 감지: {date_hint} 일정 삭제 시도[/bold red]")
                update_ui_function("SCHEDULE_DELETE", date_hint, "")
            
            # [추가] 일정 등록 키워드 직접 감지 (Heuristic fallback)
            elif any(k in u_clean for k in ["등록", "추가", "기록", "할일"]):
                if not match:
                    # 날짜 추측
                    date_hint = "오늘"
                    if "내일" in u_clean: date_hint = "내일"
                    month_day = re.search(r'(\d+)월(\d+)일', u_clean)
                    if month_day:
                        date_hint = f"{month_day.group(1)}월{month_day.group(2)}일"
                    
                    # 내용은 '일정' 또는 '등록' 앞부분 전체를 사용하거나 대략 추출
                    content_hint = user_input.replace("등록해줘", "").replace("추가해줘", "").strip()
                    console.print(f"[bold blue]💡 키워드 감지: '{date_hint}'에 '{content_hint}' 등록 시도[/bold blue]")
                    update_ui_function("REMINDER", content_hint, date_hint)

            # [추가] 일반 타이머 설정(카운트 다운)에 대한 Heuristic Fallback
            if is_timer_req and not match:
                # "10분 타이머", "1시간 반 뒤에 알려줘" 등
                # 위에서 카운트업/리셋은 이미 처리했으므로, 여기서는 다운(설정)만 처리
                if not any(k in u_clean for k in ["카운트업", "숫자커지게", "리셋", "종료", "취소"]):
                    console.print("[dim yellow]⚠ AI 명령어 누락 -> 사용자 발화에서 시간 추출 시도[/dim yellow]")
                    t_val = str(extracted_mins) if extracted_mins is not None else "5"
                    console.print(f"[bold magenta]⏳ [Fallback] {t_val}분 타이머 자동 설정[/bold magenta]")
                    update_ui_function("TIMER", "DOWN", t_val)

            clean_answer = raw_content
            if match:
                raw_cmd = match.group(0)
                cmd_type = match.group(1)
                cmd_data = match.group(2).split(':')
                
                # 디버그용 로그 출력
                console.print(f"[dim yellow][RAW CMD] {raw_cmd}[/dim yellow]")
                
                if cmd_type == "TIMER":
                    # 각 데이터 항목에서 공백 제거
                    t_val = cmd_data[0].strip() if len(cmd_data) > 0 else "5"
                    t_mode = cmd_data[1].strip().upper() if len(cmd_data) > 1 else "DOWN"
                    
                    # [Override] 사용자 발화에서 직접 시간이 추출되었다면 AI 결과 무시하고 덮어쓰기
                    if extracted_mins is not None and t_mode != "RESET":
                         console.print(f"[bold cyan]🎯 사용자 발화 시간 우선 적용: {t_val} -> {extracted_mins}[/bold cyan]")
                         t_val = str(extracted_mins)

                    # [추가] 사용자의 발화에 '카운트 업' 관련 키워드가 있으면 강제로 UP 모드 적용
                    if any(k in u_clean for k in ["카운트업", "숫자커지게", "숫자늘려", "올려줘"]):
                        t_mode = "UP"
                    # [추가] 종료 관련이면 강제로 RESET
                    if any(k in u_clean for k in ["종료", "중지", "꺼", "멈춰", "리셋", "초기화", "그만"]):
                        t_mode = "RESET"
                        t_val = "0"
                    
                    update_ui_function("TIMER", t_mode, t_val)
                elif cmd_type == "REMINDER":
                    date_val = cmd_data[0].strip() if len(cmd_data) > 0 else "오늘"
                    text_val = cmd_data[1].strip() if len(cmd_data) > 1 else "업무"
                    
                    # [강력 수정] AI가 '날짜'나 '내용'이라는 글자를 그대로 썼을 경우 Heuristic 적용
                    if date_val == "날짜" or text_val == "내일" or text_val == "내용" or text_val == "할일":
                        console.print("[bold red]⚠ AI가 플레이스홀더를 그대로 사용함 -> Heuristic 전환[/bold red]")
                        # 날짜 추출
                        month_day = re.search(r'(\d+)월(\d+)일', u_clean)
                        if month_day: date_val = f"{month_day.group(1)}월{month_day.group(2)}일"
                        elif "내일" in u_clean: date_val = "내일"
                        # 내용 추출
                        text_val = user_input.replace("등록해줘", "").replace("추가해줘", "").strip()
                    
                    update_ui_function("REMINDER", text_val, date_val)
                elif cmd_type == "DELETE_REMINDER":
                    date_val = cmd_data[0].strip() if len(cmd_data) > 0 else "오늘"
                    if date_val == "날짜":
                        month_day = re.search(r'(\d+)월(\d+)일', u_clean)
                        if month_day: date_val = f"{month_day.group(1)}월{month_day.group(2)}일"
                    update_ui_function("SCHEDULE_DELETE", date_val, "")
                elif cmd_type == "WEATHER":
                    raw_city = cmd_data[0].strip() if len(cmd_data) > 0 and cmd_data[0] else "Seoul"
                    
                    # [강력 수정] AI가 '도시명'을 썼거나, 도시명을 제대로 못 뽑았을 경우를 위한 통합 Heuristic
                    city_name = raw_city
                    if any(k in raw_city for k in ["도시명", "미정", "지역", "어디"]):
                        console.print("[bold red]⚠ AI가 플레이스홀더 사용 혹은 도시명 추출 실패 -> Heuristic 전환[/bold red]")
                        city_name = "Seoul" # 기본값
                    
                    # 발화 내용에서 실제 지명 찾기 (가장 정확)
                    if "서울" in u_clean or "Seoul" in user_input: city_name = "Seoul"
                    elif "부산" in u_clean or "Busan" in user_input: city_name = "Busan"
                    elif "사천" in u_clean or "Sacheon" in user_input: city_name = "Sacheon-si"
                    elif "인천" in u_clean or "Incheon" in user_input: city_name = "Incheon"
                    elif "대구" in u_clean or "Daegu" in user_input: city_name = "Daegu"
                    elif "대전" in u_clean or "Daejeon" in user_input: city_name = "Daejeon"
                    
                    # 만약 AI가 한글로 "부산"이라고만 보냈을 경우를 대비한 매핑
                    city_map = {"서울": "Seoul", "부산": "Busan", "사천": "Sacheon-si", "인천": "Incheon"}
                    if city_name in city_map: city_name = city_map[city_name]

                    console.print(f"[dim yellow][DEBUG] 최종 결정된 도시: {city_name} (입력값: {raw_city})[/dim yellow]")
                    weather_res = get_weather(city_name)
                    
                    if "error" not in weather_res:
                        # 1. 화면 위젯 업데이트를 위해 API 호출
                        try:
                            requests.post("http://127.0.0.1:5000/api/weather/update", json=weather_res, timeout=3)
                        except: pass
                        
                        # 2. 음성 응답용 텍스트 생성
                        w_text = f"현재 {city_name}의 기온은 {weather_res['temp']}도이며, {weather_res['condition']} 상태입니다."
                        clean_answer = f"{w_text} {re.sub(command_pattern, '', raw_content).strip()}"
                        update_ui_function("WEATHER", city_name, "")
                    else:
                        clean_answer = f"죄송합니다. {city_name}의 날씨 정보를 가져오지 못했습니다. {weather_res['error']}"
                
            # 모든 COMMAND 패턴, 생각(think) 태그 및 남은 대괄호 패턴 강제 제거
            clean_answer = re.sub(r"<think>.*?</think>", "", clean_answer, flags=re.DOTALL)
            clean_answer = re.sub(r"\[COMMAND:.*?\]", "", clean_answer)
            clean_answer = re.sub(r"\[.*?\]", "", clean_answer)
            clean_answer = clean_answer.replace("COMMAND:", "").strip()

            return clean_answer, tokens
        else:
            error_msg = res_json.get('error', {}).get('message', 'Unknown API Error')
            return f"오류가 발생했습니다: {error_msg}", 0
            
    except Exception as e:
        console.print(f"[red]❗ API 호출/처리 중 치명적 오류 발생: {e}[/red]")
        # 상세 스택트레이스 출력을 위해 타이핑이 가능하다면 좋겠지만, 일단 메시지만이라도 출력
        import traceback
        console.print(f"[dim red]{traceback.format_exc()}[/dim red]")
        return "연결 실패", 0

def main(on_message=None):
    r = sr.Recognizer()
    r.energy_threshold = 400
    r.dynamic_energy_threshold = True

    console.print(Panel("[bold cyan]👾 데브고치(MiniMax M2.1) 시스템 가동[/bold cyan]", 
                        subtitle="Standard API Mode (Timer/Weather Enabled)", border_style="cyan"))
    
    chat_history = []
    
    while True:
        with sr.Microphone() as source:
            # 시작 시 한 번 소음 조정
            console.print("[cyan]🎤 배경 소음 측정 중...[/cyan]")
            r.adjust_for_ambient_noise(source, duration=1)
            console.print(f"[cyan]✓ 측정 완료 (에너지 임계값: {int(r.energy_threshold)})[/cyan]")
            
            while True:
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
                        if on_message: on_message(user_input, "user")
                        req_id = str(uuid.uuid4())[:8]
                        start_time = time.time()
                        
                        console.print(f"[bold cyan]You>[/bold cyan] {user_input}")
                        
                        with Live(Spinner("dots", text="MiniMax 응답 생성 중..."), console=console, transient=True) as live:
                            full_answer, token_count = call_minimax_standard(user_input, chat_history)
                            live.update(Markdown(full_answer))
                        
                        if on_message: on_message(full_answer, "ai")
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
                
                # 루프 끝에서 아주 짧은 휴식 후 다시 루프
                time.sleep(0.1)

if __name__ == "__main__":
    main()