import asyncio
import aiohttp
import aiofiles
import json
import re
import os
import time
from bs4 import BeautifulSoup

COURSELOOP_SEARCH_URL = "https://api-ap-southeast-2.prod.courseloop.com/publisher/search-all?from={}&query=&searchType=advanced&siteId=monash-prod-pres&siteYear=current&size=100"
UNIT_URL_TEMPLATE = "https://handbook.monash.edu/current/units/{}"

async def fetch_unit_codes():
    print("Fetching list of all units from CourseLoop API...")
    codes = set()
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        offset = 0
        while True:
            try:
                async with session.get(COURSELOOP_SEARCH_URL.format(offset)) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("data", {}).get("results", [])
                        if not results:
                            break
                        for item in results:
                            code = item.get("code")
                            if code:
                                codes.add(code)
                        print(f"Fetched offset {offset}, total unique so far: {len(codes)}")
                        offset += 100
                        # Be polite between pagination requests
                        await asyncio.sleep(0.5)
                    else:
                        print(f"Failed to fetch unit list at offset {offset}, status: {response.status}")
            except Exception as e:
                print(f"Error fetching offset {offset}: {e}")
    
    print(f"Total unique units found: {len(codes)}")
    return list(codes)

async def fetch_unit_details(session, code, semaphore):
    async with semaphore:
        url = UNIT_URL_TEMPLATE.format(code)
        try:
            async with session.get(url, timeout=15) as response:
                if response.status != 200:
                    return None
                    
                html = await response.text()
                match = re.search(r'id="__NEXT_DATA__" type="application/json">([^<]+)</script>', html)
                if not match:
                    return None
                    
                data = json.loads(match.group(1))
                page_content = data.get('props', {}).get('pageProps', {}).get('pageContent', {})
                
                if not page_content:
                    return None
                    
                # Clean HTML from all nested fields to retain everything
                def clean_html(value):
                    if isinstance(value, str):
                        if '<' in value and '>' in value:
                            soup = BeautifulSoup(value, 'html.parser')
                            return soup.get_text(separator='\\n', strip=True)
                        return value
                    elif isinstance(value, dict):
                        return {k: clean_html(v) for k, v in value.items() if v is not None and v != ""}
                    elif isinstance(value, list):
                        return [clean_html(v) for v in value if v is not None and v != ""]
                    else:
                        return value
                
                clean_content_dict = clean_html(page_content)
                
                # Format into a context block
                content = json.dumps(clean_content_dict, indent=2)
                
                return {
                    "code": code,
                    "content": content
                }
        except Exception as e:
            return None

async def scrape_handbook():
    start_time = time.time()
    os.makedirs("data/silver/handbook", exist_ok=True)
    
    codes = await fetch_unit_codes()
    # Limit for quick testing/processing, or do all if production. Let's do all.
    # To be polite to Monash's servers and avoid IP bans, we limit concurrency.
    semaphore = asyncio.Semaphore(15)
    
    print(f"Starting concurrent fetch of {len(codes)} units...")
    
    success_count = 0
    headers = {"User-Agent": "Mozilla/5.0"}
    
    connector = aiohttp.TCPConnector(limit=15)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        tasks = [fetch_unit_details(session, code, semaphore) for code in codes]
        
        # Process as they complete
        for completed_task in asyncio.as_completed(tasks):
            result = await completed_task
            if result:
                code = result["code"]
                content = result["content"]
                
                # Save to silver layer directly
                async with aiofiles.open(f"data/silver/handbook/{code}.clean.txt", "w", encoding="utf-8") as f:
                    await f.write(content)
                success_count += 1
                
                if success_count % 500 == 0:
                    print(f"Processed {success_count}/{len(codes)} units...")
                    
    end_time = time.time()
    print(f"Handbook scraper complete. Successfully saved {success_count} units in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    asyncio.run(scrape_handbook())
