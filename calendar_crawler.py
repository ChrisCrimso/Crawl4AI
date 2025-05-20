#!/usr/bin/env python3
# calendar_crawler.py - Specialized crawler for FIU Calendar events

import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timedelta

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

# Calendar configuration
CALENDAR_CONFIG = {
    "name": "Calendar",
    "base_url": "https://calendar.fiu.edu",
}

# Special URLs to ensure past/current/future events are captured
CALENDAR_SPECIAL_URLS = [
    "https://calendar.fiu.edu/",  # Current events
    "https://calendar.fiu.edu/upcoming",  # Upcoming events
    "https://calendar.fiu.edu/day",  # Today's events
    "https://calendar.fiu.edu/week",  # This week's events
    "https://calendar.fiu.edu/month",  # This month's events
    "https://calendar.fiu.edu/categories",  # Event categories
]

# Add URLs for past events (last 12 months)
#Go as far back as 2024
current_date = datetime.now()
for i in range(1, 13):  # Past 12 months
    past_date = current_date - timedelta(days=30*i)
    month_str = past_date.strftime("%Y/%m")
    CALENDAR_SPECIAL_URLS.append(f"https://calendar.fiu.edu/calendar/{month_str}")

# Add URLs for future events (next 12 months)
#This goes as far as 2026
for i in range(1, 13):  # Next 12 months
    future_date = current_date + timedelta(days=30*i)
    month_str = future_date.strftime("%Y/%m")
    CALENDAR_SPECIAL_URLS.append(f"https://calendar.fiu.edu/calendar/{month_str}")

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

def save_markdown(content: str, metadata: dict, url: str, index: int = None):
    out_dir = Path("fiu_content") / "Calendar"
    out_dir.mkdir(parents=True, exist_ok=True)

    filepath = out_dir / create_markdown_filename(url, index)
    front = (
        f"---\n"
        f"url: {url}\n"
        f"site: Calendar\n"
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

async def extract_event_date_info(page):
    """Extract additional date information for event pages"""
    try:
        date_info = await page.evaluate("""() => {
            const dateElements = document.querySelectorAll('.event-date, .date-display-single, .date-display-range, .datetime');
            if (dateElements.length) {
                return Array.from(dateElements).map(el => el.textContent.trim()).join(', ');
            }
            return '';
        }""")
        return date_info
    except:
        return ""

async def crawl_calendar_with_date_focus():
    """Enhanced crawler for FIU Calendar with focus on past, present, and future events"""
    base = CALENDAR_CONFIG["base_url"]
    print(f"\n📅 Enhanced crawling of Calendar site @ {base}")
    print(f"🔍 Special focus on past, present, and future events")
    
    # Create output directory
    Path("fiu_content/Calendar").mkdir(parents=True, exist_ok=True)
    
    browser_cfg = BrowserConfig()
    # Deep crawl with higher page limit for calendar
    bfs = BFSDeepCrawlStrategy(max_depth=4, max_pages=500, include_external=False)
    md_gen = DefaultMarkdownGenerator(content_filter=PruningContentFilter(0.48,"fixed"))
    
    # Special configuration for calendar with JS wait time
    cfg = CrawlerRunConfig(
        deep_crawl_strategy=bfs,
        markdown_generator=md_gen,
        cache_mode=CacheMode.BYPASS,
        exclude_external_links=True,
        check_robots_txt=True,
        process_iframes=False,
        remove_overlay_elements=True,
        wait_until="networkidle",  # Wait longer for calendar events to load
        page_timeout=60000  # Extended timeout (60 seconds) to ensure content loads
    )
    
    # Custom JS to evaluate on each page to help extract event dates
    js_code = """() => {
        // Scroll down to load lazy-loaded content
        window.scrollTo(0, document.body.scrollHeight);
        
        // Return any date information we can find
        const dateInfo = {
            eventDates: Array.from(document.querySelectorAll('.date-display-single, .date-display-range, .datetime'))
                .map(el => el.textContent.trim()),
            hasEventListing: !!document.querySelector('.view-events, .view-content, .events-list')
        };
        return dateInfo;
    }"""
    
    async with AsyncWebCrawler(config=browser_cfg) as cr:
        # First crawl specific month/day/category URLs to ensure we get past/future events
        special_results = []
        for url in CALENDAR_SPECIAL_URLS:
            print(f"🌟 Crawling special calendar URL: {url}")
            result = await cr.arun(url, config=cfg)
            if result and len(result) > 0:
                special_results.extend(result)
            await asyncio.sleep(1)  # Small delay between special URLs
        
        # Strict Calendar domain filtering for regular crawl
        def strict_calendar_filter(url):
            try:
                parsed = urlparse(url)
                
                # Only allow calendar.fiu.edu domain
                calendar_domain = "calendar.fiu.edu"
                if parsed.netloc.lower() != calendar_domain:
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
                        return False
                
                # Special priority for event pages and date-based content
                event_patterns = ['/event/', '/day/', '/month/', '/week/', '/calendar/', '/categories/', '/department/']
                if any(pattern in url.lower() for pattern in event_patterns):
                    return True
                    
                # Permitted calendar paths
                allowed_paths = [
                    "/", "/events", "/calendar", "/categories", 
                    "/view", "/search", "/month", "/week", "/day",
                    "/department", "/college", "/upcoming"
                ]
                
                # Check if URL path starts with any allowed path or contains specific event indicators
                path_allowed = any(parsed.path.lower().startswith(path.lower()) for path in allowed_paths)
                if not path_allowed:
                    return False
                        
                return True
            except Exception:
                return False
                
        cr.link_filter = strict_calendar_filter
        
        # Now do a regular crawl to find more events
        print("\n🕸️ Performing regular crawl to find additional events")
        regular_results = await cr.arun(base, config=cfg)
        
        # Combine all results
        all_results = special_results + regular_results
        calendar_only_results = []
        for res in all_results:
            try:
                if urlparse(res.url).netloc.lower() == "calendar.fiu.edu":
                    calendar_only_results.append(res)
            except:
                continue
        
        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for res in calendar_only_results:
            if res.url not in seen_urls:
                seen_urls.add(res.url)
                unique_results.append(res)
        
        print(f"\n📊 Processing {len(unique_results)} Calendar pages...")
        for idx, res in enumerate(unique_results, start=1):
            u = res.url
            if res.success:
                try:
                    content = ""
                    if hasattr(res, "markdown"):
                        if isinstance(res.markdown, str):
                            content = res.markdown
                        elif hasattr(res.markdown, "fit_markdown"):
                            content = str(res.markdown.fit_markdown) if res.markdown.fit_markdown else ""
                        else:
                            content = str(res.markdown)
                    
                    # Add extracted date info if it's an event page
                    if '/event/' in u.lower():
                        # Try to extract event dates
                        try:
                            event_date = await extract_event_date_info(res.page)
                            if event_date:
                                content = f"**Event Date(s):** {event_date}\n\n{content}"
                        except:
                            pass
                    
                    metadata = getattr(res, "metadata", {})
                    save_markdown(content, metadata, u, index=idx)
                    print(f"✅ {u}")
                except Exception as e:
                    print(f"❌ Error processing {u}: {str(e)}")
            else:
                print(f"❌ {u} failed: {getattr(res,'error','?')}")
            
            # Add delay to avoid overloading the server
            await asyncio.sleep(1)

async def main():
    Path("fiu_content").mkdir(exist_ok=True)
    print("🗓️ Starting enhanced Calendar crawler - focusing on past, present, and future events")
    await crawl_calendar_with_date_focus()
    print("✅ Calendar crawling complete")

if __name__ == "__main__":
    asyncio.run(main()) 