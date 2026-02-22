import csv
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup, Comment
import os
import asyncio
import aiofiles
import time

# Scrape contents in the urls defined
async def scrape_page(links, browser, title, url):

    context = await browser.new_context() 
    page = await context.new_page()

    # Update scraping status
    current_index = links.index((title, url)) + 1
    total_links = len(links)
    print(f"Scraping ({current_index}/{total_links}): {title} - {url}")

    # For simplicity, we will disregard pdf files at this MVP phase
    if url.lower().endswith(".pdf"):
        print(f"Skipping PDF: {url}")
        return
    
    try:
        await page.goto(url, timeout=15000)
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        await page.close()
        return

    # Handles cases when we are prompt to accept cookies
    try:
        await page.click('text="Accept all"', timeout=2000)
    except:
        pass

    # Here BeautifulSoup is used as the page is rather static
    html = await page.content()
    soup = BeautifulSoup(html, "html.parser") 

    # All pages share the same main content structure as of 24 June 2025
    raw_html = soup.find("div", class_="content-inner__main")
    if not raw_html:
        raw_html = soup.find("div", class_="main-content")
        
    if not raw_html:
        print(f"Error: Main container not found for {url}")
        await page.close()
        return

    # These are the tags to be excluded as there are a waste of tokens
    for tag in raw_html.find_all(["nav", "style", "script", "noscript", "iframe"]):
        tag.decompose()

    # Exclude the common faq help panel
    faq_help_panel = raw_html.find("div", id="monash-faq-help-panel")
    if faq_help_panel:
        faq_help_panel.decompose()

    # Exclude comments
    for comment in raw_html.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    response = str(raw_html)

    # Finally we write the result to files under data/bronze/pages/{title}.txt
    # aiofiles is used as we are performing asynchronous tasks and we would not want
    # to block the I/O thread.
    async with aiofiles.open(f"data/bronze/pages/{title}.txt", "w", encoding="utf-8") as out:
        await out.write(response)

    # Close page and context to prevent resources leakage
    await context.close()
    await page.close()

# Main function to scrape asynchronously
async def scrape_pages():

    start_time = time.time()

    # Extract all the links
    links = []
    with open("data/bronze/links.csv", newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            links.append((row["Title"], row["URL"]))

    os.makedirs("data/bronze/pages", exist_ok=True)
    
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch()

        # Currently, we limit concurrency to 5 to scrape responsibly
        semaphore = asyncio.Semaphore(5)

        # Wrapper to scrape page
        async def sem_scrape(title, url):
            async with semaphore:
                await scrape_page(links, browser, title, url)

        tasks = [sem_scrape(title, url) for title, url in links]
        await asyncio.gather(*tasks)
        await browser.close()

        end_time = time.time()
        print(f"Scraper took {end_time - start_time:.2f} seconds to scrape all URL's information.")
