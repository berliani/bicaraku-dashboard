from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re
import time
import requests
from scraping.model import MongoDBHandler

# Helper functions
def extract_keywords(text):
    stopwords = {"yang", "dan", "dengan", "untuk", "pada", "oleh", "atau", "dalam", "adalah", "ini", "itu", "sebagai", "juga",
        "karena", "agar", "supaya", "bagi", "ke", "di", "dari", "sebuah", "mereka", "kami", "kita", "anda", "saya",
        "lebih", "tidak", "hanya", "akan", "bisa", "telah", "telah", "sudah", "belum", "masih", "apa", "siapa", "bagaimana",
        "dimana", "mengapa", "apakah", "itu", "jadi", "lalu", "kemudian", "namun", "tetapi", "oleh", "selain", "setelah",
        "sebelum", "antara", "hingga", "saat", "waktu", "karena", "adalah", "yakni", "bahwa", "baru", "dapat", "memiliki", "jika", "suatu", "secara", "beberapa", "kata", "seperti", "banyak"}
    words = re.findall(r'\b\w+\b', text.lower())
    return [w for w in words if len(w) > 3 and w not in stopwords]

relevant_keywords = {
        "speech delay", "terlambat bicara", "komunikasi anak", "anak berbicara",
        "terapi wicara", "keterlambatan bicara", "perkembangan anak",
        "stimulasi bicara", "bahasa"}

def get_wikipedia_summary(keyword):
    url = "https://id.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "titles": keyword,
        "exintro": True,
        "explaintext": True
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        pages = data["query"]["pages"]
        return next(iter(pages.values()))["extract"]
    except:
        return None

# Scraping implementations
def scrape_haibunda(driver, db_handler):
    try:
        base_url = "https://www.haibunda.com/parenting/indeks/58/"
        for page in range(1, 7): 
            driver.get(f"{base_url}{page}")
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            for article in soup.select("article a"):
                title = article.get_text(strip=True)
                link = article.get('href')
                
                if not title or not link:
                    continue
                
                try:
                    driver.get(link)
                    time.sleep(2)
                    detail_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    content = " ".join([p.get_text() for p in detail_soup.select("div.isi-text p")])
                    
                    if not any(kw in content.lower() for kw in relevant_keywords):
                        continue
                        
                    keywords = extract_keywords(content)
                    db_handler.upsert_article(title, {
                        "title": title,
                        "link": link,
                        "content": content,
                        "keywords": keywords,
                        "source": "Haibunda"
                    })
                    
                except Exception as e:
                    print(f"Error scraping {link}: {str(e)}")
    
    except Exception as e:
        print(f"Error accessing Haibunda: {str(e)}")
#  Sraping hellosehat
def scrape_hellosehat(driver, db_handler):
    try:
        base_url = "https://hellosehat.com/parenting/"
        print("[Hellosehat] Memulai scraping...")
        driver.get(base_url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Cari semua artikel parenting
        articles = soup.select('a[href*="/parenting/"]')
        visited_links = set()

        for article in articles:
            link = article.get("href")
            if not link or link in visited_links:
                continue
                
            if "hellosehat.com/parenting/" not in link:
                continue
                
            visited_links.add(link)
            title = article.get_text(strip=True)
            
            if not title:
                continue

            try:
                # Scrape detail artikel
                driver.get(link)
                time.sleep(2)
                detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # Ekstrak konten
                content_div = detail_soup.find("div", class_="content-detail")
                if not content_div:
                    continue
                    
                paragraphs = content_div.find_all("p")
                article_text = " ".join([p.get_text(strip=True) for p in paragraphs])

                if not any(kw in article_text.lower() for kw in relevant_keywords):
                    continue

                # Simpan ke database
                keywords = extract_keywords(article_text)
                db_handler.upsert_article(title, {
                    "title": title,
                    "link": link,
                    "content": article_text,
                    "keywords": keywords,
                    "source": "Hellosehat"
                })
                
            except Exception as e:
                print(f"Error scraping {link}: {str(e)}")

    except Exception as e:
        print(f"[Hellosehat] Error: {str(e)}")

def run_scraping(connection_uri):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    # Biarkan selenium/webdriver-manager mendeteksi path sistem secara otomatis
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"Gagal menginisialisasi ChromeDriver: {str(e)}")
        return False
    
    db_handler = MongoDBHandler(connection_uri)
    
    try:
        # Scrape Haibunda
        scrape_haibunda(driver, db_handler)
        # Scrape HelloSehat
        scrape_hellosehat(driver, db_handler)  
        # Scrape Wikipedia
        keywords = relevant_keywords
        for kw in keywords:
            content = get_wikipedia_summary(kw)
            if content:
                db_handler.upsert_article(kw, {
                    "title": kw,
                    "content": content,
                    "keywords": extract_keywords(content),
                    "source": "Wikipedia"
                })
        return True
    except Exception as e:
        print(f"Scraping error: {str(e)}")
        return False
    finally:
        driver.quit()