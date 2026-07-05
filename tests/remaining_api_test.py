import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"
passed = 0
failed = 0

def test(method, path, data=None, timeout=30):
    global passed, failed
    try:
        if method == "GET":
            r = requests.get(f"{BASE_URL}{path}", timeout=timeout)
        elif method == "POST":
            r = requests.post(f"{BASE_URL}{path}", json=data, timeout=timeout)
        else:
            r = requests.request(method, f"{BASE_URL}{path}", json=data, timeout=timeout)

        ok = 200 <= r.status_code < 300
        if ok:
            print(f"PASS [{r.status_code}] {method} {path}")
            passed += 1
        else:
            print(f"FAIL [{r.status_code}] {method} {path}: {r.text[:150]}")
            failed += 1
        return r
    except Exception as e:
        print(f"FAIL [ERR] {method} {path}: {e}")
        failed += 1
        return None

# Test daily review as POST (correct method)
r = test("POST", "/api/review/daily", {"user_id": "default_user", "focus": "daily_start"})
if r and r.status_code == 200:
    data = r.json()
    print(f"  Review date: {data.get('review_date')}, completion: {data.get('completion_rate')}")

# Test tasks/generate with correct schema
payload = {
    "user_id": "default_user",
    "goal": "Build a morning workout habit",
    "struggle": "Lack of consistency",
    "max_tasks_to_generate": 2,
    "energy_level": "medium",
}
r = test("POST", "/api/tasks/generate", payload, timeout=30)
if r and r.status_code == 200:
    data = r.json()
    print(f"  Generated {len(data.get('tasks', []))} tasks")
    print(f"  Strategy: {data.get('strategy_used', 'N/A')}")
    print(f"  Confidence: {data.get('confidence', 'N/A')}")

# Test tasks/active with user_id
r = test("GET", "/api/tasks/active?user_id=default_user")
if r and r.status_code == 200:
    data = r.json()
    print(f"  Active tasks: {len(data.get('tasks', []))}")

# Test tasks/history with user_id
r = test("GET", "/api/tasks/history?user_id=default_user")
if r and r.status_code == 200:
    data = r.json()
    print(f"  History tasks: {len(data.get('tasks', []))}")

# Test tasks/{id}/complete and fail (need a real task - skip if none)
# Test identity endpoint
r = test("GET", "/api/identity")
if r and r.status_code == 200:
    data = r.json()
    print(f"  Identity user_id: {data.get('user_id', 'N/A')}")

# Test users endpoint
r = test("GET", "/api/users")
if r and r.status_code == 200:
    data = r.json()
    print(f"  Users: {data}")

# Summary
total = passed + failed
print(f"\n=== REMAINING API TESTS: {passed}/{total} passed, {failed} failed ===")
exit(0 if failed == 0 else 1)