import os
import django
import undetected_chromedriver as uc
import zipfile
import time
import random
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium_stealth import stealth
from selenium.webdriver.common.action_chains import ActionChains
import json



# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jobsite.settings')
django.setup()

from jobportal.models import ScrapedJob  # import your Django model

# === Proxy Config ===
PROXY_HOST = "brd.superproxy.io"
PROXY_PORT = 33335
PROXY_USER = "brd-customer-hl_9f14443b-zone-final_job_scraper"
PROXY_PASS = "6rtces3omqbs"


def create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass):
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = f"""
    var config = {{
        mode: "fixed_servers",
        rules: {{
            singleProxy: {{
                scheme: "http",
                host: "{proxy_host}",
                port: parseInt({proxy_port})
            }},
            bypassList: ["localhost"]
        }}
    }};

    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

    function callbackFn(details) {{
        return {{
            authCredentials: {{
                username: "{proxy_user}",
                password: "{proxy_pass}"
            }}
        }};
    }}

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        {{urls: ["<all_urls>"]}},
        ['blocking']
    );
    """

    plugin_path = "proxy_auth_plugin.zip"
    with zipfile.ZipFile(plugin_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return plugin_path


plugin_path = create_proxy_auth_extension(
    proxy_host=PROXY_HOST,
    proxy_port=PROXY_PORT,
    proxy_user=PROXY_USER,
    proxy_pass=PROXY_PASS
)

options = uc.ChromeOptions()
options.add_extension(plugin_path)

def get_chrome_driver():
    options = uc.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_extension(plugin_path)

    driver = uc.Chrome(options=options)

    # Optional: add stealth
    from selenium_stealth import stealth
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    return driver



def test_proxy_connection():
    print("🧪 Testing proxy connection using https://ipinfo.io/json..")
    try:
        driver = get_chrome_driver()
        driver.get("https://geo.brdtest.com/welcome.txt")
        time.sleep(5)
        print(driver.find_element(By.TAG_NAME, "body").text)
        driver.quit()
    except Exception as e:
        print(f"❌ Proxy connection test failed: {e}")


def save_job(**kwargs):
    try:
        ScrapedJob.objects.get_or_create(
            job_url=kwargs['job_url'],
            defaults={**kwargs}
        )
    except Exception as e:
        print(f"❌ Django ORM save error: {e}")



import json
from selenium.webdriver.common.action_chains import ActionChains

def scrape_indeed(keyword):
    print(f"\n📍 Scraping Indeed for: {keyword}")
    driver = get_chrome_driver()
    actions = ActionChains(driver)
    base_url = "https://ph.indeed.com"
    collected_jobs = []

    def human_like_scroll(driver):
        total_height = driver.execute_script("return document.body.scrollHeight")
        scroll_points = random.randint(5, 10)
        for i in range(scroll_points):
            scroll_distance = total_height // scroll_points
            driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
            time.sleep(random.uniform(0.5, 1.5))

    for page in range(0, 30, 10):
        search_url = f"{base_url}/jobs?q={keyword.replace(' ', '+')}&l=Philippines&start={page}"
        driver = get_chrome_driver()

        time.sleep(random.uniform(8, 12))
        human_like_scroll(driver)

        job_cards = driver.find_elements(By.CLASS_NAME, "job_seen_beacon")
        for card in job_cards:
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", card)
                actions.move_to_element(card).perform()
                time.sleep(random.uniform(0.3, 0.7))

                title_elem = card.find_element(By.CSS_SELECTOR, 'a.jcs-JobTitle')
                job_title = title_elem.text.strip()
                job_link = title_elem.get_attribute("href")
                job_link = job_link if job_link.startswith("http") else base_url + job_link
                try:
                    company = card.find_element(By.CSS_SELECTOR, '[data-testid="company-name"]').text.strip()
                except:
                    company = "N/A"
                try:
                    posted_text = card.find_element(By.CLASS_NAME, 'date').text.strip()
                    posted_date = convert_posted_date_indeed(posted_text)
                except:
                    posted_date = "N/A"
                collected_jobs.append((job_title, company, job_link, posted_date))
            except:
                continue

        time.sleep(random.uniform(3, 6))

    driver.quit()
    time.sleep(10)
    driver = get_chrome_driver()
    actions = ActionChains(driver)

    for job_title, company, job_url, posted_date in collected_jobs:
        try:
            driver.get(job_url)
            time.sleep(random.uniform(6, 9))
            human_like_scroll(driver)

            try:
                location = driver.find_element(By.CSS_SELECTOR, '[data-testid="jobsearch-JobInfoHeader-companyLocation"]').text.strip()
            except:
                location = "N/A"

            page_text = driver.page_source.lower()
            employment_type = "Full-time" if "full-time" in page_text else "Part-time" if "part-time" in page_text else "Contract" if "contract" in page_text else "Not specified"
            seniority_level = "Entry level" if "entry level" in job_title else "Associate" if "associate" in job_title else "Manager" if "manager" in job_title else "Senior" if "senior" in job_title else "Not specified"
            remote_option = "Remote" if "remote" in page_text else "Hybrid" if "hybrid" in page_text else "On-site" if "on-site" in page_text or "on site" in page_text else "Not specified" 

            if posted_date == "N/A":
                posted_date = None

            save_job(
                job_title=job_title, company_name=company, location=location,
                job_url=job_url, employment_type=employment_type,
                remote_option=remote_option, posted_date=posted_date,
                platform="Indeed", keyword=keyword, seniority_level=seniority_level,
                scraped_at=datetime.now()
            )
        except Exception as e:
            print(f"❌ Error scraping Indeed job: {e}")
    driver.quit()


def scrape_jobstreet(keyword):
    print(f"\n📍 Scraping JobStreet for: {keyword}")
    driver = get_chrome_driver()
    page_urls = [f"https://ph.jobstreet.com/{keyword.lower().replace(' ', '-')}-jobs?page={i}" for i in range(1,4)]
    all_jobs = []

    for url in page_urls:
        driver.get(url)
        time.sleep(random.uniform(5, 7))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        jobs = soup.select('a[data-automation="jobTitle"]')

        for job in jobs:
            href = job['href'].split("#")[0]
            job_url = "https://ph.jobstreet.com" + href
            posted_tag = job.find_next('span', attrs={"data-automation": "jobListingDate"})
            raw_posted = posted_tag.text.strip().replace("Posted ", "") if posted_tag else "N/A"
            posted_date = convert_posted_date_jobstreet(raw_posted)
            all_jobs.append((job_url, posted_date))

    driver.quit()
    time.sleep(2)
    driver = get_chrome_driver()

    for job_url, posted_date in all_jobs:
        try:
            driver.get(job_url)
            time.sleep(random.uniform(4, 6))
            soup = BeautifulSoup(driver.page_source, "html.parser")

            job_title = soup.select_one('[data-automation="job-detail-title"]').text.strip() if soup.select_one('[data-automation="job-detail-title"]') else "N/A"
            company = soup.select_one('[data-automation="advertiser-name"]').text.strip() if soup.select_one('[data-automation="advertiser-name"]') else "N/A"
            location = soup.select_one('[data-automation="job-detail-location"]').text.strip() if soup.select_one('[data-automation="job-detail-location"]') else "N/A"

            work_type = soup.find('span', attrs={"data-automation": "job-detail-work-type"})
            employment_type = work_type.a.text.strip() if work_type and work_type.a else "N/A"

            text = soup.get_text().lower()
            remote_option = "Remote" if "remote" in text else "Hybrid" if "hybrid" in text else "On-site"
            seniority_level = "Entry level" if "entry level" in text else "Associate" if "associate" in text else "Manager" if "manager" in text else "Senior" if "senior" in text else "Not specified"

            if posted_date == "N/A":
                posted_date = None

            save_job(
                job_title=job_title, company_name=company, location=location,
                job_url=job_url, employment_type=employment_type,
                remote_option=remote_option, posted_date=posted_date,
                platform="JobStreet", keyword=keyword, seniority_level=seniority_level,
                scraped_at=datetime.now()
            )
        except Exception as e:
            print(f"❌ Error scraping JobStreet job: {e}")
    driver.quit()

def scrape_linkedin(keyword):
    print(f"\n📍 Scraping LinkedIn for: {keyword}")
    driver = get_chrome_driver()
    driver.get(f"https://www.linkedin.com/jobs/search/?keywords={keyword.replace(' ', '%20')}&location=Philippines")
    time.sleep(10)

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "section[role='dialog']")))
        driver.execute_script("""
            const rect = document.querySelector("section[role='dialog']").getBoundingClientRect();
            const clickX = rect.left - 10;
            const clickY = rect.top - 10;
            document.elementFromPoint(clickX, clickY).click();
        """)
        print("✅ Modal dismissed.")
        time.sleep(2)
    except:
        pass

    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(3, 6))

    job_cards = driver.find_elements(By.CLASS_NAME, 'base-card')

    for job in job_cards[:50]:
        try:
            job.click()
            time.sleep(random.uniform(2, 4))
            title = job.find_element(By.CLASS_NAME, 'base-search-card__title').text.strip()
            company = job.find_element(By.CLASS_NAME, 'base-search-card__subtitle').text.strip()
            location = job.find_element(By.CLASS_NAME, 'job-search-card__location').text.strip()
            link = job.find_element(By.TAG_NAME, 'a').get_attribute('href')

            job_text = driver.page_source.lower()
            posted_date = linkedin_format_posted_date(driver.find_element(By.CLASS_NAME, 'posted-time-ago__text').text.strip())

            employment_type = "N/A"
            seniority_level = "N/A"
            try:
                criteria = driver.find_elements(By.CLASS_NAME, 'description__job-criteria-text')
                if len(criteria) >= 2:
                    seniority_level = criteria[0].text.strip()
                    employment_type = criteria[1].text.strip()
            except:
                pass

            remote_option = "Remote" if "remote" in job_text else "Hybrid" if "hybrid" in job_text else "On-site"


            if posted_date == "N/A":
                posted_date = None
            
            save_job(
                job_title=title, company_name=company, location=location,
                job_url=link, employment_type=employment_type,
                remote_option=remote_option, posted_date=posted_date,
                platform="LinkedIn", keyword=keyword, seniority_level=seniority_level,
                scraped_at=datetime.now()
            )
        except Exception as e:
            print(f"❌ Error scraping LinkedIn job: {e}")
    driver.quit()

# === Utilities for Date Conversion ===
def convert_posted_date_indeed(text):
    now = datetime.now()
    text = text.lower()
    if "today" in text or "just posted" in text: return now.strftime("%Y-%m-%d")
    if "day" in text: return (now - timedelta(days=int(text.split()[0]))).strftime("%Y-%m-%d")
    if "week" in text: return (now - timedelta(weeks=int(text.split()[0]))).strftime("%Y-%m-%d")
    if "month" in text: return (now - timedelta(days=30 * int(text.split()[0]))).strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")

def convert_posted_date_jobstreet(text):
    now = datetime.now()
    if "day" in text or "d" in text:
        days = int(''.join(filter(str.isdigit, text)))
        return (now - timedelta(days=days)).strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")

def linkedin_format_posted_date(text):
    now = datetime.now()
    if "today" in text or "just now" in text: return now.strftime("%Y-%m-%d")
    if "yesterday" in text: return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    if "day" in text: return (now - timedelta(days=int(text.split()[0]))).strftime("%Y-%m-%d")
    if "week" in text: return (now - timedelta(weeks=int(text.split()[0]))).strftime("%Y-%m-%d")
    if "month" in text: return (now - timedelta(days=30 * int(text.split()[0]))).strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")

# === Main Entry ===
if __name__ == "__main__":
    test_proxy_connection()
    keywords = [
        "Financial Management",
    ]
    for keyword in keywords:
        scrape_indeed(keyword)







