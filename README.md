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

## FIU Knowledge Base - Question Answering System

We've developed two search systems for the FIU knowledge base:

### 1. Simple Search System (No API Key Required)

This system uses basic keyword matching to find relevant documents:

```
# Command line usage:
# Build the search index
python fiu_simple_search.py --build

# Search for something
python fiu_simple_search.py --query "computer science major"

# Or use the Streamlit interface
streamlit run fiu_simple_search.py
```

### 2. Advanced RAG System (Requires OpenAI API Key)

We've also developed a simple Retrieval-Augmented Generation (RAG) system that can answer questions about FIU based on the crawled content.

### Setup

1. Install the required packages:
   ```
   pip install -r requirements_rag.txt
   ```

2. Create a `.env` file with your OpenAI API key:
   ```
   # Copy the sample env file
   copy sample.env .env
   # Then edit the .env file to add your OpenAI API key
   ```

### Usage

Run the Streamlit application for a web interface:
```
streamlit run fiu_rag.py
```

Or use the command-line interface:
```
# Build the vector store (only needed once)
python fiu_qa_cli.py --build

# Ask a question directly
python fiu_qa_cli.py --question "What events are happening at FIU next month?"

# Or use interactive mode
python fiu_qa_cli.py
```

The first time you run it, you'll need to build the vector store by clicking the "Build Vector Store" button in the Streamlit app or using the `--build` flag in the CLI.

Once built, you can ask questions about FIU, and the system will retrieve relevant information from the crawled content and provide answers.

See `rag_system_guide.md` for more details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 