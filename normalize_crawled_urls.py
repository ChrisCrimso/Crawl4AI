#!/usr/bin/env python3
"""
This script normalizes URLs in crawled content, fixing common issues like:
1. Duplicate 'index.html' segments
2. Double slashes in paths
3. Missing or unnecessary trailing slashes
4. Improper URL encoding/decoding
5. Query parameter normalization
"""

import os
import re
import glob
import json
from tqdm import tqdm
from datetime import datetime
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, unquote

# Directories to search
DIRECTORIES = ["crawl_errors", "fiu_content"]
OUTPUT_DIR = "normalized_urls"

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

def normalize_url(url):
    """Normalize a URL by fixing common issues."""
    if not url:
        return url, []
    
    original_url = url
    changes = []
    
    try:
        # Parse URL
        parsed_url = urlparse(url)
        
        # 1. Fix duplicate 'index.html' segments
        path = parsed_url.path
        segments = path.split('/')
        index_segments = [i for i, segment in enumerate(segments) if segment.lower() == 'index.html']
        
        if len(index_segments) > 1:
            for i in index_segments[:-1]:
                segments[i] = ''
            changes.append("Removed duplicate index.html")
        
        # 2. Remove double slashes
        new_segments = []
        for segment in segments:
            if segment or segment == '':  # Keep empty strings for joining
                new_segments.append(segment)
            
        # 3. Handle trailing slashes consistently
        if len(new_segments) > 0 and new_segments[-1].lower() == 'index.html':
            # Remove trailing index.html
            new_segments[-1] = ''
            changes.append("Removed trailing index.html")
        
        # 4. Decode URL-encoded characters where appropriate
        decoded_segments = [unquote(segment) for segment in new_segments]
        if decoded_segments != new_segments:
            changes.append("Decoded URL-encoded characters")
            new_segments = decoded_segments
        
        # Rebuild path without empty segments
        new_path = '/'.join([segment for segment in new_segments if segment != ''])
        if new_path and not new_path.startswith('/'):
            new_path = '/' + new_path
            
        # Add trailing slash to directory paths (not ending with file extension)
        if new_path and not new_path.endswith('/') and '.' not in new_path.split('/')[-1]:
            new_path += '/'
            changes.append("Added trailing slash to directory path")
        
        # 5. Normalize query parameters
        query = parsed_url.query
        if query:
            # Parse and sort query parameters
            params = parse_qs(query)
            # Sort parameters and values
            sorted_params = {}
            for key in sorted(params.keys()):
                sorted_params[key] = sorted(params[key])
            
            # Rebuild query string
            new_query = urlencode(sorted_params, doseq=True)
            if new_query != query:
                changes.append("Normalized query parameters")
                query = new_query
        
        # Rebuild URL
        normalized_url = urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            new_path,
            parsed_url.params,
            query,
            parsed_url.fragment
        ))
        
        # Check if URL was changed
        if normalized_url != original_url:
            return normalized_url, changes
        else:
            return original_url, []
            
    except Exception as e:
        print(f"Error normalizing URL {url}: {str(e)}")
        return url, [f"Error: {str(e)}"]

def update_file_with_normalized_url(file_path, old_url, new_url, changes, output_dir=OUTPUT_DIR):
    """Update a file with the normalized URL and save to the output directory."""
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
            
            # Add normalization info to metadata
            normalized_at = datetime.now().isoformat()
            normalization_info = f"normalized_at: {normalized_at}\nnormalization_changes: {', '.join(changes)}"
            
            # Add after frontmatter
            updated_content = updated_content.replace('---\n\n', f'---\n{normalization_info}\n\n', 1)
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
    """Main function to find and normalize URLs in crawled content."""
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Keep track of normalized files
    normalized_files = []
    
    # Process each directory
    for directory in DIRECTORIES:
        if not os.path.exists(directory):
            print(f"Directory {directory} does not exist, skipping.")
            continue
            
        print(f"Searching for URLs to normalize in {directory}...")
        
        # Find all markdown files
        md_files = glob.glob(f"{directory}/**/*.md", recursive=True)
        print(f"Found {len(md_files)} markdown files")
        
        # Check each file
        for file_path in tqdm(md_files):
            metadata, _ = extract_metadata_from_file(file_path)
            url = metadata.get('url', '')
            
            normalized_url, changes = normalize_url(url)
            
            if changes:  # URL was changed
                print(f"\nNormalized URL in {file_path}:")
                print(f"  Original: {url}")
                print(f"  Normalized: {normalized_url}")
                print(f"  Changes: {', '.join(changes)}")
                
                # Update the file with the normalized URL
                output_file = update_file_with_normalized_url(file_path, url, normalized_url, changes)
                
                if output_file:
                    normalized_files.append({
                        'file_path': file_path,
                        'original_url': url,
                        'normalized_url': normalized_url,
                        'changes': changes,
                        'output_file': output_file
                    })
    
    # Print summary
    print(f"\nNormalized URLs in {len(normalized_files)} files")
    print(f"Updated files are saved in the '{OUTPUT_DIR}' directory")
    
    # Create a report
    report_path = os.path.join(OUTPUT_DIR, 'normalization_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# URL Normalization Report\n\n")
        f.write(f"Normalized URLs in {len(normalized_files)} files.\n\n")
        
        # Group by change type
        change_types = {}
        for item in normalized_files:
            for change in item['changes']:
                change_types[change] = change_types.get(change, 0) + 1
        
        f.write("## Changes Made\n\n")
        for change, count in sorted(change_types.items(), key=lambda x: x[1], reverse=True):
            f.write(f"- **{change}**: {count} files\n")
        
        f.write("\n## Details\n\n")
        for item in normalized_files:
            f.write(f"### {os.path.basename(item['file_path'])}\n")
            f.write(f"- **Original File:** `{item['file_path']}`\n")
            f.write(f"- **Original URL:** {item['original_url']}\n")
            f.write(f"- **Normalized URL:** {item['normalized_url']}\n")
            f.write(f"- **Changes:** {', '.join(item['changes'])}\n")
            f.write(f"- **Updated File:** `{item['output_file']}`\n\n")
    
    # Save JSON data for potential programmatic analysis
    json_path = os.path.join(OUTPUT_DIR, 'normalization_data.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'normalization_date': datetime.now().isoformat(),
            'total_files_checked': sum(len(glob.glob(f"{directory}/**/*.md", recursive=True)) for directory in DIRECTORIES if os.path.exists(directory)),
            'files_normalized': len(normalized_files),
            'change_types': change_types,
            'normalized_files': normalized_files
        }, f, indent=2)
    
    print(f"Report written to {report_path}")
    print(f"JSON data saved to {json_path}")

if __name__ == "__main__":
    main() 