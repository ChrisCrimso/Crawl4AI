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
        "allowed_domains": ["catalog.fiu.edu"],  # Explicitly specify allowed domain
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
        "base_url": "https://mymajor.fiu.edu/individual/215GEOSCBS",
        # no 'sitemap_urls' key here
    },
    
    # Example site with sitemap (keeping for reference)
    "onestop": {
        "name": "OneStop",
        "base_url": "https://onestop.fiu.edu",
        "sitemap_urls": ["https://onestop.fiu.edu/_assets/sitemap.xml"]
    },
    "calendar": {
        "name": "Calendar",
        "base_url": "https://calendar.fiu.edu",
        # no 'sitemap_urls' key here
    },
    "emergency": {
        "name": "Emergency",
        "base_url": "https://dem.fiu.edu",
        # no 'sitemap_urls' key here
    }
}

# ─── Helpers ────────────────────────────────────────────────────────────────

def create_markdown_filename(url: str, index: int = None) -> str:
    fn = url.replace("https://", "").replace("http://", "")
    fn = fn.replace("/", "_").replace(".", "_").replace("?", "_")
    fn = fn[:100]
    if index is not None:
        fn = f"{index:03d}_{fn}"
    # Always add .md extension
    if not fn.endswith(".md"):
        fn += ".md"
    return fn

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
    
    # Only save files with actual content or add a placeholder
    if content and len(content.strip()) > 0:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(front)
            f.write(content or "")
        print(f"💾 Saved: {filepath}")
    else:
        # Add placeholder for empty content
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(front)
            f.write("*Content could not be retrieved - this may be a page with dynamic JavaScript content.*\n")
        print(f"⚠️ Saved with placeholder (no content): {filepath}")

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

    # Special handling for catalog site
    if site_cfg["name"] == "Catalog":
        print("\n⚠️ Catalog site - using strict domain filtering and crawling")
        
        browser_cfg = BrowserConfig()
        
        # Use slightly deeper crawl for catalog with longer timeout
        bfs = BFSDeepCrawlStrategy(max_depth=3, max_pages=200, include_external=False)
        md_gen = DefaultMarkdownGenerator(content_filter=PruningContentFilter(0.48,"fixed"))
        cfg = CrawlerRunConfig(
            deep_crawl_strategy=bfs,
            markdown_generator=md_gen,
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            check_robots_txt=True,
            process_iframes=False,
            remove_overlay_elements=True
        )
        
        async with AsyncWebCrawler(config=browser_cfg) as cr:
            # Strict catalog domain filtering
            def strict_catalog_filter(url):
                try:
                    parsed = urlparse(url)
                    
                    # Must be exactly catalog.fiu.edu domain
                    if parsed.netloc.lower() != "catalog.fiu.edu":
                        print(f"🚫 Skipping non-catalog domain: {parsed.netloc}")
                        return False
                    
                    # Skip file extensions
                    if any(ext in url.lower() for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.ico']):
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
                            
                    # Permitted catalog paths - only crawl specific sections
                    allowed_paths = [
                        "/", "/courses", "/programs", "/college-school-department",
                        "/search", "/policies", "/resources"
                    ]
                    
                    # Check if URL path starts with any allowed path
                    path_allowed = any(parsed.path.lower().startswith(path.lower()) for path in allowed_paths)
                    if not path_allowed:
                        print(f"🚫 Skipping non-essential catalog path: {parsed.path}")
                        return False
                        
                    return True
                except Exception as e:
                    print(f"⚠️ Error filtering URL {url}: {str(e)}")
                    return False
                    
            cr.link_filter = strict_catalog_filter
            results = await cr.arun(base, config=cfg)
            
            # Filter results again to ensure we only process catalog.fiu.edu
            catalog_only_results = []
            for res in results:
                try:
                    if urlparse(res.url).netloc.lower() == "catalog.fiu.edu":
                        catalog_only_results.append(res)
                    else:
                        print(f"⚠️ Filtered out non-catalog URL from results: {res.url}")
                except:
                    continue
            
            print(f"\n📊 Processing {len(catalog_only_results)} catalog pages (strictly catalog.fiu.edu domain only)...")
            for idx, res in enumerate(catalog_only_results, start=1):
                u = res.url
                if res.success:
                    try:
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
                    except Exception as e:
                        print(f"❌ Error processing {u}: {str(e)}")
                else:
                    print(f"❌ {u} failed: {getattr(res,'error','?')}")
                
                # Add small delay between requests
                await asyncio.sleep(1)
        
        return  # End catalog-specific processing

    # Enhanced handling for SAS site which has many external links
    elif site_cfg["name"] == "SAS":
        print("\n⚠️ SAS site has many external links - using strict domain filtering")
        
        browser_cfg = BrowserConfig()
        bfs = BFSDeepCrawlStrategy(max_depth=2, max_pages=200, include_external=False)
        md_gen = DefaultMarkdownGenerator(content_filter=PruningContentFilter(0.48,"fixed"))
        cfg = CrawlerRunConfig(
            deep_crawl_strategy=bfs,
            markdown_generator=md_gen,
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            check_robots_txt=True,
            process_iframes=False,
            remove_overlay_elements=True
        )
        
        async with AsyncWebCrawler(config=browser_cfg) as cr:
            # Strict SAS domain filtering with detailed logging
            def strict_sas_filter(url):
                try:
                    parsed = urlparse(url)
                    
                    # Must be exactly sas.fiu.edu domain
                    if parsed.netloc.lower() != "sas.fiu.edu":
                        print(f"🚫 Skipping non-SAS domain: {parsed.netloc}")
                        return False
                    
                    # Skip file extensions
                    if any(ext in url.lower() for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.ico']):
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
                            
                    # Permitted SAS paths - only crawl specific sections
                    allowed_paths = [
                        "/", "/news", "/about", "/departments", 
                        "/research", "/centers", "/people",
                        "/undergraduate", "/graduate", "/resources",
                        "/partners", "/college-access", "/edeffect",
                        "/vision-mission", "/pre-collegiate-programs", "/staff"
                    ]
                    
                    # Check if URL path starts with any allowed path
                    path_allowed = any(parsed.path.lower().startswith(path.lower()) for path in allowed_paths)
                    if not path_allowed:
                        print(f"🚫 Skipping non-essential SAS path: {parsed.path}")
                        return False
                        
                    return True
                except Exception as e:
                    print(f"⚠️ Error filtering URL {url}: {str(e)}")
                    return False
                    
            cr.link_filter = strict_sas_filter
            results = await cr.arun(base, config=cfg)
            
            # Filter results again to ensure we only process sas.fiu.edu
            sas_only_results = []
            for res in results:
                try:
                    if urlparse(res.url).netloc.lower() == "sas.fiu.edu":
                        sas_only_results.append(res)
                    else:
                        print(f"⚠️ Filtered out non-SAS URL from results: {res.url}")
                except:
                    continue
            
            print(f"\n📊 Processing {len(sas_only_results)} SAS pages (strictly sas.fiu.edu domain only)...")
            for idx, res in enumerate(sas_only_results, start=1):
                u = res.url
                if res.success:
                    try:
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
                    except Exception as e:
                        print(f"❌ Error processing {u}: {str(e)}")
                else:
                    print(f"❌ {u} failed: {getattr(res,'error','?')}")
                
                # Add delay to avoid overloading the server
                await asyncio.sleep(2 if idx % 5 == 0 else 1)
        
        return  # End SAS-specific processing

    # Enhanced handling for MainSite (www.fiu.edu)
    elif site_cfg["name"] == "MainSite":
        print("\n⚠️ Main FIU site - using strict domain filtering and crawling")
        
        browser_cfg = BrowserConfig()
        # Use deeper crawl for main site
        bfs = BFSDeepCrawlStrategy(max_depth=3, max_pages=300, include_external=False)
        md_gen = DefaultMarkdownGenerator(content_filter=PruningContentFilter(0.48,"fixed"))
        cfg = CrawlerRunConfig(
            deep_crawl_strategy=bfs,
            markdown_generator=md_gen,
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            check_robots_txt=True,
            process_iframes=False,
            remove_overlay_elements=True
        )
        
        async with AsyncWebCrawler(config=browser_cfg) as cr:
            # Strict Main FIU domain filtering with detailed logging
            def strict_main_filter(url):
                try:
                    parsed = urlparse(url)
                    
                    # Must be exactly www.fiu.edu domain
                    if parsed.netloc.lower() != "www.fiu.edu":
                        print(f"🚫 Skipping non-main FIU domain: {parsed.netloc}")
                        return False
                    
                    # Skip file extensions
                    if any(ext in url.lower() for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.ico']):
                        return False
                    
                    # Skip common external link patterns
                    skip_patterns = [
                        "redirect", "external", "outgoing", "goto", 
                        "instagram", "facebook", "twitter", "linkedin",
                        "mailto:", "tel:", "javascript:", "youtube",
                        "login", "signin", "auth"
                    ]
                    
                    for pattern in skip_patterns:
                        if pattern in url.lower():
                            print(f"🚫 Skipping external link pattern ({pattern}): {url}")
                            return False
                            
                    # Permitted main FIU paths - only crawl specific sections
                    allowed_paths = [
                        "/", "/about", "/admissions", "/academics", 
                        "/college", "/school", "/directory", "/research",
                        "/students", "/parents", "/alumni", "/faculty-staff",
                        "/campus-life", "/careers", "/libraries", "/news",
                        "/events", "/locations", "/programs", "/community"
                    ]
                    
                    # Check if URL path starts with any allowed path
                    path_allowed = any(parsed.path.lower().startswith(path.lower()) for path in allowed_paths)
                    if not path_allowed:
                        print(f"🚫 Skipping non-essential main FIU path: {parsed.path}")
                        return False
                        
                    return True
                except Exception as e:
                    print(f"⚠️ Error filtering URL {url}: {str(e)}")
                    return False
                    
            cr.link_filter = strict_main_filter
            results = await cr.arun(base, config=cfg)
            
            # Filter results again to ensure we only process www.fiu.edu
            main_only_results = []
            for res in results:
                try:
                    if urlparse(res.url).netloc.lower() == "www.fiu.edu":
                        main_only_results.append(res)
                    else:
                        print(f"⚠️ Filtered out non-main FIU URL from results: {res.url}")
                except:
                    continue
            
            print(f"\n📊 Processing {len(main_only_results)} main FIU pages (strictly www.fiu.edu domain only)...")
            for idx, res in enumerate(main_only_results, start=1):
                u = res.url
                if res.success:
                    try:
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
                    except Exception as e:
                        print(f"❌ Error processing {u}: {str(e)}")
                else:
                    print(f"❌ {u} failed: {getattr(res,'error','?')}")
                
                # Add delay to avoid overloading the server
                await asyncio.sleep(2 if idx % 5 == 0 else 1)
        
        return  # End main FIU-specific processing

    # Enhanced handling for MyMajor site
    elif site_cfg["name"] == "MyMajor":
        print("\n⚠️ MyMajor site - using strict domain filtering and crawling")
        
        browser_cfg = BrowserConfig()
        # Use deeper crawl for MyMajor site
        bfs = BFSDeepCrawlStrategy(max_depth=1, max_pages=300, include_external=False)
        md_gen = DefaultMarkdownGenerator(content_filter=PruningContentFilter(0.48,"fixed"))
        cfg = CrawlerRunConfig(
            deep_crawl_strategy=bfs,
            markdown_generator=md_gen,
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            check_robots_txt=True,
            process_iframes=False,
            remove_overlay_elements=True
        )
        
        async with AsyncWebCrawler(config=browser_cfg) as cr:
            # Strict MyMajor domain filtering with detailed logging
            def strict_mymajor_filter(url):
                try:
                    parsed = urlparse(url)
                    
                    # Must be exactly mymajor.fiu.edu domain
                    if parsed.netloc.lower() != "mymajor.fiu.edu":
                        print(f"🚫 Skipping non-MyMajor domain: {parsed.netloc}")
                        return False
                    
                    # Skip file extensions
                    if any(ext in url.lower() for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.ico']):
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
                            
                    return True
                except Exception as e:
                    print(f"⚠️ Error filtering URL {url}: {str(e)}")
                    return False
                    
            cr.link_filter = strict_mymajor_filter
            results = await cr.arun(base, config=cfg)
            
            # Filter results again to ensure we only process mymajor.fiu.edu
            mymajor_only_results = []
            for res in results:
                try:
                    if urlparse(res.url).netloc.lower() == "mymajor.fiu.edu":
                        mymajor_only_results.append(res)
                    else:
                        print(f"⚠️ Filtered out non-MyMajor URL from results: {res.url}")
                except:
                    continue
            
            print(f"\n📊 Processing {len(mymajor_only_results)} MyMajor pages (strictly mymajor.fiu.edu domain only)...")
            for idx, res in enumerate(mymajor_only_results, start=1):
                u = res.url
                if res.success:
                    try:
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
                    except Exception as e:
                        print(f"❌ Error processing {u}: {str(e)}")
                else:
                    print(f"❌ {u} failed: {getattr(res,'error','?')}")
                
                # Add delay to avoid overloading the server
                await asyncio.sleep(2 if idx % 5 == 0 else 1)
        
        return  # End MyMajor-specific processing

    # Enhanced handling for Emergency site
    elif site_cfg["name"] == "Emergency":
        print("\n⚠️ Emergency site - using strict domain filtering and crawling")
        
        browser_cfg = BrowserConfig()
        # Use appropriate crawl depth for emergency site
        bfs = BFSDeepCrawlStrategy(max_depth=1, max_pages=200, include_external=False)
        md_gen = DefaultMarkdownGenerator(content_filter=PruningContentFilter(0.48,"fixed"))
        cfg = CrawlerRunConfig(
            deep_crawl_strategy=bfs,
            markdown_generator=md_gen,
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            check_robots_txt=True,
            process_iframes=False,
            remove_overlay_elements=True
        )
        
        async with AsyncWebCrawler(config=browser_cfg) as cr:
            # Strict Emergency domain filtering with detailed logging
            def strict_emergency_filter(url):
                try:
                    parsed = urlparse(url)
                    
                    # Must be exactly dem.fiu.edu domain
                    if parsed.netloc.lower() != "dem.fiu.edu":
                        print(f"🚫 Skipping non-Emergency domain: {parsed.netloc}")
                        return False
                    
                    # Skip file extensions
                    if any(ext in url.lower() for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.ico']):
                        return False
                    
                    # Skip common external link patterns
                    skip_patterns = [
                        "redirect", "external", "outgoing", "goto", 
                        "instagram", "facebook", "twitter", "linkedin",
                        "mailto:", "tel:", "javascript:", "youtube",
                        "login", "signin", "auth"
                    ]
                    
                    for pattern in skip_patterns:
                        if pattern in url.lower():
                            print(f"🚫 Skipping external link pattern ({pattern}): {url}")
                            return False
                            
                    # Permitted emergency paths - only crawl specific sections
                    allowed_paths = [
                        "/", "/about", "/alerts", "/emergency", 
                        "/preparedness", "/resources", "/plans",
                        "/training", "/contact", "/services",
                        "/safety", "/procedures", "/information",
                        "/response", "/recovery", "/mitigation",
                        "/hurricane", "/weather", "/team"
                    ]
                    
                    # Check if URL path starts with any allowed path
                    path_allowed = any(parsed.path.lower().startswith(path.lower()) for path in allowed_paths)
                    if not path_allowed:
                        print(f"🚫 Skipping non-essential Emergency path: {parsed.path}")
                        return False
                        
                    return True
                except Exception as e:
                    print(f"⚠️ Error filtering URL {url}: {str(e)}")
                    return False
                    
            cr.link_filter = strict_emergency_filter
            results = await cr.arun(base, config=cfg)
            
            # Filter results again to ensure we only process dem.fiu.edu
            emergency_only_results = []
            for res in results:
                try:
                    if urlparse(res.url).netloc.lower() == "dem.fiu.edu":
                        emergency_only_results.append(res)
                    else:
                        print(f"⚠️ Filtered out non-Emergency URL from results: {res.url}")
                except:
                    continue
            
            print(f"\n📊 Processing {len(emergency_only_results)} Emergency pages (strictly dem.fiu.edu domain only)...")
            for idx, res in enumerate(emergency_only_results, start=1):
                u = res.url
                if res.success:
                    try:
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
                    except Exception as e:
                        print(f"❌ Error processing {u}: {str(e)}")
                else:
                    print(f"❌ {u} failed: {getattr(res,'error','?')}")
                
                # Add delay to avoid overloading the server
                await asyncio.sleep(2 if idx % 5 == 0 else 1)
        
        return  # End Emergency-specific processing

    # Enhanced handling for CampusLabs site
    elif site_cfg["name"] == "CampusLabs":
        print("\n⚠️ CampusLabs site - using strict domain filtering and crawling")
        
        browser_cfg = BrowserConfig()
        # Use deeper crawl for CampusLabs
        bfs = BFSDeepCrawlStrategy(max_depth=3, max_pages=300, include_external=False)
        md_gen = DefaultMarkdownGenerator(content_filter=PruningContentFilter(0.48,"fixed"))
        cfg = CrawlerRunConfig(
            deep_crawl_strategy=bfs,
            markdown_generator=md_gen,
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            check_robots_txt=True,
            process_iframes=False,
            remove_overlay_elements=True
        )
        
        async with AsyncWebCrawler(config=browser_cfg) as cr:
            # Strict CampusLabs domain filtering
            def strict_campuslabs_filter(url):
                try:
                    parsed = urlparse(url)
                    
                    # Only allow fiu.campuslabs.com domain
                    campuslabs_domain = "fiu.campuslabs.com"
                    if parsed.netloc.lower() != campuslabs_domain:
                        print(f"🚫 Skipping non-CampusLabs domain: {parsed.netloc}")
                        return False
                    
                    # Skip file extensions
                    if any(ext in url.lower() for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.ico']):
                        return False
                    
                    # Skip common external link patterns
                    skip_patterns = [
                        "redirect", "external", "outgoing", "goto", 
                        "instagram", "facebook", "twitter", "linkedin",
                        "mailto:", "tel:", "javascript:", "youtube",
                        "login", "signin", "auth"
                    ]
                    
                    for pattern in skip_patterns:
                        if pattern in url.lower():
                            print(f"🚫 Skipping external link pattern ({pattern}): {url}")
                            return False
                    
                    # Make sure the URL has the engage path (most important content)
                    if "/engage" not in url.lower() and url.lower() != campuslabs_domain:
                        print(f"🚫 Skipping non-engage CampusLabs path: {url}")
                        return False
                            
                    return True
                except Exception as e:
                    print(f"⚠️ Error filtering URL {url}: {str(e)}")
                    return False
                    
            cr.link_filter = strict_campuslabs_filter
            results = await cr.arun(base, config=cfg)
            
            # Filter results again to ensure we only process fiu.campuslabs.com
            campuslabs_only_results = []
            for res in results:
                try:
                    if urlparse(res.url).netloc.lower() == "fiu.campuslabs.com":
                        campuslabs_only_results.append(res)
                    else:
                        print(f"⚠️ Filtered out non-CampusLabs URL from results: {res.url}")
                except:
                    continue
            
            print(f"\n📊 Processing {len(campuslabs_only_results)} CampusLabs pages (strictly fiu.campuslabs.com domain only)...")
            for idx, res in enumerate(campuslabs_only_results, start=1):
                u = res.url
                if res.success:
                    try:
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
                    except Exception as e:
                        print(f"❌ Error processing {u}: {str(e)}")
                else:
                    print(f"❌ {u} failed: {getattr(res,'error','?')}")
                
                # Add delay to avoid overloading the server
                await asyncio.sleep(2 if idx % 5 == 0 else 1)
        
        return  # End CampusLabs-specific processing

    # Enhanced handling for Calendar site
    elif site_cfg["name"] == "Calendar":
        print("\n⚠️ Calendar site - using strict domain filtering and crawling")
        
        browser_cfg = BrowserConfig()
        # Use appropriate crawl depth for calendar site
        bfs = BFSDeepCrawlStrategy(max_depth=4, max_pages=300, include_external=False)
        md_gen = DefaultMarkdownGenerator(content_filter=PruningContentFilter(0.48,"fixed"))
        cfg = CrawlerRunConfig(
            deep_crawl_strategy=bfs,
            markdown_generator=md_gen,
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            check_robots_txt=True,
            process_iframes=False,
            remove_overlay_elements=True
        )
        
        async with AsyncWebCrawler(config=browser_cfg) as cr:
            # Strict Calendar domain filtering
            def strict_calendar_filter(url):
                try:
                    parsed = urlparse(url)
                    
                    # Only allow calendar.fiu.edu domain
                    calendar_domain = "calendar.fiu.edu"
                    if parsed.netloc.lower() != calendar_domain:
                        print(f"🚫 Skipping non-Calendar domain: {parsed.netloc}")
                        return False
                    
                    # Skip file extensions 
                    if any(ext in url.lower() for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.ico', '.ics', '.xml']):
                        return False
                    
                    # Skip common external link patterns
                    skip_patterns = [
                        "redirect", "external", "outgoing", "goto", 
                        "instagram", "facebook", "twitter", "linkedin",
                        "mailto:", "tel:", "javascript:", "youtube",
                        "login", "signin", "auth", "webcal://", 
                        "download", "export", "subscribe", "feed"
                    ]
                    
                    for pattern in skip_patterns:
                        if pattern in url.lower():
                            print(f"🚫 Skipping external link pattern ({pattern}): {url}")
                            return False
                    
                    # Specific calendar paths to include (focus on event listings and categories)
                    allowed_paths = [
                        "/", "/events", "/calendar", "/categories", 
                        "/view", "/search", "/month", "/week", "/day",
                        "/department", "/college", "/upcoming"
                    ]
                    
                    # Check if URL path starts with any allowed path or contains specific event indicators
                    path_allowed = any(parsed.path.lower().startswith(path.lower()) for path in allowed_paths) or '/event/' in parsed.path.lower()
                    if not path_allowed:
                        print(f"🚫 Skipping non-essential Calendar path: {parsed.path}")
                        return False
                            
                    return True
                except Exception as e:
                    print(f"⚠️ Error filtering URL {url}: {str(e)}")
                    return False
                    
            cr.link_filter = strict_calendar_filter
            results = await cr.arun(base, config=cfg)
            
            # Filter results again to ensure we only process calendar.fiu.edu
            calendar_only_results = []
            for res in results:
                try:
                    if urlparse(res.url).netloc.lower() == "calendar.fiu.edu":
                        calendar_only_results.append(res)
                    else:
                        print(f"⚠️ Filtered out non-Calendar URL from results: {res.url}")
                except:
                    continue
            
            print(f"\n📊 Processing {len(calendar_only_results)} Calendar pages (strictly calendar.fiu.edu domain only)...")
            for idx, res in enumerate(calendar_only_results, start=1):
                u = res.url
                if res.success:
                    try:
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
                    except Exception as e:
                        print(f"❌ Error processing {u}: {str(e)}")
                else:
                    print(f"❌ {u} failed: {getattr(res,'error','?')}")
                
                # Add delay to avoid overloading the server
                await asyncio.sleep(2 if idx % 5 == 0 else 1)
        
        return  # End Calendar-specific processing

    # Normal processing for all other sites (unchanged)
    browser_cfg = BrowserConfig()
    # Adjust depth based on the site
    
    bfs = BFSDeepCrawlStrategy(max_depth=1, max_pages=400, include_external=False)
    md_gen = DefaultMarkdownGenerator(content_filter=PruningContentFilter(0.48,"fixed"))
    cfg = CrawlerRunConfig(
        deep_crawl_strategy=bfs,
        markdown_generator=md_gen,
        cache_mode=CacheMode.BYPASS,
        exclude_external_links=True,
        check_robots_txt=True,
        process_iframes=True,
        remove_overlay_elements=True
    )

    # Domain-specific link filter
    current_domain = urlparse(base).netloc.lower()
    
    async with AsyncWebCrawler(config=browser_cfg) as cr:
        # Add domain filtering for the specific site
        cr.link_filter = lambda url: urlparse(url).netloc.lower() == current_domain
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
            
            # Add small delay to be nice to the server
            if idx % 10 == 0:
                await asyncio.sleep(1)

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
   
    # Uncomment the sites you want to crawl
    
    # Choose which site to crawl
    #await crawl_site("main")
    
    # Other sites - uncomment as needed
    # await crawl_site("calendar")
    # await crawl_site("mymajor")
    # await crawl_site("catalog")
    # await crawl_site("athletics")
    # await crawl_site("sas")
    # await crawl_site("campuslabs")
    # await crawl_site("academicworks")
    await crawl_site("emergency")

if __name__ == "__main__":
    asyncio.run(main())