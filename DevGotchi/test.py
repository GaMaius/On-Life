import requests
import json

# 방금 주신 새 API 키
NEW_API_KEY = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiLsobDshLHtmLgiLCJVc2VyTmFtZSI6IuyhsOyEse2YuCIsIkFjY291bnQiOiIiLCJTdWJqZWN0SUQiOiIxOTMyNzg4MDg5OTQwMzQ5MzU3IiwiUGhvbmUiOiIiLCJHcm91cElEIjoiMTkzMjc4ODA4OTkzMTk2MDc0OSIsIlBhZ2VOYW1lIjoiIiwiTWFpbCI6ImRvbmdoYWUyQGtvZGVrb3JlYS5rciIsIkNyZWF0ZVRpbWUiOiIyMDI1LTExLTExIDE3OjQ4OjAzIiwiVG9rZW5UeXBlIjoxLCJpc3MiOiJtaW5pbWF4In0.zC_Qvd46kgOslNn6ub2q3b96q6zZxRMEfACOxrfR96tXuFw4RXSTCRQDrlegUHd9NYq4D1jp983hwJNqilx7TUM8Jqcc2PkJDkv3QC7D3DULil7KuPyvVHFoebdC0U1bp4KfckM79hfyzGCbx-iAw912QtAUjHqqnStE7n_ppvm3xwqmGAphpaflcrm2PxF_ByZR9YjZOBAUM6dfRlDwrrrajDPmzVQZH_eB-Ru-phSnGc98bJVc--gm-jcN1mFigAmdaqvwVkgNJXn7OPPaNXSc2E7H8V2LcbuOmv7CBDjtSUdFqIY3Tr-Vj_MlpCfl-N_jm1Q_qvjduSldN4s8cQ"

# 키에서 추출한 Group ID
GROUP_ID = "1932788089931960749"

url = f"https://api.minimax.chat/v1/text/chatcompletion_v2?GroupId={GROUP_ID}"

headers = {
    "Authorization": f"Bearer {NEW_API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "abab5.5-chat",
    "messages": [{"sender_type": "USER", "sender_name": "User", "text": "Hello"}],
    "bot_setting": [{"bot_name": "Bot", "content": "Assistant"}],
    "reply_constraints": {"sender_type": "BOT", "sender_name": "Bot"}
}

try:
    print("Testing API Key...")
    response = requests.post(url, headers=headers, json=payload, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")