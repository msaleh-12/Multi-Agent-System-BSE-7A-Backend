"""
Simple test script to verify the API is working
Run this after starting the server with: uvicorn app.main:app --reload
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")

def test_similarity():
    """Test similarity detection"""
    print("Testing similarity detection...")
    data = {
        "text1": "Artificial intelligence is transforming the world.",
        "text2": "AI is changing the world."
    }
    response = requests.post(f"{BASE_URL}/api/v1/check-similarity", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

def test_rephrase():
    """Test rephrasing"""
    print("Testing rephrasing...")
    data = {
        "text": "Artificial intelligence is transforming the way we work.",
        "preserve_meaning": True
    }
    response = requests.post(f"{BASE_URL}/api/v1/rephrase-text", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

def test_process():
    """Test main processing endpoint"""
    print("Testing main processing endpoint...")
    with open("example_request.json", "r") as f:
        data = json.load(f)
    
    response = requests.post(f"{BASE_URL}/api/v1/process-text", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

if __name__ == "__main__":
    try:
        test_health()
        test_similarity()
        test_rephrase()
        test_process()
        print("All tests completed!")
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API. Make sure the server is running:")
        print("  uvicorn app.main:app --reload")
    except Exception as e:
        print(f"Error: {e}")

