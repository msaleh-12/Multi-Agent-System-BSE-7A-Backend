from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, UnstructuredPDFLoader

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class RAGResult:
    """Container for RAG search results"""
    content: str
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class RAGService:
    """Service for handling PDF document processing and RAG functionality"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", chunk_size: int = 500, chunk_overlap: int = 100):
        self.embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"}
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False
        )
        self.db = None
        self.documents = []

    def _load_texts_via_langchain(self, pdf_paths: List[str]) -> List[str]:
        """Load and process PDF files into text chunks"""
        out: List[str] = []
        for p in pdf_paths:
            if not os.path.exists(p):
                print(f"File not found: {p}")
                continue

            print(f"\nProcessing {p}...")
            docs = []
            
            # Try PyPDFLoader first
            try:
                print("Attempting PyPDFLoader...")
                loader = PyPDFLoader(p)
                docs = loader.load()
                print(f"Successfully loaded {len(docs)} pages with PyPDFLoader")
            except Exception as e:
                print(f"PyPDFLoader error: {str(e)}")
                docs = []

            # Fallback to UnstructuredPDFLoader
            if not docs:
                try:
                    print("Attempting UnstructuredPDFLoader...")
                    loader = UnstructuredPDFLoader(p)
                    docs = loader.load()
                    print(f"Successfully loaded {len(docs)} pages with UnstructuredPDFLoader")
                except Exception as e:
                    print(f"UnstructuredPDFLoader error: {str(e)}")
                    docs = []

            if docs:
                print(f"Processing {len(docs)} pages of content...")
                for i, d in enumerate(docs):
                    header = f"Source: {os.path.basename(p)} -- Page {i+1}/{len(docs)}\n"
                    content = d.page_content.strip() if d.page_content else ""
                    if content:
                        out.append(header + content)
                        print(f"Added page {i+1} ({len(content)} chars)")
            else:
                msg = f"Could not load {p} via any PDF loader"
                print(msg)
                out.append(msg)

        return out

    def load_pdfs(self, pdf_paths: List[str]) -> None:
        """Load PDFs and prepare them for RAG"""
        texts = self._load_texts_via_langchain(pdf_paths)
        
        print("\nSplitting texts into chunks...")
        self.documents = self.text_splitter.create_documents(texts)
        print(f"Created {len(self.documents)} chunks")
        
        self.db = FAISS.from_documents(self.documents, self.embeddings)
        print("Vector store created successfully")

    def add_texts(self, texts: List[str]) -> None:
        """Add additional texts to the RAG knowledge base"""
        new_documents = self.text_splitter.create_documents(texts)
        if self.db is None:
            self.db = FAISS.from_documents(new_documents, self.embeddings)
        else:
            self.db.add_documents(new_documents)
        self.documents.extend(new_documents)

    def search(self, query: str, k: int = 3) -> List[RAGResult]:
        """Search the vector store for relevant content"""
        if not self.db:
            raise ValueError("No documents have been loaded yet.")
            
        try:
            results = self.db.similarity_search_with_score(query, k=k)
            return [
                RAGResult(
                    content=doc.page_content,
                    score=score,
                    metadata=doc.metadata if hasattr(doc, 'metadata') else None
                )
                for doc, score in results
            ]
        except Exception as e:
            print(f"Error during similarity search: {str(e)}")
            retriever = self.db.as_retriever(search_kwargs={"k": k})
            docs = retriever.get_relevant_documents(query)
            return [
                RAGResult(
                    content=doc.page_content,
                    metadata=doc.metadata if hasattr(doc, 'metadata') else None
                )
                for doc in docs[:k]
            ]

    def get_document_count(self) -> int:
        """Return the number of document chunks"""
        return len(self.documents)
        
    def clear(self) -> None:
        """Clear all documents"""
        self.documents = []
        self.db = None