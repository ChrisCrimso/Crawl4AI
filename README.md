# Crawl4AI - FIU Website Crawler

A specialized web crawler for extracting content from various FIU (Florida International University) websites, with a particular focus on handling JavaScript-heavy single-page applications (SPAs) like MyMajor.

## Features

- Multi-site crawling with domain-specific strategies
- Support for traditional websites and JavaScript SPAs
- Intelligent content extraction and markdown generation
- Configurable crawl depth and filtering
- Specialized handling for MyMajor website using Playwright
- Fallback mechanisms for when dynamic content can't be accessed

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Crawl4AI.git
cd Crawl4AI
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install chromium
```

## Usage

### Crawling FIU Websites

To crawl multiple FIU websites:

```bash
python sum.py
```

### Crawling the MyMajor Website

For specialized crawling of the MyMajor SPA website:

```bash
python mymajor_crawler.py
```

This script uses Playwright to render JavaScript and extract content from the MyMajor SPA. It can:
- Crawl known program pages directly
- Discover new program pages by navigating the site
- Generate structured markdown content for each program
- Fall back to known data when dynamic extraction fails

## File Structure

- `sum.py`: Main crawler for multiple FIU sites
- `mymajor_crawler.py`: Specialized crawler for the MyMajor SPA
- `requirements.txt`: Python dependencies
- `fiu_sites.py`: Configuration for FIU websites
- `fiu_content/`: Directory containing extracted website content

## Handling SPAs

The project demonstrates two approaches to handling Single Page Applications:

1. **Traditional crawler + manual data**: Used in `sum.py`, combining basic HTML crawling with manually curated data
2. **Headless browser + DOM analysis**: Used in `mymajor_crawler.py`, rendering JavaScript and extracting content from the live DOM

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 