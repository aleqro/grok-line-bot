import os
import requests
from datetime import datetime, timezone, timedelta

GROK_API_KEY = os.environ.get('GROK_API_KEY')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')

# 複数のUser IDに対応
LINE_USER_IDS_RAW = os.environ.get('LINE_USER_IDS_1', os.environ.get('LINE_USER_ID'))
LINE_USER_IDS = [uid.strip() for uid in LINE_USER_IDS_RAW.split(',') if uid.strip()]

COMMON_INSTRUCTION = """
  この回答はBot配信するのでやり取りは発生しないことを認識してください。
  注意事項は必要ありません。
  LINEで配信するため読みやすさを工夫してください。
  必ず最新の情報を検索してください。
  本日のWeb検索やXのトレンドから情報を取得してください。
  文章の最後に⭐️をつけてください。
"""

def get_today_date():
    """今日の日付を日本時間で取得"""
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst)
    return today.strftime("%Y年%m月%d日")

def get_daily_questions():
    """実行日を含む複数の質問を生成"""
    today = get_today_date()
    base_questions = [
        f"{today}時点の最新の日本株の動向を教えてください。",
        f"{today}時点の日本株のおすすめを10銘柄教えてください。（1株3000円以下で）"
    ]
    return [f"{q}\n{COMMON_INSTRUCTION}" for q in base_questions]

def ask_grok(question):
    """Grok APIに質問を送信"""
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "grok-4-1-fast-reasoning",
        "messages": [{"role": "user", "content": question}],
        "stream": False,
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

def send_line_message_to_user(user_id, message):
    """特定のユーザーにメッセージを送信"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "to": user_id,
        "messages": [{"type": "text", "text": message}]
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.status_code

def main():
    print("=== Bot 1: 日本株情報 ===")
    print(f"配信対象: {len(LINE_USER_IDS)}人")
    print(f"User IDs: {LINE_USER_IDS}")
    
    questions = get_daily_questions()
    
    # Grokに質問（1回だけ実行）
    all_answers = []
    for i, question in enumerate(questions, 1):
        question_only = question.split('\n')[0]
        print(f"\n質問 {i}: {question_only}")
        
        try:
            grok_answer = ask_grok(question)
            all_answers.append((question_only, grok_answer))
            print(f"回答取得成功: {len(grok_answer)}文字")
        except Exception as e:
            print(f"エラー: {e}")
            continue
    
    # 各ユーザーに送信
    for idx, user_id in enumerate(LINE_USER_IDS, 1):
        print(f"\n--- ユーザー {idx}/{len(LINE_USER_IDS)} ({user_id}) に送信中 ---")
        for i, (question_only, grok_answer) in enumerate(all_answers, 1):
            try:
                message = f"【質問{i}】{question_only}\n\n{grok_answer}"
                send_line_message_to_user(user_id, message)
                print(f"質問{i} 送信完了")
            except Exception as e:
                print(f"送信エラー: {e}")
    
    print("\n=== 完了 ===")

if __name__ == "__main__":
    main()
