import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(method, path, test_name, data=None, headers=None):
    url = f"{BASE_URL}{path}"
    start_time = time.time()
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method.upper() == "PATCH":
            response = requests.patch(url, json=data, headers=headers, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # milliseconds
        
        try:
            json_data = response.json()
            has_json = True
        except:
            json_data = None
            has_json = False
            
        result = {
            "test_name": test_name,
            "method": method,
            "path": path,
            "status_code": response.status_code,
            "response_time_ms": round(response_time, 2),
            "success": 200 <= response.status_code < 300,
            "content_length": len(response.content),
            "has_json": has_json,
            "error": None
        }
        return result
    except Exception as e:
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        return {
            "test_name": test_name,
            "method": method,
            "path": path,
            "status_code": 0,
            "response_time_ms": round(response_time, 2),
            "success": False,
            "content_length": 0,
            "has_json": False,
            "error": str(e)
        }

def main():
    results = []
    
    # Test endpoints
    results.append(test_endpoint("GET", "/", "Root endpoint"))
    results.append(test_endpoint("GET", "/api/karma", "GET /api/karma"))
    
    chat_data = {"message": "Test message"}
    results.append(test_endpoint("POST", "/api/chat", "POST /api/chat", data=chat_data))
    
    results.append(test_endpoint("GET", "/api/tasks", "GET /api/tasks"))
    
    # Test with invalid UUID
    results.append(test_endpoint("PATCH", "/api/tasks/00000000-0000-0000-0000-000000000000", 
                                "PATCH /api/tasks/{id} (invalid ID)", data={}))
    
    results.append(test_endpoint("GET", "/api/health", "GET /api/health"))
    results.append(test_endpoint("GET", "/api/provider-health", "GET /api/provider-health"))
    results.append(test_endpoint("GET", "/api/provider-audit", "GET /api/provider-audit"))
    results.append(test_endpoint("GET", "/api/token-audit", "GET /api/token-audit"))
    results.append(test_endpoint("GET", "/api/karma-summary", "GET /api/karma-summary"))
    
    # Print results
    print("\\nTest Results:")
    print("{:<50} {:<8} {:<12} {:<10} {}".format("Test", "Status", "Time(ms)", "Success", "Error"))
    print("-" * 90)
    for result in results:
        status = f"{result['status_code']}" if result['status_code'] != 0 else "ERROR"
        time_str = f"{result['response_time_ms']}" if result['response_time_ms'] else "N/A"
        success_str = "PASS" if result['success'] else "FAIL"
        error_str = (result['error'][:30] if result['error'] else "") if result['error'] else ""
        print("{:<50} {:<8} {:<12} {:<10} {}".format(
            result['test_name'], status, time_str, success_str, error_str))
    
    # Summary
    passed = sum(1 for r in results if r['success'])
    failed = len(results) - passed
    print(f"\\nSummary: {passed} passed, {failed} failed")
    
    # Save results to file
    with open('.\\tests\\api_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
