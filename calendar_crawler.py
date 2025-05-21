#!/usr/bin/env python3
# calendar_crawler.py - Specialized crawler for FIU Calendar events (PRESENT & FUTURE ONLY)
# This script is designed to be run automatically on a schedule to keep dynamic event data updated

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

# Special URLs to ensure present/future events are captured
# Note: We're excluding past events as those will be manually crawled
CALENDAR_SPECIAL_URLS = [
    "https://calendar.fiu.edu/",  # Current events
    "https://calendar.fiu.edu/upcoming",  # Upcoming events
    "https://calendar.fiu.edu/day",  # Today's events
    "https://calendar.fiu.edu/week",  # This week's events
    "https://calendar.fiu.edu/month",  # This month's events
    "https://calendar.fiu.edu/categories",  # Event categories
]

# Add URLs for FUTURE events only (next 18 months - extending to capture more future events)
current_date = datetime.now()
for i in range(0, 18):  # Current month + next 17 months (1.5 years into future) 
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

def is_past_event(event_date_str: str) -> bool:
    """Determine if an event is in the past"""
    if not event_date_str:
        return False  # If we can't determine, default to treating as current/future
        
    try:
        # Handle various date formats commonly found on the calendar
        event_date_str = event_date_str.split(',')[0].strip()
        event_date_str = event_date_str.split('-')[0].strip()
        event_date_str = event_date_str.split('@')[0].strip()
        
        # Try to parse the date
        for fmt in ["%B %d %Y", "%b %d %Y", "%m/%d/%Y", "%Y-%m-%d"]:
            try:
                event_date = datetime.strptime(event_date_str, fmt)
                # Compare with current date
                return event_date.date() < datetime.now().date()
            except ValueError:
                continue
                
        return False  # If we can't parse the date, default to current/future
    except:
        return False

def save_markdown(content: str, metadata: dict, url: str, index: int = None):
    try:
        # Determine if this is a past event or present/future event
        event_date = ""
        is_past = False
        
        if "Event Date(s):" in content:
            try:
                event_date = content.split("Event Date(s):")[1].split("\n")[0].strip()
                is_past = is_past_event(event_date)
            except:
                pass
        
        # Save to appropriate folder based on timing
        if is_past:
            # Past events go to regular Calendar folder (static)
            out_dir = Path("fiu_content") / "Calendar"
        else:
            # Present/future events go to Calendar_Dynamic folder
            out_dir = Path("fiu_content") / "Calendar_Dynamic"
            
        out_dir.mkdir(parents=True, exist_ok=True)

        filepath = out_dir / create_markdown_filename(url, index)
        
        front = (
            f"---\n"
            f"url: {url}\n"
            f"site: Calendar\n"
            f"crawled_at: {metadata.get('crawled_at', datetime.now().isoformat())}\n"
            f"title: {metadata.get('title','No title')}\n"
            f"event_date: {event_date}\n"
            f"dynamic: {not is_past}\n"
            f"---\n\n"
        )
        
        # Only save files with actual content or add a placeholder
        if content and len(content.strip()) > 0:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(front)
                f.write(content or "")
            print(f"💾 Saved {'past' if is_past else 'future/current'} event: {filepath}")
        else:
            # Skip empty content
            print(f"⚠️ Skipping empty content for: {url}")
            
    except Exception as e:
        print(f"❌ Error saving markdown for {url}: {str(e)}")

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
    """Enhanced crawler for FIU Calendar with focus on present and future events"""
    base = CALENDAR_CONFIG["base_url"]
    print(f"\n📅 Enhanced crawling of Calendar site @ {base}")
    print(f"🔍 Special focus on present and future events (dynamic)")
    
    # Create output directories
    Path("fiu_content/Calendar").mkdir(parents=True, exist_ok=True)
    Path("fiu_content/Calendar_Dynamic").mkdir(parents=True, exist_ok=True)
    
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
        wait_until="networkidle"  # Wait longer for calendar events to load
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
    print("🗓️ FIU Calendar Crawler - Dynamic Events (PRESENT & FUTURE)")
    print("📅 Running at:", datetime.now().strftime("%Y-%m-%d %H:%M"))
    await crawl_calendar_with_date_focus()
    
    # Save URL log
    log_file = Path("fiu_content/Calendar_Dynamic") / f"url_log_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(log_file, 'w') as f:
        import json
        json.dump({
            "crawl_time": datetime.now().isoformat(),
            "log": "Present and future calendar events crawl"
        }, f, indent=2)
    
    print("✅ Calendar crawling complete")
    print(f"📝 URL log saved to {log_file}")
    print("ℹ️ Run this script regularly to keep future event data updated")

if __name__ == "__main__":
    asyncio.run(main()) 