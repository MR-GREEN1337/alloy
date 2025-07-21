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


async def generate_chat_response(messages: List[Dict[str, Any]], report_context: str) -> AsyncGenerator[str, None]:
    """
    Generates a conversational response from the LLM, maintaining chat history.
    """
    model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
    
    # Map our role names ('assistant') to Gemini's ('model')
    gemini_history = []
    for msg in messages:
        role = "model" if msg["role"] in ["assistant", "bot"] else "user"
        gemini_history.append({'role': role, 'parts': [msg['content']]})

    # The system prompt and report context are prepended to the very first user message
    # to give the model its instructions and the necessary data context for the entire conversation.
    if gemini_history and gemini_history[0]['role'] == 'user':
        first_user_content = gemini_history[0]['parts'][0]
        system_and_report_context = f"""
You are an expert M&A analyst acting as a follow-up assistant. Your sole task is to answer questions based *only* on the provided report context and the ongoing conversation. Do not use any outside knowledge or make up information. If the answer is not in the context, state that clearly. Provide concise, professional answers. Format your response using Markdown.
---
**REPORT CONTEXT:**
{report_context}
---
**USER'S FIRST QUESTION:**
{first_user_content}
"""
        gemini_history[0]['parts'] = [system_and_report_context]
    
    # The last message is the new query, the rest is history
    history_for_chat = gemini_history[:-1]
    new_query_content = gemini_history[-1]['parts'][0] if gemini_history else ""

    if not new_query_content:
        yield "I'm sorry, I didn't receive a question. Please try again."
        return

    try:
        chat = model.start_chat(history=history_for_chat)
        response_stream = await chat.send_message_async(new_query_content, stream=True)
        async for chunk in response_stream:
            yield chunk.text
    except Exception as e:
        logger.error(f"Gemini chat stream failed: {e}")
        yield "There was an error processing your request. Please try again."