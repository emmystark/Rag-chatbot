# app.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
from pathlib import Path
import base64

from rag_engine import RAGEngine

app = FastAPI(title="Local RAG + Vision Chatbot", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_engine = RAGEngine(
    text_model="deepseek-r1:1.5b",      # you have this
    vision_model="moondream:latest"     # you have this
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

class QueryRequest(BaseModel):
    question: str

@app.get("/")
async def root():
    return {"message": "Local RAG + Vision API ready", "models": ["deepseek-r1:1.5b", "moondream"]}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    allowed = ['.pdf', '.txt', '.docx', '.md']
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        f.write(await file.read())

    chunks = rag_engine.add_document(str(file_path))
    return {"message": "Uploaded & indexed", "filename": file.filename, "chunks": chunks}

@app.post("/ask")
async def ask_question(request: QueryRequest):
    return rag_engine.query_text(request.question)

@app.post("/vision")
async def vision_question(
    question: str = Form(...),
    image: UploadFile = File(...)
):
    image_bytes = await image.read()
    return rag_engine.query_vision(question, image_bytes)

@app.delete("/clear")
async def clear_all():
    rag_engine.clear_database()
    return {"message": "All documents cleared"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)