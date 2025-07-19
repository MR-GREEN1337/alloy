from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import RedirectResponse
import httpx
from typing import Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from loguru import logger

from src.core.settings import get_settings
from src.services.search import find_official_website
from fastapi_simple_rate_limiter import rate_limiter

router = APIRouter()
settings = get_settings()

async def fetch_with_scraper(client: httpx.AsyncClient, url: str) -> httpx.Response:
    if not settings.SCRAPER_API_KEY or settings.SCRAPER_API_KEY == "YOUR_SCRAPER_API_KEY_HERE":
        logger.warning("ScraperAPI key not configured. Attempting direct request.")
        return await client.get(url, timeout=10)
    logger.info(f"Using ScraperAPI for URL: {url}")
    scraper_url = "http://api.scraperapi.com"
    params = {'api_key': settings.SCRAPER_API_KEY, 'url': url}
    return await client.get(scraper_url, params=params, timeout=30)

async def find_favicon_url(url: str, client: httpx.AsyncClient) -> Optional[str]:
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
        if e.response.status_code in [401, 403]:
            logger.warning(f"Direct access to {url} failed ({e.response.status_code}). Retrying with scraper.")
            response = await fetch_with_scraper(client, url)
            response.raise_for_status()
        else:
            raise
    soup = BeautifulSoup(response.text, "html.parser")
    icon_rels = ["icon", "shortcut icon", "apple-touch-icon"]
    icon_link = soup.find("link", rel=lambda r: r and r.lower() in icon_rels)
    if icon_link and icon_link.has_attr("href"):
        favicon_href = icon_link["href"]
        favicon_url = urljoin(str(response.url), favicon_href)

        # --- FIX: Add a check to ignore generic scraper favicons ---
        if "scraperapi.com" in favicon_url:
            logger.warning(f"Ignoring generic scraper favicon for {url}")
            return None # Explicitly return None to continue searching

        logger.success(f"Successfully found favicon for {url} at {favicon_url}")
        return favicon_url
    return None

async def fetch_favicon_bytes(brand_name: str) -> Optional[bytes]:
    """Finds a brand's favicon and returns its raw bytes."""
    logger.info(f"Fetching favicon bytes for PDF: '{brand_name}'")
    try:
        website_url = await find_official_website(brand_name)
        if not website_url:
            return None
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
            favicon_url = await find_favicon_url(website_url, client)
            if not favicon_url:
                return None
            
            response = await client.get(favicon_url, timeout=10)
            response.raise_for_status()
            return response.content
    except Exception as e:
        logger.warning(f"Could not fetch favicon bytes for '{brand_name}': {e}")
        return None

@router.get("/favicon", response_class=RedirectResponse, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
@rate_limiter(limit=200, seconds=60)
async def get_favicon(
    url: Optional[str] = Query(None),
    brandName: Optional[str] = Query(None)
) -> RedirectResponse:
    """
    Finds and redirects to the favicon for a given URL or brand name.
    Prioritizes brandName if both are provided.
    """
    if not brandName and not url:
        raise HTTPException(status_code=400, detail="Either 'url' or 'brandName' query parameter is required.")

    final_url = url
    if brandName:
        logger.info(f"Initiating favicon search for brand: '{brandName}'")
        final_url = await find_official_website(brandName)
        if not final_url:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find an official website for '{brandName}'.")
    
    if not final_url:
        raise HTTPException(status_code=400, detail="Invalid URL provided.")

    if not final_url.startswith('http'):
        final_url = 'https://' + final_url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
        try:
            favicon_url = await find_favicon_url(final_url, client)
            if favicon_url:
                return RedirectResponse(url=favicon_url)
            raise HTTPException(status_code=404, detail="Favicon not found for the discovered URL.")
        except httpx.RequestError as e:
            logger.warning(f"Could not fetch URL {final_url}: {e}")
            raise HTTPException(status_code=400, detail=f"Could not fetch the provided URL: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching favicon for {final_url}: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred.")