import os
import json
import requests

# *** FastAPI エンドポイントを呼び出す新しい実装 ***（以前の Bedrock API 実装からの切り替え）
FASTAPI_ENDPOINT = os.environ.get("FASTAPI_ENDPOINT", "")
if FASTAPI_ENDPOINT is None or FASTAPI_ENDPOINT == "":
    # （注：実際の Lambda では FASTAPI_ENDPOINT 環境変数が設定されている前提）
    FASTAPI_ENDPOINT = ""

def lambda_handler(event, context):
    # イベントからユーザー入力メッセージと過去の会話履歴を取得
    message = event.get("message", "")
    conversation_history = event.get("conversationHistory", [])
    # conversation_history をリスト形式に正規化
    if conversation_history is None:
        conversation_history = []
    elif isinstance(conversation_history, str):
        try:
            # JSON 文字列の場合はパース
            conversation_history = json.loads(conversation_history)
            if isinstance(conversation_history, dict):
                conversation_history = [conversation_history]
        except json.JSONDecodeError:
            # ただの文字列の場合はリストに格納
            conversation_history = [conversation_history]
    elif not isinstance(conversation_history, list):
        conversation_history = [conversation_history]
    
    # 新しいユーザー発話を会話履歴に追加
    conversation_history.append(message)
    
    # モデルへの入力プロンプトを準備（最新のユーザー発話のみを使用）
    prompt_text = message
    # 変更点: 会話履歴はモデル入力に含めず、Lambda 内で管理 (FastAPI には最新のユーザー発話のみ送信)
    
    # FastAPI に送信するリクエストボディを構築（プロンプトと生成パラメータ）
    payload = {
        "prompt": prompt_text,
        "temperature": 0.7,     # 生成の温度パラメータ（多様性制御）
        "top_p": 0.9,           # 生成の top_p パラメータ
        "max_new_tokens": 200,  # 生成する最大トークン数
        "do_sample": True       # サンプリングを有効化（Trueでランダム性あり）
    }
    
    # FastAPI の /generate エンドポイントURLを作成（環境変数のベースURLとパスを結合）
    url = FASTAPI_ENDPOINT.rstrip("/") + "/generate"
    try:
        # 変更点: requests.post を使用して FastAPI エンドポイントへ POST リクエスト送信
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        # 変更点: FastAPI が応答しない/ネットワークエラーの場合のエラーハンドリング
        error_message = f"Error: Failed to connect to FastAPI endpoint. ({e})"
        print(error_message)
        return {
            "response": error_message,
            "conversationHistory": conversation_history
        }
    
    # FastAPI からの JSON 応答をパースし、生成テキストを抽出
    try:
        result = response.json()
    except ValueError:
        error_message = "Error: Invalid JSON response from FastAPI."
        print(error_message)
        return {
            "response": error_message,
            "conversationHistory": conversation_history
        }
    generated_text = result.get("generated_text")
    if generated_text is None:
        error_message = "Error: 'generated_text' not found in FastAPI response."
        print(error_message)
        return {
            "response": error_message,
            "conversationHistory": conversation_history
        }
    
    # 生成されたテキスト（アシスタントの応答）を会話履歴に追加
    conversation_history.append(generated_text)
    
    # 応答テキストと更新された会話履歴を含む結果を返す
    return {
        "response": generated_text,
        "conversationHistory": conversation_history
    }
