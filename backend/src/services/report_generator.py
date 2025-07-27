import google.generativeai as genai
from typing import List, Dict, Any, AsyncGenerator
from loguru import logger
import json

from src.core.settings import get_settings
from src.services.search import web_search

settings = get_settings()
genai.configure(api_key=settings.GEMINI_API_KEY)
QLOO_BASE_URL = "https://hackathon.api.qloo.com"

async def get_corporate_profile_via_search(brand_name: str) -> Dict[str, Any]:
    """
    Performs a Tavily search and returns the entire result object,
    including the context string and the list of sources.
    """
    logger.info(f"Performing Tavily search for corporate profile of '{brand_name}'")
    query = f"Corporate profile, brand identity, key products, and target audience for '{brand_name}'"
    search_result = await web_search(query)
    return search_result


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


async def generate_chat_response(
    messages: List[Dict[str, Any]], 
    report_context: str, 
    use_grounding: bool
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Generates a conversational response from the LLM, optionally using web search to ground the answer.
    Yields structured JSON events for sources and text chunks.
    """
    model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)

    # 1. Separate history from the new query
    gemini_history = []
    for msg in messages[:-1]:
        role = "model" if msg["role"] in ["assistant", "bot"] else "user"
        gemini_history.append({'role': role, 'parts': [msg['content']]})

    # 2. Prepare the latest user query and handle grounding
    last_user_message = messages[-1]['content'] if messages else ""
    if not last_user_message:
        return

    final_query_prompt = last_user_message
    if use_grounding:
        logger.info(f"Chat grounding enabled. Searching for: '{last_user_message}'")
        search_results = await web_search(last_user_message)
        if search_results and search_results['sources']:
            for source in search_results['sources']:
                yield {"type": "source", "payload": source}
            
            final_query_prompt = f"""
Based on the following live web search results, answer my question.
You should also use the initial report context and our conversation history if needed for full context.

**WEB SEARCH RESULTS:**
---
{search_results['context_str']}
---

**MY QUESTION:** {last_user_message}
"""
    
    # 3. Add the main system prompt to the first message in a conversation
    if not gemini_history:
        final_query_prompt = f"""
You are an expert M&A analyst acting as a follow-up assistant. Your sole task is to answer questions based *only* on the provided report context, conversation history, and any live web search results provided for the current query. Do not use any outside knowledge or make up information. If the answer is not in the provided materials, state that clearly. Provide concise, professional answers. Format your response using Markdown.
---
**INITIAL REPORT CONTEXT:**
{report_context}
---
{final_query_prompt}
"""
    
    try:
        chat = model.start_chat(history=gemini_history)
        response_stream = await chat.send_message_async(final_query_prompt, stream=True)
        async for chunk in response_stream:
            yield {"type": "chunk", "payload": chunk.text}
    except Exception as e:
        logger.error(f"Gemini chat stream failed: {e}")
        yield {"type": "error", "payload": "There was an error processing your request. Please try again."}