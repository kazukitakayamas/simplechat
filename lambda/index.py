# lambda/index.py
import os
import json
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# ここで “バックエンドのモデル呼び出し先” を指定
# （もし同じプロジェクト内にモデル実装があるならパスを合わせてください）
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
    """
    POST /chat
    {
      "message": "...",
      "conversationHistory": [
         {"role":"user","content":"..."},
         {"role":"assistant","content":"..."},
         ...
      ]
    }
    を受け取って、別の FastAPI モデルサーバーに転送し、
    返ってきた JSON をそのままクライアントに返します。
    """
    try:
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
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Colab 上で直接起動するとき
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("index:app", host="0.0.0.0", port=port, reload=True)
