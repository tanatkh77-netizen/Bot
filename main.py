import os
import requests
from bs4 import BeautifulSoup
import time
import re
import tweepy
from google import genai

KEYWORDS = ["てとぼ", "テトぼ", "テトリスぼ", "スワぼ", "すわぼ", "テトボ", "テトリス募集", "スワップ募集","スワップぼ"]

BLOCKED_IDS = ["K9jFFdajDs32941","3hiraganabot2", "sw_maha", "tekito878700", "Nito_R1" ]
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
        
        prompt = f"あなたは、テトリスの対戦募集ツイートを自動でリツイートするTwitterのBOT「てとぼっと」の判断部分です。「てとぼ」或いは「スワぼ」の単語が含まれるツイートがTwitter上から自動であなたに転送されます。そのツイート内容が、本当にその時点でテトリス或いはスワップの対戦相手を募集する意図があるのかどうかを判定しなさい。尚、スワップとはぷよぷよとテトリスを交互に遊ぶゲームのことです。「てとぼ」「テトぼ」はテトリス募集の略称であり、「スワぼ」「スワップぼ」はスワップ募集の略であるが、関係のない文章の中に紛れる可能性も大いにある為これらを判断の根拠にはしないこと。15先などは15本先取の略称、飽き抜けは飽きたら抜けて良いの略、3000↑などは、レート制限を表します。注意点として、文章の最後には、ツイート主の名前と@から連なるIDがあなたに渡されてしまうが、それらは単なるユーザーネームなので判断の上では無視しなさい。例:「いんたい」や「圧倒的暇人」などはユーザーネームです。「てとぼ」が含まれるが募集を意図していない例①帰ってとぼとぼ帰宅:「てとぼ」が含まれるが、「て」に「とぼとぼ」がついただけで募集の意図はない。②重音テトぼいす:キャラクターの「重音テト」に「ぼ」が付いただけで募集の意図はない\nまず結論は決めず文章を解析し、その後判断の根拠を述べた後、最後に改行して、募集の意図がある場合は1、ない場合は0の数字1文字のみを出力しなさい。\n\n{text}"
        
        # モデルを最新かつ最安価な gemini-2.5-flashに変更
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        result = response.text.strip()
        
        print(f"Gemini判定結果: {result} / 対象テキスト: {text}")

        if result.endswith("0"):
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

ICON_URL = "https://raw.githubusercontent.com/tanatkh77-netizen/Bot/main/TERAyun_seisyo_aikon.png"

def post_to_discord(text, url):
    if not DISCORD_WEBHOOK_URL:
        return
    
    data = {
        "username": "てらゆん",
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
            text = container.get_text(" ", strip=True) if container else "詳細なし"
            
            full_container = a_tag
            for _ in range(3):
                if full_container and full_container.parent:
                    full_container = full_container.parent
            full_text = full_container.get_text(" ", strip=True) if full_container else text

            text = re.sub(r'\d{1,2}(秒|分|時間|日)前', '', text)
            full_text = re.sub(r'\d{1,2}(秒|分|時間|日)前', '', full_text)

            if len(text) > 150:
                text = text[:150] + "..."

            found_tweets.append({
                "url": clean_url,
                "text": text,
                "full_text": full_text
            })


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

        if not any(k in tweet['text'] or k in tweet.get('full_text', '') for k in KEYWORDS):
            print(f"Skipped split keyword: {url}")
            continue

        if "@tetobobot" in tweet['text'] or "@tetobobot" in tweet.get('full_text', ''):
            print(f"@tetobobot検出 強制採用: {url}")
            is_recruitment = True
        else:
            is_recruitment = check_gemini(tweet['full_text'])

        if not is_recruitment:
            print(f"Gemini判定によりスキップ: {url}")
            new_history.insert(0, url)
            continue

        print(f"New Tweet Found! : {url}")
        
        discord_banned_users = ["Hikarukisi_lv77", "magyou1111"]
        if any(user in tweet['full_text'] or user in tweet['text'] for user in discord_banned_users):
            print(f"Discord特定ユーザー検出: {url}")
        else:
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
