from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import RedirectResponse
import httpx
from typing import Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urlencode
from loguru import logger

from src.services.search import find_official_website
from src.core.settings import get_settings

router = APIRouter()
settings = get_settings()

async def fetch_with_scraper(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """Fetches a URL using ScraperAPI to bypass blocking."""
    if not settings.SCRAPER_API_KEY or settings.SCRAPER_API_KEY == "YOUR_SCRAPER_API_KEY_HERE":
        logger.warning("ScraperAPI key not configured. Attempting direct request.")
        return await client.get(url, timeout=10)

    logger.info(f"Using ScraperAPI for URL: {url}")
    scraper_url = "http://api.scraperapi.com"
    params = {
        'api_key': settings.SCRAPER_API_KEY,
        'url': url
    }
    return await client.get(scraper_url, params=params, timeout=30)

async def find_favicon_url(url: str, client: httpx.AsyncClient) -> Optional[str]:
    """Helper to find the favicon URL."""
    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    ico_url = urljoin(base_url, "/favicon.ico")
    
    try:
        ico_check = await client.head(ico_url, timeout=5)
        if ico_check.status_code == 200 and 'image' in ico_check.headers.get('content-type', ''):
            logger.info(f"Found favicon for {url} at default /favicon.ico")
            return ico_url
    except httpx.RequestError:
        pass

    logger.info(f"Checking HTML for favicon link in {url}")
    try:
        response = await client.get(url, timeout=10)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            logger.warning(f"Direct access to {url} forbidden (403). Retrying with scraper API.")
            response = await fetch_with_scraper(client, url)
            response.raise_for_status()
        else:
            raise
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    icon_rels = ["icon", "shortcut icon", "apple-touch-icon"]
    icon_link = None
    for rel in icon_rels:
        icon_link = soup.find("link", rel=rel)
        if icon_link:
            break

    if icon_link and icon_link.has_attr("href"):
        favicon_href = icon_link["href"]
        favicon_url = urljoin(str(response.url), favicon_href)
        logger.success(f"Successfully found favicon for {url} at {favicon_url}")
        return favicon_url
    
    return None

@router.get("/favicon", response_class=RedirectResponse, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def get_favicon(brand_name: str = Query(..., alias="brandName")) -> RedirectResponse:
    """Finds the official website for a brand, then finds and redirects to its favicon."""
    logger.info(f"Initiating favicon search for brand: '{brand_name}'")

    url = await find_official_website(brand_name)
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find an official website for '{brand_name}'.")

    if not url.startswith('http'):
        url = 'https://' + url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
        try:
            favicon_url = await find_favicon_url(url, client)
            if favicon_url:
                return RedirectResponse(url=favicon_url)
            
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favicon not found in HTML or at default location for the discovered website.")

        except httpx.RequestError as e:
            logger.warning(f"Could not fetch discovered URL {url} for brand '{brand_name}': {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not fetch the discovered website URL: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching favicon for {brand_name}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred.")