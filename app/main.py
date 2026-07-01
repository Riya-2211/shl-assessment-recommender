
from fastapi import FastAPI
from app.schemas import ChatRequest, ChatResponse
from app.agent import handle_chat

app = FastAPI(title="SHL Assessment Recommender")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    return handle_chat(request)
