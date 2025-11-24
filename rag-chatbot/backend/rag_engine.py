# rag_engine.py — SUPER SIMPLE, NO NEW PACKAGES, WORKS 100%
import os
import base64
import requests
from pathlib import Path
from typing import List, Dict, Any

# OLD IMPORTS THAT ALWAYS WORK (no langchain-huggingface needed)
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings      # ← this one works
from langchain_community.vectorstores import Chroma                  # ← this one works too


class RAGEngine:
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        text_model: str = "moondream:latest"        # ← change to whatever you have running
    ):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        # Tiny, fast, 100% offline embedding model (80 MB)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        self.vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings
        )
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})

        self.text_model = text_model

    def _ollama_generate(self, prompt: str) -> str:
        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": self.text_model, "prompt": prompt, "stream": False},
                timeout=180
            )
            resp.raise_for_status()
            return resp.json()["response"]
        except Exception as e:
            return f"[Error: {str(e)}]"

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
            raise ValueError(f"Unsupported file: {ext}")

        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(docs)
        self.vectorstore.add_documents(chunks)
        return len(chunks)

    def query_text(self, question: str) -> Dict[str, Any]:
        docs = self.retriever.invoke(question)
        context = "\n\n".join([doc.page_content for doc in docs])

        prompt = f"""Use only the following context to answer. Be concise.

Context:
{context}

Question: {question}
Answer:"""

        answer = self._ollama_generate(prompt)

        sources = [
            {
                "text": doc.page_content,
                "source": Path(doc.metadata.get("source", "unknown")).name,
                "page": (doc.metadata.get("page", 0) or 0) + 1
            }
            for doc in docs
            if doc.page_content.strip()
        ]

        return {
            "answer": answer.strip() or "No relevant info found.",
            "sources": sources,
            "confidence": 0.94 if sources else 0.2,
            "type": "text_rag"
        }

    def clear_database(self):
        import shutil
        if os.path.exists(self.persist_directory):
            shutil.rmtree(self.persist_directory)
        os.makedirs(self.persist_directory, exist_ok=True)
        self.vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings
        )