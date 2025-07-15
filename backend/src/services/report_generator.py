import httpx
import google.generativeai as genai
from typing import List, Dict, Any
from loguru import logger
import json

from src.core.settings import get_settings

settings = get_settings()

# --- Configure APIs ---
genai.configure(api_key=settings.GEMINI_API_KEY)
# --- Ensure we are using the correct Hackathon URL ---
QLOO_BASE_URL = "https://hackathon.api.qloo.com/v2"


# --- DEFINITIVE FIX: Revert to the correct 2-step Search -> Affinities logic ---
async def get_qloo_taste_data(
    brand_name: str, client: httpx.AsyncClient
) -> List[Dict[str, Any]]:
    """
    Fetches the taste affinities for a given brand using the correct
    two-step process: search for the entity ID, then get its audience affinities.
    """
    headers = {"x-api-key": settings.QLOO_API_KEY}
    
    # STEP 1: Search for the brand to get its Qloo ID.
    search_params = {"q": brand_name, "type": "brand", "limit": 1}
    try:
        logger.info(f"Searching for brand ID for: '{brand_name}'")
        search_response = await client.get(f"{QLOO_BASE_URL}/search", params=search_params, headers=headers)
        search_response.raise_for_status()
        search_results = search_response.json()
        
        if not search_results or not search_results.get('data'):
            logger.warning(f"Qloo Search: No entity found for brand '{brand_name}'")
            return []
        
        brand_id = search_results['data'][0]['id']
        logger.success(f"Qloo Search: Found entity ID '{brand_id}' for brand '{brand_name}'")

    except httpx.HTTPStatusError as e:
        logger.error(f"Qloo Search API error for '{brand_name}': {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred during Qloo search for '{brand_name}': {e}")
        return []

    # STEP 2: Use the brand ID to get its audience's taste affinities.
    taste_params = {"id": [brand_id]}
    try:
        logger.info(f"Fetching taste affinities for ID: '{brand_id}'")
        taste_response = await client.get(f"{QLOO_BASE_URL}/taste-affinities/audiences", params=taste_params, headers=headers)
        taste_response.raise_for_status()
        
        taste_data = taste_response.json().get('data', [])
        logger.success(f"Qloo Affinities: Found {len(taste_data)} taste points for ID '{brand_id}'")
        return taste_data

    except httpx.HTTPStatusError as e:
        logger.error(f"Qloo Affinities API error for ID '{brand_id}': {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching Qloo affinities for ID '{brand_id}': {e}")
        return []


# --- Analysis Service (Unchanged) ---
def calculate_affinity_overlap(acquirer_data: List[Dict], target_data: List[Dict]) -> float:
    if not acquirer_data or not target_data:
        return 0.0
    
    acquirer_interests = {item['name'] for item in acquirer_data}
    target_interests = {item['name'] for item in target_data}

    intersection = len(acquirer_interests.intersection(target_interests))
    union = len(acquirer_interests.union(target_interests))
    
    return round((intersection / union) * 100, 2) if union > 0 else 0.0

def find_culture_clashes(acquirer_data: List[Dict], target_data: List[Dict]) -> List[Dict[str, Any]]:
    acquirer_map = {item['name']: item['type'] for item in acquirer_data}
    target_map = {item['name']: item['type'] for item in target_data}

    acquirer_interests = set(acquirer_map.keys())
    target_interests = set(target_map.keys())

    unique_to_acquirer = acquirer_interests - target_interests
    unique_to_target = target_interests - acquirer_interests

    clashes = []
    for interest in list(unique_to_acquirer)[:5]:
        clashes.append({
            "topic": interest, 
            "description": f"Audience shows strong affinity for this, a taste not shared by the Target's audience.", 
            "severity": "MEDIUM"
        })

    for interest in list(unique_to_target)[:5]:
         clashes.append({
             "topic": interest, 
             "description": f"Audience shows strong affinity for this, a taste not shared by the Acquirer's audience.", 
             "severity": "HIGH"
         })

    return clashes

def find_untapped_growth(acquirer_data: List[Dict], target_data: List[Dict]) -> List[Dict[str, Any]]:
    acquirer_interests = {item['name'] for item in acquirer_data}
    target_interests = {item['name'] for item in target_data}
    shared_interests = acquirer_interests.intersection(target_interests)
    
    opportunities = []
    for interest in list(shared_interests)[:5]:
        opportunities.append({
            "description": f"Both audiences show a strong affinity for '{interest}'. This shared passion point could be a key pillar for joint marketing campaigns and product integrations post-acquisition.",
            "potential_impact_score": 8
        })
    return opportunities

# --- Gemini (LLM) Service ---
async def generate_llm_insights(acquirer_brand: str, target_brand: str, acquirer_tastes: str, target_tastes: str) -> Dict[str, str]:
    model = genai.GenerativeModel('gemini-pro')
    prompt = f"""
    As an expert M&A brand strategist, analyze the cultural taste data for an acquisition scenario: {acquirer_brand} (Acquirer) and {target_brand} (Target).
    Based *only* on the raw audience affinity data provided, generate two distinct summaries. Do not use outside knowledge.

    **Audience Taste Data:**
    - **{acquirer_brand} (Acquirer) Affinities:** {acquirer_tastes}
    - **{target_brand} (Target) Affinities:** {target_tastes}

    **Required Output Format:**
    Return a single, valid JSON object with exactly two keys: "brand_archetype_summary" and "strategic_summary".

    1.  **brand_archetype_summary (Stringified JSON):**
        - Create a JSON string with two keys: "acquirer_archetype" and "target_archetype".
        - For each, write a concise, 2-3 sentence paragraph describing the personality and values of the brand's audience. Deduce their cultural "archetype" from their tastes.

    2.  **strategic_summary (String):**
        - Write a 3-4 sentence high-level executive summary.
        - Synthesize the findings to explain the overall cultural compatibility.
        - Highlight the primary risks based on taste clashes and the most significant strategic opportunities from the data overlap.
    """
    
    try:
        response = await model.generate_content_async(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(cleaned_response)
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")
        return {
            "brand_archetype_summary": '{"acquirer_archetype": "Error generating analysis.", "target_archetype": "Error generating analysis."}',
            "strategic_summary": "Could not generate AI-powered strategic summary due to an API error."
        }