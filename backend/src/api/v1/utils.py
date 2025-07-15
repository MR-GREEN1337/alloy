from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import RedirectResponse
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from loguru import logger

router = APIRouter()

@router.get("/favicon", response_class=RedirectResponse, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def get_favicon(url: str = Query(...)):
    """
    Finds and redirects to the favicon for a given URL.
    """
    if not url.startswith('http'):
        url = 'https://' + url

    # CORE FIX 1: Add a common browser User-Agent to avoid 403 Forbidden errors.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with httpx.AsyncClient(follow_redirects=True, timeout=10, headers=headers) as client:
        try:
            # 1. First, try the default /favicon.ico path
            base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            ico_url = urljoin(base_url, "/favicon.ico")
            
            ico_check = await client.head(ico_url)
            if ico_check.status_code == 200 and 'image' in ico_check.headers.get('content-type', ''):
                logger.info(f"Found favicon for {url} at default /favicon.ico")
                return RedirectResponse(url=ico_url)

            # 2. If not found, fetch the page and parse HTML for <link> tags
            logger.info(f"Checking HTML for favicon link in {url}")
            response = await client.get(url)
            response.raise_for_status()

            # CORE FIX 2: Use Python's built-in 'html.parser' instead of 'lxml'
            # to avoid requiring an external dependency.
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Prioritized list of rel attributes
            icon_rels = ["icon", "shortcut icon", "apple-touch-icon"]
            icon_link = None
            for rel in icon_rels:
                icon_link = soup.find("link", rel=rel)
                if icon_link:
                    break

            if icon_link and icon_link.has_attr("href"):
                favicon_href = icon_link["href"]
                # Resolve relative URLs
                favicon_url = urljoin(response.url, favicon_href)
                logger.success(f"Successfully found favicon for {url} at {favicon_url}")
                return RedirectResponse(url=favicon_url)
            
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favicon not found in HTML or at default location.")

        except httpx.RequestError as e:
            logger.warning(f"Could not fetch URL {url}: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not fetch the provided URL: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching favicon for {url}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred.")