import os
import requests
from bs4 import BeautifulSoup
import time
import re
import random
import pickle
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import urllib.parse

# --- 設定エリア ---
KEYWORDS = ["てとぼ", "テトぼ", "テトぼっと", "テトリスぼ", "スワぼ", "すわぼ", "スワップぼ"]
BLOCKED_IDS = ["Hikarukisi_lv77", "sw_maha"]
QUERY = " OR ".join(KEYWORDS)
HISTORY_FILE = "history.txt"
COOKIE_FILE = "cookies.pkl"
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
        
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'--user-agent={self.user_agent}')
        
        # ボット検知回避用
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
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
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        try:
            self.driver.save_screenshot(f"{prefix}_{timestamp}.png")
            with open(f"{prefix}_{timestamp}.html", 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
        except Exception:
            pass

    def human_type(self, element, text):
        """人間のように1文字ずつ入力する"""
        element.click()
        time.sleep(0.5)
        element.clear()
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2)) # 入力間隔をランダムに
        time.sleep(0.5)

    def save_cookies(self):
        try:
            cookies = self.driver.get_cookies()
            with open(COOKIE_FILE, "wb") as f:
                pickle.dump(cookies, f)
            print("  -> Cookieを保存しました。")
        except Exception as e:
            print(f"  -> Cookie保存エラー: {e}")

    def load_cookies(self):
        if not os.path.exists(COOKIE_FILE):
            print("  -> 保存されたCookieが見つかりません。")
            return False
        
        try:
            self.driver.get("https://x.com")
            with open(COOKIE_FILE, "rb") as f:
                cookies = pickle.load(f)
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
            print("  -> Cookieを読み込みました。")
            self.driver.refresh()
            time.sleep(5)
            
            if "home" in self.driver.current_url or self.driver.find_elements(By.XPATH, "//div[@data-testid='tweetTextarea_0']"):
                print("  -> Cookieによるログイン再開に成功しました。")
                return True
            else:
                print("  -> Cookieが無効です。再ログインします。")
                return False
        except Exception as e:
            print(f"  -> Cookie読み込みエラー: {e}")
            return False

    def login(self):
        if self.load_cookies():
            return True

        driver = self.driver
        print("  -> 新規ログインプロセス開始...")
        driver.get('https://x.com/i/flow/login')
        time.sleep(random.uniform(4, 6))
        
        try:
            # 1. メールアドレス入力
            print("  -> メール入力欄を検索中...")
            email_input = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@autocomplete='username' or @name='text']")))
            
            # 人間のように入力
            self.human_type(email_input, self.email)
            
            # 入力が反映されているか確認
            input_val = email_input.get_attribute('value')
            if not input_val:
                print("  -> 入力が空です。再入力します。")
                email_input.send_keys(self.email)
            
            print(f"  -> メール入力完了: {input_val}")
            
            # 「次へ」ボタンを検索してクリック
            print("  -> 「次へ」ボタンをクリックします")
            try:
                next_btns = driver.find_elements(By.XPATH, "//span[contains(text(), 'Next') or contains(text(), '次へ')]")
                if next_btns:
                    # 見つかったボタンの親要素(buttonタグ)をクリック
                    driver.execute_script("arguments[0].closest('button').click();", next_btns[0])
                else:
                    # 見つからない場合はエンターキーで代用
                    email_input.send_keys(Keys.RETURN)
            except Exception as e:
                print(f"  -> ボタンクリック失敗、エンターキーで試行: {e}")
                email_input.send_keys(Keys.RETURN)

            time.sleep(random.uniform(3, 5))
            
            # 2. ユーザー名確認 (もしあれば)
            try:
                verify_input = driver.find_elements(By.XPATH, "//input[@data-testid='ocfEnterTextTextInput']")
                if verify_input:
                    print("  -> ユーザー名確認が求められました。")
                    self.human_type(verify_input[0], self.username)
                    verify_input[0].send_keys(Keys.RETURN)
                    time.sleep(random.uniform(3, 5))
            except Exception:
                pass

            # 3. パスワード入力
            print("  -> パスワード入力欄を待機中...")
            password_input = self.wait.until(EC.visibility_of_element_located((By.NAME, "password")))
            self.human_type(password_input, self.password)
            password_input.send_keys(Keys.RETURN)
            
            # ログイン完了待機
            self.wait.until(EC.url_contains("home"))
            print("  -> ログイン成功")
            self.save_cookies()
            return True
                
        except Exception as e:
            print(f"  -> ログイン処理中にエラー発生: {type(e).__name__} {e}")
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
            tweet_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='tweetButton']")))
            driver.execute_script("arguments[0].click();", tweet_btn)
            time.sleep(random.uniform(5, 8))
            print(f"  -> 投稿完了")
            return True
        except Exception as e:
            print(f"  -> 投稿ボタンが見つかりません: {e}")
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
    
    new_tweets = []
    for t in tweets:
        if t['url'] in history: continue
        if any(uid in t['url'] for uid in BLOCKED_IDS): continue
        new_tweets.append(t)
    
    if not new_tweets:
        print("新着ツイートなし。")
        return

    print(f"{len(new_tweets)} 件の新着があります。Twitter投稿を開始します。")

    bot = Tweetbot(TWITTER_EMAIL, TWITTER_PASSWORD, TWITTER_USERNAME)
    if bot.login():
        success_urls = []
        for tweet in reversed(new_tweets):
            post_to_discord(tweet['text'], tweet['url'])
            if bot.tweet_url(tweet['url']):
                success_urls.append(tweet['url'])
                time.sleep(random.uniform(10, 15))
        
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
