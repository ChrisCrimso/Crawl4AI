#!/usr/bin/env python3
"""
Compare the content of the original problematic files with the new crawled versions
to evaluate the effectiveness of the improved crawler.
"""

import os
import re
import glob
import json
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

# Constants
RECRAWLED_DIR = "recrawled_content"
ISSUES_DIR = "404_issues"
OUTPUT_DIR = "comparison_results"

def ensure_dir(directory):
    """Ensure a directory exists."""
    Path(directory).mkdir(parents=True, exist_ok=True)

def extract_content(file_path):
    """Extract content from a markdown file, excluding frontmatter."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Remove frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2].strip()
            else:
                content = ""
                
        return content
    except Exception as e:
        print(f"Error reading {file_path}: {str(e)}")
        return ""

def extract_metadata(file_path):
    """Extract metadata from a markdown file's frontmatter."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        metadata = {}
        
        # Check if there's frontmatter
        if content.startswith('---'):
            frontmatter_match = re.search(r'---(.*?)---', content, re.DOTALL)
            if frontmatter_match:
                frontmatter = frontmatter_match.group(1).strip()
                
                # Extract key-value pairs
                for line in frontmatter.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()
                        
        return metadata
    except Exception as e:
        print(f"Error extracting metadata from {file_path}: {str(e)}")
        return {}

def clean_html_content(html_content):
    """Clean HTML content for comparison by removing tags and extra whitespace."""
    try:
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get text only
        text = soup.get_text()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    except Exception as e:
        print(f"Error cleaning HTML: {str(e)}")
        return html_content

def compare_file_content(original_file, recrawled_file):
    """Compare the content of the original and recrawled files."""
    original_content = extract_content(original_file)
    recrawled_content = extract_content(recrawled_file)
    
    original_metadata = extract_metadata(original_file)
    recrawled_metadata = extract_metadata(recrawled_file)
    
    # Clean HTML content
    original_text = clean_html_content(original_content)
    recrawled_text = clean_html_content(recrawled_content)
    
    # Calculate content length
    original_length = len(original_text)
    recrawled_length = len(recrawled_text)
    
    # Calculate improvement percentage
    if original_length > 0:
        improvement_percentage = ((recrawled_length - original_length) / original_length) * 100
    else:
        improvement_percentage = float('inf') if recrawled_length > 0 else 0
    
    # Get crawl success flag
    crawl_success = recrawled_metadata.get('crawl_success', 'False') == 'True'
    
    # Get screenshot path if available
    screenshot = recrawled_metadata.get('screenshot', None)
    
    return {
        "original_file": original_file,
        "recrawled_file": recrawled_file,
        "original_length": original_length,
        "recrawled_length": recrawled_length,
        "improvement_percentage": improvement_percentage,
        "original_title": original_metadata.get('title', 'Unknown'),
        "recrawled_title": recrawled_metadata.get('title', 'Unknown'),
        "url": recrawled_metadata.get('url', 'Unknown'),
        "crawl_success": crawl_success,
        "screenshot": screenshot,
        "error": recrawled_metadata.get('error', None)
    }

def find_original_file(recrawled_metadata):
    """Find the original file based on metadata in the recrawled file."""
    original_file = recrawled_metadata.get('original_file', None)
    if original_file and os.path.exists(original_file):
        return original_file
    
    # If original_file not found, try to find by URL
    url = recrawled_metadata.get('url', None)
    if url:
        # Search for files in the issues directory with this URL
        for file_path in glob.glob(f"{ISSUES_DIR}/**/*.md", recursive=True):
            metadata = extract_metadata(file_path)
            if metadata.get('url', '') == url:
                return file_path
                
    return None

def find_recrawled_files():
    """Find all recrawled files."""
    return glob.glob(f"{RECRAWLED_DIR}/**/*.md", recursive=True)

def generate_comparison_report(comparisons):
    """Generate a comparison report in HTML format."""
    # Ensure the output directory exists
    ensure_dir(OUTPUT_DIR)
    
    # Create a timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Create the HTML file
    html_file = os.path.join(OUTPUT_DIR, f"comparison_report_{timestamp}.html")
    
    # Calculate summary statistics
    total_files = len(comparisons)
    successful_crawls = sum(1 for c in comparisons if c["crawl_success"])
    avg_improvement = sum(c["improvement_percentage"] for c in comparisons if c["crawl_success"]) / successful_crawls if successful_crawls > 0 else 0
    
    # Create HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Crawler Comparison Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #333; }}
            .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .comparison {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 5px; }}
            .comparison.success {{ border-left: 5px solid #4CAF50; }}
            .comparison.failure {{ border-left: 5px solid #F44336; }}
            .stats {{ display: flex; gap: 20px; }}
            .stat {{ flex: 1; }}
            .improvement {{ font-weight: bold; }}
            .improvement.positive {{ color: #4CAF50; }}
            .improvement.negative {{ color: #F44336; }}
            .screenshot {{ max-width: 600px; border: 1px solid #ddd; margin-top: 10px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
            tr:hover {{ background-color: #f5f5f5; }}
        </style>
    </head>
    <body>
        <h1>Crawler Comparison Report</h1>
        <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        
        <div class="summary">
            <h2>Summary</h2>
            <p>Total files compared: {total_files}</p>
            <p>Successfully recrawled: {successful_crawls} ({(successful_crawls/total_files)*100:.2f}%)</p>
            <p>Average content improvement: {avg_improvement:.2f}%</p>
        </div>
        
        <h2>Successful Crawls</h2>
    """
    
    # Add successful comparisons
    successful = [c for c in comparisons if c["crawl_success"]]
    for comparison in sorted(successful, key=lambda x: x["improvement_percentage"], reverse=True):
        improvement_class = "positive" if comparison["improvement_percentage"] > 0 else "negative"
        
        html_content += f"""
        <div class="comparison success">
            <h3>URL: {comparison["url"]}</h3>
            <div class="stats">
                <div class="stat">
                    <strong>Original Content Length:</strong> {comparison["original_length"]} characters<br>
                    <strong>Recrawled Content Length:</strong> {comparison["recrawled_length"]} characters<br>
                    <span class="improvement {improvement_class}">
                        Improvement: {comparison["improvement_percentage"]:.2f}%
                    </span>
                </div>
                <div class="stat">
                    <strong>Original Title:</strong> {comparison["original_title"]}<br>
                    <strong>Recrawled Title:</strong> {comparison["recrawled_title"]}<br>
                </div>
            </div>
            <p>
                <strong>Original File:</strong> {comparison["original_file"]}<br>
                <strong>Recrawled File:</strong> {comparison["recrawled_file"]}
            </p>
        """
        
        # Add screenshot if available
        if comparison["screenshot"]:
            screenshot_path = os.path.join(RECRAWLED_DIR, comparison["screenshot"])
            if os.path.exists(screenshot_path):
                # Copy the screenshot to the output directory
                output_screenshot = os.path.join(OUTPUT_DIR, os.path.basename(screenshot_path))
                try:
                    with open(screenshot_path, 'rb') as src, open(output_screenshot, 'wb') as dst:
                        dst.write(src.read())
                    html_content += f"""
                    <div>
                        <strong>Screenshot:</strong><br>
                        <img src="{os.path.basename(output_screenshot)}" class="screenshot" alt="Screenshot">
                    </div>
                    """
                except Exception as e:
                    print(f"Error copying screenshot: {str(e)}")
        
        html_content += "</div>"
    
    # Add failed comparisons
    html_content += "<h2>Failed Crawls</h2>"
    
    failed = [c for c in comparisons if not c["crawl_success"]]
    for comparison in failed:
        html_content += f"""
        <div class="comparison failure">
            <h3>URL: {comparison["url"]}</h3>
            <p><strong>Error:</strong> {comparison["error"]}</p>
            <p>
                <strong>Original File:</strong> {comparison["original_file"]}<br>
                <strong>Recrawled File:</strong> {comparison["recrawled_file"]}
            </p>
        </div>
        """
    
    # Close HTML
    html_content += """
    </body>
    </html>
    """
    
    # Write the HTML file
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Also create a JSON file for programmatic access
    json_file = os.path.join(OUTPUT_DIR, f"comparison_report_{timestamp}.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            "summary": {
                "total_files": total_files,
                "successful_crawls": successful_crawls,
                "success_rate": (successful_crawls/total_files) if total_files > 0 else 0,
                "avg_improvement": avg_improvement
            },
            "comparisons": comparisons
        }, f, indent=2)
    
    return html_file, json_file

def main():
    """Main function."""
    print("Finding recrawled files...")
    recrawled_files = find_recrawled_files()
    
    if not recrawled_files:
        print("No recrawled files found. Run playwright_crawler.py first.")
        return
        
    print(f"Found {len(recrawled_files)} recrawled files.")
    
    # Process each recrawled file
    comparisons = []
    for recrawled_file in recrawled_files:
        # Get metadata from recrawled file
        recrawled_metadata = extract_metadata(recrawled_file)
        
        # Find the original file
        original_file = find_original_file(recrawled_metadata)
        
        if original_file:
            print(f"Comparing {os.path.basename(original_file)} with {os.path.basename(recrawled_file)}...")
            comparison = compare_file_content(original_file, recrawled_file)
            comparisons.append(comparison)
        else:
            print(f"Could not find original file for {recrawled_file}")
    
    if comparisons:
        # Generate comparison report
        html_file, json_file = generate_comparison_report(comparisons)
        print(f"Comparison report generated: {html_file}")
        print(f"JSON data: {json_file}")
    else:
        print("No comparisons could be made.")

if __name__ == "__main__":
    main() 