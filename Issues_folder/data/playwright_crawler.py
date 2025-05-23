#!/usr/bin/env python3
"""
Improved crawler using Playwright to handle JavaScript-heavy sites.
This script tests crawling problematic URLs from the 404_issues directory
to see if using a headless browser improves content extraction.
"""

import os
import re
import glob
import json
import time
import random
import argparse
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

# Constants
OUTPUT_DIR = "recrawled_content"
ISSUES_DIR = "404_issues"
SAMPLE_SIZE = 10  # Number of URLs to test from each directory

def ensure_dir(directory):
    """Ensure a directory exists."""
    Path(directory).mkdir(parents=True, exist_ok=True)

def extract_metadata_from_file(file_path):
    """Extract URL and other metadata from a markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Extract URL
        url_match = re.search(r'url:\s*(http[s]?://[^\s\n]+)', content)
        if not url_match:
            return None
            
        url = url_match.group(1).strip()
        
        # Extract title if present
        title = None
        title_match = re.search(r'title:\s*(.+?)[\n\r]', content)
        if title_match:
            title = title_match.group(1).strip()
            
        # Extract crawl date if present
        crawl_date = None
        date_match = re.search(r'crawled_at:\s*(.+?)[\n\r]', content)
        if date_match:
            crawl_date = date_match.group(1).strip()
            
        # Extract site if present
        site = None
        site_match = re.search(r'site:\s*(.+?)[\n\r]', content)
        if site_match:
            site = site_match.group(1).strip()
            
        return {
            "url": url,
            "title": title,
            "crawled_at": crawl_date,
            "site": site,
            "original_file": file_path
        }
    except Exception as e:
        print(f"Error extracting metadata from {file_path}: {str(e)}")
        return None

def get_sample_urls(directory, sample_size=SAMPLE_SIZE):
    """Get a sample of URLs from the specified directory in the issues folder."""
    dir_path = os.path.join(ISSUES_DIR, directory)
    if not os.path.exists(dir_path):
        print(f"Directory {dir_path} does not exist.")
        return []
        
    md_files = glob.glob(os.path.join(dir_path, "**", "*.md"), recursive=True)
    if not md_files:
        print(f"No markdown files found in {dir_path}.")
        return []
        
    # Select a random sample
    sample = random.sample(md_files, min(sample_size, len(md_files)))
    
    # Extract URLs from the files
    urls = []
    for file_path in sample:
        metadata = extract_metadata_from_file(file_path)
        if metadata and metadata["url"]:
            urls.append(metadata)
            
    return urls

def crawl_with_playwright(url, wait_time=5, wait_for_network_idle=True, timeout=30000):
    """
    Crawl a URL using Playwright with customizable options.
    
    Args:
        url: The URL to crawl
        wait_time: Additional time to wait after page load (seconds)
        wait_for_network_idle: Whether to wait for network to be idle
        timeout: Timeout for navigation in milliseconds
        
    Returns:
        dict: Result containing content, title, and other metadata
    """
    try:
        with sync_playwright() as p:
            # Launch browser (can also use firefox or webkit)
            browser = p.chromium.launch()
            
            # Create a new page
            page = browser.new_page()
            
            # Set user agent to avoid bot detection
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            # Navigate to the URL
            if wait_for_network_idle:
                page.goto(url, wait_until="networkidle", timeout=timeout)
            else:
                page.goto(url, timeout=timeout)
                
            # Wait additional time if specified
            if wait_time > 0:
                time.sleep(wait_time)
                
            # Get page content
            content = page.content()
            
            # Get page title
            title = page.title()
            
            # Take a screenshot
            screenshot = page.screenshot()
            
            # Close the browser
            browser.close()
            
            return {
                "success": True,
                "content": content,
                "title": title,
                "screenshot": screenshot
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def save_crawled_content(metadata, crawl_result, output_dir=OUTPUT_DIR):
    """Save the crawled content to a markdown file with metadata."""
    # Create a directory based on the site
    site = metadata.get("site", "Unknown")
    url_parsed = urlparse(metadata["url"])
    domain = url_parsed.netloc
    
    # Create output directory
    site_dir = os.path.join(output_dir, site)
    ensure_dir(site_dir)
    
    # Create a filename based on the URL
    path_parts = url_parsed.path.strip('/').split('/')
    if path_parts:
        filename = '_'.join([p for p in path_parts if p])
        if not filename:
            filename = domain
    else:
        filename = domain
        
    # Add a timestamp to ensure uniqueness
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{filename}_{timestamp}.md"
    
    # Save the screenshot if available
    screenshot_path = None
    if crawl_result.get("screenshot"):
        screenshots_dir = os.path.join(site_dir, "screenshots")
        ensure_dir(screenshots_dir)
        screenshot_path = os.path.join(screenshots_dir, f"{Path(filename).stem}.png")
        with open(screenshot_path, 'wb') as f:
            f.write(crawl_result["screenshot"])
    
    # Create markdown content with frontmatter
    md_content = "---\n"
    md_content += f"url: {metadata['url']}\n"
    md_content += f"site: {site}\n"
    md_content += f"original_crawled_at: {metadata.get('crawled_at', 'Unknown')}\n"
    md_content += f"recrawled_at: {datetime.now().isoformat()}\n"
    md_content += f"title: {crawl_result.get('title', 'Unknown')}\n"
    if screenshot_path:
        md_content += f"screenshot: {os.path.relpath(screenshot_path, output_dir)}\n"
    md_content += f"original_file: {os.path.relpath(metadata['original_file'], os.getcwd())}\n"
    md_content += f"crawl_success: {crawl_result.get('success', False)}\n"
    if not crawl_result.get('success', False):
        md_content += f"error: {crawl_result.get('error', 'Unknown error')}\n"
    md_content += "---\n\n"
    
    # Add the content
    if crawl_result.get('success', False):
        md_content += crawl_result.get('content', '')
    
    # Write to file
    output_path = os.path.join(site_dir, filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
        
    return output_path

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Crawl problematic URLs using Playwright.')
    parser.add_argument('--directory', type=str, default='Athletics',
                        help='Directory in 404_issues to sample URLs from')
    parser.add_argument('--sample', type=int, default=SAMPLE_SIZE,
                        help='Number of URLs to sample from the directory')
    parser.add_argument('--wait', type=float, default=5,
                        help='Additional time to wait after page load (seconds)')
    parser.add_argument('--timeout', type=int, default=30000,
                        help='Timeout for navigation in milliseconds')
    args = parser.parse_args()
    
    print(f"Getting sample URLs from {args.directory}...")
    urls = get_sample_urls(args.directory, sample_size=args.sample)
    
    if not urls:
        print(f"No URLs found in {args.directory}.")
        return
        
    print(f"Found {len(urls)} URLs to crawl.")
    
    # Ensure output directory exists
    ensure_dir(OUTPUT_DIR)
    
    # Log file to track results
    log_file = os.path.join(OUTPUT_DIR, f"crawl_log_{args.directory}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
    
    # Track successful and failed crawls
    results = {
        "successful": [],
        "failed": []
    }
    
    # Crawl each URL
    for metadata in tqdm(urls):
        url = metadata["url"]
        print(f"Crawling {url}...")
        
        crawl_result = crawl_with_playwright(
            url, 
            wait_time=args.wait, 
            timeout=args.timeout
        )
        
        # Save the content
        output_path = save_crawled_content(metadata, crawl_result)
        
        # Log the result
        result_entry = {
            "url": url,
            "success": crawl_result.get("success", False),
            "output_file": output_path,
            "original_file": metadata["original_file"],
            "title": crawl_result.get("title", "Unknown") if crawl_result.get("success", False) else None
        }
        
        if crawl_result.get("success", False):
            results["successful"].append(result_entry)
            print(f"Successfully crawled: {url}")
        else:
            result_entry["error"] = crawl_result.get("error", "Unknown error")
            results["failed"].append(result_entry)
            print(f"Failed to crawl: {url} - {crawl_result.get('error', 'Unknown error')}")
    
    # Write results to log file
    with open(log_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\nCrawl Summary:")
    print(f"Total URLs: {len(urls)}")
    print(f"Successfully crawled: {len(results['successful'])}")
    print(f"Failed to crawl: {len(results['failed'])}")
    print(f"Log file: {log_file}")
    print(f"Output directory: {OUTPUT_DIR}")

if __name__ == "__main__":
    main() 