import os
import requests
import json

# 環境変数から取得
GROK_API_KEY = os.environ.get('GROK_API_KEY')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.environ.get('LINE_USER_ID')

# 定型文の質問
DAILY_QUESTION = "直近の日本株の動向とおすすめを教えてください。"

def ask_grok(question):
    """Grok APIに質問を送信"""
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "grok-4-1-fast-non-reasoning",
        "messages": [
            {
                "role": "user",
                "content": question
            }
        ],
        "stream": False,
        "temperature": 0.7
    }
    
    print(f"リクエストURL: {url}")
    print(f"モデル: {data['model']}")
    
    response = requests.post(url, headers=headers, json=data)
    
    # ★ エラー詳細を出力
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス内容: {response.text}")
    
    response.raise_for_status()
    
    result = response.json()
    return result['choices'][0]['message']['content']

def send_line_message(message):
    """LINE Messaging APIでメッセージを送信"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    
    return response.status_code

def main():
    print("=== Grok LINE Bot 開始 ===")
    
    # Grokに質問
    print(f"質問: {DAILY_QUESTION}")
    grok_answer = ask_grok(DAILY_QUESTION)
    print(f"回答: {grok_answer[:100]}...")
    
    # LINEに送信
    status = send_line_message(grok_answer)
    print(f"LINE送信完了: {status}")
    
    print("=== 完了 ===")

if __name__ == "__main__":
    main()
