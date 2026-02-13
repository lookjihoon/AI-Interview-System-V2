"""
Test script for API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    print("=" * 80)
    print("Testing AI Interview System API")
    print("=" * 80)
    
    # Test 1: Initialize Seed Data
    print("\n1. Testing POST /api/system/init-data")
    print("-" * 80)
    try:
        response = requests.post(f"{BASE_URL}/api/system/init-data")
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: List Job Postings
    print("\n2. Testing GET /api/recruit/jobs")
    print("-" * 80)
    try:
        response = requests.get(f"{BASE_URL}/api/recruit/jobs")
        print(f"Status Code: {response.status_code}")
        jobs = response.json()
        print(f"Found {len(jobs)} job posting(s)")
        for job in jobs:
            print(f"\nJob ID: {job['id']}")
            print(f"Title: {job['title']}")
            print(f"Status: {job['status']}")
            print(f"Min Experience: {job['min_experience']} years")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Get User (KimDev)
    print("\n3. Testing GET /api/candidate/users/2")
    print("-" * 80)
    try:
        response = requests.get(f"{BASE_URL}/api/candidate/users/2")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            user = response.json()
            print(f"User ID: {user['id']}")
            print(f"Name: {user['name']}")
            print(f"Email: {user['email']}")
            print(f"Role: {user['role']}")
        else:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Get User Resume
    print("\n4. Testing GET /api/candidate/users/2/resume")
    print("-" * 80)
    try:
        response = requests.get(f"{BASE_URL}/api/candidate/users/2/resume")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            resume_data = response.json()
            print(f"User: {resume_data['name']}")
            print(f"Resume Length: {len(resume_data['resume_text'])} characters")
            print(f"Resume Preview:")
            print(resume_data['resume_text'][:200] + "...")
        else:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 5: Health Check
    print("\n5. Testing GET /api/health")
    print("-" * 80)
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 80)
    print("API Testing Complete!")
    print("=" * 80)

if __name__ == "__main__":
    test_api()
