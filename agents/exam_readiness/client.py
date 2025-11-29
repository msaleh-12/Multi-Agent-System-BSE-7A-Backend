import requests
from typing import Dict, Any, List, Optional


class AssessmentAgentClient:
    """Client for interacting with the Assessment Generation Agent"""
    
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url.rstrip('/')
    
    def health_check(self) -> Dict[str, Any]:
        """Check agent health and capabilities"""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def generate_assessment(
        self,
        subject: str,
        assessment_type: str,
        difficulty: str,
        question_count: int,
        type_counts: Dict[str, int],
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a new assessment"""
        payload = {
            "subject": subject,
            "assessment_type": assessment_type,
            "difficulty": difficulty,
            "question_count": question_count,
            "type_counts": type_counts,
            **kwargs
        }
        response = requests.post(f"{self.base_url}/generate", json=payload)
        response.raise_for_status()
        return response.json()
    
    def upload_pdfs(self, file_paths: List[str]) -> Dict[str, Any]:
        """Upload PDF files for RAG processing"""
        files = [('files', open(path, 'rb')) for path in file_paths]
        try:
            response = requests.post(f"{self.base_url}/upload-pdfs", files=files)
            response.raise_for_status()
            return response.json()
        finally:
            for _, f in files:
                f.close()
    
    def search_rag(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """Search the RAG knowledge base"""
        payload = {"query": query, "top_k": top_k}
        response = requests.post(f"{self.base_url}/rag/search", json=payload)
        response.raise_for_status()
        return response.json()
    
    def export_pdf(self, assessment_data: Dict[str, Any], output_path: str) -> None:
        """Export assessment as PDF"""
        response = requests.post(f"{self.base_url}/export-pdf", json=assessment_data)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            f.write(response.content)
    
    def clear_rag(self) -> Dict[str, Any]:
        """Clear RAG knowledge base"""
        response = requests.delete(f"{self.base_url}/rag/clear")
        response.raise_for_status()
        return response.json()
    
    def rag_status(self) -> Dict[str, Any]:
        """Get RAG knowledge base status"""
        response = requests.get(f"{self.base_url}/rag/status")
        response.raise_for_status()
        return response.json()