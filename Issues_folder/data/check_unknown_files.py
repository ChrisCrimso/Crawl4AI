#!/usr/bin/env python3
"""
Examine a sample of the Unknown files to better understand their format and content.
"""

import os
import re
import glob
import random
from collections import Counter

def check_directory_structure():
    """
    Check the directory structure of the 404_issues directory.
    """
    print("Checking 404_issues directory structure...")
    
    # List all directories in 404_issues
    dirs = [d for d in os.listdir("404_issues") if os.path.isdir(os.path.join("404_issues", d))]
    
    print(f"Found {len(dirs)} directories in 404_issues:")
    for d in dirs:
        file_count = len(glob.glob(os.path.join("404_issues", d, "**", "*.md"), recursive=True))
        print(f"  - {d}: {file_count} files")
    
    # If Unknown directory doesn't exist, check if the files are directly in 404_issues
    unknown_dir = os.path.join("404_issues", "Unknown")
    if not os.path.exists(unknown_dir):
        direct_files = glob.glob(os.path.join("404_issues", "*.md"))
        print(f"Files directly in 404_issues: {len(direct_files)}")

def find_unknown_files():
    """
    Find Unknown files in the 404_issues directory.
    """
    print("\nLooking for Unknown files...")
    
    # First check if Unknown directory exists
    unknown_dir = os.path.join("404_issues", "Unknown")
    if os.path.exists(unknown_dir):
        unknown_files = glob.glob(os.path.join(unknown_dir, "**", "*.md"), recursive=True)
        print(f"Found {len(unknown_files)} files in the Unknown directory")
        return unknown_files
    
    # If not, check for files directly in 404_issues that don't belong to a specific directory
    all_files = glob.glob(os.path.join("404_issues", "*.md"))
    print(f"Found {len(all_files)} files directly in 404_issues")
    return all_files

def analyze_sample_files(files, sample_size=10):
    """
    Analyze a sample of files to understand their format and content.
    """
    if not files:
        print("No files to analyze.")
        return
    
    print(f"\nAnalyzing a sample of {sample_size} files...")
    
    # Choose a random sample
    sample = random.sample(files, min(sample_size, len(files)))
    
    # Statistics
    has_url = 0
    has_title = 0
    has_frontmatter = 0
    content_sizes = []
    domains = Counter()
    
    for i, file_path in enumerate(sample):
        print(f"\nFile {i+1}: {os.path.basename(file_path)}")
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Check if it has frontmatter
            has_front = content.startswith('---')
            has_frontmatter += 1 if has_front else 0
            print(f"  Has frontmatter: {has_front}")
            
            # Extract URL if present
            url_match = re.search(r'url:\s*(http[s]?://[^\s\n]+)', content)
            if url_match:
                has_url += 1
                url = url_match.group(1).strip()
                print(f"  URL: {url}")
                
                # Extract domain
                domain_match = re.search(r'https?://([^/]+)', url)
                if domain_match:
                    domain = domain_match.group(1)
                    domains[domain] += 1
                    print(f"  Domain: {domain}")
            else:
                print("  No URL found")
            
            # Extract title if present
            title_match = re.search(r'title:\s*(.+?)[\n\r]', content)
            if title_match:
                has_title += 1
                title = title_match.group(1).strip()
                print(f"  Title: {title}")
            else:
                print("  No title found")
            
            # Get content size
            content_size = len(content)
            content_sizes.append(content_size)
            print(f"  Content size: {content_size} bytes")
            
            # Show a snippet of content
            content_snippet = content[:200] + "..." if len(content) > 200 else content
            print(f"  Content snippet: {content_snippet}")
            
        except Exception as e:
            print(f"  Error analyzing file: {str(e)}")
    
    # Print summary statistics
    print("\nSummary:")
    print(f"  Files with frontmatter: {has_frontmatter}/{sample_size}")
    print(f"  Files with URL: {has_url}/{sample_size}")
    print(f"  Files with title: {has_title}/{sample_size}")
    if content_sizes:
        avg_size = sum(content_sizes) / len(content_sizes)
        print(f"  Average content size: {avg_size:.2f} bytes")
    
    print("\nDomain distribution:")
    for domain, count in domains.most_common():
        print(f"  {domain}: {count}")

def main():
    """Main function."""
    check_directory_structure()
    unknown_files = find_unknown_files()
    
    if unknown_files:
        analyze_sample_files(unknown_files, sample_size=10)
    else:
        print("No unknown files found to analyze.")

if __name__ == "__main__":
    main() 