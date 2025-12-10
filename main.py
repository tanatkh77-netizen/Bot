import os
import requests
from bs4 import BeautifulSoup
import time
import re

KEYWORDS = ["てとぼ", "テトぼ", "テトリスぼ", "スワぼ", "すわぼ", "スワップぼ"]
QUERY = " OR ".join(KEYWORDS)

HISTORY_FILE = "history.txt"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return [line.strip() for line in f.read().splitlines() if line.strip()]

def save_history(urls):

    with open(HISTORY_FILE, "w") as f:
        f.write("\n".join(urls[:100]))

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
      
        print(f"New Tweet Found! : {url}")
        post_to_discord(tweet['text'], url)
             
        new_history.insert(0, url)
        send_count += 1
      
    if send_count > 0:
        save_history(new_history)
        print(f"Total {send_count} tweets sent.")
    else:
        print("新着ツイートはありませんでした。")

if __name__ == "__main__":
    main()
