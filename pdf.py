#!/usr/bin/env python3
# pdf.py

import asyncio
import httpx
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
import PyPDF2
import io
import re

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

# Reuse the same site configurations from sum.py
FIU_SITES = {
    "main": {
        "name": "MainSite",
        "base_url": "https://www.fiu.edu",
    },
    "catalog": {
        "name": "Catalog",
        "base_url": "https://catalog.fiu.edu",
        "allowed_domains": ["catalog.fiu.edu"],
    },
    "athletics": {
        "name": "Athletics",
        "base_url": "https://fiusports.com",
    },
    "sas": {
        "name": "SAS",
        "base_url": "https://sas.fiu.edu",
    },
    "campuslabs": {
        "name": "CampusLabs", 
        "base_url": "https://fiu.campuslabs.com/engage",
    },
    "academicworks": {
        "name": "AcademicWorks",
        "base_url": "https://fiu.academicworks.com",
    },
    "calendar": {
        "name": "Calendar",
        "base_url": "https://calendar.fiu.edu",
    },
}

def extract_text_from_pdf(pdf_content):
    """Extract text content from PDF bytes"""
    try:
        # Create a BytesIO object from the PDF content
        pdf_file = io.BytesIO(pdf_content)
        
        # Create a PDF reader object
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Extract text from each page
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n\n"
        
        # Clean up the text - remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text
    except Exception as e:
        print(f"⚠️ Error extracting text: {str(e)}")
        return "Error extracting text from PDF."

async def download_pdf(url: str, output_dir: Path) -> bool:
    """Download a PDF file from the given URL and extract its text content"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            if response.status_code == 200 and 'application/pdf' in response.headers.get('content-type', '').lower():
                # Create filename from URL
                filename = url.split('/')[-1]
                if not filename.endswith('.pdf'):
                    filename += '.pdf'
                
                # Save the PDF
                pdf_filepath = output_dir / filename
                with open(pdf_filepath, 'wb') as f:
                    f.write(response.content)
                
                # Extract and save text content
                text_content = extract_text_from_pdf(response.content)
                text_filename = filename.replace('.pdf', '.txt')
                text_filepath = output_dir / text_filename
                
                with open(text_filepath, 'w', encoding='utf-8') as f:
                    # Add metadata
                    f.write(f"---\n")
                    f.write(f"url: {url}\n")
                    f.write(f"filename: {filename}\n")
                    f.write(f"extracted_at: {datetime.now().isoformat()}\n")
                    f.write(f"---\n\n")
                    # Write the extracted text
                    f.write(text_content)
                
                print(f"✅ Downloaded PDF and extracted text: {filename}")
                return True
    except Exception as e:
        print(f"❌ Failed to download {url}: {str(e)}")
    return False

async def crawl_pdfs(site_cfg: dict):
    """Crawl PDFs from a specific FIU site"""
    base = site_cfg["base_url"]
    site_name = site_cfg["name"]
    print(f"\n📄 Crawling PDFs from {site_name} @ {base}")
    
    # Create output directory within the site's folder
    output_dir = Path("fiu_content") / site_name / "pdfs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    browser_cfg = BrowserConfig()
    bfs = BFSDeepCrawlStrategy(max_depth=2, max_pages=300, include_external=False)
    cfg = CrawlerRunConfig(
        deep_crawl_strategy=bfs,
        cache_mode=CacheMode.BYPASS,
        exclude_external_links=True,
        check_robots_txt=True,
    )
    
    async with AsyncWebCrawler(config=browser_cfg) as cr:
        # Get the exact domain for this site
        exact_domain = urlparse(base).netloc.lower()
        print(f"⚠️ Enforcing strict domain filtering for {exact_domain}")
        
        # Site-specific filtering (similar to sum.py)
        def strict_pdf_filter(url):
            try:
                parsed = urlparse(url)
                url_domain = parsed.netloc.lower()
                
                # Must be exactly from the site's domain
                if url_domain != exact_domain:
                    print(f"🚫 Skipping non-{site_name} domain: {url_domain}")
                    return False
                
                # Only allow PDF files
                if not url.lower().endswith('.pdf'):
                    return False
                
                # Skip common external link patterns
                skip_patterns = [
                    "redirect", "external", "outgoing", "goto", 
                    "instagram", "facebook", "twitter", "linkedin",
                    "mailto:", "tel:", "javascript:", "youtube"
                ]
                
                for pattern in skip_patterns:
                    if pattern in url.lower():
                        print(f"🚫 Skipping external link pattern ({pattern}): {url}")
                        return False
                
                # Add site-specific filtering if needed
                if site_name == "MainSite":
                    # Only allow PDFs from the exact www.fiu.edu domain
                    if url_domain != "www.fiu.edu":
                        print(f"🚫 Skipping non-Main FIU domain: {url_domain}")
                        return False
                        
                elif site_name == "Catalog":
                    # Only allow PDFs from the exact catalog.fiu.edu domain
                    if url_domain != "catalog.fiu.edu":
                        print(f"🚫 Skipping non-Catalog domain: {url_domain}")
                        return False
                        
                elif site_name == "Athletics":
                    # Only allow PDFs from the fiusports.com domain
                    if url_domain != "fiusports.com":
                        print(f"🚫 Skipping non-Athletics domain: {url_domain}")
                        return False
                
                elif site_name == "SAS":
                    # Only allow PDFs from the sas.fiu.edu domain
                    if url_domain != "sas.fiu.edu":
                        print(f"🚫 Skipping non-SAS domain: {url_domain}")
                        return False
                
                elif site_name == "CampusLabs":
                    # Only allow PDFs from the fiu.campuslabs.com domain
                    if url_domain != "fiu.campuslabs.com":
                        print(f"🚫 Skipping non-CampusLabs domain: {url_domain}")
                        return False
                
                elif site_name == "AcademicWorks":
                    # Only allow PDFs from the fiu.academicworks.com domain
                    if url_domain != "fiu.academicworks.com":
                        print(f"🚫 Skipping non-AcademicWorks domain: {url_domain}")
                        return False
                
                elif site_name == "Calendar":
                    # Only allow PDFs from the calendar.fiu.edu domain
                    if url_domain != "calendar.fiu.edu":
                        print(f"🚫 Skipping non-Calendar domain: {url_domain}")
                        return False
                
                # Accepted PDF URL
                print(f"✅ Found PDF: {url}")
                return True
                
            except Exception as e:
                print(f"⚠️ Error filtering URL {url}: {str(e)}")
                return False
        
        cr.link_filter = strict_pdf_filter
        results = await cr.arun(base, config=cfg)
        
        # Double-check results to ensure domain compliance
        pdf_urls = []
        for res in results:
            try:
                if res.success and res.url.lower().endswith('.pdf'):
                    url_domain = urlparse(res.url).netloc.lower()
                    if url_domain == exact_domain:
                        pdf_urls.append(res.url)
                    else:
                        print(f"⚠️ Filtered out non-{site_name} URL from results: {res.url}")
            except:
                continue
        
        print(f"\n📊 Found {len(pdf_urls)} PDF files to download from {exact_domain}")
        
        # Download PDFs
        for url in pdf_urls:
            await download_pdf(url, output_dir)
            # Add small delay between downloads
            await asyncio.sleep(1)

async def main():
    # Create both the main content and pdf directories
    Path("fiu_content").mkdir(exist_ok=True)
    
    # Choose which site to crawl PDFs from
    # Uncomment the sites you want to process
    #await crawl_pdfs(FIU_SITES["main"])✅(depth 3)
    #await crawl_pdfs(FIU_SITES["catalog"])✅ It had 0 pdf files (depth 3)
    #await crawl_pdfs(FIU_SITES["athletics"])✅ (depth 3)
    #await crawl_pdfs(FIU_SITES["sas"]) (depth 2)✅
    #await crawl_pdfs(FIU_SITES["campuslabs"])✅ (depth 2)
    #await crawl_pdfs(FIU_SITES["academicworks"])✅ (depth 2)
    #await crawl_pdfs(FIU_SITES["calendar"])✅ (depth 3)

if __name__ == "__main__":
    asyncio.run(main())
