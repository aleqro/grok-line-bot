import os
from datetime import datetime, timezone, timedelta
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import web_search, x_search
import requests

# 環境変数から取得
XAI_API_KEY = os.environ.get('GROK_API_KEY')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')

LINE_USER_IDS_RAW = os.environ.get('LINE_USER_IDS_1', os.environ.get('LINE_USER_ID'))
LINE_USER_IDS = [uid.strip() for uid in LINE_USER_IDS_RAW.split(',') if uid.strip()]

COMMON_INSTRUCTION = """
この回答はBot配信するのでやり取りは発生しないことを認識してください。
注意事項は必要ありません。
LINEで配信するため読みやすさを工夫してください。
文章の最後に⭐️をつけてください。
"""

def get_today_date():
    """今日の日付を日本時間で取得"""
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst)
    return today.strftime("%Y年%m月%d日")

def get_date_range():
    """過去1ヶ月の日付範囲を取得（datetimeオブジェクト）"""
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst)
    one_month_ago = today - timedelta(days=30)
    
    return {
        "from_date": one_month_ago,  # datetimeオブジェクトをそのまま返す
        "to_date": today              # datetimeオブジェクトをそのまま返す
    }

def get_daily_questions():
    """実行日を含む複数の質問を生成"""
    today = get_today_date()
    
    base_questions = [
        f"""必ず最新の情報をWeb検索とX検索の両方で調べてください。

{today}時点の最新の日本株市場の動向を教えてください。

以下の情報を含めてください：
1. 日経平均株価の最新値と前日比
2. 市場全体のトレンド
3. Xで話題になっている注目トピック（過去1ヶ月）

{COMMON_INSTRUCTION}""",
        
        f"""必ず最新の情報をWeb検索とX検索の両方で調べてください。

{today}時点で、1株3000円以下の日本株のおすすめ銘柄を10個教えてください。

以下の情報を含めてください：
1. 銘柄名と株価
2. おすすめ理由
3. Xで話題になっている情報（過去1週間）があれば含める
4. Xの情報が正しいかは必ずWeb検索で確認してください（特に現在の株価）

{COMMON_INSTRUCTION}"""
    ]
    
    return base_questions

def ask_grok_with_search(question):
    """Grok APIにWeb検索 + X検索付きで質問（xAI SDK使用）"""
    try:
        client = Client(api_key=XAI_API_KEY)
        
        date_range = get_date_range()
        
        chat = client.chat.create(
            model="grok-4-1-fast",  # Web検索推奨モデル
            tools=[
                web_search(),  # Web検索を有効化
                x_search(      # X検索を有効化（過去1ヶ月）
                    from_date=date_range["from_date"],  # datetimeオブジェクト
                    to_date=date_range["to_date"]        # datetimeオブジェクト
                )
            ]
        )
        
        chat.append(user(question))
        
        # 回答を取得
        response = chat.sample()
        return response.content
        
    except Exception as e:
        print(f"Grok API エラー詳細: {e}")
        import traceback
        traceback.print_exc()
        raise

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
    print("=== Bot 1: 日本株情報（Web検索 + X検索有効） ===")
    print(f"配信対象: {len(LINE_USER_IDS)}人")
    print(f"User IDs: {LINE_USER_IDS}")
    
    date_range = get_date_range()
    # 表示用にフォーマット
    from_date_str = date_range['from_date'].strftime("%Y-%m-%d")
    to_date_str = date_range['to_date'].strftime("%Y-%m-%d")
    print(f"X検索期間: {from_date_str} 〜 {to_date_str} (過去1ヶ月)")
    
    questions = get_daily_questions()
    
    # Grokに質問（1回だけ実行）
    all_answers = []
    for i, question in enumerate(questions, 1):
        # 表示用の質問文（検索指示を除去）
        question_display = question.split('\n\n')[1] if '\n\n' in question else question.split('\n')[0]
        question_display = question_display.replace("必ず最新の情報をWeb検索とX検索の両方で調べてください。", "").strip()
        question_display = question_display.split('\n')[0]
        
        print(f"\n質問 {i}: {question_display}")
        
        try:
            grok_answer = ask_grok_with_search(question)
            all_answers.append((question_display, grok_answer))
            print(f"✅ 回答取得成功: {len(grok_answer)}文字")
        except Exception as e:
            print(f"❌ エラー: {e}")
            continue
    
    # 各ユーザーに送信
    for idx, user_id in enumerate(LINE_USER_IDS, 1):
        print(f"\n--- ユーザー {idx}/{len(LINE_USER_IDS)} ({user_id}) に送信中 ---")
        for i, (question_display, grok_answer) in enumerate(all_answers, 1):
            try:
                message = f"【質問{i}】{question_display}\n\n{grok_answer}"
                send_line_message_to_user(user_id, message)
                print(f"✅ 質問{i} 送信完了")
            except Exception as e:
                print(f"❌ 送信エラー: {e}")
    
    print("\n=== 完了 ===")

if __name__ == "__main__":
    main()
