import httpx
import google.generativeai as genai
from typing import List, Dict, Any, AsyncGenerator
from loguru import logger
import json
import asyncio

from src.core.settings import get_settings
from src.services.search import tavily_search

settings = get_settings()
genai.configure(api_key=settings.GEMINI_API_KEY)
QLOO_BASE_URL = "https://hackathon.api.qloo.com"

# ... (get_corporate_profile_via_search and get_cultural_profile_via_qloo are unchanged)
async def get_corporate_profile_via_search(brand_name: str) -> Dict[str, Any]:
    """
    Performs a Tavily search and returns the entire result object,
    including the context string and the list of sources.
    """
    logger.info(f"Performing Tavily search for corporate profile of '{brand_name}'")
    query = f"Corporate profile, brand identity, key products, and target audience for '{brand_name}'"
    search_result = await tavily_search(query)
    return search_result

async def get_cultural_profile_via_qloo(corporate_profile: str, brand_name: str, client: httpx.AsyncClient) -> List[Dict]:
    logger.info(f"Extracting cultural proxies for '{brand_name}'")
    proxy_extraction_model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
    prompt = f"From the following text about '{brand_name}', extract up to 5 of the most culturally significant and well-known entities (movies, artists, TV shows, specific well-known product names like 'iPhone' or 'Model S', etc.). Return them as a simple comma-separated list. TEXT: {corporate_profile}"
    try:
        response = await proxy_extraction_model.generate_content_async(prompt)
        proxy_names = [name.strip() for name in response.text.split(',')]
        logger.success(f"Extracted proxies for '{brand_name}': {proxy_names}")
    except Exception as e:
        logger.error(f"Failed to extract proxies for '{brand_name}': {e}")
        return []

    if not proxy_names: return []
    payload = {"signal": { "interests": { "entities": { "query": proxy_names } } }, "filter": { "type": "urn:entity:brand" }, "take": 50}
    insights_endpoint = f"{QLOO_BASE_URL}/v2/insights"
    headers = {"x-api-key": settings.QLOO_API_KEY}
    try:
        logger.info(f"Querying Qloo with proxies for '{brand_name}'")
        qloo_response = await client.post(insights_endpoint, json=payload, headers=headers)
        qloo_response.raise_for_status()
        return qloo_response.json().get('data', [])
    except httpx.HTTPStatusError as e:
        logger.error(f"Qloo Insights API error for '{brand_name}' proxies: {e.response.status_code} - {e.response.text}")
        return []


# --- Analysis Functions (Unchanged) ---
def calculate_affinity_overlap(acquirer_data: List[Dict], target_data: List[Dict]) -> float:
    if not acquirer_data or not target_data: return 0.0
    acquirer_interests = {item.get('name') for item in acquirer_data if item.get('name')}
    target_interests = {item.get('name') for item in target_data if item.get('name')}
    intersection = len(acquirer_interests.intersection(target_interests))
    union = len(acquirer_interests.union(target_interests))
    return round((intersection / union) * 100, 2) if union > 0 else 0.0
def find_culture_clashes(acquirer_data: List[Dict], target_data: List[Dict]) -> List[Dict[str, Any]]:
    acquirer_interests = {item.get('name') for item in acquirer_data if item.get('name')}
    target_interests = {item.get('name') for item in target_data if item.get('name')}
    unique_to_acquirer = acquirer_interests - target_interests
    unique_to_target = target_interests - acquirer_interests
    clashes = []
    for interest in list(unique_to_acquirer)[:5]:
        clashes.append({"topic": interest, "description": "Audience shows strong affinity for this, a taste not shared by the Target's audience.", "severity": "MEDIUM"})
    for interest in list(unique_to_target)[:5]:
         clashes.append({"topic": interest, "description": "Audience shows strong affinity for this, a taste not shared by the Acquirer's audience.", "severity": "HIGH"})
    return clashes
def find_untapped_growth(acquirer_data: List[Dict], target_data: List[Dict]) -> List[Dict[str, Any]]:
    #...
    acquirer_interests = {item.get('name') for item in acquirer_data if item.get('name')}
    target_interests = {item.get('name') for item in target_data if item.get('name')}
    shared_interests = acquirer_interests.intersection(target_interests)
    opportunities = []
    for interest in list(shared_interests)[:5]:
        opportunities.append({"description": f"Both audiences show a strong affinity for '{interest}'. This shared passion point could be a key pillar for joint marketing campaigns and product integrations post-acquisition.", "potential_impact_score": 8})
    return opportunities


async def generate_llm_insights(acquirer_brand: str, target_brand: str, acquirer_profile: str, target_profile: str, acquirer_tastes: str, target_tastes: str, use_grounding: bool, user_context: str | None) -> Dict[str, Any]:
    model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
    
    search_results_context = ""
    search_sources = []
    grounding_instruction = "Analyze based *only* on the Corporate Profiles, Qloo taste data, and any user-provided context."
    
    if use_grounding:
        logger.info("Internet grounding is enabled. Performing Tavily search...")
        search_query = f"Cultural compatibility, brand identity, and audience overlap between '{acquirer_brand}' and '{target_brand}'"
        search_result = await tavily_search(search_query)
        search_results_context = f"\n**Data Source 3: Current Events & Analysis (from Tavily Search)**\n{search_result['context_str']}\n"
        search_sources = search_result['sources']
        grounding_instruction = "Synthesize a comprehensive analysis using all data sources: Corporate Profiles, Qloo taste data, user-provided context, AND the following real-time search results."

    context_section = f"\n**User-Provided Context:**\n{user_context}\n" if user_context else ""
    
    prompt = f"""
    As an expert M&A brand strategist, provide a deep cultural analysis for the acquisition of **{target_brand}** by **{acquirer_brand}**.
    {grounding_instruction}

    **Data Source 1: Corporate Profiles**
    - **{acquirer_brand} Profile:** {acquirer_profile}
    - **{target_brand} Profile:** {target_profile}

    **Data Source 2: Cultural Taste Profiles (from Qloo API via proxy analysis)**
    - **{acquirer_brand} Audience Tastes:** {acquirer_tastes}
    - **{target_brand} Audience Tastes:** {target_tastes}
    {context_section}
    {search_results_context}
    **Required Output Format:**
    Return a single, valid JSON object with exactly two keys: "brand_archetype_summary" and "strategic_summary".

    1.  **brand_archetype_summary (Stringified JSON):** Create a JSON string with keys "acquirer_archetype" and "target_archetype". For each, write a concise, 2-3 sentence paragraph describing the brand's core identity, values, and audience persona. Synthesize this from all available information.

    2.  **strategic_summary (String):** Write a 3-4 sentence high-level executive summary for a board of directors. Synthesize all findings to explain the overall cultural compatibility. Base your assessment on how the corporate identities align and where the cultural tastes overlap or clash. Highlight the primary risks and the most significant strategic opportunities from the combined data. Be decisive and clear.
    """
    try:
        response = await model.generate_content_async(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        llm_json = json.loads(cleaned_response)
        # Add sources to the returned dictionary
        llm_json['sources'] = search_sources
        return llm_json
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")
        return {"brand_archetype_summary": '{"acquirer_archetype": "Error generating analysis.", "target_archetype": "Error generating analysis."}', "strategic_summary": "Could not generate AI-powered strategic summary due to an API error.", "sources": []}

# ... (generate_chat_response remains the same)
async def generate_chat_response(query: str, report_context: str) -> AsyncGenerator[str, None]:
    model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
    prompt = f"""
    You are an expert M&A analyst acting as a follow-up assistant. Your sole task is to answer the user's question based *only* on the provided report context. Do not use any outside knowledge or make up information. If the answer is not in the context, state that clearly. Provide concise, professional answers. Format your response using Markdown.
    ---
    **REPORT CONTEXT:**
    {report_context}
    ---
    **USER'S QUESTION:**
    {query}
    ---
    **YOUR ANSWER:**
    """
    try:
        response_stream = await model.generate_content_async(prompt, stream=True)
        async for chunk in response_stream:
            yield chunk.text
    except Exception as e:
        logger.error(f"Gemini chat stream failed: {e}")
        yield "There was an error processing your request. Please try again."