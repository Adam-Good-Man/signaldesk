from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # 无头模式，不弹出浏览器
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def fetch_crypto_tweets(keyword="crypto"):
    url = f"https://x.com/search?q={keyword}&f=live"

    driver = init_driver()
    driver.get(url)
    time.sleep(5)  # 等待页面加载

    # 模拟滑动加载更多推文
    for _ in range(2):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    tweets = soup.find_all("div", {"data-testid": "tweet"})

    print(f"📢 共抓取到 {len(tweets)} 条关于“{keyword}”的推文：")

    for i, tweet in enumerate(tweets[:10], 1):  # 只显示前10条
        text_elem = tweet.find("div", {"lang": True})
        content = text_elem.get_text() if text_elem else "[无法提取文本]"
        print(f"\n[{i}] {content}")

    driver.quit()

if __name__ == "__main__":
    fetch_crypto_tweets("crypto OR bitcoin OR ethereum")
