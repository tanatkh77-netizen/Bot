import os
import requests
from bs4 import BeautifulSoup
import time
import re
import random
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import urllib.parse

# --- 設定エリア ---
KEYWORDS = ["てとぼ", "テトぼ", "テトぼっと", "テトリスぼ", "スワぼ", "すわぼ", "スワップぼ"]
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
        
        # ボット検知回避用
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # navigator.webdriverの偽装
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })
        
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 25) # 待機時間をさらに延長

    def save_debug_info(self, prefix="debug"):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.driver.save_screenshot(f"{prefix}_{timestamp}.png")
        with open(f"{prefix}_{timestamp}.html", 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)

    def login(self):
        driver = self.driver
        print("  -> Twitterログインプロセス開始...")
        driver.get('https://x.com/login')
        time.sleep(random.uniform(5, 8))
        
        try:
            # 1. メールアドレス入力
            email_input = self.wait.until(EC.visibility_of_element_located((By.NAME, "text")))
            email_input.send_keys(self.email)
            time.sleep(random.uniform(1, 2))
            
            # 「次へ」ボタンを直接クリック
            next_btn = driver.find_element(By.XPATH, "//span[text()='Next' or text()='次へ']")
            driver.execute_script("arguments[0].click();", next_btn)
            print("  -> メール送信完了、次へ進みます")
            time.sleep(random.uniform(3, 5))
            
            # 2. ユーザー名確認画面またはパスワード入力画面の判定
            # 現在のURLや画面内のテキストを確認
            try:
                # ユーザー名を求められている場合 (data-testid="ocfEnterTextTextInput")
                verify_input = driver.find_elements(By.XPATH, "//input[@data-testid='ocfEnterTextTextInput']")
                if verify_input:
                    print("  -> ユーザー名確認が求められました。")
                    verify_input[0].send_keys(self.username)
                    time.sleep(1)
                    v_next_btn = driver.find_element(By.XPATH, "//span[text()='Next' or text()='次へ']")
                    driver.execute_script("arguments[0].click();", v_next_btn)
                    time.sleep(random.uniform(3, 5))
            except Exception:
                pass

            # 3. パスワード入力
            password_input = self.wait.until(EC.visibility_of_element_located((By.NAME, "password")))
            password_input.send_keys(self.password)
            time.sleep(1)
            
            # ログインボタンをクリック
            login_btn = driver.find_element(By.XPATH, "//span[text()='Log in' or text()='ログイン']")
            driver.execute_script("arguments[0].click();", login_btn)
            
            # ログイン完了待機（ホーム画面のURLになるまで）
            self.wait.until(EC.url_contains("home"))
            print("  -> ログイン成功")
            return True
                
        except Exception as e:
            print(f"  -> ログイン処理中にエラー発生: {type(e).__name__}")
            self.save_debug_info("login_error_detail")
            return False

    def tweet_url(self, tweet_url):
        driver = self.driver
        print(f"  -> 投稿開始: {tweet_url}")
        
        text = urllib.parse.quote(f"RT {tweet_url}")
        url = f"https://x.com/intent/tweet?text={text}"
        driver.get(url)
        time.sleep(random.uniform(5, 7))
        
        try:
            # 投稿ボタンをクリック
            tweet_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='tweetButton']")))
            driver.execute_script("arguments[0].click();", tweet_btn)
            time.sleep(random.uniform(5, 8))
            print(f"  -> 投稿完了")
            return True
        except Exception as e:
            print(f"  -> 投稿ボタンが見つかりません。")
            self.save_debug_info("post_error")
            return False
    
    def close(self):
        self.driver.quit()

def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE, "r", encoding='utf-8') as f:
        return [line.strip() for line in f.read().splitlines() if line.strip()]

def save_history(urls):
    with open(HISTORY_FILE, "w", encoding='utf-8') as f:
        f.write("\n".join(urls[:500]))

def post_to_discord(text, url):
    if not DISCORD_WEBHOOK_URL: return
    data = {"username": "てとぼっと", "content": f"\n{text}\n{url}"}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)
    except: pass

def get_yahoo_realtime_tweets():
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
    
    # 処理すべき新規ツイートのみをフィルタリング
    new_tweets = []
    for t in tweets:
        if t['url'] in history: continue
        if any(uid in t['url'] for uid in BLOCKED_IDS): continue
        new_tweets.append(t)
    
    if not new_tweets:
        print("新着ツイートなし。ブラウザは起動しません。")
        return

    print(f"{len(new_tweets)} 件の新着があります。Twitter投稿を開始します。")

    # 新着があった場合のみログインを試みる
    bot = Tweetbot(TWITTER_EMAIL, TWITTER_PASSWORD, TWITTER_USERNAME)
    if bot.login():
        success_urls = []
        for tweet in reversed(new_tweets):
            post_to_discord(tweet['text'], tweet['url'])
            if bot.tweet_url(tweet['url']):
                success_urls.append(tweet['url'])
                time.sleep(random.uniform(10, 15)) # レート制限回避
        
        # 成功した分だけ履歴を更新
        if success_urls:
            current_history = load_history()
            for url in success_urls:
                current_history.insert(0, url)
            save_history(current_history)
            print(f"計 {len(success_urls)} 件を投稿しました。")
    
    bot.close()
    print("--- 全ての処理を完了しました ---")

if __name__ == "__main__":
    main()
