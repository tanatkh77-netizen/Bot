import os
import requests
from bs4 import BeautifulSoup
import time
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import urllib.parse

# --- 設定エリア ---
KEYWORDS = ["てとぼ", "テトぼ", "テトリスぼ", "スワぼ", "すわぼ", "スワップぼ"]
BLOCKED_IDS = ["Hikarukisi_lv77", "sw_maha"]
QUERY = " OR ".join(KEYWORDS)
HISTORY_FILE = "history.txt"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

TWITTER_EMAIL = os.environ.get("TWITTER_EMAIL")
TWITTER_PASSWORD = os.environ.get("TWITTER_PASSWORD")
TWITTER_USERNAME = os.environ.get("TWITTER_USERNAME")

class Tweetbot:
    def __init__(self, email, password, username):
        self.email = email
        self.password = password
        self.username = username
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        profile_dir = os.path.join(os.getcwd(), 'twitter_profile')
        os.makedirs(profile_dir, exist_ok=True)
        
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'--user-agent={self.user_agent}')
        chrome_options.add_argument(f'--user-data-dir={profile_dir}')
        
        # ボット検知回避用の追加設定
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # navigator.webdriverをundefinedにする（検知回避の核心）
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })
        
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 20)

    def save_debug_info(self, prefix="debug"):
        """エラー時の画面とソースを保存（デバッグ用）"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.driver.save_screenshot(f"{prefix}_{timestamp}.png")
        with open(f"{prefix}_{timestamp}.html", 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        print(f"  [DEBUG] {prefix} 情報を保存しました。")

    def login(self):
        """Twitterログイン処理"""
        driver = self.driver
        print("  -> Twitterログイン開始...")
        driver.get('https://twitter.com/login')
        time.sleep(5)
        
        try:
            # 1. メールアドレス入力
            email_field = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@name='text']")))
            email_field.send_keys(self.email)
            email_field.send_keys(Keys.RETURN)
            print("  -> メールアドレス送信完了")
            time.sleep(3)
            
            # 2. ユーザー名確認画面（もし出たら）
            # 入力フィールドが1つ以上あり、URLがログイン途中の場合にチェック
            curr_url = driver.current_url
            if "login" in curr_url or "checkpoint" in curr_url:
                try:
                    # ユーザー名入力が必要なフィールドを特定
                    username_field = driver.find_elements(By.XPATH, "//input[@data-testid='ocfEnterTextTextInput']")
                    if username_field:
                        print("  -> ユーザー名確認を求められました。入力します。")
                        username_field[0].send_keys(self.username)
                        username_field[0].send_keys(Keys.RETURN)
                        time.sleep(3)
                except:
                    pass

            # 3. パスワード入力
            password_field = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@name='password']")))
            password_field.send_keys(self.password)
            password_field.send_keys(Keys.RETURN)
            print("  -> パスワード送信完了")
            
            # ホーム画面に遷移するまで待機
            self.wait.until(EC.url_contains("home"))
            print("  -> Twitterログイン成功")
            return True
                
        except Exception as e:
            print(f"  -> ログイン失敗: {type(e).__name__}")
            self.save_debug_info("login_fail")
            return False

    def tweet_url(self, tweet_url):
        """指定URLを投稿"""
        driver = self.driver
        print(f"  -> ツイート投稿開始: {tweet_url}")
        
        text = urllib.parse.quote(f"RT {tweet_url}")
        url = f"https://twitter.com/intent/tweet?text={text}"
        driver.get(url)
        time.sleep(5)
        
        try:
            # 投稿ボタンをクリック（data-testid="tweetButton" または 属性で探す）
            tweet_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='tweetButton']")))
            driver.execute_script("arguments[0].click();", tweet_btn)
            time.sleep(5)
            print(f"  -> 投稿成功: {tweet_url}")
            return True
        except Exception as e:
            print(f"  -> 投稿ボタンが見つかりません。")
            self.save_debug_info("tweet_error")
            return False
    
    def close(self):
        self.driver.quit()

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding='utf-8') as f:
        return [line.strip() for line in f.read().splitlines() if line.strip()]

def save_history(urls):
    with open(HISTORY_FILE, "w", encoding='utf-8') as f:
        f.write("\n".join(urls[:500]))

def post_to_discord(text, url):
    if not DISCORD_WEBHOOK_URL:
        return
    data = {
        "username": "てとぼっと",
        "content": f"\n{text}\n{url}"
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)
    except:
        pass

def get_yahoo_realtime_tweets():
    """Yahoo検索から新着取得"""
    encoded_query = urllib.parse.quote(QUERY)
    url = f"https://search.yahoo.co.jp/realtime/search?p={encoded_query}&m=recent"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        found_tweets = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if ("/status/" in href) and ("twitter.com" in href or "x.com" in href):
                clean_url = href.split('?')[0]
                container = a_tag.find_parent('div')
                text = container.get_text(strip=True)[:150] if container else ""
                found_tweets.append({"url": clean_url, "text": text})
        
        # 重複削除
        unique_tweets = []
        seen = set()
        for t in found_tweets:
            if t['url'] not in seen:
                seen.add(t['url'])
                unique_tweets.append(t)
        return unique_tweets
    except Exception as e:
        print(f"Yahoo検索エラー: {e}")
        return []

def main():
    print("--- 検索開始 ---")
    tweets = get_yahoo_realtime_tweets()
    history = load_history()
    
    # 履歴に含まれず、ブロック対象でないツイートを抽出
    new_tweets = []
    for t in tweets:
        if t['url'] in history:
            continue
        if any(uid in t['url'] for uid in BLOCKED_IDS):
            continue
        new_tweets.append(t)
    
    if not new_tweets:
        print("新着ツイートはありませんでした。")
        return

    print(f"{len(new_tweets)} 件の新着があります。Twitter投稿プロセスを開始します。")

    # 新着があった場合のみ、ブラウザを起動してログイン
    bot = Tweetbot(TWITTER_EMAIL, TWITTER_PASSWORD, TWITTER_USERNAME)
    if bot.login():
        success_urls = []
        # 古いものから順に投稿するため反転
        for tweet in reversed(new_tweets):
            post_to_discord(tweet['text'], tweet['url'])
            if bot.tweet_url(tweet['url']):
                success_urls.append(tweet['url'])
                time.sleep(15) # Xのレート制限対策で間隔をあける
        
        # 成功した分だけ履歴を更新
        if success_urls:
            new_history = load_history()
            for url in success_urls:
                new_history.insert(0, url)
            save_history(new_history)
            print(f"合計 {len(success_urls)} 件を履歴に追加しました。")
    
    bot.close()
    print("--- 処理完了 ---")

if __name__ == "__main__":
    main()
