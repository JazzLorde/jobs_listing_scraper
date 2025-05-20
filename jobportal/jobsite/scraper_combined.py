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
import re
import json
import random



# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jobsite.settings')
django.setup()

from jobportal.models import ScrapedJob  # import your Django model


def get_chrome_driver(load_cookies_from=None):
    options = uc.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")

    driver = uc.Chrome(options=options)

    languages = [["en-US", "en"], ["en-GB", "en"], ["en"], ["en-US"]]
    vendors = ["Google Inc.", "Apple Inc.", "Mozilla Foundation"]
    platforms = ["Win32", "Linux x86_64", "MacIntel"]
    renderers = ["Intel Iris OpenGL Engine", "AMD Radeon Pro", "NVIDIA GeForce", "Apple M1"]

    stealth(driver,
        languages=random.choice(languages),
        vendor=random.choice(vendors),
        platform=random.choice(platforms),
        webgl_vendor="Intel Inc.",  # Keep this consistent if needed
        renderer=random.choice(renderers),
        fix_hairline=True,
    )

    if load_cookies_from:
        driver.get("https://ph.indeed.com")
        time.sleep(5)
        load_cookies(driver, load_cookies_from)
        driver.refresh()

    return driver

def clear_scraped_jobs():
    try:
        deleted_count, _ = ScrapedJob.objects.all().delete()
        print(f"🧹 Cleared {deleted_count} existing job entries from the database.")
    except Exception as e:
        print(f"❌ Failed to clear job data: {e}")


def save_job(**kwargs):
    try:
        obj, created = ScrapedJob.objects.get_or_create(
            job_url=kwargs['job_url'],
            defaults={**kwargs}
        )
        if created:
            print(f"✅ Saved new job: {kwargs['job_title']} at {kwargs['company_name']}")
        else:
            print(f"⚠️ Duplicate job skipped: {kwargs['job_title']} at {kwargs['company_name']}")
    except Exception as e:
        print(f"❌ Django ORM save error: {e}")


def contains_keyword(text, keywords):
    return any(re.search(rf"\b{k}\b", text) for k in keywords)


def save_cookies(driver, filename):
    with open(filename, 'w') as f:
        json.dump(driver.get_cookies(), f)

def load_cookies(driver, filename):
    with open(filename, 'r') as f:
        cookies = json.load(f)
        for cookie in cookies:
            driver.add_cookie(cookie)


def scrape_indeed(keyword, driver):
    MAX_JOBS = 3  # ✅ Desired number of job cards to scrape
    print(f"\n📍 Scraping Indeed for: {keyword}")
    actions = ActionChains(driver)
    base_url = "https://ph.indeed.com"
    collected_jobs = []

    def human_like_scroll(driver):
        total_height = driver.execute_script("return document.body.scrollHeight")
        scroll_points = random.randint(5, 10)
        for _ in range(scroll_points):
            scroll_distance = total_height // scroll_points
            driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
            time.sleep(random.uniform(0.5, 1.5))

    # 🔁 Scrape search result pages until max jobs are collected
    for page in range(0, 100, 10):  # 10 pages max as safety cap
        if len(collected_jobs) >= MAX_JOBS:
            break

        search_url = f"{base_url}/jobs?q={keyword.replace(' ', '+')}&l=Philippines&start={page}"
        driver.get(search_url)
        time.sleep(random.uniform(8, 12))
        human_like_scroll(driver)

        job_cards = driver.find_elements(By.CLASS_NAME, "job_seen_beacon")

        for card in job_cards:
            if len(collected_jobs) >= MAX_JOBS:
                break
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
                    posted_elem = card.find_element(By.XPATH, './/span[contains(@class, "date")]')
                    posted_text = posted_elem.text.strip()
                    posted_date = convert_posted_date_indeed(posted_text)
                except:
                    posted_date = "N/A"

                collected_jobs.append((job_title, company, job_link, posted_date))
            except:
                continue

        time.sleep(random.uniform(3, 6))

    # 🧭 Second stage: Visit individual job pages (reuse same driver)
    for job_title, company, job_url, posted_date in collected_jobs:
        try:
            driver.get(job_url)
            time.sleep(random.uniform(6, 9))
            human_like_scroll(driver)

            try:
                location = driver.find_element(By.CSS_SELECTOR, '[data-testid="jobsearch-JobInfoHeader-companyLocation"]').text.strip()
            except:
                location = "N/A"

            try:
                job_description = driver.find_element(By.ID, "jobDescriptionText").text.lower()
            except:
                job_description = ""

            combined_text = f"{job_title.lower()} {job_description}"
            location_lower = location.lower()

            if any(k in job_description for k in [
                "not remote", "not wfh", "not work from home", "not a hybrid role",
                "must work in office", "in the office full time", "on-site only", "office based", "office base"
            ]):
                remote_option = "On-site"
            elif any(k in location_lower for k in ["remote", "wfh", "work from home"]):
                remote_option = "Remote"
            elif "hybrid" in job_description:
                remote_option = "Hybrid"
            elif any(k in job_description for k in ["remote", "wfh", "work from home"]):
                remote_option = "Remote"
            else:
                remote_option = "On-site"

            employment_type = (
                "Full-time" if "full-time" in job_description else
                "Part-time" if "part-time" in job_description else
                "Contract" if "contract" in job_description else
                "Not specified"
            )

            if contains_keyword(job_title.lower(), ["manager", "director", "executive", "lead", "head", "officer", "team leader"]):
                seniority_level = "Mid-Senior level"
            elif contains_keyword(combined_text, ["associate", "specialist", "coordinator", "1 year", "2 years", "3 years"]):
                seniority_level = "Associate"
            elif contains_keyword(combined_text, ["intern", "internship"]):
                seniority_level = "Intern"
            elif contains_keyword(combined_text, ["fresh graduate", "entry-level", "assistant", "Bachelor's"]):
                seniority_level = "Entry-level"
            else:
                seniority_level = "Not specified"

            # 🔁 Fallback: Try to get posted_date from JSON-LD in detail page
            if posted_date == "N/A" or posted_date is None:
                try:
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    script_tag = soup.find('script', type='application/ld+json')
                    if script_tag:
                        json_data = json.loads(script_tag.text)
                        posted_raw = json_data.get("datePosted")
                        if posted_raw:
                            posted_date = posted_raw[:10]  # format: YYYY-MM-DD
                except Exception as e:
                    print(f"⚠️ Failed to extract posted date from job detail JSON: {e}")

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
    MAX_JOBS = 3  # INPUT NUMBER OF JOBS
    print(f"\n📍 Scraping JobStreet for: {keyword}")
    driver = get_chrome_driver()
    all_jobs = []
    page = 1

    while len(all_jobs) < MAX_JOBS:
        url = f"https://ph.jobstreet.com/{keyword.lower().replace(' ', '-')}-jobs?page={page}"
        driver.get(url)
        time.sleep(random.uniform(5, 7))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        jobs = soup.select('a[data-automation="jobTitle"]')

        if not jobs:
            break  

        for job in jobs:
            if len(all_jobs) >= MAX_JOBS:
                break
            href = job['href'].split("#")[0]
            job_url = "https://ph.jobstreet.com" + href
            posted_tag = job.find_next('span', attrs={"data-automation": "jobListingDate"})
            raw_posted = posted_tag.text.strip().replace("Posted ", "") if posted_tag else "N/A"
            posted_date = convert_posted_date_jobstreet(raw_posted)
            all_jobs.append((job_url, posted_date))

        page += 1

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
            combined_text = f"{job_title.lower()} {text}"

            if any(k in combined_text for k in ["remote", "wfh", "work from home"]):
                remote_option = "Remote"
            elif "hybrid" in combined_text:
                remote_option = "Hybrid"
            else:
                remote_option = "On-site"

            if contains_keyword(job_title.lower(), ["manager", "director", "executive", "lead", "head", "officer"]):
                seniority_level = "Mid-Senior level"
            elif contains_keyword(combined_text, ["associate", "specialist", "coordinator","1 year", "2 years", "3 years"]):
                seniority_level = "Associate"
            elif contains_keyword(combined_text, ["intern", "internship"]):
                seniority_level = "Intern"
            elif contains_keyword(combined_text, ["fresh graduate", "entry-level", "assistant"]):
                seniority_level = "Entry-level"
            else:
                seniority_level = "Not specified"

            if posted_date == "N/A":
                posted_date = None

            save_job(
                job_title=job_title,
                company_name=company,
                location=location,
                job_url=job_url,
                employment_type=employment_type,
                remote_option=remote_option,
                posted_date=posted_date,
                platform="JobStreet",
                keyword=keyword,
                seniority_level=seniority_level,
                scraped_at=datetime.now()
            )
        except Exception as e:
            print(f"❌ Error scraping JobStreet job: {e}")

    driver.quit()
    
def scrape_linkedin(keyword):
    MAX_JOBS = 3  # ✅ Desired number of jobs to scrape
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

    # 🔁 Scroll until enough cards are loaded
    total_scrolls = 0
    while True:
        job_cards = driver.find_elements(By.CLASS_NAME, 'base-card')
        if len(job_cards) >= MAX_JOBS or total_scrolls >= 10:
            break
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(3, 5))
        total_scrolls += 1

    job_cards = driver.find_elements(By.CLASS_NAME, 'base-card')[:MAX_JOBS]

    for job in job_cards:
        try:
            job.click()
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'description__text'))
            )
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'description__job-criteria-text'))
            )
            time.sleep(random.uniform(2, 4))

            title = job.find_element(By.CLASS_NAME, 'base-search-card__title').text.strip()
            company = job.find_element(By.CLASS_NAME, 'base-search-card__subtitle').text.strip()
            location = job.find_element(By.CLASS_NAME, 'job-search-card__location').text.strip()
            link = job.find_element(By.TAG_NAME, 'a').get_attribute('href')

            description_element = driver.find_element(By.CLASS_NAME, 'description__text')
            job_description = description_element.text.lower()
            combined_text = f"{title.lower()} {job_description}"

            posted_date = linkedin_format_posted_date(
                driver.find_element(By.CLASS_NAME, 'posted-time-ago__text').text.strip()
            )

            employment_type = "N/A"
            seniority_level = "N/A"
            try:
                criteria = driver.find_elements(By.CLASS_NAME, 'description__job-criteria-text')
                if len(criteria) >= 2:
                    seniority_level = criteria[0].text.strip()
                    employment_type = criteria[1].text.strip()
            except:
                pass

            if "hybrid" in combined_text:
                remote_option = "Hybrid"
            elif any(k in combined_text for k in ["remote", "wfh", "work from home"]):
                remote_option = "Remote"
            else:
                remote_option = "On-site"

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


def manual_captcha_and_save_cookies(keyword="marketing", cookie_file="indeed_cookies.json"):
    driver = get_chrome_driver()
    url = f"https://ph.indeed.com/jobs?q={keyword}&l=Philippines"
    driver.get(url)
    input("🛑 Solve the CAPTCHA manually in the browser window, then press Enter here...")
    save_cookies(driver, cookie_file)
    driver.quit()
    print("✅ Cookies saved.")

# === Main Entry ===
if __name__ == "__main__":
#    manual_captcha_and_save_cookies()
    clear_scraped_jobs()

    keywords = [
        "Marketing","Business Analytics"
    ]

    for keyword in keywords:
        scrape_jobstreet(keyword)
        scrape_linkedin(keyword)

        # ✅ Refresh driver per keyword (safely)
        indeed_driver = get_chrome_driver(load_cookies_from="indeed_cookies.json")
        scrape_indeed(keyword, driver=indeed_driver)
        indeed_driver.quit()
