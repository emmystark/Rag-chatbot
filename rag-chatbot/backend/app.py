import os
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
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

from rag_engine import RAGEngine
rag = RAGEngine()

# Auto-load documents at startup
DATA_DIR = Path("/Volumes/Stark/Repo/Rag-chatbot/rag-chatbot/backend/data")
if DATA_DIR.exists():
    print("Loading documents...")
    for file_path in DATA_DIR.rglob("*"):
        if file_path.is_file() and file_path.stat().st_size < 1_000_000_000:
            try:
                rag.add_document(str(file_path))
                print(f"Indexed: {file_path.name}")
            except ValueError:
                print(f"Skipped unsupported file: {file_path.name}")
            except Exception as e:
                print(f"Failed {file_path.name}: {e}")
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
# @app.post("/chat")
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

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        file_path = DATA_DIR / file.filename
        with file_path.open("wb") as buffer:
            buffer.write(await file.read())
        num_chunks = rag.add_document(str(file_path))
        return {"message": f"Document {file.filename} uploaded and indexed successfully. Chunks: {num_chunks}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/vision")
async def vision(question: str = Form(default="Describe this image in detail."), image: UploadFile = File(...)):
    try:
        img_bytes = await image.read()
        b64 = base64.b64encode(img_bytes).decode()
        answer = rag._generate(question, images=[b64])
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision processing failed: {str(e)}")

@app.post("/api/multimodal_chat")
async def multimodal_chat(question: str = Form(...), image: UploadFile = File(None)):
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question is required.")

    try:
        image_desc = ""
        if image:
            img_bytes = await image.read()
            b64 = base64.b64encode(img_bytes).decode()
            desc_prompt = "Describe this image in detail, focusing on elements relevant to the question."
            image_desc = rag._generate(desc_prompt, images=[b64])
            question = f"{question}\nImage context: {image_desc}"

        result = rag.query_text(question)
        now = datetime.utcnow().isoformat() + "Z"

        return {
            "messages": [
                {
                    "role": "user",
                    "content": question,
                    "timestamp": now
                },
                {
                    "role": "assistant",
                    "content": result["answer"],
                    "timestamp": now,
                    "sources": result["sources"],
                    "image_description": image_desc if image else None
                }
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multimodal chat failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)