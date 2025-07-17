from tavily import TavilyClient
from src.core.settings import get_settings
from loguru import logger
from typing import Dict, List, Any, TypedDict, Optional
import google.generativeai as genai
from urllib.parse import urlparse

settings = get_settings()
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


class TavilySearchToolOutput(TypedDict):
    context_str: str
    sources: List[Dict[str, str]]

async def web_search(query: str) -> TavilySearchToolOutput:
    """
    Performs a search using the Tavily API and returns a structured dictionary
    containing the formatted results for an LLM and a list of sources.
    """
    if not settings.TAVILY_API_KEY:
        logger.warning("Tavily API key is not set. Skipping search.")
        return {
            "context_str": "Tavily search was not performed because the API key is missing.",
            "sources": []
        }

    try:
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=5
        )

        # Format the results into a string for the LLM prompt
        context_str = "\n\n".join(
            [f"Title: {res['title']}\nURL: {res['url']}\nContent: {res['content']}" for res in response['results']]
        )
        
        # Extract sources for storage and display
        sources = [{"title": res.get("title", ""), "url": res.get("url", "")} for res in response.get('results', [])]
        
        logger.success(f"Tavily search successful for query: '{query}'")
        return {
            "context_str": context_str,
            "sources": sources
        }

    except Exception as e:
        logger.error(f"An error occurred during Tavily search: {e}")
        return {
            "context_str": f"An error occurred during the search: {str(e)}",
            "sources": []
        }

async def find_official_website(brand_name: str) -> Optional[str]:
    """
    Uses Gemini to find the most likely official website for a given brand name.
    """
    if not settings.GEMINI_API_KEY:
        logger.warning("Gemini API key is not set. Skipping website search.")
        return None

    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
        prompt = f"""
        You are a research assistant. Your only task is to find the official homepage URL for a given company.
        Return ONLY the URL and nothing else. Do not add any explanatory text, markdown, or greetings.
        If you cannot find a definitive official website, return the text "NOT_FOUND".
    
        Company Name: "{brand_name}"
        Official URL:
        """
        
        response = await model.generate_content_async(prompt)
        
        # CORE FIX: Use a more robust check for safety-blocked responses.
        # Check if the response is empty and if there are safety ratings indicating a block.
        if not response.parts and response.prompt_feedback.safety_ratings:
            logger.warning(f"Gemini response for '{brand_name}' was blocked by safety settings. Ratings: {response.prompt_feedback.safety_ratings}")
            return None

        url_candidate = response.text.strip()
        
        logger.info(f"Gemini proposed URL for '{brand_name}': '{url_candidate}'")

        if "NOT_FOUND" in url_candidate or not url_candidate:
            logger.warning(f"Gemini could not find a website for '{brand_name}'.")
            return None
        
        parsed_url = urlparse(url_candidate)
        if parsed_url.scheme and parsed_url.netloc:
            logger.success(f"Successfully found and validated website for '{brand_name}': {url_candidate}")
            return url_candidate
        else:
            logger.warning(f"Gemini returned an invalid URL format for '{brand_name}': '{url_candidate}'")
            return None

    except Exception as e:
        # Catch specific "Invalid operation" error when .text is accessed on an empty response
        if "Invalid operation" in str(e) and "none were returned" in str(e):
             logger.warning(f"Gemini returned an empty response for '{brand_name}', likely due to safety filters.")
             return None
        logger.error(f"An error occurred during Gemini website search for '{brand_name}': {e}")
        return None