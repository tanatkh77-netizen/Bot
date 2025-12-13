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
        
        # Chromeオプションの設定
        chrome_options = webdriver.ChromeOptions()
        
        # GitHub Actions用の設定
        chrome_options.add_argument('--headless')
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
            time.sleep(5)
        except Exception as e:
            print(f"  -> パスワード入力エラー: {e}")
            self.save_debug_info("login_password")
        
        print("  -> Twitterログイン完了")
    
    def find_tweet_button(self):
        """ツイートボタンを複数の方法で探す"""
        driver = self.driver
        
        # 候補となるセレクター一覧（よく変わるので複数用意）
        button_selectors = [
            # data-testidを使ったセレクター
            (By.XPATH, "//div[@data-testid='tweetButtonInline']"),
            (By.XPATH, "//div[@data-testid='tweetButton']"),
            (By.XPATH, "//button[@data-testid='tweetButton']"),
            
            # テキスト内容で探す（日本語）
            (By.XPATH, "//div[@role='button']//span[contains(text(), 'ツイート')]"),
            (By.XPATH, "//button//span[contains(text(), 'ツイート')]"),
            (By.XPATH, "//*[contains(text(), 'ツイート') and @role='button']"),
            
            # テキスト内容で探す（英語）
            (By.XPATH, "//div[@role='button']//span[contains(text(), 'Post')]"),
            (By.XPATH, "//button//span[contains(text(), 'Post')]"),
            (By.XPATH, "//*[contains(text(), 'Post') and @role='button']"),
            
            # aria-labelで探す
            (By.XPATH, "//div[@aria-label='ツイートする']"),
            (By.XPATH, "//button[@aria-label='Post']"),
            
            # CSSセレクター
            (By.CSS_SELECTOR, "div[data-testid='tweetButton']"),
            (By.CSS_SELECTOR, "button[data-testid='tweetButton']"),
            (By.CSS_SELECTOR, "div[role='button']:has(span:contains('ツイート'))"),
            
            # より一般的なセレクター
            (By.XPATH, "//button[contains(@class, 'tweet')]"),
            (By.XPATH, "//div[contains(@class, 'tweet')]"),
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
        
        # 見つからなかった場合、ページのボタンを全てリストアップ
        print("  -> ツイートボタンが見つかりません。ページ内のボタンを調査します...")
        
        # 全てのボタン要素を取得
        all_buttons = driver.find_elements(By.XPATH, "//button | //div[@role='button']")
        print(f"  -> ページ内のボタン数: {len(all_buttons)}")
        
        for i, button in enumerate(all_buttons[:20]):  # 最初の20個だけ表示
            try:
                text = button.text.strip()[:50]
                html = button.get_attribute('outerHTML')[:200]
                print(f"    ボタン{i+1}: テキスト='{text}', HTML={html}")
            except:
                pass
        
        return None
    
    def tweet_url(self, tweet_url):
        """指定したURLをリツイートする"""
        driver = self.driver
        
        print(f"  -> 投稿開始: {tweet_url}")
        
        # ツイート投稿ページを開く
        text = urllib.parse.quote(f"RT {tweet_url}", safe='')
        url = f"https://twitter.com/intent/tweet?text={text}"
        
        driver.get(url)
        time.sleep(8)  # ページ読み込みに十分な時間
        
        # 現在のURLとタイトルを表示
        print(f"  -> 現在のURL: {driver.current_url}")
        print(f"  -> ページタイトル: {driver.title}")
        
        # デバッグ情報を保存（常に保存）
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
            
            # JavaScriptでクリック（より確実な方法）
            driver.execute_script("arguments[0].click();", tweet_button)
            time.sleep(5)
            
            # 成功確認
            self.save_debug_info("after_tweet")
            
            # 投稿後のページを確認
            print(f"  -> 投稿後のURL: {driver.current_url}")
            
            # 成功の目印を探す
            success_indicators = [
                "投稿しました",
                "ツイートしました",
                "Tweet sent",
                "Your Tweet was sent"
            ]
            
            page_text = driver.page_source
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
            
            profile_dir = os.path.join(os.getcwd(), 'twitter_profile')
            if not os.path.isdir(profile_dir):
                print("  -> 新規ログインが必要です")
                bot.login()
            else:
                print("  -> 既存のセッションを使用します")
            
            result = bot.tweet_url(tweet_url)
            bot.close()
            return result
        else:
            return bot_instance.tweet_url(tweet_url)
            
    except Exception as e:
        print(f"  -> Twitter投稿エラー: {e}")
        return False

# ...（以下、load_history(), save_history(), post_to_discord(), get_yahoo_realtime_tweets(), main() 関数は変更なし）...

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
    
    # Twitterボットインスタンスを作成
    twitter_bot = None
    if all([TWITTER_EMAIL, TWITTER_PASSWORD, TWITTER_USERNAME]):
        try:
            twitter_bot = Tweetbot(TWITTER_EMAIL, TWITTER_PASSWORD, TWITTER_USERNAME)
            profile_dir = os.path.join(os.getcwd(), 'twitter_profile')
            if not os.path.isdir(profile_dir):
                print("  -> Twitter: 新規ログイン")
                twitter_bot.login()
            else:
                print("  -> Twitter: 既存セッションを使用")
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
