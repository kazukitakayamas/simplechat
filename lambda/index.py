# lambda/index.py

import json
import os
import requests
import re

# FastAPI のエンドポイント URL を環境変数から取得
# 例: FASTAPI_ENDPOINT = "https://abcd1234.ngrok.io"
FASTAPI_ENDPOINT = os.environ.get("FASTAPI_ENDPOINT")
if not FASTAPI_ENDPOINT:
    raise RuntimeError("環境変数 FASTAPI_ENDPOINT が設定されていません")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # Cognito 認証情報があれば取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            claims = event['requestContext']['authorizer']['claims']
            user_info = claims.get('email') or claims.get('cognito:username')
            print(f"Authenticated user: {user_info}")

        # リクエストボディの解析
        body = json.loads(event.get('body', '{}'))
        message = body.get('message', '')
        conversation_history = body.get('conversationHistory', [])

        print("Processing message:", message)

        # Lambda 内での会話履歴保持用
        messages = conversation_history.copy()
        messages.append({
            "role": "user",
            "content": message
        })

        # FastAPI 側 /generate エンドポイントに渡すペイロード
        # SimpleGenerationRequest を想定
        fastapi_payload = {
            "prompt": message,
            "max_new_tokens": body.get('max_new_tokens', 512),
            "do_sample":        body.get('do_sample', True),
            "temperature":      body.get('temperature', 0.7),
            "top_p":            body.get('top_p', 0.9),
        }

        print("Calling FastAPI /generate with payload:", fastapi_payload)
        resp = requests.post(
            f"{FASTAPI_ENDPOINT.rstrip('/')}/generate",
            json=fastapi_payload,
            timeout=30
        )
        resp.raise_for_status()

        gen = resp.json()
        assistant_response = gen.get("generated_text", "").strip()
        print("FastAPI response:", assistant_response)

        # 会話履歴にアシスタント応答を追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })

        # 成功時レスポンス
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
                "conversationHistory": messages
            })
        }

    except Exception as error:
        print("Error in lambda_handler:", str(error))
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
