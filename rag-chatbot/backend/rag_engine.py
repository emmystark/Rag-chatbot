# rag_engine.py
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
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        text_model: str = "deepseek-r1:1.5b",      # your fast local model
        vision_model: str = "moondream:latest"     # your vision model
    ):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        # Embedding model (uses your nomic-embed-text if pulled, otherwise falls back)
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name="nomic-ai/nomic-embed-text-v1.5")
        except:
            self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

        # Load or create vector DB
        self.vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings
        )
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})

        # Ollama models
        self.text_model = text_model
        self.vision_model = vision_model

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
        self.vectorstore.persist()
        return len(chunks)

    def query_text(self, question: str) -> Dict[str, Any]:
        docs = self.retriever.invoke(question)
        context = "\n\n".join([doc.page_content for doc in docs])

        prompt = f"""Use only the following context to answer the question.
If you don't know, say "I don't know".

Context:
{context}

Question: {question}
Answer:"""

        answer = self._ollama_generate(prompt)

        # ←←← CORRECT SOURCES FORMAT (frontend expects "text") ←←←
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
            "answer": answer.strip() or "I couldn't find relevant information.",
            "sources": sources,
            "confidence": 0.94 if sources else 0.2,
            "type": "text_rag"
        }

    def query_text(self, question: str) -> Dict[str, Any]:
        docs = self.retriever.invoke(question)
        context = "\n\n".join([doc.page_content for doc in docs])

        prompt = f"""Use only the following context to answer the question.
If you don't know, say "I don't know".

Context:
{context}

Question: {question}
Answer:"""

        answer = self._ollama_generate(prompt)

        sources = [
    {
        "text": doc.page_content,        # ← changed from "content" to "text"
        "source": Path(doc.metadata.get("source", "")).name,
        "page": doc.metadata.get("page", 0) + 1
    }
    for doc in docs
]

# Inside query_vision() — also fix the sources (it reuses text_result):
        sources = [
            {
                "text": src.get("content", "") or src.get("text", ""),  # safe fallback
                "source": src.get("source", "unknown"),
                "page": src.get("page", "N/A")
            }
            for src in text_result["sources"]
        ]

        return {
            "answer": answer,
            "sources": sources,
            "confidence": 0.94 if docs else 0.3,
            "type": "text_rag"
        }

    def query_vision(self, question: str, image_bytes: bytes) -> Dict[str, Any]:
        # First: let moondream see the image
        b64_image = base64.b64encode(image_bytes).decode()
        vision_answer = self._ollama_generate(question, images=[b64_image])

        # Second: also search your text documents as fallback/enrichment
        text_result = self.query_text(question)

        final_answer = f"""From the image (moondream):
    {vision_answer}

    From your uploaded documents:
    {text_result['answer']}"""

        return {
            "answer": final_answer.strip(),
            "sources": text_result["sources"],
            "confidence": 0.96,
            "type": "vision+text_rag",
            "vision_model": self.vision_model
        }

    def clear_database(self):
        import shutil
        if os.path.exists(self.persist_directory):
            shutil.rmtree(self.persist_directory)
        os.makedirs(self.persist_directory, exist_ok=True)
        self.vectorstore = Chroma(persist_directory=self.persist_directory, embedding_function=self.embeddings)