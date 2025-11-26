import os
import base64
from pathlib import Path
from typing import List, Dict, Any
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import Chroma
from llama_cpp import Llama
from PIL import Image
import io

class CustomMoondreamEmbeddings(Embeddings):
    def __init__(self, model):
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.embed(texts)  # note: pass list directly
        # moondream often returns [[[float]]] → fix the shape
        while isinstance(embeddings, list) and len(embeddings) == 1 and isinstance(embeddings[0], list):
            embeddings = embeddings[0]
        # Now ensure it's List[List[float]]
        if isinstance(embeddings[0], list) and len(embeddings[0]) > 0 and not isinstance(embeddings[0][0], list):
            return embeddings
        elif isinstance(embeddings, list) and all(isinstance(e, float) for e in embeddings):
            return [embeddings]  # single text case
        else:
            raise ValueError(f"Unexpected embedding shape: {type(embeddings)}, {embeddings[:2] if embeddings else 'empty'}")

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.embed(text)  # single string
        # Same fix: moondream wraps too many times
        while isinstance(embedding, list) and len(embedding) == 1 and isinstance(embedding[0], list):
            embedding = embedding[0]
        if isinstance(embedding, list) and all(isinstance(x, float) for x in embedding):
            return embedding
        elif isinstance(embedding[0], list):
            return embedding[0]  # one more level
        else:
            raise ValueError(f"Failed to flatten embedding for query: {type(embedding)}")
class RAGEngine:
    def __init__(self, persist_directory: str = "./chroma_db", model_path: str = os.path.expanduser("~/.ollama/models/blobs/sha256-aabd4debf0c8f08881923f2c25fc0fdeed24435271c2b3e92c4af36704040dbc"), mmproj_path: str = os.path.expanduser("~/.ollama/models/blobs/sha256-a85fe2a2e58e2426116d3686dfdc1a6ea58640c1e684069976aa730be6c1fa01")):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        self.model = Llama(model_path=model_path, clip_model_path=mmproj_path, n_ctx=4096, verbose=False, embedding=True)
        self.embeddings = CustomMoondreamEmbeddings(self.model)
        self.vectorstore = Chroma(persist_directory=persist_directory, embedding_function=self.embeddings)
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})

    def _generate(self, prompt: str, images: List[str] = None) -> str:
        try:
            kwargs = {
                "prompt": prompt,
                "max_tokens": 512,
                "temperature": 0.3,
                "stop": ["<|endoftext|>", "Question:"]
            }
            if images:
                img_bytes = base64.b64decode(images[0])
                image = Image.open(io.BytesIO(img_bytes))
                kwargs["images"] = [image]  # llama_cpp supports image list for multimodal

            response = self.model.create_completion(**kwargs)
            return response["choices"][0]["text"].strip()
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

        answer = self._generate(prompt)

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