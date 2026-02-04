import asyncio
from bleak import BleakScanner, BleakClient
from flask import Flask
from flask_socketio import SocketIO

# 웹 서버 설정
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# 아이폰 nRF Connect에서 설정한 서비스 UUID (예시입니다. 직접 정하셔도 됩니다.)
CHARACTERISTIC_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

def notification_handler(sender, data):
    """아이폰에서 데이터를 받았을 때 실행되는 함수"""
    message = data.decode('utf-8')
    print(f"아이폰 알림 수신: {message}")
    # 웹 브라우저로 실시간 전송
    socketio.emit('new_notification', {'msg': message})

async def run_ble():
    print("아이폰(nRF Connect)을 찾는 중...")
    # 실제 아이폰의 이름이나 주소로 필터링 가능
    device = await BleakScanner.find_device_by_name("iPhone") 
    
    if device:
        async with BleakClient(device) as client:
            print(f"아이폰 연결 성공: {device.address}")
            # 데이터 수신 시작
            await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
            while True:
                await asyncio.sleep(1) # 연결 유지
    else:
        print("아이폰을 찾을 수 없습니다.")

if __name__ == "__main__":
    import threading
    # 블루투스 루프를 별도 스레드에서 실행
    loop = asyncio.get_event_loop()
    threading.Thread(target=loop.run_until_complete, args=(run_ble(),)).start()
    
    # 웹 소켓 서버 실행
    socketio.run(app, host='0.0.0.0', port=5001)