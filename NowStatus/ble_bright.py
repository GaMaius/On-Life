import asyncio
from bleak import BleakScanner, BleakClient
from flask import Flask
from flask_socketio import SocketIO
import threading

# Flask 서버 설정
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# 원정님이 확인한 UUID (128비트 풀 형식)
CHARACTERISTIC_UUID = "00002ac8-0000-1000-8000-00805f9b34fb"

def notification_handler(sender, data):
    """아이폰에서 텍스트를 보냈을 때 실행"""
    try:
        message = data.decode('utf-8')
        print(f"아이폰 알림 수신: {message}")
        socketio.emit('new_notification', {'msg': message})
    except Exception as e:
        print(f"데이터 해석 에러: {e}")

async def run_ble():
    print("아이폰(iPhone) 찾는 중...")
    while True:
        # 'iPhone'이라는 이름으로 기기 검색
        device = await BleakScanner.find_device_by_name("iPhone")
        if device:
            print(f"아이폰 연결 시도 중: {device.address}")
            try:
                async with BleakClient(device) as client:
                    print("연결 성공! 이제 아이폰 앱에서 Value를 업데이트하세요.")
                    await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
                    while client.is_connected:
                        await asyncio.sleep(1)
            except Exception as e:
                print(f"연결 끊김 또는 에러: {e}")
        else:
            print("아이폰을 찾을 수 없습니다. nRF Connect 앱의 광고 스위치를 확인하세요.")
            await asyncio.sleep(5)

def start_ble_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_ble())

if __name__ == "__main__":
    # 블루투스 루프를 별도 스레드에서 실행
    threading.Thread(target=start_ble_loop, daemon=True).start()
    # 웹소켓 서버 실행 (포트 5001)
    socketio.run(app, host='0.0.0.0', port=5001)
