# backend/app.py
import os
import requests
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
import uvicorn

os.environ["TOKENIZERS_PARALLELISM"] = "false"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use your RAGEngine with moondream
from rag_engine import RAGEngine
rag = RAGEngine(text_model="moondream:latest")

# Auto-load your documents
DATA_DIR = Path("/Volumes/Stark/Repo/Rag-chatbot/rag-chatbot/backend/data")
if DATA_DIR.exists():
    print("Loading your documents...")
    for pdf in DATA_DIR.rglob("*.pdf"):
        if pdf.stat().st_size < 100_000_000:
            print(f"Indexing: {pdf.name}")
            try:
                rag.add_document(str(pdf))
            except Exception as e:
                print(f"Failed {pdf.name}: {e}")
    print("All documents loaded!")

class QueryRequest(BaseModel):
    question: str

class Message(BaseModel):
    role: str
    content: str
    timestamp: str
    sources: list = []

@app.get("/")
def home():
    return {"status": "RAG + moondream ready"}

@app.post("/api/chat")
@app.post("/chat")
def chat(request: QueryRequest):
    if not request.question.strip():
        return {"messages": []}

    result = rag.query_text(request.question.strip())
    now = datetime.utcnow().isoformat() + "Z"

    return {
        "messages": [
            {
                "role": "user",
                "content": request.question,
                "timestamp": now
            },
            {
                "role": "assistant",
                "content": result["answer"],
                "timestamp": now,
                "sources": result["sources"]
            }
        ]
    }

@app.post("/vision")
async def vision(question: str = "", image: UploadFile = File(...)):
    from rag_engine import rag  # reuse
    img_bytes = await image.read()
    b64 = base64.b64encode(img_bytes).decode()
    prompt = question or "Describe this image in detail."
    answer = rag._ollama_generate(prompt, images=[b64])
    return {"answer": answer}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)