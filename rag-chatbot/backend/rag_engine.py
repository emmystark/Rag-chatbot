# backend/rag_engine.py
import os
import base64
import requests
from pathlib import Path
from typing import List, Dict, Any
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

class RAGEngine:
    def __init__(self, persist_directory: str = "./chroma_db", text_model: str = "moondream:latest"):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vectorstore = Chroma(persist_directory=persist_directory, embedding_function=self.embeddings)
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
        self.text_model = text_model

    def _ollama_generate(self, prompt: str, images: List[str] = None) -> str:
        payload = {
            "model": self.text_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_ctx": 4096}
        }
        if images:
            payload["images"] = images

        try:
            r = requests.post("http://localhost:11434/api/generate", json=payload, timeout=180)
            r.raise_for_status()
            return r.json().get("response", "").strip()
        except Exception as e:
            return f"[Model error: {e}]"

    def add_document(self, file_path: str) -> int:
        path = Path(file_path)
        ext = path.suffix.lower()
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif ext in [".txt", ".md"]:
            loader = TextLoader(file_path, encoding="utf-8")
        elif ext == ".docx":
            loader = Docx2txtLoader(file_path)
        else:
            raise ValueError("Unsupported file")

        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(docs)
        self.vectorstore.add_documents(chunks)
        return len(chunks)

    def query_text(self, question: str) -> Dict[str, Any]:
        docs = self.retriever.invoke(question)
        context = "\n\n".join([d.page_content for d in docs]) if docs else ""

        prompt = f"""Use this context to answer:

{context}

Question: {question}
Answer clearly:"""

        answer = self._ollama_generate(prompt)

        sources = [
            {
                "text": d.page_content,
                "source": Path(d.metadata.get("source", "unknown")).name,
                "page": (d.metadata.get("page", 0) or 0) + 1
            }
            for d in docs
        ]

        return {
            "answer": answer or "I don't know.",
            "sources": sources,
            "confidence": 0.9 if sources else 0.1
        }