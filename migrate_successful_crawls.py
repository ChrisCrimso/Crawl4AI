#!/usr/bin/env python3
"""
Script to migrate successfully recrawled content back to the main FIU_content directory.
This takes content that was successfully recrawled using the Playwright crawler and
moves it to the appropriate FIU_content subdirectory.

This version focuses on preserving raw text content only, with no HTML.
"""

import os
import json
import re
import glob
import shutil
import argparse
from pathlib import Path
from tqdm import tqdm
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Constants
COMPARISON_DIR = "comparison_results"
RECRAWLED_DIR = "recrawled_content"
FIU_CONTENT_DIR = "FIU_content"
MIGRATION_LOG = "migration_log.json"

def ensure_dir(directory):
    """Ensure a directory exists."""
    Path(directory).mkdir(parents=True, exist_ok=True)

def get_latest_comparison_report():
    """Get the most recent comparison report."""
    reports = glob.glob(os.path.join(COMPARISON_DIR, "*.json"))
    if not reports:
        return None
    return max(reports, key=os.path.getctime)

def determine_target_directory(url, metadata):
    """
    Determine the appropriate FIU_content subdirectory based on the URL and metadata.
    Returns a tuple of (main_dir, subdirectory)
    """
    url_lower = url.lower()
    parsed_url = urlparse(url)
    hostname = parsed_url.netloc.lower()
    
    # Check for fiusports.com (Athletics)
    if "fiusports.com" in hostname:
        return "Athletics", determine_athletics_subdir(url, parsed_url.path)
    
    # Check for calendar
    if "calendar.fiu.edu" in hostname or "events.fiu.edu" in hostname:
        return "CampusLabs", "calendar"
    
    # Check for catalog
    if "catalog.fiu.edu" in hostname:
        return "Catalog", ""
    
    # Check for MyMajor
    if "mymajor.fiu.edu" in hostname:
        return "MyMajor", ""
    
    # Check for SAS
    if "sas.fiu.edu" in hostname or "studyabroad.fiu.edu" in hostname:
        return "SAS", ""
    
    # Check for PDF files
    if url_lower.endswith('.pdf') or '/pdf/' in url_lower:
        return "pdf", ""
    
    # Default to MainSite
    return "MainSite", determine_mainsite_subdir(parsed_url.path)

def determine_athletics_subdir(url, path):
    """Determine subdirectory for Athletics content."""
    if "/sports/" in url:
        # Extract sport name
        match = re.search(r'/sports/([^/]+)', url)
        if match:
            return match.group(1)
    
    if "/news/" in url:
        return "news"
    
    if "/galleries/" in url:
        return "galleries"
    
    # Extract first level directory
    parts = path.strip('/').split('/')
    if parts:
        return parts[0]
    
    return ""

def determine_mainsite_subdir(path):
    """Determine subdirectory for MainSite content."""
    parts = path.strip('/').split('/')
    if parts and parts[0]:
        return parts[0]
    return ""

def create_target_filename(source_file, target_dir):
    """Create a unique filename for the target directory."""
    filename = os.path.basename(source_file)
    base, ext = os.path.splitext(filename)
    
    # Remove timestamp from base if present (typically added during recrawling)
    base = re.sub(r'_\d{14}$', '', base)
    
    # Ensure it has .md extension
    if not ext or ext.lower() != '.md':
        ext = '.md'
    
    new_filename = base + ext
    
    # Check for existing file and rename if needed
    counter = 1
    while os.path.exists(os.path.join(target_dir, new_filename)):
        new_filename = f"{base}_{counter}{ext}"
        counter += 1
    
    return new_filename

def extract_content_and_metadata(file_path):
    """Extract content and metadata from a markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        metadata = {}
        content_text = content
        
        # Check if there's frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                # Extract frontmatter
                frontmatter = parts[1].strip()
                for line in frontmatter.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()
                
                # Get content without frontmatter
                content_text = parts[2].strip()
        
        # Make sure any remaining HTML is removed
        if re.search(r'<[^>]+>', content_text):
            soup = BeautifulSoup(content_text, 'html.parser')
            content_text = soup.get_text(separator='\n')
            
            # Clean up text
            content_text = re.sub(r'\n\s*\n', '\n\n', content_text)
            content_text = re.sub(r'[ \t]+', ' ', content_text)
            
            # Remove empty lines
            lines = [line.strip() for line in content_text.split('\n')]
            lines = [line for line in lines if line]
            content_text = '\n'.join(lines)
            
        return metadata, content_text
    except Exception as e:
        print(f"Error reading {file_path}: {str(e)}")
        return {}, ""

def format_markdown_content(metadata, content_text):
    """Format content with metadata as a markdown file."""
    md_content = "---\n"
    
    # Add essential metadata
    for key, value in metadata.items():
        # Skip any HTML-related fields
        if key.lower() not in ['html', 'raw_html']:
            md_content += f"{key}: {value}\n"
    
    # Ensure content_type is set to raw_text
    if 'content_type' not in metadata:
        md_content += "content_type: raw_text\n"
    
    # Add migration timestamp if not present
    if 'migrated_at' not in metadata:
        from datetime import datetime
        md_content += f"migrated_at: {datetime.now().isoformat()}\n"
    
    md_content += "---\n\n"
    md_content += content_text
    
    return md_content

def migrate_file(source_file, url, metadata):
    """Migrate a file to the appropriate FIU_content directory."""
    if not os.path.exists(source_file):
        return False, f"Source file {source_file} does not exist"
    
    # Extract content and metadata from the source file
    file_metadata, content_text = extract_content_and_metadata(source_file)
    
    # Combine metadata from the file with provided metadata
    combined_metadata = {**file_metadata, **metadata}
    combined_metadata['url'] = url
    combined_metadata['content_type'] = 'raw_text'
    
    # Determine target directory
    main_dir, subdir = determine_target_directory(url, combined_metadata)
    target_base_dir = os.path.join(FIU_CONTENT_DIR, main_dir)
    
    if not os.path.exists(target_base_dir):
        return False, f"Target directory {target_base_dir} does not exist"
    
    # Create subdirectory if needed
    target_dir = target_base_dir
    if subdir:
        target_dir = os.path.join(target_base_dir, subdir)
        ensure_dir(target_dir)
    
    # Create target filename
    target_filename = create_target_filename(source_file, target_dir)
    target_file = os.path.join(target_dir, target_filename)
    
    # Format the markdown content
    md_content = format_markdown_content(combined_metadata, content_text)
    
    try:
        # Write to the target file
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # Copy any associated files (like screenshots)
        source_dir = os.path.dirname(source_file)
        screenshot_dir = os.path.join(source_dir, "screenshots")
        if os.path.exists(screenshot_dir):
            base_name = os.path.splitext(os.path.basename(source_file))[0]
            # Look for matching screenshot
            for screenshot in glob.glob(os.path.join(screenshot_dir, f"{base_name}*.*")):
                target_screenshot_dir = os.path.join(target_dir, "screenshots")
                ensure_dir(target_screenshot_dir)
                
                target_screenshot = os.path.join(
                    target_screenshot_dir, 
                    os.path.basename(screenshot)
                )
                shutil.copy2(screenshot, target_screenshot)
                
        return True, target_file
    except Exception as e:
        return False, str(e)

def process_comparison_report(report_path):
    """Process the comparison report to migrate successfully recrawled files."""
    if not os.path.exists(report_path):
        print(f"Report file {report_path} not found.")
        return []
        
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        successful = [item for item in data["comparisons"] if item["crawl_success"]]
        print(f"Found {len(successful)} successfully recrawled files to migrate.")
        
        results = []
        
        for item in tqdm(successful, desc="Migrating files"):
            url = item["url"]
            recrawled_file = item["recrawled_file"]
            
            # Set up the metadata to include with the migration
            metadata = {
                "title": item["recrawled_title"],
                "original_file": item["original_file"],
                "recrawled_file": recrawled_file,
                "recrawl_improvement": f"{item['improvement_percentage']:.2f}%",
                "content_type": "raw_text"
            }
            
            # Add word counts if available
            if "original_words" in item and "recrawled_words" in item:
                metadata["original_word_count"] = str(item["original_words"])
                metadata["recrawled_word_count"] = str(item["recrawled_words"])
            
            success, message = migrate_file(recrawled_file, url, metadata)
            results.append({
                "url": url,
                "source_file": recrawled_file,
                "success": success,
                "message": message if not success else f"Migrated to {message}",
                "content_type": "raw_text"
            })
            
        # Write migration log
        log_file = os.path.join(COMPARISON_DIR, MIGRATION_LOG)
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({
                "migration_results": results,
                "total": len(results),
                "successful": sum(1 for r in results if r["success"]),
                "failed": sum(1 for r in results if not r["success"]),
                "content_type": "raw_text" 
            }, f, indent=2)
            
        # Print summary
        successful_count = sum(1 for r in results if r["success"])
        print(f"\nMigration complete: {successful_count} of {len(results)} files successfully migrated.")
        print(f"Migration log saved to {log_file}")
        
        return results
    except Exception as e:
        print(f"Error processing report: {str(e)}")
        return []

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Migrate successfully recrawled RAW TEXT content to FIU_content directory.'
    )
    parser.add_argument('--report', type=str, default=None,
                        help='Path to the comparison report (default: latest)')
    args = parser.parse_args()
    
    # Get report file
    report_file = args.report
    if not report_file:
        report_file = get_latest_comparison_report()
        
    if not report_file:
        print("No comparison report found. Please run the crawler and comparison tool first.")
        return
        
    print(f"Using comparison report: {report_file}")
    
    # Process the report
    process_comparison_report(report_file)
    
if __name__ == "__main__":
    main() 