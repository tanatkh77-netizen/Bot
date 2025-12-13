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

KEYWORDS = ["てとぼ", "テトぼ", "テトリスぼ", "スワぼ", "すわぼ", "スワップぼ"]
BLOCKED_IDS = ["Hikarukisi_lv77", "sw_maha"]
QUERY = " OR ".join(KEYWORDS)

HISTORY_FILE = "history.txt"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Twitter認証情報（Selenium用）
TWITTER_EMAIL = os.environ.get("TWITTER_EMAIL")
TWITTER_PASSWORD = os.environ.get("TWITTER_PASSWORD")
TWITTER_USERNAME = os.environ.get("TWITTER_USERNAME")

class Tweetbot:
    def __init__(self, email, password, username):
        self.email = email
        self.password = password
        self.username = username
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # プロファイルディレクトリの設定（セッション維持用）
        profile_dir = os.path.join(os.getcwd(), 'twitter_profile')
        os.makedirs(profile_dir, exist_ok=True)
        
        # Chromeオプションの設定
        chrome_options = webdriver.ChromeOptions()
        
        # GitHub Actions用の設定
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'--user-agent={self.user_agent}')
        chrome_options.add_argument(f'--user-data-dir={profile_dir}')
        
        # インスタンス化
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 15)

    def save_debug_info(self, prefix="debug"):
        """デバッグ情報を保存"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screenshot_file = f"{prefix}_{timestamp}.png"
        source_file = f"{prefix}_{timestamp}.html"
        
        # スクリーンショットを保存
        self.driver.save_screenshot(screenshot_file)
        print(f"  -> スクリーンショット保存: {screenshot_file}")
        
        # ページソースを保存
        with open(source_file, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        print(f"  -> HTMLソース保存: {source_file}")
        
        return screenshot_file, source_file

    def login(self):
        """Twitterにログインする"""
        driver = self.driver
        
        print("  -> Twitterログイン中...")
        driver.get('https://twitter.com/login')
        time.sleep(5)
        
        # メールアドレス入力
        try:
            email_input = driver.find_element(By.XPATH, "//input[@name='text']")
            email_input.send_keys(self.email)
            email_input.send_keys(Keys.RETURN)
            time.sleep(3)
        except Exception as e:
            print(f"  -> メール入力エラー: {e}")
            self.save_debug_info("login_email")
        
        # ユーザー名入力（必要な場合）
        try:
            username_input = driver.find_element(By.XPATH, "//input[@name='text']")
            username_input.send_keys(self.username)
            username_input.send_keys(Keys.RETURN)
            time.sleep(3)
        except:
            pass
        
        # パスワード入力
        try:
            password_input = driver.find_element(By.XPATH, "//input[@name='password']")
            password_input.send_keys(self.password)
            password_input.send_keys(Keys.RETURN)
            
            # URLがホームなどに切り替わるのを待つ、または長めに待機
            try:
                self.wait.until(EC.url_contains("home"))
            except:
                time.sleep(10)
                
        except Exception as e:
            print(f"  -> パスワード入力エラー: {e}")
            self.save_debug_info("login_password")
        
        print("  -> Twitterログイン完了")
    
    def find_tweet_button(self):
        """ツイートボタンを複数の方法で探す"""
        driver = self.driver
        
        # 候補となるセレクター一覧
        button_selectors = [
            (By.XPATH, "//div[@data-testid='tweetButtonInline']"),
            (By.XPATH, "//div[@data-testid='tweetButton']"),
            (By.XPATH, "//button[@data-testid='tweetButton']"),
            (By.XPATH, "//div[@role='button']//span[contains(text(), 'ツイート')]"),
            (By.XPATH, "//button//span[contains(text(), 'ツイート')]"),
            (By.XPATH, "//*[contains(text(), 'ツイート') and @role='button']"),
            (By.XPATH, "//div[@role='button']//span[contains(text(), 'Post')]"),
            (By.XPATH, "//button//span[contains(text(), 'Post')]"),
            (By.XPATH, "//*[contains(text(), 'Post') and @role='button']"),
            (By.XPATH, "//div[@aria-label='ツイートする']"),
            (By.XPATH, "//button[@aria-label='Post']"),
            (By.CSS_SELECTOR, "div[data-testid='tweetButton']"),
            (By.CSS_SELECTOR, "button[data-testid='tweetButton']"),
        ]
        
        for by, selector in button_selectors:
            try:
                elements = driver.find_elements(by, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        print(f"  -> ボタン発見: {selector}")
                        return element
            except:
                continue
        
        # 見つからなかった場合
        print("  -> ツイートボタンが見つかりませんでした")
        return None
    
    def tweet_url(self, tweet_url):
        """指定したURLをリツイートする"""
        driver = self.driver
        
        print(f"  -> 投稿開始: {tweet_url}")
        
        # ツイート投稿ページを開く
        text = urllib.parse.quote(f"RT {tweet_url}", safe='')
        url = f"https://twitter.com/intent/tweet?text={text}"
        
        driver.get(url)
        time.sleep(8)
        
        print(f"  -> 現在のURL: {driver.current_url}")
        print(f"  -> ページタイトル: {driver.title}")
        
        # デバッグ情報を保存
        self.save_debug_info("before_tweet")
        
        # ツイートボタンを探す
        tweet_button = self.find_tweet_button()
        
        if not tweet_button:
            print("  -> ツイートボタンが見つかりませんでした")
            self.save_debug_info("tweet_button_not_found")
            return False
        
        # ツイートボタンをクリック
        try:
            print("  -> ツイートボタンをクリックします...")
            driver.execute_script("arguments[0].click();", tweet_button)
            time.sleep(5)
            
            self.save_debug_info("after_tweet")
            print(f"  -> 投稿後のURL: {driver.current_url}")
            
            page_text = driver.page_source
            success_indicators = ["投稿しました", "ツイートしました", "Tweet sent", "Your Tweet was sent"]
            
            for indicator in success_indicators:
                if indicator in page_text:
                    print(f"  -> 成功メッセージを検出: {indicator}")
                    break
            
            print(f"  -> Twitter投稿成功: {tweet_url}")
            return True
            
        except Exception as e:
            print(f"  -> ツイートボタンクリックエラー: {e}")
            self.save_debug_info("tweet_click_error")
            return False
    
    def close(self):
        """ドライバーを閉じる"""
        self.driver.quit()

def post_to_twitter(tweet_url, bot_instance=None):
    """Seleniumを使用してTwitterに投稿する"""
    if not all([TWITTER_EMAIL, TWITTER_PASSWORD, TWITTER_USERNAME]):
        print("Twitter認証情報が設定されていません。")
        return None
    
    try:
        if bot_instance is None:
            bot = Tweetbot(TWITTER_EMAIL, TWITTER_PASSWORD, TWITTER_USERNAME)
            
            # GitHub Actionsではプロファイルが保持されないため、毎回ログインを実行する
            print("  -> Twitter: ログイン処理を実行します")
            bot.login()
            
            result = bot.tweet_url(tweet_url)
            bot.close()
            return result
        else:
            return bot_instance.tweet_url(tweet_url)
            
    except Exception as e:
        print(f"  -> Twitter投稿エラー: {e}")
        return False

def load_history():
    """履歴ファイルを読み込む"""
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding='utf-8') as f:
        return [line.strip() for line in f.read().splitlines() if line.strip()]

def save_history(urls):
    """履歴ファイルを保存する"""
    with open(HISTORY_FILE, "w", encoding='utf-8') as f:
        f.write("\n".join(urls[:1000]))

ICON_URL = "https://raw.githubusercontent.com/tanatkh77-netizen/Bot/main/IMG_7525.jpeg"

def post_to_discord(text, url):
    """Discordに投稿する"""
    if not DISCORD_WEBHOOK_URL:
        print("  -> DISCORD_WEBHOOK_URLが設定されていません")
        return
    
    data = {
        "username": "てとぼっと",
        "avatar_url": ICON_URL,
        "content": f"\n{text}\n{url}"
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        response.raise_for_status()
        print(f"  -> Discord送信成功: {url}")
        time.sleep(2)
    except Exception as e:
        print(f"  -> Discord送信エラー: {e}")

def get_yahoo_realtime_tweets():
    """Yahooリアルタイム検索からツイートを取得する"""
    encoded_query = urllib.parse.quote(QUERY, safe='')
    url = f"https://search.yahoo.co.jp/realtime/search?p={encoded_query}&m=recent"
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
    """メイン関数"""
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
    
    # Twitterボットインスタンスを作成
    twitter_bot = None
    if all([TWITTER_EMAIL, TWITTER_PASSWORD, TWITTER_USERNAME]):
        try:
            twitter_bot = Tweetbot(TWITTER_EMAIL, TWITTER_PASSWORD, TWITTER_USERNAME)
            # GitHub Actionsではプロファイルが保持されないため、毎回ログインを実行する
            print("  -> Twitter: ログイン処理を実行します")
            twitter_bot.login()
        except Exception as e:
            print(f"  -> Twitterボット初期化エラー: {e}")
            twitter_bot = None

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

        print(f"New Tweet Found! : {url}")
        post_to_discord(tweet['text'], url)
        
        if twitter_bot:
            post_to_twitter(url, twitter_bot)
        else:
            post_to_twitter(url)
             
        new_history.insert(0, url)
        send_count += 1
      
    if twitter_bot:
        twitter_bot.close()
    
    if send_count > 0:
        save_history(new_history)
        print(f"Total {send_count} tweets sent.")
    else:
        print("新着ツイートはありませんでした。")

if __name__ == "__main__":
    main()
