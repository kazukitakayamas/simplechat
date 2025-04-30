
# lambda/index.py
import json
import os
import requests                           # ★ 追加: HTTP リクエスト用
from botocore.exceptions import ClientError

# Bedrock 関連をすべて削除
# bedrock_client = None
# MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")

FASTAPI_ENDPOINT = os.environ.get("2vt8GU9hfEYfTaeJAsHxi6NbLWL_6Tr8gUZGbTcr7GiKFBgza")
if not FASTAPI_ENDPOINT:
    raise RuntimeError("FASTAPI_ENDPOINT environment variable is not set")  # :contentReference[oaicite:3]{index=3}

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # Cognito 認証情報の取得（任意）
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        body = json.loads(event.get('body', '{}'))
        message = body.get('message')
        conversation_history = body.get('conversationHistory', [])

        # FastAPI に渡すペイロード
        payload = {
            "message": message,
            "conversationHistory": conversation_history
        }

        print("Calling FastAPI endpoint:", FASTAPI_ENDPOINT)
        print("Payload:", json.dumps(payload))

        # ★ FastAPI サーバーへ POST
        response = requests.post(
            FASTAPI_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()  # HTTP エラー時に例外発生 :contentReference[oaicite:4]{index=4}

        result = response.json()     # JSON レスポンスをパース
        print("FastAPI response:", json.dumps(result))

        # FastAPI 側で返す JSON フォーマットを想定
        assistant_response = result.get("response")
        conversation_history = result.get("conversationHistory", conversation_history)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": conversation_history
            })
        }

    except Exception as error:
        print("Error:", str(error))
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
