# lambda/index.py
import json
import os
import re
import requests
from requests.exceptions import RequestException

# APIのベースURL
API_BASE_URL = "https://2c41-34-87-69-11.ngrok-free.app"

# モデルID（元のコードと互換性のために保持）
MODEL_ID = os.environ.get("MODEL_ID", "local-model")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        
        # 会話履歴から最後のN個のメッセージを取得し、コンテキストを構築
        # 最後のユーザーメッセージを含む会話履歴から適切なプロンプトを作成
        prompt = format_prompt_from_history(conversation_history, message)
        
        # FastAPIサーバーへのリクエストペイロードを作成
        request_payload = {
            "prompt": prompt,
            "max_new_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "do_sample": True
        }
        
        print(f"Calling local LLM API at {API_BASE_URL}/generate")
        
        # FastAPIサーバーにリクエストを送信
        response = requests.post(
            f"{API_BASE_URL}/generate",
            json=request_payload,
            timeout=30  # タイムアウト設定
        )
        
        # レスポンスが成功した場合
        if response.status_code == 200:
            response_data = response.json()
            print("LLM API response:", json.dumps(response_data, default=str))
            
            # アシスタントの応答を取得
            assistant_response = response_data.get('generated_text', '')
            if not assistant_response:
                raise Exception("No response content from the model")
            
            # アシスタントの応答を会話履歴に追加
            messages = conversation_history.copy()
            # ユーザーメッセージを追加
            messages.append({
                "role": "user",
                "content": message
            })
            # アシスタントの応答を追加
            messages.append({
                "role": "assistant",
                "content": assistant_response
            })
            
            # 成功レスポンスの返却
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
        else:
            # APIエラーの場合
            error_msg = f"LLM API returned status code {response.status_code}: {response.text}"
            print(error_msg)
            raise Exception(error_msg)
        
    except RequestException as e:
        error_msg = f"Request to LLM API failed: {str(e)}"
        print(error_msg)
        return create_error_response(500, error_msg)
        
    except Exception as error:
        print("Error:", str(error))
        return create_error_response(500, str(error))

def format_prompt_from_history(conversation_history, new_message):
    """
    会話履歴と新しいメッセージからプロンプトを作成する
    
    Args:
        conversation_history (list): これまでの会話履歴
        new_message (str): 新しいユーザーメッセージ
    
    Returns:
        str: フォーマットされたプロンプト
    """
    formatted_history = ""
    
    # 会話履歴がある場合、それをフォーマット
    if conversation_history:
        for msg in conversation_history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user":
                formatted_history += f"ユーザー: {content}\n"
            elif role == "assistant":
                formatted_history += f"アシスタント: {content}\n"
    
    # 新しいメッセージを追加
    formatted_history += f"ユーザー: {new_message}\nアシスタント: "
    
    return formatted_history

def create_error_response(status_code, error_message):
    """
    エラーレスポンスを作成する
    
    Args:
        status_code (int): HTTPステータスコード
        error_message (str): エラーメッセージ
    
    Returns:
        dict: エラーレスポンス
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*", 
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "OPTIONS,POST"
        },
        "body": json.dumps({
            "success": False,
            "error": error_message
        })
    }
