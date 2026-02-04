import json
import os

DATA_FILE = "user_data.json"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f"Current HP: {data.get('hp')}")
        print(f"Current Level: {data.get('level')}")
        print(f"Quests: {len(data.get('quests', []))} active")
else:
    print("No user_data.json found.")
