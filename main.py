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
        
        # ボット検知回避
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 20)

    def save_debug_info(self, prefix="error"):
        """デバッグ情報を確実に保存する"""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename_png = f"{prefix}_{timestamp}.png"
            filename_html = f"{prefix}_{timestamp}.html"
            
            self.driver.save_screenshot(filename_png)
            with open(filename_html, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"  -> デバッグファイルを保存しました: {filename_png}")
        except Exception as e:
            print(f"  -> デバッグ保存に失敗: {e}")

    def human_type(self, element, text):
        """1文字ずつ入力"""
        element.click()
        time.sleep(0.5)
        # 念のためクリア
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.DELETE)
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
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
            print("  -> 保存されたCookieなし。")
            return False
        try:
            self.driver.get("https://x.com")
            with open(COOKIE_FILE, "rb") as f:
                cookies = pickle.load(f)
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
            print("  -> Cookie読込完了。リロードします。")
            self.driver.refresh()
            time.sleep(5)
            
            # ログイン確認
            if "home" in self.driver.current_url or self.driver.find_elements(By.XPATH, "//div[@data-testid='tweetTextarea_0']"):
                print("  -> Cookieログイン成功。")
                return True
            else:
                print("  -> Cookie無効。再ログインします。")
                return False
        except Exception:
            return False

    def login(self):
        if self.load_cookies():
            return True

        driver = self.driver
        print("  -> 新規ログイン開始")
        driver.get('https://x.com/i/flow/login')
        time.sleep(random.uniform(4, 6))
        
        try:
            # --- 1. メールアドレス入力 ---
            print("  -> メール入力...")
            email_input = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@autocomplete='username' or @name='text']")))
            self.human_type(email_input, self.email)
            
            # 戦略A: Enterキーで送信 (最優先)
            print("  -> Enterキーで送信を試みます")
            email_input.send_keys(Keys.RETURN)
            time.sleep(3)

            # --- 2. 画面遷移の確認と分岐 ---
            # パスワード欄が出ているか？
            if driver.find_elements(By.NAME, "password"):
                print("  -> パスワード画面に遷移しました")
            
            # ユーザー名確認が出ているか？
            elif driver.find_elements(By.XPATH, "//input[@data-testid='ocfEnterTextTextInput']"):
                print("  -> ユーザー名確認画面です")
                verify_input = driver.find_element(By.XPATH, "//input[@data-testid='ocfEnterTextTextInput']")
                self.human_type(verify_input, self.username)
                verify_input.send_keys(Keys.RETURN)
                time.sleep(3)
            
            # まだメール画面のままなら、ボタンクリックを試す (戦略B)
            else:
                print("  -> Enterで遷移しなかったため、ボタンクリックを試みます")
                try:
                    next_btn = driver.find_element(By.XPATH, "//button[.//span[contains(text(),'Next') or contains(text(),'次へ')]]")
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(3)
                except:
                    print("  -> ボタンクリックも失敗")

            # --- 3. パスワード入力 ---
            print("  -> パスワード入力を待機...")
            password_input = self.wait.until(EC.visibility_of_element_located((By.NAME, "password")))
            self.human_type(password_input, self.password)
            password_input.send_keys(Keys.RETURN)
            
            # ログイン完了待機
            self.wait.until(EC.url_contains("home"))
            print("  -> ログイン成功")
            self.save_cookies()
            return True
                
        except Exception as e:
            print(f"  -> ログインエラー: {e}")
            self.save_debug_info("login_failed")
            return False

    def tweet_url(self, tweet_url):
        driver = self.driver
        print(f"  -> 投稿開始: {tweet_url}")
        
        text = urllib.parse.quote(f"RT {tweet_url}")
        url = f"https://x.com/intent/tweet?text={text}"
        driver.get(url)
        time.sleep(random.uniform(5, 7))
        
        try:
            # 投稿ボタン (data-testid="tweetButton")
            tweet_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='tweetButton']")))
            driver.execute_script("arguments[0].click();", tweet_btn)
            time.sleep(random.uniform(5, 8))
            print(f"  -> 投稿完了")
            return True
        except Exception as e:
            print(f"  -> 投稿失敗: {e}")
            self.save_debug_info("post_failed")
            return False
    
    def close(self):
        try:
            self.driver.quit()
        except:
            pass

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
        print("新着なし。")
        return

    print(f"{len(new_tweets)} 件の新着あり。")

    bot = Tweetbot(TWITTER_EMAIL, TWITTER_PASSWORD, TWITTER_USERNAME)
    # エラーが起きてもブラウザを確実に閉じる
    try:
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
                print(f"計 {len(success_urls)} 件投稿完了。")
    except Exception as e:
        print(f"予期せぬエラー: {e}")
        bot.save_debug_info("main_crash")
    finally:
        bot.close()
    print("--- 完了 ---")

if __name__ == "__main__":
    main()
