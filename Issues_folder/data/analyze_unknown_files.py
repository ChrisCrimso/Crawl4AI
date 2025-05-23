#!/usr/bin/env python3
"""
Analyze the files in the 'Unknown' category from the issues log
to find patterns in the file names and URLs.
"""

import os
import re
import glob
from collections import Counter

# Log file path
LOG_FILE = os.path.join("404_issues", "issues_log.txt")

def extract_unknown_files():
    """
    Extract file paths of Unknown directory files from the log.
    """
    if not os.path.exists(LOG_FILE):
        print(f"Error: Log file not found at {LOG_FILE}")
        return []
        
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        log_content = f.read()
    
    # Extract all file paths and reasons
    file_reason_pattern = re.compile(r"([\w\\]+\.md)\nReason: (.+?)\n\n", re.DOTALL)
    file_reason_matches = file_reason_pattern.findall(log_content)
    
    # Filter for Unknown directory
    unknown_files = []
    for file_path, reason in file_reason_matches:
        directory = file_path.split('\\')[0] if '\\' in file_path else "Unknown"
        if directory == "Unknown":
            unknown_files.append((file_path, reason))
    
    return unknown_files

def analyze_file_patterns(unknown_files):
    """
    Analyze patterns in the unknown files.
    """
    # Counter for file name patterns
    file_patterns = Counter()
    
    # Patterns to check
    patterns = [
        (r".*\.js\.md$", "JavaScript files"),
        (r".*\.css\.md$", "CSS files"),
        (r".*\.ico\.md$", "Icon files"),
        (r".*\.png\.md$", "PNG images"),
        (r".*\.jpg\.md$", "JPG images"),
        (r".*\.jpeg\.md$", "JPEG images"),
        (r".*\.gif\.md$", "GIF images"),
        (r".*\.svg\.md$", "SVG images"),
        (r".*\.pdf\.md$", "PDF files"),
        (r".*\.html\.md$", "HTML files"),
        (r".*\.aspx\.md$", "ASPX files"),
        (r".*\.php\.md$", "PHP files"),
        (r".*\.txt\.md$", "Text files"),
        (r".*\/calendar\/.*\.md$", "Calendar URLs"),
        (r".*\/api\/.*\.md$", "API URLs"),
        (r".*\/search\/.*\.md$", "Search URLs"),
        (r".*\/rss\/.*\.md$", "RSS feeds"),
        (r".*\/wp-content\/.*\.md$", "WordPress content"),
        (r".*\/wp-includes\/.*\.md$", "WordPress includes"),
        (r".*\/wp-admin\/.*\.md$", "WordPress admin"),
        (r".*\/login.*\.md$", "Login pages"),
        (r".*\/signup.*\.md$", "Signup pages"),
        (r".*\/register.*\.md$", "Registration pages"),
        (r".*\/feed.*\.md$", "Feed URLs"),
        (r".*\/tag\/.*\.md$", "Tag pages"),
        (r".*\/category\/.*\.md$", "Category pages"),
        (r".*\/author\/.*\.md$", "Author pages"),
        (r".*\/page\/\d+\.md$", "Pagination pages"),
        (r".*\/comments\/.*\.md$", "Comment pages"),
    ]
    
    # Check each unknown file against the patterns
    for file_path, _ in unknown_files:
        matched = False
        for pattern, label in patterns:
            if re.match(pattern, file_path, re.IGNORECASE):
                file_patterns[label] += 1
                matched = True
                break
        
        if not matched:
            file_patterns["Other/unclassified"] += 1
    
    return file_patterns

def analyze_actual_files():
    """
    Analyze the actual files in the 404_issues directory to get URL patterns.
    """
    url_patterns = Counter()
    domain_counts = Counter()
    
    # Look for files in the 404_issues directory
    unknown_files = glob.glob(os.path.join("404_issues", "Unknown", "*.md"))
    
    # Sample some files to extract URL patterns
    sample_count = min(100, len(unknown_files))
    for i, file_path in enumerate(unknown_files[:sample_count]):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Extract URL from frontmatter
                url_match = re.search(r'url:\s*(http[s]?://[^\s\n]+)', content)
                if url_match:
                    url = url_match.group(1).strip()
                    
                    # Extract domain
                    domain_match = re.search(r'https?://([^/]+)', url)
                    if domain_match:
                        domain = domain_match.group(1)
                        domain_counts[domain] += 1
                    
                    # Check URL patterns
                    if '/wp-' in url:
                        url_patterns['WordPress URLs'] += 1
                    elif '.php' in url:
                        url_patterns['PHP URLs'] += 1
                    elif '.aspx' in url:
                        url_patterns['ASPX URLs'] += 1
                    elif '/api/' in url:
                        url_patterns['API URLs'] += 1
                    elif '/feed' in url or '/rss' in url:
                        url_patterns['Feed URLs'] += 1
                    elif '/search' in url:
                        url_patterns['Search URLs'] += 1
                    elif '/calendar' in url:
                        url_patterns['Calendar URLs'] += 1
                    elif '/login' in url or '/signin' in url:
                        url_patterns['Login URLs'] += 1
                    elif re.search(r'\.(js|css|png|jpg|gif|ico|svg)$', url):
                        url_patterns['Static resource URLs'] += 1
                    else:
                        url_patterns['Other URLs'] += 1
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
    
    return url_patterns, domain_counts

def main():
    """Main function."""
    print("Analyzing unknown files from issues log...")
    unknown_files = extract_unknown_files()
    print(f"Found {len(unknown_files)} unknown files in the issues log")
    
    file_patterns = analyze_file_patterns(unknown_files)
    
    print("\nAnalyzing actual files in 404_issues directory...")
    url_patterns, domain_counts = analyze_actual_files()
    
    # Print and save results
    stats_file = os.path.join("404_issues", "unknown_stats.txt")
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("UNKNOWN FILES ANALYSIS\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Total unknown files: {len(unknown_files)}\n\n")
        
        f.write("-" * 40 + "\n")
        f.write("File name patterns:\n")
        f.write("-" * 40 + "\n")
        
        for pattern, count in sorted(file_patterns.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(unknown_files) * 100
            line = f"{pattern:<30} {count:>8} ({percentage:>6.2f}%)"
            f.write(line + "\n")
            print(line)
        
        f.write("\n" + "-" * 40 + "\n")
        f.write("URL patterns (from sampled files):\n")
        f.write("-" * 40 + "\n")
        
        total_url_patterns = sum(url_patterns.values())
        for pattern, count in sorted(url_patterns.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total_url_patterns * 100 if total_url_patterns else 0
            line = f"{pattern:<30} {count:>8} ({percentage:>6.2f}%)"
            f.write(line + "\n")
            print("\n" + line)
        
        f.write("\n" + "-" * 40 + "\n")
        f.write("Domain distribution (from sampled files):\n")
        f.write("-" * 40 + "\n")
        
        total_domains = sum(domain_counts.values())
        for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total_domains * 100 if total_domains else 0
            line = f"{domain:<30} {count:>8} ({percentage:>6.2f}%)"
            f.write(line + "\n")
            print(line)
    
    print(f"\nStatistics written to {stats_file}")

if __name__ == "__main__":
    main() 