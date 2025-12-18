import os
import requests
from bs4 import BeautifulSoup
import time
import re
import tweepy
from google import genai

KEYWORDS = ["てとぼ", "テトぼ", "テトリスぼ", "スワぼ", "すわぼ", "スワップぼ"]

BLOCKED_IDS = ["K9jFFdajDs32941", "sw_maha"]
QUERY = " OR ".join(KEYWORDS)

HISTORY_FILE = "history.txt"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def check_gemini(text):
    if not GEMINI_API_KEY:
        print("Gemini API Key未設定のためスルーします")
        return True

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"あなたは、以下の文章にテトリスの対戦相手を募集する意図があるかどうかを判定しなさい。意図がある場合、1を、ない場合は0だけを出力しなさい\n\n{text}"
        
        # モデルを最新かつ最安価な gemini-2.5-flash-lite に変更
        response = client.models.generate_content(
            model="gemini-3-flash", 
            contents=prompt
        )
        result = response.text.strip()
        
        print(f"Gemini判定結果: {result} / 対象テキスト: {text[:20]}...")

        if result == "0":
            return False
        else:
            return True

    except Exception as e:
        # エラー発生時はログを出して、安全のため通過(True)させる既存ロジックを維持
        print(f"Geminiエラー発生(通過させます): {e}")
        return True

def post_to_twitter(tweet_url):
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("Twitter APIキーが設定されていません。")
        return

    try:
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )

        text = tweet_url

        client.create_tweet(text=text)
        print(f"  -> Twitter投稿成功: {tweet_url}")
        time.sleep(2)

    except Exception as e:
        print(f"  -> Twitter投稿エラー: {e}")

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return [line.strip() for line in f.read().splitlines() if line.strip()]

def save_history(urls):

    with open(HISTORY_FILE, "w") as f:
        f.write("\n".join(urls[:1000]))

ICON_URL = "https://raw.githubusercontent.com/tanatkh77-netizen/Bot/main/IMG_7525.jpeg"

def post_to_discord(text, url):
    if not DISCORD_WEBHOOK_URL:
        return
    
    data = {
        "username": "てとぼっと",
        "avatar_url": ICON_URL,
        "content": f"\n{text}\n{url}"
    }
    
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=data)
        print(f"  -> Discord送信成功: {url}")
        time.sleep(2)
    except Exception as e:
        print(f"  -> Discord送信エラー: {e}")

def get_yahoo_realtime_tweets():
    url = f"https://search.yahoo.co.jp/realtime/search?p={QUERY}&m=recent"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print(f"Accessing: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Access Error: {e}")
        return []

    soup = BeautifulSoup(response.text, 'lxml')
    
    found_tweets = []
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        
        if ("/status/" in href) and ("twitter.com" in href or "x.com" in href):
            clean_url = href.split('?')[0]
            
            container = a_tag.find_parent('div')
            text = container.get_text(strip=True) if container else "詳細なし"
            
            text = re.sub(r'\d{1,2}(秒|分|時間|日)前', '', text)

            if len(text) > 150:
                text = text[:150] + "..."

            found_tweets.append({
                "url": clean_url,
                "text": text
            })

    unique_tweets = []
    seen = set()
    for t in found_tweets:
        if t['url'] not in seen:
            seen.add(t['url'])
            unique_tweets.append(t)
            
    print(f" {len(unique_tweets)} 件の新規ツイートを発見しました。")
    return unique_tweets

def main():
    print("--- Start Checking ---")
    tweets = get_yahoo_realtime_tweets()
    
    if not tweets:
        print("ツイートが見つかりませんでした。")
        return

    history = load_history()
    print(f"履歴数: {len(history)} 件")
    tweets.reverse()
    
    new_history = history.copy()
    send_count = 0

    for tweet in tweets:
        url = tweet['url']

        if url in history:
            continue

        is_blocked = False
        for blocked_id in BLOCKED_IDS:
            if blocked_id in url:
                is_blocked = True
                break
        
        if is_blocked:
            print(f"Skipped blocked user: {url}")
            continue

        excluded_keywords = ["てとぼっと", "トボトボ", "とぼとぼ", "ぽてと"]
        if any(keyword in tweet['text'] for keyword in excluded_keywords):
            print(f"Skipped excluded keyword: {url}")
            continue

        # Geminiチェック呼び出し
        if not check_gemini(tweet['text']):
            print(f"Gemini判定によりスキップ: {url}")
            new_history.insert(0, url)
            continue

        print(f"New Tweet Found! : {url}")
        post_to_discord(tweet['text'], url)
        post_to_twitter(url)
             
        new_history.insert(0, url)
        send_count += 1
      
    if new_history != history:
        save_history(new_history)
        print(f"Total {send_count} tweets sent (History updated).")
    else:
        print("新着ツイートはありませんでした。")

if __name__ == "__main__":
    main()
