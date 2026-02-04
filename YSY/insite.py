# pandas 패키지 깔아야 함

import math
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 1. 사선 각도 계산 함수
def calculate_side_angles(ear, shoulder, hip):
    # 수직선(Vertical) 대비 목과 등의 기울기 계산
    # ear, shoulder, hip은 각각 [x, y] 좌표
    neck_angle = math.degrees(math.atan2(abs(ear[0] - shoulder[0]), abs(ear[1] - shoulder[1])))
    back_angle = math.degrees(math.atan2(abs(shoulder[0] - hip[0]), abs(shoulder[1] - hip[1])))
    return neck_angle, back_angle

# 2. 데이터 수집 시뮬레이션 (최근 7회차 기록)
data = {
    'Session': ['1회', '2회', '3회', '4회', '5회', '6회', '오늘'],
    'Neck_Angle': [15, 18, 25, 30, 28, 35, 42], # 높을수록 거북목 심화
    'Back_Angle': [10, 12, 15, 20, 22, 25, 30]  # 높을수록 등이 굽음
}
df = pd.DataFrame(data)

# 3. 인사이트 제공용 인포그래픽 생성
def generate_infographic(df):
    plt.style.use('dark_background')
    fig, ax1 = plt.subplots(figsize=(10, 5))

    # 목 각도 추이 (Line Chart)
    ax1.plot(df['Session'], df['Neck_Angle'], color='#00ffcc', marker='o', label='Neck Angle (Turtle)')
    ax1.set_ylabel('Angle (Degrees)', color='white')
    ax1.tick_params(axis='y', labelcolor='#00ffcc')

    # 등 굽음 추이 (Bar Chart)
    ax2 = ax1.twinx()
    ax2.bar(df['Session'], df['Back_Angle'], color='#ff3366', alpha=0.3, label='Back Angle (Slumped)')
    ax2.set_ylim(0, 50)
    
    plt.title("Side-view Posture Trend Analysis", color='white', size=15)
    fig.tight_layout()
    plt.savefig('posture_insight.png', transparent=True)
    return df.iloc[-1].to_dict() # 오늘의 데이터 반환

current_stat = generate_infographic(df)
print(current_stat)
