# simplechat/lambda/index.py

import os
import json
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# ここにあなたのモデルサーバー（または別の FastAPI）の URL を指定
# Colab 上で同一フォルダに立てたモデル用 FastAPI を呼ぶなら "http://localhost:9000/model" など
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:9000/model")

class ChatRequest(BaseModel):
    message: str
    conversationHistory: list = []

class ChatResponse(BaseModel):
    success: bool
    response: str | None = None
    conversationHistory: list | None = None
    error: str | None = None

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    try:
        # 受け取ったメッセージと履歴をそのままバックエンドに転送
        payload = {
            "message": req.message,
            "conversationHistory": req.conversationHistory
        }
        resp = requests.post(BACKEND_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(
            success=True,
            response=data.get("response"),
            conversationHistory=data.get("conversationHistory")
        )
    except Exception as e:
        # エラーは 500 で返す
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("index:app", host="0.0.0.0", port=port, reload=True)
