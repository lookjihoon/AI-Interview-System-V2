"""
Test Interview API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_interview_flow():
    print("=" * 80)
    print("Testing AI Interview System - Interview Flow")
    print("=" * 80)
    
    # Test 1: Start Interview
    print("\n1. Testing POST /api/interview/start")
    print("-" * 80)
    try:
        start_data = {
            "user_id": 2,  # KimDev
            "job_id": 1    # Python Backend Developer
        }
        response = requests.post(f"{BASE_URL}/api/interview/start", json=start_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 201:
            session_data = response.json()
            session_id = session_data["session_id"]
            print(f"Session ID: {session_id}")
            print(f"User: {session_data['user_name']}")
            print(f"Job: {session_data['job_title']}")
            print(f"Greeting: {session_data['message'][:100]}...")
        else:
            print(f"Response: {response.json()}")
            return
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # Test 2: Get First Question
    print("\n2. Testing POST /api/interview/chat (First Question)")
    print("-" * 80)
    try:
        chat_data = {
            "session_id": session_id
        }
        response = requests.post(f"{BASE_URL}/api/interview/chat", json=chat_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            chat_response = response.json()
            first_question = chat_response["next_question"]
            question_id = chat_response["question_id"]
            category = chat_response["category"]
            
            print(f"Question ID: {question_id}")
            print(f"Category: {category}")
            print(f"Question: {first_question[:150]}...")
        else:
            print(f"Response: {response.json()}")
            return
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # Test 3: Answer Question and Get Next
    print("\n3. Testing POST /api/interview/chat (Answer + Next Question)")
    print("-" * 80)
    try:
        answer_data = {
            "session_id": session_id,
            "user_answer": "I have 5 years of experience with Python, primarily using FastAPI and Django for building RESTful APIs. I've worked extensively with PostgreSQL for database management and have implemented caching strategies using Redis. I'm also familiar with Docker and Kubernetes for containerization and orchestration."
        }
        response = requests.post(f"{BASE_URL}/api/interview/chat", json=answer_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            chat_response = response.json()
            
            # Show evaluation
            if chat_response.get("evaluation"):
                eval_data = chat_response["evaluation"]
                print(f"\nEvaluation:")
                print(f"  Score: {eval_data.get('score', 'N/A')}/100")
                print(f"  Feedback: {eval_data.get('feedback', 'N/A')[:150]}...")
                print(f"  Follow-up: {eval_data.get('follow_up_question', 'N/A')[:100]}...")
            
            # Show next question
            next_question = chat_response["next_question"]
            question_id = chat_response["question_id"]
            category = chat_response["category"]
            
            print(f"\nNext Question:")
            print(f"  Question ID: {question_id}")
            print(f"  Category: {category}")
            print(f"  Question: {next_question[:150]}...")
        else:
            print(f"Response: {response.json()}")
            return
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # Test 4: Get Session Details
    print("\n4. Testing GET /api/interview/session/{session_id}")
    print("-" * 80)
    try:
        response = requests.get(f"{BASE_URL}/api/interview/session/{session_id}")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            session_details = response.json()
            print(f"Session ID: {session_details['session_id']}")
            print(f"User: {session_details['user_name']}")
            print(f"Job: {session_details['job_title']}")
            print(f"Status: {session_details['status']}")
            print(f"Transcript Items: {len(session_details['transcript'])}")
            
            print(f"\nTranscript Preview:")
            for i, item in enumerate(session_details['transcript'][:3]):
                print(f"  [{i+1}] {item['sender']}: {item['content'][:80]}...")
        else:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 5: End Interview
    print("\n5. Testing POST /api/interview/session/{session_id}/end")
    print("-" * 80)
    try:
        response = requests.post(f"{BASE_URL}/api/interview/session/{session_id}/end")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            end_response = response.json()
            print(f"Message: {end_response['message']}")
            print(f"Final Status: {end_response['status']}")
        else:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 80)
    print("Interview Flow Testing Complete!")
    print("=" * 80)

if __name__ == "__main__":
    test_interview_flow()
