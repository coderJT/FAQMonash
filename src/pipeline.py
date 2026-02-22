import asyncio
from source_urls_scraper import scrape_url
from url_details_scraper import scrape_pages
from clean_scraped_result import process_data
from build_index import indexing

def run_pipeline():
    print("--- Starting Data Pipeline ---")
    
    print("\n[1/4] Scraping source URLs (Bronze Layer)")
    try:
        asyncio.run(scrape_url())
    except Exception as e:
        print(f"Error in scraping source URLs: {e}")

    print("\n[2/4] Scraping page details (Bronze Layer)")
    try:
        asyncio.run(scrape_pages())
    except Exception as e:
        print(f"Error in scraping detailed pages: {e}")
        
    print("\n[3/4] Cleaning scraped results (Silver Layer)")
    try:
        process_data()
    except Exception as e:
        print(f"Error in processing/cleaning data: {e}")
        
    print("\n[4/4] Building index (Gold Layer)")
    try:
        indexing()
    except Exception as e:
        print(f"Error in building index: {e}")
        
    print("\n--- Data Pipeline Completed ---")

if __name__ == "__main__":
    run_pipeline()
