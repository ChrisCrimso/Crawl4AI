#!/usr/bin/env python3
# main.py

import asyncio
import httpx
import xml.etree.ElementTree as ET

from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

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
}

# ─── Helpers ────────────────────────────────────────────────────────────────

def create_markdown_filename(url: str, index: int = None) -> str:
    fn = url.replace("https://", "").replace("http://", "")
    fn = fn.replace("/", "_").replace(".", "_").replace("?", "_")
    fn = fn[:100]
    if index is not None:
        fn = f"{index:03d}_{fn}"
    return fn + ".md"

def save_markdown(content: str, metadata: dict, site_name: str, url: str, index: int = None):
    out_dir = Path("fiu_content") / site_name
    out_dir.mkdir(parents=True, exist_ok=True)

    filepath = out_dir / create_markdown_filename(url, index)
    front = (
        f"---\n"
        f"url: {url}\n"
        f"site: {site_name}\n"
        f"crawled_at: {metadata.get('crawled_at', datetime.now().isoformat())}\n"
        f"title: {metadata.get('title','No title')}\n"
        f"---\n\n"
    )
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(front)
        f.write(content or "")

    print(f"💾 Saved: {filepath}")

# ─── Sitemap parsing (with recursive fallback) ─────────────────────────────

async def parse_sitemap(url: str) -> list[str]:
    print(f"📄 Fetching sitemap: {url}")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, follow_redirects=True, timeout=20)
        if resp.status_code != 200:
            print(f"❌ HTTP {resp.status_code} for {url}")
            return []

        root = ET.fromstring(resp.text)
        ns   = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Try <sm:url><sm:loc>
        elems = root.findall(".//sm:url/sm:loc", ns) or root.findall(".//url/loc")
        if not elems:
            # Maybe it's a sitemap index?
            smaps = root.findall(".//sm:sitemap/sm:loc", ns) or root.findall(".//sitemap/loc")
            urls = []
            for e in smaps:
                urls += await parse_sitemap(e.text.strip())
            return urls

        # Filter extensions
        exclude = {".pdf",".jpg",".jpeg",".png",".mp4",".js",".webp",".css",".gif"}
        out = []
        for e in elems:
            u = e.text.strip()
            if not any(u.lower().endswith(ext) for ext in exclude):
                out.append(u)
        print(f"  → {len(out)} URLs (excluded {len(elems)-len(out)})")
        return out

    except Exception as e:
        print(f"❌ Error parsing sitemap {url}: {e}")
        return []

# ─── Crawl by sitemap (then fallback) ───────────────────────────────────────

async def crawl_with_sitemap(site_cfg: dict):
    urls = []
    for sm in site_cfg.get("sitemap_urls", []):
        urls += await parse_sitemap(sm)
    urls = list(dict.fromkeys(urls))  # de‑dup

    print(f"\n🔗 Total URLs from sitemap: {len(urls)}")
    if not urls:
        print("⚠️  Sitemap empty or missing → falling back to deep crawl")
        await crawl_with_deep_crawl(site_cfg)
        return

    # batch crawl
    browser_cfg = BrowserConfig()
    md_gen = DefaultMarkdownGenerator(content_filter=PruningContentFilter(0.48,"fixed"))
    cfg = CrawlerRunConfig(
        markdown_generator=md_gen,
        cache_mode=CacheMode.BYPASS,
        exclude_external_links=True,
        check_robots_txt=True,
        process_iframes=True,
        remove_overlay_elements=True
    )

    async with AsyncWebCrawler(config=browser_cfg) as cr:
        batches = [urls[i:i+5] for i in range(0, len(urls), 5)]
        idx = 1
        for batch in batches:
            print(f"\n📦 Batch {idx}/{len(batches)}")
            results = await cr.arun_many(urls=batch, config=cfg)
            for res, u in zip(results, batch):
                if res.success:
                    try:
                        # Improved markdown content handling with type safety
                        content = ""
                        if hasattr(res, "markdown"):
                            markdown_content = res.markdown
                            if isinstance(markdown_content, str):
                                content = markdown_content
                            elif hasattr(markdown_content, "fit_markdown"):
                                content = str(markdown_content.fit_markdown) if markdown_content.fit_markdown is not None else ""
                            elif hasattr(markdown_content, "raw_markdown"):
                                content = str(markdown_content.raw_markdown) if markdown_content.raw_markdown is not None else ""
                            else:
                                content = str(markdown_content)
                            
                        # Ensure content is a string
                        content = str(content) if content is not None else ""
                            
                        metadata = getattr(res, "metadata", {})
                        save_markdown(content, metadata, site_cfg["name"], u, index=idx)
                        print(f"✅ {u}")
                    except Exception as e:
                        print(f"⚠️ Error processing markdown for {u}: {str(e)}")
                        # Save raw content instead
                        try:
                            metadata = getattr(res, "metadata", {})
                            raw_content = getattr(res, "raw_content", "") or getattr(res, "content", "")
                            if raw_content:
                                save_markdown(f"## Raw Content (Error in processing)\n\n{raw_content[:20000]}", 
                                            metadata, site_cfg["name"], u, index=idx)
                                print(f"⚠️ Saved raw content for {u} instead")
                        except Exception as e2:
                            print(f"❌ Failed to save even raw content for {u}: {str(e2)}")
                else:
                    print(f"❌ {u} failed: {getattr(res,'error','?')}")
                idx += 1
            await asyncio.sleep(1)

# ─── BFS Deep‑crawl (host‑bound) ────────────────────────────────────────────

async def crawl_with_deep_crawl(site_cfg: dict):
    base = site_cfg["base_url"]
    host = urlparse(base).netloc.lower()
    print(f"\n🕷️ Deep crawling {site_cfg['name']} @ {base}")

    browser_cfg = BrowserConfig()
    # Increased max_depth to 3 and max_pages to 400 for more thorough crawling
    bfs = BFSDeepCrawlStrategy(max_depth=3, max_pages=400)
    md_gen = DefaultMarkdownGenerator(content_filter=PruningContentFilter(0.48,"fixed"))
    cfg = CrawlerRunConfig(
        deep_crawl_strategy=bfs,
        markdown_generator=md_gen,
        cache_mode=CacheMode.BYPASS,
        exclude_external_links=True,  # Changed to True to exclude external links
        check_robots_txt=True,
        process_iframes=True,
        remove_overlay_elements=True
    )

    async with AsyncWebCrawler(config=browser_cfg) as cr:
        # Stricter link filter that checks the exact host
        cr.link_filter = lambda u: urlparse(u).netloc.lower() == host and not any(ext in u.lower() for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js'])
        results = await cr.arun(base, config=cfg)

    print(f"→ Found {len(results)} pages under {host}")
    for idx, res in enumerate(results, start=1):
        u = res.url
        if res.success:
            content = ""
            if hasattr(res, "markdown"):
                if isinstance(res.markdown, str):
                    content = res.markdown
                elif hasattr(res.markdown, "fit_markdown"):
                    content = str(res.markdown.fit_markdown)
                else:
                    content = str(res.markdown)
            metadata = getattr(res, "metadata", {})
            save_markdown(content, metadata, site_cfg["name"], u, index=idx)
            print(f"✅ {u}")
        else:
            print(f"❌ {u} failed: {getattr(res,'error','?')}")

# ─── Main function and site crawler ───────────────────────────────────────

async def crawl_site(key: str):
    cfg = FIU_SITES.get(key)
    if not cfg:
        print(f"Unknown site: {key}")
        return

    print(f"\n{'='*60}\nCrawling site: {cfg['name']} ({cfg['base_url']})\n{'='*60}")
    if cfg.get("sitemap_urls"):
        await crawl_with_sitemap(cfg)
    else:
        await crawl_with_deep_crawl(cfg)

async def main():
    Path("fiu_content").mkdir(exist_ok=True)
   
    # Crawl the catalog site only
    await crawl_site("catalog")
    
    # Other sites commented out for now
    # await crawl_site("main")
    # await crawl_site("athletics")
    # await crawl_site("sas")
    # await crawl_site("campuslabs")
    # await crawl_site("academicworks")
    # await crawl_site("mymajor")

if __name__ == "__main__":
    asyncio.run(main())