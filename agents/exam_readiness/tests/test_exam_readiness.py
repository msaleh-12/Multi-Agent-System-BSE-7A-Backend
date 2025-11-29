"""
Integration test for Exam Readiness Agent Pipeline
Tests: PDF upload -> RAG retrieval -> Assessment generation -> PDF export
"""
import requests
import time
from pathlib import Path

SUPERVISOR_URL = "http://localhost:8000"
EXAM_READINESS_URL = "http://localhost:8003"

# This file is in agents/exam_readiness/tests/
# parent.parent gives us agents/exam_readiness/
BASE_DIR = Path(__file__).parent.parent
RAG_DOCUMENTS_DIR = BASE_DIR / "rag_documents"
GENERATED_ASSESSMENTS_DIR = BASE_DIR / "generated_assessments"

TEST_PDF_FILENAME = "python_tutorial.pdf"


def wait_for_service(url, name, timeout=30):
    retries = timeout // 2
    while retries > 0:
        try:
            r = requests.get(f"{url}/health", timeout=2)
            if r.status_code == 200:
                print(f"✓ {name} is up!")
                return True
        except:
            print(f"⏳ Waiting for {name}...")
            time.sleep(2)
            retries -= 1
    return False


def login():
    r = requests.post(f"{SUPERVISOR_URL}/api/auth/login", json={"email": "test@example.com", "password": "password"})
    assert r.status_code == 200
    print("✓ Login successful")
    return r.json()["token"]


def test_basic_generation():
    print("\n" + "="*70)
    print("TEST 1: Basic Assessment Generation")
    print("="*70)
    
    #assert wait_for_service(SUPERVISOR_URL, "Supervisor")
   # assert wait_for_service(EXAM_READINESS_URL, "Exam Readiness")
    
    token = login()
    
    print("🔄 Sending request to supervisor...")
    r = requests.post(
        f"{SUPERVISOR_URL}/api/supervisor/request",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "agentId": "exam-readiness-agent",
            "request": "Generate a Python quiz",
            "subject": "Python Programming",
            "assessment_type": "quiz",
            "difficulty": "easy",
            "question_count": 3,
            "type_counts": {"mcq": 2, "short_text": 1}
        },
        timeout=120
    )
    
    print(f"📥 Response status: {r.status_code}")
    print(f"📥 Response body: {r.text[:500]}...")
    
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    print(f"✓ Response parsed successfully")
    
    if data.get("error"):
        print(f"❌ Error in response: {data['error']}")
        raise AssertionError(f"Response contains error: {data['error']}")
    
    assert "response" in data, f"Missing 'response' key in data: {data.keys()}"
    assert "total_questions" in data["response"], f"Missing 'total_questions' in response: {data['response'].keys()}"
    assert data["response"]["total_questions"] == 3, f"Expected 3 questions, got {data['response']['total_questions']}"
    
    print(f"✓ Generated: {data['response']['title']}")
    print("✅ TEST 1 PASSED\n")


def test_complete_pipeline():
    print("\n" + "="*70)
    print("TEST 2: Complete Pipeline (RAG + Generation + PDF)")
    print("="*70)
    
    pdf_path = RAG_DOCUMENTS_DIR / TEST_PDF_FILENAME
    if not pdf_path.exists():
        print(f"⚠️  Test PDF not found: {pdf_path}")
        print("Skipping test")
        return
    
    #assert wait_for_service(SUPERVISOR_URL, "Supervisor")
    #assert wait_for_service(EXAM_READINESS_URL, "Exam Readiness")
    
    token = login()
    
    print("🔄 Sending request with RAG + PDF export...")
    r = requests.post(
        f"{SUPERVISOR_URL}/api/supervisor/request",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "agentId": "exam-readiness-agent",
            "request": "Generate quiz with RAG and PDF export",
            "subject": "Python Programming",
            "assessment_type": "quiz",
            "difficulty": "medium",
            "question_count": 5,
            "type_counts": {"mcq": 3, "short_text": 2},
            "pdf_input_paths": [TEST_PDF_FILENAME],
            "use_rag": True,
            "export_pdf": True,
            "pdf_output_filename": "test_output.pdf"
        },
        timeout=120
    )
    
    print(f"📥 Response status: {r.status_code}")
    print(f"📥 Response body: {r.text[:500]}...")
    
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    print(f"✓ Response parsed successfully")
    
    if data.get("error"):
        print(f"❌ Error in response: {data['error']}")
        raise AssertionError(f"Response contains error: {data['error']}")
    
    assessment = data["response"]
    assert assessment["total_questions"] == 5, f"Expected 5 questions, got {assessment['total_questions']}"
    assert assessment["metadata"]["used_rag"] is True, "RAG was not used"
    
    metadata = data.get("metadata", {})
    assert metadata.get("pdf_exported") is True, "PDF was not exported"
    
    pdf_file = GENERATED_ASSESSMENTS_DIR / metadata["pdf_path"]
    assert pdf_file.exists(), f"PDF file not found: {pdf_file}"
    
    print(f"✓ Assessment: {assessment['title']}")
    print(f"✓ RAG used: True")
    print(f"✓ PDF: {metadata['pdf_path']} ({pdf_file.stat().st_size} bytes)")
    print("✅ TEST 2 PASSED\n")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("EXAM READINESS AGENT - INTEGRATION TEST")
    print("="*70)
    
    try:
        test_basic_generation()
        test_complete_pipeline()
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70 + "\n")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        raise