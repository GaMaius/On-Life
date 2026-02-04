# pandas 패키지 깔아야함

import pandas as pd
import os
import matplotlib.pyplot as plt

# 1. 데이터 로그 초기화
LOG_FILE = 'user_posture_log.csv'

def save_current_posture(neck_angle, back_angle):
    """실시간으로 수집된 좌표/각도를 CSV에 한 줄씩 추가"""
    new_data = pd.DataFrame([{
        'timestamp': pd.Timestamp.now(),
        'neck_angle': neck_angle,
        'back_angle': back_angle
    }])
    
    # 파일이 없으면 새로 만들고, 있으면 한 줄 추가(append)
    if not os.path.isfile(LOG_FILE):
        new_data.to_csv(LOG_FILE, index=False)
    else:
        new_data.to_csv(LOG_FILE, mode='a', header=False, index=False)

# 2. 분석 및 그래프 생성 로직 (데이터가 있을 때만 실행)
def generate_dynamic_report():
    if not os.path.isfile(LOG_FILE):
        return None, "데이터가 아직 부족합니다. 수집을 시작하세요!"
    
    df = pd.read_csv(LOG_FILE)
    
    # 데이터가 최소 5개는 쌓여야 그래프를 그림
    if len(df) < 5:
        return None, f"데이터 수집 중... (현재 {len(df)}개 / 최소 5개 필요)"
    
    # 그래프 생성
    plt.figure(figsize=(8, 4))
    plt.plot(df['neck_angle'], label='Neck', color='#00ffcc')
    plt.plot(df['back_angle'], label='Back', color='#ff3366')
    plt.title("Real-time Posture Log")
    plt.savefig('real_posture_report.png')
    plt.close()
    
    return df.iloc[-1].to_dict(), "분석 리포트가 갱신되었습니다."
