import os
import base64
from pathlib import Path
from typing import List, Dict, Any

from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings  # ← Uses your local nomic-embed-text
from llama_cpp import Llama
from PIL import Image
import io

class RAGEngine:
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
    ):
        os.makedirs(persist_directory, exist_ok=True)

        # 1. Use your local nomic-embed-text (already pulled)
        self.embeddings = OllamaEmbeddings(
            model="nomic-embed-text:latest",
            base_url="http://localhost:11434"  # Ollama must be running
        )

        # 2. Chroma saves embeddings permanently here: ./chroma_db
        self.vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings
        )
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})

        # 3. Moondream for generation + vision (your existing GGUF files)
        self.llm = Llama(
            model_path=os.path.expanduser("~/.ollama/models/blobs/sha256-e554c6b9de016673fd2c732e0342967727e9659ca5f853a4947cc96263fa602b"),
            clip_model_path=os.path.expanduser("~/.ollama/models/blobs/sha256-4cc1cb3660d87ff56432ebeb7884ad35d67c48c7b9f6b2856f305e39c38eed8f"),
            n_ctx=2048,
            n_batch=512,
            verbose=False
        )

    def add_document(self, file_path: str) -> int:
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif ext in [".txt", ".md", ".csv"]:
            loader = TextLoader(file_path, encoding="utf-8")
        elif ext == ".docx":
            loader = Docx2txtLoader(file_path)
        else:
            print(f"Skipped unsupported: {path.name}")
            return 0

        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(docs)

        self.vectorstore.add_documents(chunks)
        print(f"Indexed {len(chunks)} chunks → {path.name}")
        return len(chunks)

    def _generate(self, prompt: str, images: List[str] = None) -> str:
        try:
            kwargs = {
                "prompt": prompt,
                "max_tokens": 512,
                "temperature": 0.3,
                "stop": ["<|endoftext|>", "Question:"]
            }
            if images:
                img = Image.open(io.BytesIO(base64.b64decode(images[0]))).convert("RGB")
                kwargs["images"] = [img]

            result = self.llm.create_completion(**kwargs)
            return result["choices"][0]["text"].strip()
        except Exception as e:
            return f"[Error: {e}]"

    def query_text(self, question: str) -> Dict[str, Any]:
        docs = self.retriever.invoke(question)
        context = "\n\n".join([d.page_content for d in docs]) if docs else "No relevant documents found."

        prompt = f"""Use only this context to answer clearly:

{context}

Question: {question}
Answer:"""

        answer = self._generate(prompt)

        sources = [
            {
                "text": d.page_content[:500],
                "source": Path(d.metadata.get("source", "unknown")).name,
                "page": d.metadata.get("page", 0) + 1 if d.metadata.get("page") is not None else 1
            }
            for d in docs
        ]

        return {
            "answer": answer,
            "sources": sources,
            "confidence": 0.95 if docs else 0.1
        }