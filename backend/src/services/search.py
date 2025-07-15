from tavily import TavilyClient
from src.core.settings import get_settings
from loguru import logger
from typing import Dict, List, Any

settings = get_settings()

async def tavily_search(query: str) -> Dict[str, Any]:
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