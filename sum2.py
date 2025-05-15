#!/usr/bin/env python3
# main.py
 
import asyncio
import httpx
import xml.etree.ElementTree as ET
import re
from bs4 import BeautifulSoup  # You might need to pip install beautifulsoup4
 
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, urljoin
 
from crawl4ai import AsyncWebCrawler, BestFirstCrawlingStrategy, ContentTypeFilter, DomainFilter, FilterChain, KeywordRelevanceScorer, URLPatternFilter
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
 
# Global list to store PDF URLs
pdf_urls = []
 
# ─── Your site configs ─────────────────────────────────────────────────────
FIU_SITES = {
    # Main FIU websites (no sitemaps)
    "main": {
        "name": "MainSite",
        "base_url": "https://www.fiu.edu",
        # no 'sitemap_urls' key here
    },
    "catalog": {
        "name": "Catalog",
        "base_url": "https://catalog.fiu.edu",
        # no 'sitemap_urls' key here
    },
    "athletics": {
        "name": "Athletics",
        "base_url": "https://fiusports.com",
        # no 'sitemap_urls' key here
    },
    "sas": {
        "name": "SAS",
        "base_url": "https://sas.fiu.edu",
        # no 'sitemap_urls' key here
    },
    "campuslabs": {
        "name": "CampusLabs",
        "base_url": "https://fiu.campuslabs.com/engage",
        # no 'sitemap_urls' key here
    },
    "academicworks": {
        "name": "AcademicWorks",
        "base_url": "https://fiu.academicworks.com",
        # no 'sitemap_urls' key here
    },
    "mymajor": {
        "name": "MyMajor",
        "base_url": "https://mymajor.fiu.edu",
        # no 'sitemap_urls' key here
    },
    
    # Example site with sitemap (keeping for reference)
    "onestop": {
        "name": "OneStop",
        "base_url": "https://onestop.fiu.edu",
        "sitemap_urls": ["https://onestop.fiu.edu/_assets/sitemap.xml"]
    },
    "dem": {
        "name": "Department of Emergency Management",
        "base_url": "https://dem.fiu.edu/",
    },
    "dasa": {
        "name": "Division of Student Affairs",
        "base_url": "https://dasa.fiu.edu",
    },
    
}
 
# ─── Helpers ────────────────────────────────────────────────────────────────
 
async def run_advanced_crawler():
    # Define only domain filter
    filter_chain = FilterChain([
        DomainFilter(allowed_domains=["mymajor.fiu.edu"]),
    ])
 
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=2,
            include_external=False,
            filter_chain=filter_chain
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
    )
 
    # Process results after crawling
    pdf_urls = []
    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun("https://mymajor.fiu.edu", config=config)
        
        # Post-process to filter PDFs
        for result in results:
            if result.url.lower().endswith('.pdf'):
                pdf_urls.append(result.url)
 
    # Print results
    print(f"\nFound {len(pdf_urls)} PDF files:")
    for pdf in pdf_urls:
        print(f"- {pdf}")
 
if __name__ == "__main__":
    asyncio.run(run_advanced_crawler())