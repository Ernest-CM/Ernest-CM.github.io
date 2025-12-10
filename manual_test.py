#!/usr/bin/env python
"""
Manual test script for the Customer Support Resolution Agent API
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint"""
    print("=" * 60)
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_csv_upload_issue():
    """Test CSV upload issue workflow"""
    print("=" * 60)
    print("Test 1: CSV Upload Issue (Auto-Resolve)")
    print("=" * 60)
    
    # Step 1: Submit ticket
    print("\n1. Submitting ticket...")
    ticket_data = {
        "ticket_id": "t100",
        "user_id": "u123",
        "subject": "App crashes on CSV upload v2.1",
        "body": "When I upload CSV it crashes with stacktrace X..."
    }
    
    response = requests.post(f"{BASE_URL}/webhook/ticket", json=ticket_data)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    # Step 2: Get plan
    print("\n2. Getting plan...")
    response = requests.get(f"{BASE_URL}/ticket/t100/plan")
    print(f"Status: {response.status_code}")
    plan = response.json()
    print(f"Plan: {json.dumps(plan, indent=2)}")
    
    print()

def test_password_reset():
    """Test password reset workflow (requires approval)"""
    print("=" * 60)
    print("Test 2: Password Reset (Requires Approval)")
    print("=" * 60)
    
    # Step 1: Submit ticket
    print("\n1. Submitting password reset ticket...")
    ticket_data = {
        "ticket_id": "t200",
        "user_id": "u456",
        "subject": "Password reset request",
        "body": "I forgot my password and need to reset it."
    }
    
    response = requests.post(f"{BASE_URL}/webhook/ticket", json=ticket_data)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    # Step 2: Get plan
    print("\n2. Getting plan...")
    response = requests.get(f"{BASE_URL}/ticket/t200/plan")
    print(f"Status: {response.status_code}")
    plan = response.json()
    print(f"Plan: {json.dumps(plan, indent=2)}")
    
    # Step 3: Approve if needed
    if plan.get("requires_approval"):
        print("\n3. Approving plan...")
        response = requests.post(f"{BASE_URL}/ticket/t200/approve", json={"approved": True})
        print(f"Status: {response.status_code}")
        approval_result = response.json()
        print(f"Approval result: {json.dumps(approval_result, indent=2)}")
    
    print()

def test_metrics():
    """Test metrics endpoint"""
    print("=" * 60)
    print("Testing metrics endpoint...")
    response = requests.get(f"{BASE_URL}/metrics")
    print(f"Status: {response.status_code}")
    print(f"Metrics: {json.dumps(response.json(), indent=2)}")
    print()

if __name__ == "__main__":
    try:
        print("\n" + "=" * 60)
        print("Customer Support Resolution Agent - Manual Tests")
        print("=" * 60)
        print(f"Base URL: {BASE_URL}")
        print()
        
        # Give server time to start if needed
        time.sleep(2)
        
        test_health()
        test_csv_upload_issue()
        test_password_reset()
        test_metrics()
        
        print("=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print(f"\nError: Could not connect to {BASE_URL}")
        print("Make sure the server is running: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\nError: {e}")
