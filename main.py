from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
import os
import httpx
import json
import asyncio
from firecrawl import Firecrawl
import time
import re
from urllib.parse import urljoin, urlparse
from typing import List, Optional

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")


if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment variables")

# Initialize FastAPI app
app = FastAPI(title="Kenya Law Scraper API", version="1.0.0")

ALLOWED_ORIGINS = [
    "https://firecrawlscrape.onrender.com",
    "https://your-frontend-domain.com",
    "http://localhost:3000",
    "http://localhost:5173",
    "https://haki-chain-liard.vercel.app",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    document_id: Optional[str] = None

class ChatMessage(BaseModel):
    role: str 
    content: str

class ChatRequest(BaseModel):
    message: str
    document_id: Optional[str] = None
    context: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    document_references: List[str]
    confidence: Optional[float] = None

scraped_documents = {}

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


async def call_llm(prompt: str) -> str:
    """Call Gemini API directly via HTTP"""
    try:
        if not GEMINI_API_KEY:
            return "Error: Gemini API key not configured"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "topP": 0.8,
                        "topK": 40,
                        "maxOutputTokens": 1000
                    }
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                # Extract the text from the response
                return result["candidates"][0]["content"]["parts"][0]["text"]
            else:
                error_detail = response.text if response.text else f"Status {response.status_code}"
                return f"Error: Gemini API returned {error_detail}"
                
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return "Sorry, I'm having trouble connecting to Gemini. Please try again."


# API endpoints
@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")

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

        doc_id = f"doc_{int(time.time())}"
        scraped_documents[doc_id] = {
            "content": [result.content for result in results],
            "urls": [result.url for result in results],
            "title": results[0].title if results else "Unknown",
            "scraped_at": time.time()
        }
        
        return ScrapeResponse(
            success=True,
            message=f"Successfully scraped {len(results)} pages",
            total_pages=len(results),
            duration=round(duration, 2),
            results=results,
            document_id=doc_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat_with_document(request: ChatRequest):
    if not request.document_id or request.document_id not in scraped_documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = scraped_documents[request.document_id]
    combined_content = "\n\n".join(doc["content"])
    
    # Enhanced legal prompt for Gemini
    prompt = f"""You are a helpful legal AI assistant specializing in Kenya Law. You are analyzing legal documents from the Kenya Law website.

**DOCUMENT CONTENT:**
{combined_content[:6000]}

**INSTRUCTIONS:**
- Answer based ONLY on the provided document content
- If information isn't available in the document, clearly state: "This information is not available in the provided document"
- For legal terms, provide brief explanations when helpful
- Be precise and cite specific sections or paragraphs when possible
- Use clear, professional language
- If asked for legal advice, remind that this is for informational purposes only

**USER QUESTION:** {request.message}

**RESPONSE:**"""
    
    response = await call_llm(prompt)
    
    return ChatResponse(
        response=response,
        document_references=doc["urls"]
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

