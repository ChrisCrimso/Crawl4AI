#!/usr/bin/env python3
# mymajor_crawler.py

import asyncio
import os
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import re
from bs4 import BeautifulSoup
import httpx
from playwright.async_api import async_playwright
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from typing import Optional, Dict, Any

# Add the specific list of program URLs to crawl
PROGRAM_URLS = [
    "https://mymajor.fiu.edu/individual/411PHYBSENGR",
    "https://mymajor.fiu.edu/individual/215GEOSCBS",
    "https://mymajor.fiu.edu/individual/415PHYBA",
    "https://mymajor.fiu.edu/individual/493SPEDBSFOO",
    "https://mymajor.fiu.edu/individual/216GEOSCATM",
    "https://mymajor.fiu.edu/individual/435PSYCBA",
    "https://mymajor.fiu.edu/individual/195ENVSTBS",
    "https://mymajor.fiu.edu/individual/157ECHDEDBS",
    "https://mymajor.fiu.edu/individual/160EARTHBA",
    "https://mymajor.fiu.edu/individual/339MATHSC2CH",
    "https://mymajor.fiu.edu/individual/410PHYBS",
    "https://mymajor.fiu.edu/individual/310LIBSTBALW",
    "https://mymajor.fiu.edu/individual/175ELEMEDESL",
    "https://mymajor.fiu.edu/individual/058BIOLBAHLT",
    "https://mymajor.fiu.edu/individual/331MRKETONL",
    "https://mymajor.fiu.edu/individual/200FINBBA",
    "https://mymajor.fiu.edu/individual/030ARTBFAGRA",
    "https://mymajor.fiu.edu/individual/50THEAMUSICA",
    "https://mymajor.fiu.edu/individual/510THEAPERF",
    "https://mymajor.fiu.edu/individual/101COMARTART",
    "https://mymajor.fiu.edu/individual/104COMARTORL",
    "https://mymajor.fiu.edu/individual/130COMPSCBA",
    "https://mymajor.fiu.edu/individual/126SOFTDESBS",
    "https://mymajor.fiu.edu/individual/261ITBSONL",
    "https://mymajor.fiu.edu/individual/227GBLSTD",
    "https://mymajor.fiu.edu/individual/236HISTBAED",
    "https://mymajor.fiu.edu/individual/228GBLSTDSOC",
    "https://mymajor.fiu.edu/individual/290INTLRLBA",
    "https://mymajor.fiu.edu/individual/251HOSPHTLDO",
    "https://mymajor.fiu.edu/individual/251HOSPHTLDM",
    "https://mymajor.fiu.edu/individual/251HOSPRESCO",
    "https://mymajor.fiu.edu/individual/386NURSACCEL",
    "https://mymajor.fiu.edu/individual/416PHYBABIOP",
    "https://mymajor.fiu.edu/individual/156ECHDDEVBS",
    "https://mymajor.fiu.edu/individual/278INTSTUDBA",
    "https://mymajor.fiu.edu/individual/416PHYBABUS",
    "https://mymajor.fiu.edu/individual/450RECMGTBSO",
    "https://mymajor.fiu.edu/individual/085CHEMENV",
    "https://mymajor.fiu.edu/individual/155ECHDDEVBS",
    "https://mymajor.fiu.edu/individual/198GLOSOC",
    "https://mymajor.fiu.edu/individual/057BIOLBAONL",
    "https://mymajor.fiu.edu/individual/330MRKETBBA",
    "https://mymajor.fiu.edu/individual/315MGTBBA",
    "https://mymajor.fiu.edu/individual/313LOGSCM",
    "https://mymajor.fiu.edu/individual/034ARTEDBS",
    "https://mymajor.fiu.edu/individual/147DIARTGRAP",
    "https://mymajor.fiu.edu/individual/501THEATERBA",
    "https://mymajor.fiu.edu/individual/148DIGTVMMPR",
    "https://mymajor.fiu.edu/individual/103COMARTDES",
    "https://mymajor.fiu.edu/individual/042ASNSTBAAS",
    "https://mymajor.fiu.edu/individual/166ECONBAONL",
    "https://mymajor.fiu.edu/individual/137CRMSCIBS",
    "https://mymajor.fiu.edu/individual/476ANSOANTON",
    "https://mymajor.fiu.edu/individual/205FRENFSBA",
    "https://mymajor.fiu.edu/individual/440PABPA",
    "https://mymajor.fiu.edu/individual/307LACC",
    "https://mymajor.fiu.edu/individual/235HISTBAONL",
    "https://mymajor.fiu.edu/individual/251HOSPTORM",
    "https://mymajor.fiu.edu/individual/229GLBSTORON",
    "https://mymajor.fiu.edu/individual/463RECTHERBS",
    "https://mymajor.fiu.edu/individual/053BIOCHEMBS",
    "https://mymajor.fiu.edu/individual/310LIBSTBALO",
    "https://mymajor.fiu.edu/individual/370NAPSCIBA",
    "https://mymajor.fiu.edu/individual/390PHILBAGEN",
    "https://mymajor.fiu.edu/individual/491SPEDBSREA",
    "https://mymajor.fiu.edu/individual/520WMNSTBA",
    "https://mymajor.fiu.edu/individual/056BIOLBSED",
    "https://mymajor.fiu.edu/individual/080CHEMEDU",
    "https://mymajor.fiu.edu/individual/337MATHSC2BI",
    "https://mymajor.fiu.edu/individual/216GEOSCGINF",
    "https://mymajor.fiu.edu/individual/058BIOLBAALL",
    "https://mymajor.fiu.edu/individual/058BIOLBASCI",
    "https://mymajor.fiu.edu/individual/445REBBA",
    "https://mymajor.fiu.edu/individual/254HRMGTONL",
    "https://mymajor.fiu.edu/individual/020ARCXL",
    "https://mymajor.fiu.edu/individual/359BMORP",
    "https://mymajor.fiu.edu/individual/030ARTBFAANI",
    "https://mymajor.fiu.edu/individual/148DIGINTMED",
    "https://mymajor.fiu.edu/individual/360BMMT",
    "https://mymajor.fiu.edu/individual/349MECHEGBS",
    "https://mymajor.fiu.edu/individual/292INTLRLHON",
    "https://mymajor.fiu.edu/individual/168ECONBAPUP",
    "https://mymajor.fiu.edu/individual/167ECONBABUS",
    "https://mymajor.fiu.edu/individual/251HOSPRESCL",
    "https://mymajor.fiu.edu/individual/250HOSPBS",
    "https://mymajor.fiu.edu/individual/250HOSPBSONL",
    "https://mymajor.fiu.edu/individual/375NURSGBSN",
    "https://mymajor.fiu.edu/individual/496SUSENVBA",
    "https://mymajor.fiu.edu/individual/198PHYSE",
    "https://mymajor.fiu.edu/individual/400PESFBS",
    "https://mymajor.fiu.edu/individual/464REHTHERON",
    "https://mymajor.fiu.edu/individual/310LIBSTBAHL",
    "https://mymajor.fiu.edu/individual/411PHYBSPHED",
    "https://mymajor.fiu.edu/individual/496SUSENVBAO",
    "https://mymajor.fiu.edu/individual/336MATHSC2AP",
    "https://mymajor.fiu.edu/individual/343MATHSC2PH",
    "https://mymajor.fiu.edu/individual/182ENGLBALIN",
    "https://mymajor.fiu.edu/individual/010ACCTBACC",
    "https://mymajor.fiu.edu/individual/147DIART",
    "https://mymajor.fiu.edu/individual/365MUEDUEBM",
    "https://mymajor.fiu.edu/individual/362BMVP",
    "https://mymajor.fiu.edu/individual/034ARTEDBSCA",
    "https://mymajor.fiu.edu/individual/262ITSBS",
    "https://mymajor.fiu.edu/individual/143CYBERBS",
    "https://mymajor.fiu.edu/individual/485SPANBA",
    "https://mymajor.fiu.edu/individual/308LACCONL",
    "https://mymajor.fiu.edu/individual/043ASNSTBAAW",
    "https://mymajor.fiu.edu/individual/425POLSCBA",
    "https://mymajor.fiu.edu/individual/425POLSCBAON",
    "https://mymajor.fiu.edu/individual/466RELSTBAON",
    "https://mymajor.fiu.edu/individual/045ASNSTBSEA",
    "https://mymajor.fiu.edu/individual/441PABPAONL",
    "https://mymajor.fiu.edu/individual/210GEOGBA",
    "https://mymajor.fiu.edu/individual/228GBLSTDGEO",
    "https://mymajor.fiu.edu/individual/251HOSPTIAN",
    "https://mymajor.fiu.edu/individual/391PHILBAPRO",
    "https://mymajor.fiu.edu/individual/416PHYBAENTR",
    "https://mymajor.fiu.edu/individual/416PHYEDUBA",
    "https://mymajor.fiu.edu/individual/198ADMGMT",
    "https://mymajor.fiu.edu/individual/438PSYCBAAPO",
    "https://mymajor.fiu.edu/individual/345MATHBA",
    "https://mymajor.fiu.edu/individual/057BIOLBA",
    "https://mymajor.fiu.edu/individual/182ENGLBALIT",
    "https://mymajor.fiu.edu/individual/075CHEMBIO",
    "https://mymajor.fiu.edu/individual/316MGTBBAONL",
    "https://mymajor.fiu.edu/individual/287INTBSHON",
    "https://mymajor.fiu.edu/individual/061BUSANLBBA",
    "https://mymajor.fiu.edu/individual/285INTBSBBA",
    "https://mymajor.fiu.edu/individual/035ARTHSTBA",
    "https://mymajor.fiu.edu/individual/148DIGJRNLSM",
    "https://mymajor.fiu.edu/individual/441PRAACBS",
    "https://mymajor.fiu.edu/individual/095CIVLEGBS",
    "https://mymajor.fiu.edu/individual/265ITBAONL",
    "https://mymajor.fiu.edu/individual/131CMPSCBAON",
    "https://mymajor.fiu.edu/individual/125COMPSCBS",
    "https://mymajor.fiu.edu/individual/060BIOMEGBS",
    "https://mymajor.fiu.edu/individual/141CRMJSTONL",
    "https://mymajor.fiu.edu/individual/047ASNSTBSJA",
    "https://mymajor.fiu.edu/individual/430PORTBA",
    "https://mymajor.fiu.edu/individual/235HISTBA",
    "https://mymajor.fiu.edu/individual/465RELSTBA",
    "https://mymajor.fiu.edu/individual/475ANTSOCANT",
    "https://mymajor.fiu.edu/individual/227GBLSTDONL",
    "https://mymajor.fiu.edu/individual/138CRMSCIBSO",
    "https://mymajor.fiu.edu/individual/251HOSPSPRMO",
    "https://mymajor.fiu.edu/individual/251HOSPTORMO",
    "https://mymajor.fiu.edu/individual/230HSABHSA",
    "https://mymajor.fiu.edu/individual/470SOCWKBS",
    "https://mymajor.fiu.edu/individual/146DIETBSDID",
    "https://mymajor.fiu.edu/individual/146DIETBSNUT",
    "https://mymajor.fiu.edu/individual/150DISMGTBA",
    "https://mymajor.fiu.edu/individual/305LANDXL",
    "https://mymajor.fiu.edu/individual/280INTDXL",
    "https://mymajor.fiu.edu/individual/464REHTHERBS",
    "https://mymajor.fiu.edu/individual/490SPEDBS",
    "https://mymajor.fiu.edu/individual/055BIOLBSQBI",
    "https://mymajor.fiu.edu/individual/198BIOENV",
    "https://mymajor.fiu.edu/individual/161EARTHBAED",
    "https://mymajor.fiu.edu/individual/455RECMGTPRK",
    "https://mymajor.fiu.edu/individual/439PSYCBAIND",
    "https://mymajor.fiu.edu/individual/175ELEMEDCAR",
    "https://mymajor.fiu.edu/individual/055BIOLBSFOR",
    "https://mymajor.fiu.edu/individual/344MATHSC2ST",
    "https://mymajor.fiu.edu/individual/175ELEMEDBS",
    "https://mymajor.fiu.edu/individual/181ENGLBAONL",
    "https://mymajor.fiu.edu/individual/278INTSTUDOL",
    "https://mymajor.fiu.edu/individual/320MGTSYBBA",
    "https://mymajor.fiu.edu/individual/030ARTBFA",
    "https://mymajor.fiu.edu/individual/356MUSICBMCO",
    "https://mymajor.fiu.edu/individual/361BMJS",
    "https://mymajor.fiu.edu/individual/357BMIP",
    "https://mymajor.fiu.edu/individual/261ITBS",
    "https://mymajor.fiu.edu/individual/170ELEGBS",
    "https://mymajor.fiu.edu/individual/481SOANSOCON",
    "https://mymajor.fiu.edu/individual/480SOCANTBA",
    "https://mymajor.fiu.edu/individual/228GBLSTDINT",
    "https://mymajor.fiu.edu/individual/229GLBSTORBA",
    "https://mymajor.fiu.edu/individual/251HOSPENTMG",
    "https://mymajor.fiu.edu/individual/385NURSGRN",
    "https://mymajor.fiu.edu/individual/341MATHSC2CP",
    "https://mymajor.fiu.edu/individual/054BIOLBS",
    "https://mymajor.fiu.edu/individual/325MRNBIOBS",
    "https://mymajor.fiu.edu/individual/392PHILBASPC",
    "https://mymajor.fiu.edu/individual/411PHYBSHLTP",
    "https://mymajor.fiu.edu/individual/437PSYCBAAPP",
    "https://mymajor.fiu.edu/individual/464RECTHEONL",
    "https://mymajor.fiu.edu/individual/182ENGLBACRW",
    "https://mymajor.fiu.edu/individual/198NURHEA",
    "https://mymajor.fiu.edu/individual/342MATHSC2EC",
    "https://mymajor.fiu.edu/individual/198HUMART",
    "https://mymajor.fiu.edu/individual/070CHEMBA",
    "https://mymajor.fiu.edu/individual/090CHEMFOR",
    "https://mymajor.fiu.edu/individual/201FINBBAONL",
    "https://mymajor.fiu.edu/individual/253HRMGTBBA",
    "https://mymajor.fiu.edu/individual/505THEADESIG",
    "https://mymajor.fiu.edu/individual/147DIARTANIM",
    "https://mymajor.fiu.edu/individual/358BMKEYBOAR",
    "https://mymajor.fiu.edu/individual/120COMPEGBS",
    "https://mymajor.fiu.edu/individual/486SPANBAONL",
    "https://mymajor.fiu.edu/individual/220GBLCTLIBA",
    "https://mymajor.fiu.edu/individual/044ASNSTBACH",
    "https://mymajor.fiu.edu/individual/251HOSPSPRMG",
    "https://mymajor.fiu.edu/individual/251HOSPBEVMG"
]
#I had to maunal add of the urls because the crawler was not working properly with just mymajor.fiu.edu

# Set this to True to generate only markdown files (no JSON)
MARKDOWN_ONLY = True

# Known MyMajor program codes and their full names
KNOWN_PROGRAMS = {
    # Earth & Environment Programs
    "215GEOSCBS": "Geosciences BS",
    "216GEOSCATM": "Geosciences - Atmospheric Science BS",
    "215GEOSCGIS": "Geosciences - Environmental GIS BS",
    # Physics Programs
    "411PHYBSENGR": "Physics - Engineering Physics BS",
    "411PHYBSBAS": "Physics BS",
    # Biology Programs
    "411BIOBSBMB": "Biology - Biomolecular Sciences BS",
    "411BIOBSBAE": "Biology - Biological Education BS",
    "411ENVBSEV": "Environmental Science BS",
    # Communication Arts
    "101COMARTART": "Communication Arts - Art and Performance Studies BA"
}

# Additional program info - hardcoded from FIU website
PROGRAM_INFO = {
    "215GEOSCBS": {
        "name": "Geosciences BS",
        "degree": "BS",
        "department": "Earth and Environment",
        "college": "College of Arts, Sciences & Education",
        "campus": "Modesto Maidique Campus",
        "description": "The Bachelor of Science in Geosciences program focuses on the Earth's physical environment including the planet's resources, landforms, landscape development, climate, hazards, surface and groundwater supply, and environmental issues. The program provides a strong science background and develops technical and research skills that prepare students for professional careers in the Environmental, Earth, and Atmospheric Sciences.",
        "admission": "Admission to the program follows the general FIU admission requirements. Students need to maintain a minimum GPA of 2.0 in all courses and a minimum GPA of 2.0 in all GLY, MET, and EVR courses.",
        "careers": "Geoscientists\nHydrologists\nEnvironmental Scientists\nGeophysical Data Technicians\nSoil and Plant Scientists\nAtmospheric Scientists\nGeographers\nGeological Sample Test Technicians\nNatural Sciences Managers\nEnvironmental Science Teachers, Postsecondary",
        "requirements": "Students in the BS program take courses in Physical Geology, Historical Geology, Earth Materials, Stratigraphy, Structural Geology, Field Methods, and various advanced topics in Earth Sciences. The program requires a strong foundation in chemistry, physics, and mathematics."
    },
    "101COMARTART": {
        "name": "Communication Arts - Art and Performance Studies",
        "degree": "BA",
        "department": "Communication",
        "college": "College of Communication, Architecture + The Arts",
        "campus": "Modesto Maidique Campus",
        "description": "In today's global environment, effective communication skills have a significant impact on career success. The Bachelor of Arts in Communication Arts is for those interested in pursuing careers as directors of communication in business, government, non-profit organizations or the arts. Students enrolled in our courses can expect to develop communication skills essential for leadership, corporate communication and crisis management. Students will learn how to advocate and critically debate ideas in social and political settings, to appreciate diverse communication styles, to work productively in task oriented groups, and to engage in rewarding interpersonal relationships.",
        "admission": "1. Students entering FIU as Freshmen or as a Transfer student with less than 60 transfer credits\n\nAdmissions criteria are the same as the general FIU criteria for students entering with fewer than 60 approved credits. Click here for the details.\n\n2. Transfer students entering FIU with 60 or more transfer credits\n\nAdmissions criteria are the same as the general FIU criteria for students entering with 60 or more approved credits. Click here for the details.",
        "careers": "Related Occupations:\n\nPublic Relations Director\nAccount Supervisor\nAccount Executive\nPublic Relations Manager (PR Manager)\nCommunications Director\nCommunity Relations Director\nDirector of Public Relations\nPublic Affairs Director\nAccount Manager\nBusiness Development Director\nMost of these occupations require a four-year bachelor's degree.\n\nWages & Employment Trends for Public Relations Managers:\n\nFlorida Median income\t$100,300\nFlorida rate of growth\t+14%\nNational Median wages\t$98,700\nNational Projected growth\t+13%\nSource and more information: http://www.onetonline.org/link/summary/11-2031.00",
        "contact": "CARTA Student Services and Advising Center\nPCA 272\nMiami, FL 33199\n305-348-7500\nCARTAADV@FIU.EDU"
    }
}

# Program structure model - fields we want to extract
PROGRAM_STRUCTURE = {
    "name": "",
    "degree": "",
    "department": "",
    "college": "",
    "campus": "",
    "description": "",
    "admission": "",
    "careers": "",
    "requirements": "",
    "contact": ""
}

# Directory setup
OUTPUT_DIR = Path("fiu_content") / "MyMajor"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --------- Helper functions ---------
#Saves the crawled program data in a structured markdown format
def save_markdown(content: str, metadata: dict, url: str, filename: str = None):
    """Save content as markdown file with metadata"""
    if not filename:
        filename = create_markdown_filename(url)
    
    filepath = OUTPUT_DIR / filename
    front_matter = (
        f"---\n"
        f"url: {url}\n"
        f"site: MyMajor\n"
        f"crawled_at: {metadata.get('crawled_at', datetime.now().isoformat())}\n"
        f"title: {metadata.get('title', 'FIU MyMajor')}\n"
        f"---\n\n"
    )
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(front_matter)
        f.write(content)
    
    print(f"💾 Saved: {filepath}")
    return filepath

def create_markdown_filename(url: str) -> str:
    """Create a filename from URL"""
    program_code = extract_program_code(url)
    if program_code:
        return f"{program_code}.md"
    
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return "index.md"
    return f"{path.replace('/', '_')}.md"

def extract_program_code(url: str) -> Optional[str]:
    """Extract program code from MyMajor URL if present"""
    match = re.search(r'/individual/(\w+)', url)
    if match:
        return match.group(1)
    return None

# --------- Crawling functions ---------
#Specialized crawler function that handles the extraction of data from individual MyMajor program pages
#Takes a URL as input and uses crawl4ai to extract the data, naviagte the page, and wait for the content to load
async def crawl_program(url: str) -> bool:
    """Crawl a single MyMajor program page using Crawl4AI"""
    print(f"🎭 Crawling: {url}")
    
    # Configure browser
    #Source: https://docs.crawl4ai.com/api/parameters/
    browser_config = BrowserConfig(
        viewport={"width": 1920, "height": 1080},
        headless=True,  # Run in headless mode for better performance
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    
    # Configure markdown generator with content filter
    md_gen = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(0.48, "fixed")
    )
    
    # Configure crawler
    #Source: https://docs.crawl4ai.com/api/parameters/
    #https://docs.crawl4ai.com/core/page-interaction/
    config = CrawlerRunConfig(
        wait_for="div#user-app-root",  # Wait for the main content container
        js_code="""
        // Scroll to trigger lazy loading
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(r => setTimeout(r, 2000));
        window.scrollTo(0, 0);
        await new Promise(r => setTimeout(r, 1000));
        """,
        page_timeout=60000,  # 60 second timeout
        markdown_generator=md_gen,
        cache_mode=CacheMode.BYPASS,
        remove_overlay_elements=True,
        process_iframes=True
    )
    
    try:
        # Use context manager to handle crawler lifecycle
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Crawl the page
            result = await crawler.arun(url, config=config)
            
            if not result or not result.cleaned_html:
                print(f"❌ Failed to load page: No content received")
                return False
                
            print("Page loaded, extracting content...")
            
            # Get markdown content
            content = ""
            if hasattr(result, "markdown"):
                if isinstance(result.markdown, str):
                    content = result.markdown
                elif hasattr(result.markdown, "fit_markdown"):
                    content = str(result.markdown.fit_markdown)
                else:
                    content = str(result.markdown)
            
            # Get metadata
            metadata = getattr(result, "metadata", {})
            
            # Save the markdown file
            save_markdown(content, metadata, url)
            return True
        
    except Exception as e:
        print(f"❌ Error crawling {url}: {str(e)}")
        return False

async def main(): #This is for the output area of the crawler so it can be easier to understand what is being crawled
    """Main entry point"""
    print("🚀 Starting MyMajor Crawler")
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Crawl the specific list of program URLs
    print(f"Crawling {len(PROGRAM_URLS)} program URLs...")
    
    for url in PROGRAM_URLS:
        program_code = extract_program_code(url)
        if not program_code: #So if it cannot extract data from the url it will not crawl it
            print(f"⚠️ Could not extract program code from URL: {url}")
            continue
        
        print(f"\n🔍 Crawling program: {program_code}")
        
        success = await crawl_program(url)
        if not success: #If it fails to crawl it will not crawl it
            print(f"Failed to crawl {url}")
        
        # Add delay to avoid overloading the server
        await asyncio.sleep(2)
    
    print("\n✅ MyMajor crawling complete!")

if __name__ == "__main__":
    asyncio.run(main()) 