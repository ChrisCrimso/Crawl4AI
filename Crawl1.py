import requests
import asyncio
import json
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

# STEP 1: Get FIU OneStop URLs from the sitemap
def get_fiu_urls(sitemap_url):
    response = requests.get(sitemap_url)
    soup = BeautifulSoup(response.content, "xml")
    return [loc.text for loc in soup.find_all("loc")]

# STEP 2: Crawl each URL using Crawl4AI and extract Markdown content
async def crawl_urls(urls):
    results = []

    async with AsyncWebCrawler() as crawler:
        for url in urls:
            try:
                result = await crawler.arun(url=url)
                results.append({
                    "url": url,
                    "content": result.markdown
                })
                print(f"[✓] Crawled: {url}")
            except Exception as e:
                print(f"[!] Failed to crawl: {url} | Error: {e}")

    return results

# STEP 3: Save crawled content to a JSON file
def save_to_json(data, filename="fiu_onestop_data.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[💾] Saved data to {filename}")

# STEP 4: Main function to run everything
def main():
    sitemap_url = "https://onestop.fiu.edu/_assets/sitemap.xml"
    print("[🔎] Fetching URLs from sitemap...")
    urls = get_fiu_urls(sitemap_url)

    # Limit to the first 10 pages for now
    limited_urls = urls[:10]
    print(f"[📄] Found {len(limited_urls)} URLs to crawl")

    # Crawl & Save
    print("[⚙️] Starting crawl...")
    crawled_data = asyncio.run(crawl_urls(limited_urls))

    save_to_json(crawled_data)

if __name__ == "__main__":
    main()
