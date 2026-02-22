from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
import re
import time
import csv
import os

MONASH_STUDENT_ADMIN_URL = 'https://www.monash.edu/students/admin/dates/principal-dates'

start_time = time.time()

### Source URLs scraping logic ###
async def scrape_url():

    print("Scraping all URLS... This will take less than 30 seconds.")

    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto(MONASH_STUDENT_ADMIN_URL)

        # Accept cookies if present
        try:
            await page.click('text="Accept all"', timeout=3000)
        except:
            pass

        await page.wait_for_timeout(3000) 

        # Extract HTML after expansion
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Get all nested sidebar <li> items (level 3)
        categories = soup.find_all("li", class_="lhs-nav-list__item--lvl3")
        links = []  

        # Extract all sublinks (level 4 and 5) for each category (level 3), 
        # we need to exclude level 3 links due to repetitive structure
        for category in categories:
            a_tags = category.find_all('a', class_=re.compile(r"lhs-nav-list__item-link--lvl\d+"))
            for a_tag in a_tags:
                title = a_tag.get_text(strip=True)

                # Clean numbering in front
                cleaned_title = re.sub(r"^\d+\.\s*", "", title)
                links.append((cleaned_title, a_tag["href"]))

        # Save the links to a csv file for ease of compatability 
        os.makedirs("data/bronze", exist_ok=True)
        with open("data/bronze/links.csv", "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Title", "URL"])  
            for title, url in links:
                writer.writerow([title, url])

        await browser.close()

    end_time = time.time()
    print(f"Scraper took {end_time - start_time:.2f} seconds to scrape all URLs.")
