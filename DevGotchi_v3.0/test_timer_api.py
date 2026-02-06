import requests
import time

def test_timer_api():
    base_url = "http://127.0.0.1:5000"
    
    # 1. Set Timer (5 min Count Down)
    print("\n[TEST] 1. Setting Timer (5 min DOWN)...")
    payload = {"minutes": 5, "auto_start": True, "mode": "down"}
    try:
        res = requests.post(f"{base_url}/api/timer/set", json=payload, timeout=2)
        print("Set Response:", res.json())
    except Exception as e:
        print("Set Failed:", e)
        return

    # 2. Check Pending (Simulation of Frontend Polling)
    # The frontend polls this, so if we poll it here, the frontend might miss it if we steal it.
    # However, for verification, we can just check if the server accepted it (above) 
    # and then manually verifying in the browser is best.
    # Here we will just verify the endpoint exists and returns something if we are fast enough,
    # or just trust the Set response. 
    
    # Actually, let's just create a new command to consume ourselves for testing.
    time.sleep(1)
    
    print("\n[TEST] 2. Checking Pending Command...")
    try:
        res = requests.get(f"{base_url}/api/timer/pending", timeout=2)
        print("Pending Response:", res.json())
    except Exception as e:
        print("Pending Failed:", e)

    # 3. Reset Timer
    print("\n[TEST] 3. Resetting Timer...")
    payload = {"minutes": 0, "auto_start": False, "mode": "reset"}
    try:
        res = requests.post(f"{base_url}/api/timer/set", json=payload, timeout=2)
        print("Reset Response:", res.json())
    except Exception as e:
        print("Reset Failed:", e)

if __name__ == "__main__":
    test_timer_api()
