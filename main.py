import os
import requests
import json
import time
from datetime import datetime, timezone, timedelta

# 環境変数から取得
GROK_API_KEY = os.environ.get('GROK_API_KEY')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.environ.get('LINE_USER_ID')

# 全質問に共通の指示文
COMMON_INSTRUCTION = """
この回答はBot配信するのでやり取りは発生しないことを認識してください。
注意事項は必要ありません。
LINEで配信するため読みやすさを工夫してください。
"""

def get_today_date():
    """今日の日付を日本時間で取得"""
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst)
    return today.strftime("%Y年%m月%d日")

def get_daily_questions():
    """実行日を含む複数の質問を生成"""
    today = get_today_date()
    
    # 基本的な質問内容
    base_questions = [
        f"{today}時点の最新の日本株の動向とおすすめを教えてください。",
        f"{today}の重要なニュースを3つ教えてください。"
    ]
    
    # 各質問に共通指示文を追加
    return [f"{q}\n{COMMON_INSTRUCTION}" for q in base_questions]

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
        "tools": [
            {
                "type": "web_search"
            }
        ],
        "stream": False,
        "temperature": 0.7
    }
    
    response = requests.post(url, headers=headers, json=data)
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
    
    questions = get_daily_questions()
    
    # 複数の質問を順番に処理
    for i, question in enumerate(questions, 1):
        print(f"\n--- 質問 {i}/{len(questions)} ---")
        # 共通指示文を除いた質問内容だけを表示
        question_only = question.split('\n')[0]
        print(f"質問: {question_only}")
        
        try:
            # Grokに質問（共通指示文を含む完全な質問を送信）
            grok_answer = ask_grok(question)
            print(f"回答: {grok_answer[:100]}...")
            
            # タイトル付きでLINEに送信（共通指示文は表示しない）
            message = f"【質問{i}】{question_only}\n\n{grok_answer}"
            status = send_line_message(message)
            print(f"LINE送信完了: {status}")
            
        except Exception as e:
            print(f"エラー発生: {e}")
            # エラーが発生しても次の質問に進む
            continue
        
        # API制限を避けるため少し待機（最後の質問以外）
        if i < len(questions):
            print("待機中...")
            time.sleep(2)
    
    print("\n=== 完了 ===")

if __name__ == "__main__":
    main()
