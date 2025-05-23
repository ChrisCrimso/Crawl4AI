#!/usr/bin/env python3
"""
This script identifies potential 404 or crawling issues in the markdown files
and moves them to a 404_issues folder for further investigation.
"""

import os
import glob
import shutil
import re
from tqdm import tqdm

# Directories
SRC_DIR = "fiu_content"
DEST_DIR = "404_issues"

# Error indicators in content
ERROR_PATTERNS = [
    r"404 Not Found",
    r"Page Not Found",
    r"Error 404",
    r"does not exist",
    r"Access Denied",
    r"Forbidden",
    r"Error 403",
    r"Error 500",
    r"Internal Server Error",
    r"Service Unavailable",
    r"Error 503",
    r"The requested URL was not found on this server",
    r"Page cannot be displayed",
    r"Connection refused",
    r"Gateway Timeout",
    r"Bad Gateway",
    r"No content available",
    r"JavaScript is required",
    r"Please enable JavaScript",
]

# Minimum content length (excluding frontmatter) to consider valid
# Files with less content than this might be empty or error pages
MIN_CONTENT_LENGTH = 500  # characters

def is_problem_file(file_path):
    """
    Check if a file appears to have crawling issues based on content or size.
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # Check file size
            if len(content) < 100:  # Very small files are suspicious
                return True, "File too small"
                
            # Extract content excluding frontmatter
            content_without_frontmatter = content
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    content_without_frontmatter = parts[2]
            
            # Check if content is too small
            if len(content_without_frontmatter.strip()) < MIN_CONTENT_LENGTH:
                return True, "Content too small"
                
            # Check for error patterns
            for pattern in ERROR_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    return True, f"Contains error pattern: {pattern}"
                    
            # Check for suspicious titles
            title_match = re.search(r'title:\s*(.*)', content)
            if title_match:
                title = title_match.group(1).lower()
                if any(err.lower() in title for err in ["404", "not found", "error", "forbidden"]):
                    return True, f"Suspicious title: {title_match.group(1)}"
                    
            return False, ""
    except Exception as e:
        return True, f"Error reading file: {str(e)}"

def main():
    """
    Main function to identify and move problematic files.
    """
    # Ensure destination directory exists
    os.makedirs(DEST_DIR, exist_ok=True)
    
    # Find all markdown files in source directory
    md_files = glob.glob(f"{SRC_DIR}/**/*.md", recursive=True)
    print(f"Found {len(md_files)} markdown files to check")
    
    # Keep track of moved files and reasons
    moved_files = []
    
    # Process each file
    for file_path in tqdm(md_files):
        is_problem, reason = is_problem_file(file_path)
        
        if is_problem:
            # Create relative path structure in destination
            rel_path = os.path.relpath(file_path, SRC_DIR)
            dest_path = os.path.join(DEST_DIR, rel_path)
            
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Copy file to destination
            shutil.copy2(file_path, dest_path)
            
            # Record file and reason
            moved_files.append((rel_path, reason))
    
    # Print summary
    print(f"\nMoved {len(moved_files)} problematic files to {DEST_DIR}/")
    
    # Write log file
    log_path = os.path.join(DEST_DIR, "issues_log.txt")
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(f"Total files checked: {len(md_files)}\n")
        f.write(f"Files with potential issues: {len(moved_files)}\n\n")
        f.write("=" * 80 + "\n\n")
        
        for file_path, reason in moved_files:
            f.write(f"{file_path}\n")
            f.write(f"Reason: {reason}\n\n")
    
    print(f"Detailed log written to {log_path}")

if __name__ == "__main__":
    main() 