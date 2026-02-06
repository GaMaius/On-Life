import requests
import json

def get_weather(api_key, lat, lon):
    # API 엔드포인트 (주소)
    # units=metric: 섭씨 온도(°C) 사용
    # lang=kr: 한국어로 결과 받기
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=kr"

    try:
        response = requests.get(url)
        response.raise_for_status() # 오류 발생 시 예외 처리

        # JSON 데이터 파싱
        data = response.json()

        # 필요한 정보 추출
        location = data['name'] # 지역 이름
        weather_desc = data['weather'][0]['description'] # 날씨 상태 (예: 맑음, 구름 조금)
        
        # main 딕셔너리에 기온 정보가 들어있습니다.
        temp_current = data['main']['temp']       # 현재 기온
        temp_feels = data['main']['feels_like']   # 체감 온도
        temp_min = data['main']['temp_min']       # 최저 기온
        temp_max = data['main']['temp_max']       # 최고 기온

        # 결과 출력
        print(f"=== {location}의 현재 날씨 ===")
        print(f"날씨 상태: {weather_desc}")
        print(f"현재 기온: {temp_current}°C")
        print(f"체감 온도: {temp_feels}°C")
        print(f"최저/최고: {temp_min}°C / {temp_max}°C")

    except requests.exceptions.RequestException as e:
        print(f"연결 오류 발생: {e}")
    except KeyError:
        print("데이터를 찾을 수 없습니다. 좌표나 API 키를 확인해주세요.")

# === 설정 영역 ===
# 본인의 API 키를 입력하세요
MY_API_KEY = "f83c5f76153571e5cbd97d300cfdeea3"

# 현재 위치의 위도(lat), 경도(lon)
# 예시: 서울 시청 근처
MY_LAT = 37.5665
MY_LON = 126.9780

# 함수 실행
get_weather(MY_API_KEY, MY_LAT, MY_LON)