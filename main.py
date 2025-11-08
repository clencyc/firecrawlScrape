from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
import os
from firecrawl import Firecrawl
import time
import re
from urllib.parse import urljoin, urlparse
from typing import List, Optional

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Kenya Law Scraper API", version="1.0.0")

# Initialize Firecrawl
firecrawl = Firecrawl(api_key=os.getenv("FIRECRAWLAPI_KEY"))

# Pydantic models for request/response
class ScrapeRequest(BaseModel):
    url: HttpUrl
    limit: Optional[int] = 10
    scrape_links: Optional[bool] = True

class ScrapeResult(BaseModel):
    url: str
    content: str
    title: Optional[str] = None
    content_length: int

class ScrapeResponse(BaseModel):
    success: bool
    message: str
    total_pages: int
    duration: float
    results: List[ScrapeResult]

# Utility functions
def is_kenya_law_url(url: str) -> bool:
    """Check if URL is from kenyalaw.org domain"""
    parsed = urlparse(str(url))
    return "kenyalaw.org" in parsed.netloc.lower()

def get_start_urls(base_url: str, limit: int = 10) -> List[str]:
    """Get internal links from the base URL"""
    try:
        print(f"Discovering up to {limit} internal links from {base_url}")
        home = firecrawl.scrape(base_url, formats=["links"])
        links = home.links if hasattr(home, 'links') else []

        internal = []
        for link in links:
            if isinstance(link, str):
                href = link
            else:
                href = link.get("href") if hasattr(link, 'get') else getattr(link, 'href', None)
            
            if not href:
                continue
            abs_url = urljoin(base_url, href)
            if abs_url.startswith(base_url):
                internal.append(abs_url)
            if len(internal) >= limit:
                break
        
        print(f"Found {len(internal)} internal URLs")
        return internal[:limit]
    except Exception as e:
        print(f"Error discovering links: {e}")
        return [base_url]

# API endpoints
@app.get("/")
async def root():
    return {"message": "Kenya Law Scraper API", "status": "running"}

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_kenya_law(request: ScrapeRequest):
    """
    Scrape Kenya Law website
    - **url**: The Kenya Law URL to scrape
    - **limit**: Number of pages to scrape (default: 10)
    - **scrape_links**: Whether to scrape linked pages (default: True)
    """
    start_time = time.time()
    
    # Validate URL is from Kenya Law
    if not is_kenya_law_url(str(request.url)):
        raise HTTPException(
            status_code=400, 
            detail="URL must be from kenyalaw.org domain"
        )
    
    try:
        base_url = str(request.url)
        
        # Get URLs to scrape
        if request.scrape_links:
            urls_to_scrape = get_start_urls(base_url, request.limit) or [base_url]
        else:
            urls_to_scrape = [base_url]
        
        # Exclusion patterns
        exclude_patterns = [
            r".*\.pdf$", r".*\.jpg$", r".*\.png$", r".*\.gif$",
            r"/admin/.*", r"/login/.*"
        ]
        exclude_regex = re.compile("|".join(exclude_patterns))
        
        results = []
        for idx, url in enumerate(urls_to_scrape, 1):
            if exclude_regex.search(url):
                print(f"Skipping excluded URL: {url}")
                continue

            print(f"[{idx}/{len(urls_to_scrape)}] Scraping {url}")
            try:
                result = firecrawl.scrape(
                    url,
                    formats=["markdown"]
                )
                
                # Extract data from Document object
                content = result.content if hasattr(result, 'content') else str(result)
                title = result.title if hasattr(result, 'title') else None
                
                results.append(ScrapeResult(
                    url=url,
                    content=content,
                    title=title,
                    content_length=len(content)
                ))
                
                # Polite delay
                time.sleep(0.05)
                
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                continue
        
        end_time = time.time()
        duration = end_time - start_time
        
        return ScrapeResponse(
            success=True,
            message=f"Successfully scraped {len(results)} pages",
            total_pages=len(results),
            duration=round(duration, 2),
            results=results
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}