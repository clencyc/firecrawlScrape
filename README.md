# Kenya Law Scraper API

A FastAPI-based web scraper for Kenya Law website (kenyalaw.org) using FireCrawl API.

## Features

- Scrape Kenya Law website pages
- Extract links and crawl multiple pages
- REST API with interactive documentation
- Simple web interface
- Rate limiting and polite scraping

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd firecrawlwebscraping
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env  # If you have an example file
# OR create manually:
touch .env
```

Add your FireCrawl API key to `.env`:

```
FIRECRAWLAPI_KEY=your_firecrawl_api_key_here
```

**Get your API key from:** [FireCrawl Dashboard](https://firecrawl.dev)

### 5. Run the Application

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Access the Application

- **Web Interface:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs
- **Alternative API Docs:** http://localhost:8000/redoc

## Usage

### Web Interface

1. Open http://localhost:8000 in your browser
2. Enter a Kenya Law URL (e.g., `https://new.kenyalaw.org`)
3. Set the number of pages to scrape (default: 10)
4. Click "Scrape" and wait for results

### API Endpoints

#### POST /scrape
Scrape Kenya Law pages

**Request Body:**
```json
{
  "url": "https://new.kenyalaw.org",
  "limit": 10,
  "scrape_links": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully scraped 5 pages",
  "total_pages": 5,
  "duration": 45.2,
  "results": [
    {
      "url": "https://new.kenyalaw.org/page1",
      "content": "Page content...",
      "title": "Page Title",
      "content_length": 1500
    }
  ]
}
```

### cURL Example

```bash
curl -X POST "http://localhost:8000/scrape" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://new.kenyalaw.org",
       "limit": 5,
       "scrape_links": true
     }'
```

## Project Structure

```
firecrawlwebscraping/
├── main.py              # FastAPI application
├── index.html           # Web interface
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not in git)
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Requirements

- Python 3.8+
- FireCrawl API key
- Internet connection

## Dependencies

- FastAPI - Web framework
- FireCrawl - Web scraping service
- python-dotenv - Environment variables
- uvicorn - ASGI server
- pydantic - Data validation

## Troubleshooting

### Common Issues

1. **API Key Error:** Make sure your FireCrawl API key is correct in `.env`
2. **URL Validation:** Only Kenya Law URLs (kenyalaw.org) are accepted
3. **Slow Scraping:** Large limits may take time - start with smaller numbers
4. **Port Already In Use:** Change port with `--port 8001`

### Development Mode

```bash
# Run with auto-reload on file changes
uvicorn main:app --reload

# Run on different port
uvicorn main:app --reload --port 8001

# Run with debug logging
uvicorn main:app --reload --log-level debug
```

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions, please create an issue in the repository.
