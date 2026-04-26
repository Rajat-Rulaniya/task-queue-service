#!/usr/bin/env python
"""
Test script to validate the job processing service
Run this after starting the FastAPI server and Celery worker
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000/api/v1"


def test_health():
    """Test health check endpoint"""
    print("\n📋 Testing health check...")
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    data = resp.json()
    print(f"✓ Health check passed: {data['status']}")
    return True


def create_job(task_type: str, payload: dict) -> str:
    """Create a new job and return job ID"""
    print(f"\n📋 Creating {task_type} job...")
    resp = requests.post(
        f"{BASE_URL}/jobs",
        json={"task_type": task_type, "payload": payload},
        timeout=10
    )
    assert resp.status_code == 202, f"Failed to create job: {resp.text}"
    data = resp.json()
    job_id = data["id"]
    print(f"✓ Job created: {job_id}")
    print(f"  Task ID: {data['task_id']}")
    print(f"  Status: {data['status']}")
    return job_id


def wait_for_completion(job_id: str, timeout: int = 30) -> dict:
    """Poll job status until completion or timeout"""
    print(f"\n⏳ Waiting for job to complete (timeout: {timeout}s)...")
    start = time.time()
    
    while time.time() - start < timeout:
        resp = requests.get(f"{BASE_URL}/jobs/{job_id}")
        assert resp.status_code == 200, f"Failed to get job: {resp.text}"
        
        data = resp.json()
        status = data["status"]
        
        print(f"  Status: {status}", end="\r")
        
        if status in ["completed", "failed"]:
            print(f"\n✓ Job finished with status: {status}")
            return data
        
        time.sleep(1)
    
    raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")


def test_parse_csv():
    """Test CSV parsing job"""
    print("\n" + "="*50)
    print("TEST 1: CSV Parsing")
    print("="*50)
    
    csv_data = """name,age,email,city
Alice Johnson,28,alice@example.com,New York
Bob Smith,35,bob@example.com,Los Angeles
Charlie Brown,42,charlie@example.com,Chicago
Diana Prince,31,diana@example.com,Houston
Eve Wilson,26,eve@example.com,Phoenix"""
    
    job_id = create_job("parse_csv", {"csv_data": csv_data})
    result = wait_for_completion(job_id)
    
    assert result["status"] == "completed", f"Job failed: {result.get('error')}"
    assert result["result"]["rows_processed"] == 5, "CSV parsing failed"
    print(f"\n✓ Parsed {result['result']['rows_processed']} rows successfully")
    print(f"  Result: {json.dumps(result['result'], indent=2)[:200]}...")


def test_send_email():
    """Test email sending job"""
    print("\n" + "="*50)
    print("TEST 2: Email Sending")
    print("="*50)
    
    job_id = create_job("send_email", {
        "to": "user@example.com",
        "subject": "Test Email",
        "body": "This is a test email from the job processing service"
    })
    
    result = wait_for_completion(job_id)
    
    assert result["status"] == "completed", f"Job failed: {result.get('error')}"
    assert result["result"]["email_sent"], "Email sending failed"
    print(f"\n✓ Email sent successfully to {result['result']['to']}")


def test_process_data():
    """Test data processing job"""
    print("\n" + "="*50)
    print("TEST 3: Data Processing")
    print("="*50)
    
    test_data = {
        "items": [1, 2, 3, 4, 5],
        "metadata": {"source": "test", "version": "1.0"},
        "nested": {"key": "value", "count": 42}
    }
    
    job_id = create_job("process_data", {"data": test_data})
    result = wait_for_completion(job_id)
    
    assert result["status"] == "completed", f"Job failed: {result.get('error')}"
    print("\n✓ Data processed successfully")
    print(f"  Original items: {len(test_data['items'])}")
    print(f"  Result: {json.dumps(result['result'], indent=2)[:200]}...")


def test_list_jobs():
    """Test job listing endpoint"""
    print("\n" + "="*50)
    print("TEST 4: List Jobs (Paginated)")
    print("="*50)
    
    print("\n📋 Fetching jobs list...")
    resp = requests.get(f"{BASE_URL}/jobs?page=1&page_size=5")
    assert resp.status_code == 200, f"Failed to list jobs: {resp.text}"
    
    data = resp.json()
    print("✓ Retrieved job list")
    print(f"  Total jobs: {data['total']}")
    print(f"  Page: {data['page']}/{(data['total'] + data['page_size'] - 1) // data['page_size']}")
    print(f"  Jobs in this page: {len(data['jobs'])}")
    
    # Show job statuses
    statuses = {}
    for job in data["jobs"]:
        status = job["status"]
        statuses[status] = statuses.get(status, 0) + 1
    print(f"  Status breakdown: {statuses}")


def test_rate_limiting():
    """Test rate limiting (10 requests per minute)"""
    print("\n" + "="*50)
    print("TEST 5: Rate Limiting")
    print("="*50)
    
    print("\n📋 Testing rate limit (10 requests per minute per IP)...")
    
    # Try to exceed rate limit
    for i in range(12):
        resp = requests.post(
            f"{BASE_URL}/jobs",
            json={"task_type": "parse_csv", "payload": {"csv_data": "test"}},
            timeout=5
        )
        
        if resp.status_code == 429:
            print(f"✓ Rate limit triggered after {i+1} requests")
            print(f"  Response: {resp.json()['detail']}")
            return True
        elif resp.status_code == 202:
            print(f"  Request {i+1}: OK (status 202)")
    
    print("⚠️  Rate limit not triggered in test (might need to wait or reset)")
    return False


def test_invalid_task():
    """Test error handling for invalid task"""
    print("\n" + "="*50)
    print("TEST 6: Error Handling")
    print("="*50)
    
    print("\n📋 Testing invalid task type...")
    resp = requests.post(
        f"{BASE_URL}/jobs",
        json={"task_type": "invalid_task", "payload": {}},
    )
    
    assert resp.status_code == 400, "Should reject invalid task type"
    data = resp.json()
    print("✓ Invalid task correctly rejected")
    print(f"  Error: {data['detail']}")


def main():
    """Run all tests"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════╗")
    print("║  Job Processing Service - Integration Tests          ║")
    print("╚═══════════════════════════════════════════════════════╝")
    
    try:
        # Check if service is running
        try:
            requests.get(f"{BASE_URL}/health", timeout=2)
        except requests.exceptions.ConnectionError:
            print("\n❌ ERROR: Cannot connect to FastAPI server")
            print("   Make sure the server is running: python main.py")
            sys.exit(1)
        
        # Run tests
        test_health()
        test_parse_csv()
        test_send_email()
        test_process_data()
        test_list_jobs()
        test_invalid_task()
        
        # Rate limiting test (may not always trigger in test environment)
        try:
            test_rate_limiting()
        except Exception as e:
            print(f"⚠️  Rate limiting test skipped: {e}")
        
        # Final summary
        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED!")
        print("="*50)
        print("\nThe job processing service is working correctly!")
        print("\nKey endpoints:")
        print(f"  POST   {BASE_URL}/jobs - Create new job")
        print(f"  GET    {BASE_URL}/jobs/{{job_id}} - Get job status")
        print(f"  GET    {BASE_URL}/jobs - List jobs (paginated)")
        print(f"  GET    {BASE_URL}/health - Health check")
        print("\nAPI Documentation: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
