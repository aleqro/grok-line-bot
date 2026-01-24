import os
import requests

GROK_API_KEY = os.environ.get('GROK_API_KEY')

def test_model_with_tools(model_name):
    """モデルがツール機能をサポートしているかテスト"""
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # ツール付きでリクエスト
    data = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": "今日の日経平均株価を教えてください"
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
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"\n=== {model_name} ===")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 成功！ツール機能サポートあり")
            print(f"回答: {result['choices'][0]['message']['content'][:200]}...")
            return True
        else:
            print(f"❌ エラー: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 例外: {e}")
        return False

def main():
    print("=== Grok APIツール機能テスト ===")
    
    models_to_test = [
        "grok-4-1-fast-reasoning",
        "grok-4-fast-reasoning",
        "grok-3",
        "grok-4-1-fast-non-reasoning"
    ]
    
    for model in models_to_test:
        test_model_with_tools(model)

if __name__ == "__main__":
    main()
