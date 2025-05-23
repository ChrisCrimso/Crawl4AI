#!/usr/bin/env python3
"""
This script identifies and fixes URLs with duplicate 'index.html' segments in crawled content.
It searches through both the crawl_errors and fiu_content directories for problematic URLs.
"""

import os
import re
import glob
from tqdm import tqdm
from urllib.parse import urlparse, urlunparse

# Directories to search
DIRECTORIES = ["crawl_errors", "fiu_content"]
FIXED_DIR = "fixed_urls"

def extract_metadata_from_file(file_path):
    """Extract URL and other metadata from a markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Extract metadata
        metadata = {}
        if content.startswith('---'):
            frontmatter_match = re.search(r'---(.*?)---', content, re.DOTALL)
            if frontmatter_match:
                frontmatter = frontmatter_match.group(1).strip()
                
                # Extract key-value pairs
                for line in frontmatter.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()
        
        return metadata, content
    except Exception as e:
        print(f"Error extracting metadata from {file_path}: {str(e)}")
        return {}, ""

def has_duplicate_index_html(url):
    """Check if a URL has duplicate 'index.html' segments."""
    if not url:
        return False
        
    # Split the path into segments
    parsed_url = urlparse(url)
    path = parsed_url.path
    
    # Count occurrences of 'index.html'
    segments = path.split('/')
    index_html_count = sum(1 for segment in segments if segment.lower() == 'index.html')
    
    return index_html_count > 1

def fix_duplicate_index_html(url):
    """Fix a URL with duplicate 'index.html' segments by keeping only the last one."""
    if not url:
        return url
        
    parsed_url = urlparse(url)
    path = parsed_url.path
    
    # Split into segments
    segments = path.split('/')
    
    # Find all index.html segments (case insensitive)
    index_segments = [i for i, segment in enumerate(segments) if segment.lower() == 'index.html']
    
    # Keep only the last index.html
    if len(index_segments) > 1:
        for i in index_segments[:-1]:
            segments[i] = ''
    
    # Rebuild path without empty segments
    new_path = '/'.join([segment for segment in segments if segment])
    if new_path and not new_path.startswith('/'):
        new_path = '/' + new_path
    
    # Rebuild URL
    new_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        new_path,
        parsed_url.params,
        parsed_url.query,
        parsed_url.fragment
    ))
    
    return new_url

def update_file_with_fixed_url(file_path, old_url, new_url, output_dir=FIXED_DIR):
    """Update a file with the fixed URL and save to the output directory."""
    try:
        metadata, content = extract_metadata_from_file(file_path)
        
        # Update the URL in the content
        if content.startswith('---'):
            # Replace in frontmatter
            updated_content = re.sub(
                r'(url:\s*)' + re.escape(old_url),
                r'\1' + new_url,
                content
            )
        else:
            # If no frontmatter, just replace all occurrences
            updated_content = content.replace(old_url, new_url)
        
        # Create output directory structure
        rel_path = os.path.relpath(file_path, os.path.dirname(os.path.dirname(file_path)))
        output_file = os.path.join(output_dir, rel_path)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Write updated content
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
            
        return output_file
    except Exception as e:
        print(f"Error updating file {file_path}: {str(e)}")
        return None

def main():
    """Main function to find and fix URLs with duplicate index.html segments."""
    # Create output directory
    os.makedirs(FIXED_DIR, exist_ok=True)
    
    # Keep track of fixed files
    fixed_files = []
    
    # Process each directory
    for directory in DIRECTORIES:
        if not os.path.exists(directory):
            print(f"Directory {directory} does not exist, skipping.")
            continue
            
        print(f"Searching for problematic URLs in {directory}...")
        
        # Find all markdown files
        md_files = glob.glob(f"{directory}/**/*.md", recursive=True)
        print(f"Found {len(md_files)} markdown files")
        
        # Check each file
        for file_path in tqdm(md_files):
            metadata, _ = extract_metadata_from_file(file_path)
            url = metadata.get('url', '')
            
            if has_duplicate_index_html(url):
                new_url = fix_duplicate_index_html(url)
                
                print(f"\nFound problematic URL in {file_path}:")
                print(f"  Original: {url}")
                print(f"  Fixed:    {new_url}")
                
                # Update the file with the fixed URL
                output_file = update_file_with_fixed_url(file_path, url, new_url)
                
                if output_file:
                    fixed_files.append({
                        'file_path': file_path,
                        'original_url': url,
                        'fixed_url': new_url,
                        'output_file': output_file
                    })
    
    # Print summary
    print(f"\nFixed {len(fixed_files)} files with duplicate 'index.html' segments")
    print(f"Updated files are saved in the '{FIXED_DIR}' directory")
    
    # Create a report
    report_path = os.path.join(FIXED_DIR, 'fixed_urls_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Fixed URLs Report\n\n")
        f.write(f"Found and fixed {len(fixed_files)} files with duplicate 'index.html' segments.\n\n")
        
        f.write("## Details\n\n")
        for item in fixed_files:
            f.write(f"### {os.path.basename(item['file_path'])}\n")
            f.write(f"- **Original File:** `{item['file_path']}`\n")
            f.write(f"- **Original URL:** {item['original_url']}\n")
            f.write(f"- **Fixed URL:** {item['fixed_url']}\n")
            f.write(f"- **Updated File:** `{item['output_file']}`\n\n")
    
    print(f"Report written to {report_path}")

if __name__ == "__main__":
    main() 