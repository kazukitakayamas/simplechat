# lambda/index.py
import json
import os
import re
from botocore.exceptions import ClientError
import requests  # <-- 追加

def extract_region_from_arn(arn):
    # （必要なければこの関数も消せます）
    match = re.search(r'arn:aws:lambda:([^:]+):', arn)
    return match.group(1) if match else "us-east-1"

# FastAPI の URL を環境変数から取得
FASTAPI_URL     = os.environ.get("FASTAPI_URL", "")
FASTAPI_API_KEY = os.environ.get("FASTAPI_API_KEY")  # 必要なら

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        # Cognito 認証情報があればログ出力
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            claims = event['requestContext']['authorizer']['claims']
            user = claims.get('email') or claims.get('cognito:username')
            print(f"Authenticated user: {user}")
        
        # リクエストボディをパース
        body = json.loads(event.get('body', "{}"))
        message = body['message']
        history = body.get('conversationHistory', [])

        # FastAPI に渡すペイロード
        payload = {
            "message": message,
            "conversationHistory": history
        }
        headers = {"Content-Type": "application/json"}
        if FASTAPI_API_KEY:
            headers["Authorization"] = f"Bearer {FASTAPI_API_KEY}"

        print("Calling FastAPI:", FASTAPI_URL, "payload:", payload)
        resp = requests.post(FASTAPI_URL, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()

        result = resp.json()
        if not result.get("success"):
            raise Exception(f"FastAPI error: {result.get('error')}")
        
        assistant_response = result["response"]
        updated_history    = result.get("conversationHistory", [])
        print("FastAPI response:", assistant_response)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin":  "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": updated_history
            })
        }

    except requests.exceptions.RequestException as http_err:
        print("HTTP error calling FastAPI:", str(http_err))
        return {
            "statusCode": 502,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False,
                "error": "Failed to call FastAPI: " + str(http_err)
            })
        }

    except Exception as err:
        print("Error:", str(err))
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False,
                "error": str(err)
            })
        }
