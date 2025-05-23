# URL Normalization for Crawled Content

This directory contains tools for identifying and fixing common URL issues in crawled content from the FIU website.

## Overview

When crawling websites, various URL-related issues can occur:

1. **Duplicate path segments** (like multiple `index.html` in a path)
2. **Malformed paths** with double slashes or encoding issues
3. **Inconsistent trailing slashes** in directory paths
4. **URL-encoded characters** that should be decoded
5. **Non-normalized query parameters**

These issues can lead to duplicate content, broken links, and reduced search effectiveness.

## Tools

### 1. URL Issue Identification (`identify_crawl_errors.py`)

First, we identify files with crawling issues using the `identify_crawl_errors.py` script. This script:

- Scans the `fiu_content` directory for markdown files
- Identifies files with potential crawling issues (404s, empty content, etc.)
- Moves these files to a `crawl_errors` directory for further processing
- Creates detailed documentation explaining each issue

### 2. Fix Duplicate Index.html (`fix_duplicate_index_urls.py`)

This script specifically targets URLs with duplicate `index.html` segments:

```
Bad URL:  https://fiu.edu/solutions/index.html/products/index.html
Good URL: https://fiu.edu/solutions/products/index.html
```

The script:
- Searches both `crawl_errors` and `fiu_content` directories
- Identifies URLs with multiple `index.html` segments
- Keeps only the last instance, removing others
- Saves fixed files to the `fixed_urls` directory

### 3. Comprehensive URL Normalization (`normalize_crawled_urls.py`)

This is our most powerful tool, addressing multiple URL issues in one pass:

- **Duplicate Segments**: Removes duplicate path segments like `index.html`
- **Path Normalization**: Handles double slashes, trailing slashes, etc.
- **URL Decoding**: Properly decodes URL-encoded characters
- **Query Normalization**: Sorts and normalizes query parameters
- **Directory Consistency**: Adds trailing slashes to directory paths

The script saves normalized files to the `normalized_urls` directory and generates detailed reports on changes made.

## Usage

### Step 1: Identify Crawling Issues

```bash
python identify_crawl_errors.py
```

This creates the `crawl_errors` directory containing problematic files and a detailed report.

### Step 2: Normalize URLs

```bash
python normalize_crawled_urls.py
```

This checks both `crawl_errors` and `fiu_content` directories, normalizes URLs, and saves updated files to `normalized_urls` with detailed reports.

## Outputs

Each script produces:

1. **Fixed Content**: Copies of the original files with corrected URLs
2. **Markdown Report**: Detailed summary of changes made
3. **JSON Data**: Structured data for programmatic analysis

## When to Use

- Use these tools when preparing your crawled content for integration into knowledge bases
- Run them periodically to clean up URLs in your content repository
- Apply URL normalization before running analytics to ensure accurate data

## Benefits

- **Improved Consistency**: All URLs follow the same patterns and conventions
- **Reduced Duplication**: Eliminates duplicate content due to URL variations
- **Better Navigation**: Properly structured URLs improve navigation and linking
- **Enhanced Search**: Normalized URLs make content more findable

## Requirements

- Python 3.6+
- Required packages: `tqdm`, `beautifulsoup4` 