"""
Bot 5: アニメ情報配信Bot
毎週月曜朝5時にアニメの話題をLINEで配信
"""

import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import web_search, x_search
import requests


# ========================================
# 設定・定数
# ========================================

class Config:
    """設定を管理するクラス"""
    XAI_API_KEY = os.environ.get('GROK_API_KEY')
    LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN_5')
    LINE_USER_IDS_RAW = os.environ.get('LINE_USER_IDS_5')
    
    # 日本標準時のタイムゾーン
    JST = timezone(timedelta(hours=9))
    
    # X検索の対象期間（日数）
    X_SEARCH_DAYS = 7
    
    # Grokのモデル
    GROK_MODEL = "grok-4-1-fast"
    
    @classmethod
    def get_line_user_ids(cls) -> List[str]:
        """LINE User IDのリストを取得"""
        if not cls.LINE_USER_IDS_RAW:
            return []
        return [uid.strip() for uid in cls.LINE_USER_IDS_RAW.split(',') if uid.strip()]


COMMON_INSTRUCTION = """
この回答はBot配信するのでやり取りは発生しないことを認識してください。
注意事項は必要ありません。
LINEで配信するため読みやすさを工夫してください。
アニメファンが楽しめる内容にしてください。
文章の最後に🎬をつけてください。
"""


# ========================================
# 日付・時刻関連
# ========================================

class DateUtils:
    """日付・時刻関連のユーティリティクラス"""
    
    @staticmethod
    def get_today_jst() -> datetime:
        """今日の日付（日本時間）を取得"""
        return datetime.now(Config.JST)
    
    @staticmethod
    def get_today_formatted() -> str:
        """今日の日付を日本語形式で取得"""
        return DateUtils.get_today_jst().strftime("%Y年%m月%d日")
    
    @staticmethod
    def get_date_range(days: int = 7) -> Dict[str, datetime]:
        """指定日数前からの日付範囲を取得"""
        today = DateUtils.get_today_jst()
        past_date = today - timedelta(days=days)
        return {
            "from_date": past_date,
            "to_date": today
        }
    
    @staticmethod
    def format_date_range(date_range: Dict[str, datetime]) -> str:
        """日付範囲を文字列形式で取得（ログ表示用）"""
        from_date_str = date_range['from_date'].strftime("%Y-%m-%d")
        to_date_str = date_range['to_date'].strftime("%Y-%m-%d")
        return f"{from_date_str} 〜 {to_date_str}"


# ========================================
# 質問生成
# ========================================

class QuestionGenerator:
    """Grokへの質問を生成するクラス"""
    
    @staticmethod
    def generate_questions() -> List[str]:
        """アニメに関する質問リストを生成"""
        today = DateUtils.get_today_formatted()
        
        questions = [
            QuestionGenerator._create_trending_anime_question(today),
            QuestionGenerator._create_notable_episodes_question(today),
            QuestionGenerator._create_anime_news_question(today)
        ]
        
        return questions
    
    @staticmethod
    def _create_trending_anime_question(date: str) -> str:
        """話題のアニメの質問"""
        return f"""必ず最新の情報をX検索とWeb検索で調べてください。

{date}時点の過去1週間で、X（Twitter）で話題になった深夜アニメTOP5を教えてください。

以下の情報を含めてください：
1. アニメタイトル
2. なぜ話題になったか
3. ファンの反応や盛り上がったポイント
4. 見どころや注目シーン

{COMMON_INSTRUCTION}"""
    
    @staticmethod
    def _create_notable_episodes_question(date: str) -> str:
        """注目エピソードの質問"""
        return f"""必ず最新の情報をX検索とWeb検索で調べてください。

{date}時点の今週（過去1週間）放送された深夜アニメで、特に注目されたエピソードを3つ教えてください。

以下の情報を含めてください：
1. アニメタイトルと話数
2. エピソードの内容（ネタバレ配慮）
3. なぜ注目されたか
4. ファンの感想や反応
5. 作画・演出の評価

{COMMON_INSTRUCTION}"""
    
    @staticmethod
    def _create_anime_news_question(date: str) -> str:
        """アニメニュースの質問"""
        return f"""必ず最新の情報をWeb検索とX検索で調べてください。

{date}時点の過去1週間で、深夜アニメ関連の重要ニュースを教えてください。

以下のような情報を含めてください：
1. 新作アニメの発表や制作決定
2. 劇場版アニメの情報
3. イベント・コラボ情報
4. 声優やスタッフの重要発表
5. その他アニメファンが知るべきニュース

なければ「特に重要なニュースはありませんでした」と記載してください。

{COMMON_INSTRUCTION}"""
    
    @staticmethod
    def extract_display_text(question: str) -> str:
        """質問から表示用のテキストを抽出"""
        question_display = question.split('\n\n')[1] if '\n\n' in question else question.split('\n')[0]
        question_display = question_display.replace("必ず最新の情報をX検索とWeb検索で調べてください。", "").strip()
        question_display = question_display.replace("必ず最新の情報をWeb検索とX検索で調べてください。", "").strip()
        return question_display.split('\n')[0]


# ========================================
# Grok API
# ========================================

class GrokAPI:
    """Grok APIとの通信を管理するクラス"""
    
    @staticmethod
    def ask_with_search(question: str) -> str:
        """Web検索 + X検索付きでGrokに質問"""
        try:
            client = Client(api_key=Config.XAI_API_KEY)
            date_range = DateUtils.get_date_range(Config.X_SEARCH_DAYS)
            
            chat = client.chat.create(
                model=Config.GROK_MODEL,
                tools=[
                    web_search(),
                    x_search(
                        from_date=date_range["from_date"],
                        to_date=date_range["to_date"]
                    )
                ]
            )
            
            chat.append(user(question))
            response = chat.sample()
            
            return response.content
            
        except Exception as e:
            print(f"Grok API エラー詳細: {e}")
            import traceback
            traceback.print_exc()
            raise


# ========================================
# LINE API
# ========================================

class LineAPI:
    """LINE Messaging APIとの通信を管理するクラス"""
    
    @staticmethod
    def send_message(user_id: str, message: str) -> int:
        """指定ユーザーにメッセージを送信"""
        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Authorization": f"Bearer {Config.LINE_CHANNEL_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        data = {
            "to": user_id,
            "messages": [{"type": "text", "text": message}]
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        return response.status_code


# ========================================
# メイン処理
# ========================================

class Bot:
    """アニメ情報配信Botのメインクラス"""
    
    def __init__(self):
        self.user_ids = Config.get_line_user_ids()
    
    def run(self) -> None:
        """Botを実行"""
        self._print_header()
        
        # 質問と回答を取得
        qa_pairs = self._get_answers()
        
        if not qa_pairs:
            print("\n⚠️ 回答を取得できませんでした")
            return
        
        # 各ユーザーに送信
        self._send_to_users(qa_pairs)
        
        print("\n=== 完了 ===")
    
    def _print_header(self) -> None:
        """ヘッダー情報を表示"""
        print("=== Bot 5: アニメ情報（Web検索 + X検索有効） ===")
        print(f"配信対象: {len(self.user_ids)}人")
        print(f"User IDs: {self.user_ids}")
        
        date_range = DateUtils.get_date_range(Config.X_SEARCH_DAYS)
        date_range_str = DateUtils.format_date_range(date_range)
        print(f"X検索期間: {date_range_str} (過去{Config.X_SEARCH_DAYS}日)")
    
    def _get_answers(self) -> List[Tuple[str, str]]:
        """質問をGrokに送信して回答を取得"""
        questions = QuestionGenerator.generate_questions()
        qa_pairs = []
        
        for i, question in enumerate(questions, 1):
            question_display = QuestionGenerator.extract_display_text(question)
            print(f"\n質問 {i}: {question_display}")
            
            try:
                answer = GrokAPI.ask_with_search(question)
                qa_pairs.append((question_display, answer))
                print(f"✅ 回答取得成功: {len(answer)}文字")
                
            except Exception as e:
                print(f"❌ エラー: {e}")
                continue
        
        return qa_pairs
    
    def _send_to_users(self, qa_pairs: List[Tuple[str, str]]) -> None:
        """全ユーザーにメッセージを送信"""
        for idx, user_id in enumerate(self.user_ids, 1):
            print(f"\n--- ユーザー {idx}/{len(self.user_ids)} ({user_id}) に送信中 ---")
            
            for i, (question_display, answer) in enumerate(qa_pairs, 1):
                try:
                    message = f"【質問{i}】{question_display}\n\n{answer}"
                    LineAPI.send_message(user_id, message)
                    print(f"✅ 質問{i} 送信完了")
                    
                except Exception as e:
                    print(f"❌ 送信エラー: {e}")


# ========================================
# エントリーポイント
# ========================================

def main():
    """メイン関数"""
    bot = Bot()
    bot.run()


if __name__ == "__main__":
    main()
