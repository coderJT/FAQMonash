import os
import asyncio
from source_urls_scraper import scrape_url
from url_details_scraper import scrape_pages
from handbook_scraper import scrape_handbook
from clean_scraped_result import process_data
from build_index import indexing

def run_pipeline():
    print("--- Starting Data Pipeline ---")
    
    faq_scraped = os.path.exists("data/silver/cleaned") and len(os.listdir("data/silver/cleaned")) > 0
    
    if not faq_scraped:
        print("\n[1/5] Scraping source URLs (Bronze Layer)")
        try:
            asyncio.run(scrape_url())
        except Exception as e:
            print(f"Error in scraping source URLs: {e}")

        print("\n[2/5] Scraping page details (Bronze Layer)")
        try:
            asyncio.run(scrape_pages())
        except Exception as e:
            print(f"Error in scraping detailed pages: {e}")
            
        print("\n[3/5] Cleaning scraped results (Silver Layer)")
        try:
            process_data()
        except Exception as e:
            print(f"Error in processing/cleaning data: {e}")
    else:
        print("\n[1/5 - 3/5] FAQ data already exists. Skipping source URL, page scraping, and cleaning.")

    print("\n[4/5] Scraping Monash Handbook (Silver Layer directly)")
    try:
        asyncio.run(scrape_handbook())
    except Exception as e:
        print(f"Error in scraping handbook: {e}")

    print("\n[5/5] Building index (Gold Layer)")
    try:
        indexing()
    except Exception as e:
        print(f"Error in building index: {e}")
        
    print("\n--- Data Pipeline Completed ---")

if __name__ == "__main__":
    run_pipeline()
