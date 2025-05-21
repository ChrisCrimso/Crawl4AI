import requests
import asyncio
import json
from crawl4ai import AsyncWebCrawler

# List of target FIU-related URLs
urls = [
    {"name": "Onestop", "url": "https://onestop.fiu.edu"},
    {"name": "Commencement", "url": "https://commencement.fiu.edu"},
    {"name": "FIU", "url": "https://www.fiu.edu"},
    {"name": "Calendar", "url": "https://calendar.fiu.edu"},
    {"name": "Admissions", "url": "https://admissions.fiu.edu"},
    {"name": "Division of Student Affairs", "url": "https://dasa.fiu.edu"},
    {"name": "Student Access & Success", "url": "https://sas.fiu.edu"},
    {"name": "My Major", "url": "https://mymajor.fiu.edu"},
    {"name": "Catalog", "url": "https://catalog.fiu.edu"},
    {"name": "Scholarships", "url": "https://fiu.academicworks.com"},
    {"name": "Panther Connect", "url": "https://fiu.campuslabs.com/engagement"},
    {"name": "Parking", "url": "https://parking.fiu.edu"},
    {"name": "Operations", "url": "https://operations.fiu.edu"},
    {"name": "Emergency Management", "url": "https://dem.fiu.edu"},
    {"name": "Athletics", "url": "https://fiusports.com"},
    {"name": "Shops", "url": "https://shop.fiu.edu"},
    {"name": "News", "url": "https://news.fiu.edu"}
]

# Step 1: Crawl all URLs
async def crawl_all_sites(url_list):
    results = []

    async with AsyncWebCrawler() as crawler:
        for entry in url_list:
            name, url = entry["name"], entry["url"]
            try:
                result = await crawler.arun(url=url)
                results.append({
                    "name": name,
                    "url": url,
                    "content": result.markdown
                })
                print(f"[✓] Crawled: {name} → {url}")
            except Exception as e:
                print(f"[!] Failed to crawl {name} → {url} | Error: {e}")

    return results

# Step 2: Save to JSON
def save_to_json(data, filename="fiu_all_sites_data.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[💾] Saved data to {filename}")

# Step 3: Main function
def main():
    print("[🚀] Starting full FIU crawl...")
    crawled_data = asyncio.run(crawl_all_sites(urls))
    save_to_json(crawled_data)

if __name__ == "__main__":
    main()
# This script crawls multiple FIU-related URLs, extracts their content, and saves it to a JSON file.
# It uses the AsyncWebCrawler from the crawl4ai library to handle asynchronous crawling.