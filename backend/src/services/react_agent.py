import httpx
import google.generativeai as genai
from typing import List, Dict, Any, AsyncGenerator, Optional, Tuple, Set
from loguru import logger
import json
import asyncio

from src.core.settings import get_settings
from src.services.search import web_search

settings = get_settings()
genai.configure(api_key=settings.GEMINI_API_KEY)

# --- Agent Tool Helpers ---

async def _summarize_with_gemini(context: str, query: str) -> str:
    """Summarizes a text context using Gemini, tailored to a specific query."""
    if not context.strip():
        return "No information found from web search."
    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
        prompt = f"""
        Based *only* on the following text from a web search, provide a concise summary that directly answers the user's query.
        Focus on the most relevant facts, entities, and data points.

        USER QUERY: "{query}"

        SEARCH RESULTS CONTEXT:
        ---
        {context}
        ---

        CONCISE SUMMARY FOR AGENT:
        """
        response = await model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error during Gemini summarization: {e}")
        return "Could not summarize the search results due to an internal error."

async def _extract_cultural_proxies(context: str, brand_name: str) -> List[str]:
    """Uses an LLM to identify 3-5 key cultural products/properties from a text."""
    logger.info(f"Extracting cultural proxies for {brand_name}...")
    if not context.strip():
        return []
    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
        prompt = f"""
        Based *only* on the provided text about '{brand_name}', identify the 3 to 5 most famous and culturally significant **named entities** associated with them.
        Focus on concrete, searchable items:
        - Specific products (e.g., "iPhone 15", "Air Jordan", "Model S")
        - Hit movies, TV shows, or video games (e.g., "Stranger Things", "Call of Duty")
        - Famous public figures or spokespeople (e.g., "Michael Jordan", "Taylor Swift")
        - Well-known sub-brands (e.g., "Pixar", "Marvel Studios")

        Do NOT return abstract concepts like "innovation" or "brand loyalty".

        CONTEXT:
        ---
        {context}
        ---

        Return a single JSON array of strings. If no specific items are found, return an empty array. Example: ["Famous Product A", "Popular Show B"]
        """
        response = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
        proxies = json.loads(response.text)
        logger.success(f"Extracted proxies for {brand_name}: {proxies}")
        return proxies
    except Exception as e:
        logger.error(f"Error during cultural proxy extraction for {brand_name}: {e}")
        return []


# --- CORRECTED QLOO API FUNCTIONS ---

QLOO_HACKATHON_BASE_URL = "https://hackathon.api.qloo.com"
# A list of types to iterate through, excluding the problematic video_game type.
QLOO_ENTITY_TYPE_LIST = [
    "urn:entity:brand",
    "urn:entity:person",
    "urn:entity:artist",
    "urn:entity:movie",
    "urn:entity:tv_show",
    "urn:entity:book",
    "urn:entity:podcast",
    "urn:entity:place",
    "urn:entity:destination",
]

async def _find_qloo_id(client: httpx.AsyncClient, entity_name: str) -> Optional[str]:
    """
    Correctly uses the /search endpoint to find a Qloo entity ID by searching
    across supported types individually until a match is found.
    """
    headers = {"x-api-key": settings.QLOO_API_KEY}
    
    for entity_type in QLOO_ENTITY_TYPE_LIST:
        params = {"query": entity_name, "types": entity_type}
        try:
            resp = await client.get(f"{QLOO_HACKATHON_BASE_URL}/search", params=params, headers=headers, timeout=10.0)
            
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    qloo_id = results[0].get("id")
                    if qloo_id:
                        logger.success(f"Found Qloo ID for '{entity_name}' (as type {entity_type}): {qloo_id}")
                        return qloo_id
            elif resp.status_code == 429:
                logger.warning(f"Rate limited by Qloo /search for type {entity_type}. Waiting...")
                await asyncio.sleep(2)
        
        except Exception as e:
            logger.error(f"Qloo /search request failed for '{entity_name}' with type {entity_type}: {e}")
            continue
    
    logger.warning(f"Could not find a Qloo entity for '{entity_name}' across all supported types.")
    return None

async def _get_tastes_for_entity(client: httpx.AsyncClient, qloo_id: str) -> Set[str]:
    """Correctly uses the /v2/insights endpoint to get taste data (tags) for an entity."""
    headers = {"x-api-key": settings.QLOO_API_KEY}
    params = {
        "signal.interests.entities": qloo_id,
        "filter.type": "urn:tag",
        "take": 50
    }

    try:
        resp = await client.get(f"{QLOO_HACKATHON_BASE_URL}/v2/insights", params=params, headers=headers, timeout=15.0)

        if resp.status_code == 200:
            data = resp.json()
            entities = data.get("results", {}).get("entities", [])
            tastes = {entity.get('name') for entity in entities if entity.get('name')}
            if tastes:
                logger.success(f"Fetched {len(tastes)} tastes for ID {qloo_id}")
                return tastes
        elif resp.status_code == 429:
            logger.warning("Rate limited by Qloo /insights. Waiting...")
            await asyncio.sleep(2)
        else:
            logger.warning(f"Qloo insights for ID {qloo_id} failed with status {resp.status_code}: {resp.text[:200]}")
    
    except Exception as e:
        logger.error(f"Qloo /insights request failed for ID {qloo_id}: {e}")

    return set()

async def _get_tastes_for_term(client: httpx.AsyncClient, term: str) -> Set[str]:
    """Combined helper to find an ID and then get its tastes."""
    qloo_id = await _find_qloo_id(client, term)
    if qloo_id:
        return await _get_tastes_for_entity(client, qloo_id)
    return set()

# --- Agent Tools (Using Corrected Functions) ---

async def _web_search_tool(query: str) -> Dict[str, Any]:
    """Performs a web search, summarizes results, and returns summary and sources."""
    logger.info(f"AGENT TOOL: Web Search with query: '{query}'")
    search_result = await web_search(query)
    summary = await _summarize_with_gemini(search_result['context_str'], query)
    return {"context_str": summary, "sources": search_result["sources"]}

async def _corporate_culture_tool(brand_name: str) -> Dict[str, Any]:
    """Researches the corporate culture, values, leadership, and workplace environment of a brand."""
    logger.info(f"AGENT TOOL: Corporate Culture search for brand: '{brand_name}'")
    query = f"corporate culture, values, leadership, and workplace environment for {brand_name}"
    search_result = await web_search(query)
    summary = await _summarize_with_gemini(search_result['context_str'], query)
    return {"context_str": summary, "sources": search_result["sources"]}

async def _financial_and_market_tool(brand_name: str) -> Dict[str, Any]:
    """Researches the financial profile, market position, and recent financial news of a brand."""
    logger.info(f"AGENT TOOL: Financial/Market search for brand: '{brand_name}'")
    query = f"financial profile, market position, revenue, and recent financial news for {brand_name}"
    search_result = await web_search(query)
    summary = await _summarize_with_gemini(search_result['context_str'], query)
    return {"context_str": summary, "sources": search_result["sources"]}


async def intelligent_cultural_analysis_tool(acquirer_brand_name: str, target_brand_name: str) -> Dict[str, Any]:
    logger.info(f"AGENT TOOL: INTELLIGENT Cultural Analysis for '{acquirer_brand_name}' vs '{target_brand_name}'")

    def _analyze_tastes(acquirer_tastes: Set[str], target_tastes: Set[str], method: str, proxies: dict) -> dict:
        shared_tastes = list(acquirer_tastes.intersection(target_tastes))
        union_size = len(acquirer_tastes.union(target_tastes))
        unique_to_acquirer = list(acquirer_tastes - target_tastes)
        unique_to_target = list(target_tastes - acquirer_tastes)

        culture_clashes = [
            {"topic": interest, "description": "The Acquirer's audience shows a strong affinity for this, a taste not shared by the Target's.", "severity": "MEDIUM"}
            for interest in unique_to_acquirer[:5]
        ] + [
            {"topic": interest, "description": "The Target's audience shows a strong affinity for this, a taste not shared by the Acquirer's.", "severity": "HIGH"}
            for interest in unique_to_target[:5]
        ]
        
        untapped_growths = [
            {"description": f"Both audiences show a strong affinity for '{interest}'.", "potential_impact_score": 9}
            for interest in shared_tastes[:5]
        ]

        return {
            "context_str": json.dumps({
                "affinity_overlap_score": round((len(shared_tastes) / union_size * 100), 1) if union_size > 0 else 0,
                "analysis_method": method,
                "analysis_proxies": proxies,
            }),
            "qloo_insights_for_stream": { 
                "shared": shared_tastes[:5], 
                "acquirer_unique": unique_to_acquirer[:5], 
                "target_unique": unique_to_target[:5] 
            },
            "culture_clashes": culture_clashes,
            "untapped_growths": untapped_growths,
        }

    timeout_config = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=30.0)
    async with httpx.AsyncClient(timeout=timeout_config) as client:
        acquirer_profile_result, target_profile_result = await asyncio.gather(
            _web_search_tool(f"famous products and cultural properties of {acquirer_brand_name}"),
            _web_search_tool(f"famous products and cultural properties of {target_brand_name}")
        )
            
        try:
            acquirer_proxies, target_proxies = await asyncio.gather(
                _extract_cultural_proxies(acquirer_profile_result['context_str'], acquirer_brand_name),
                _extract_cultural_proxies(target_profile_result['context_str'], target_brand_name)
            )
            
            acquirer_search_terms = list(set([acquirer_brand_name] + acquirer_proxies))
            target_search_terms = list(set([target_brand_name] + target_proxies))
            
            logger.info(f"Primary Analysis - Acquirer Terms: {acquirer_search_terms}")
            logger.info(f"Primary Analysis - Target Terms: {target_search_terms}")

            semaphore = asyncio.Semaphore(3)
            async def _get_tastes_with_semaphore(term):
                async with semaphore:
                    await asyncio.sleep(0.5) # Gentle delay
                    return await _get_tastes_for_term(client, term)

            acquirer_tasks = [_get_tastes_with_semaphore(term) for term in acquirer_search_terms]
            target_tasks = [_get_tastes_with_semaphore(term) for term in target_search_terms]
            
            primary_acquirer_results, primary_target_results = await asyncio.gather(
                asyncio.gather(*acquirer_tasks), asyncio.gather(*target_tasks)
            )
            
            aggregated_acquirer_tastes = set().union(*primary_acquirer_results)
            aggregated_target_tastes = set().union(*primary_target_results)

            if aggregated_acquirer_tastes and aggregated_target_tastes:
                logger.success("Primary analysis successful with aggregated proxy data.")
                analysis = _analyze_tastes(aggregated_acquirer_tastes, aggregated_target_tastes, "Intelligent Proxy", {"acquirer": acquirer_search_terms, "target": target_search_terms})
                return {**analysis, "sources": acquirer_profile_result.get('sources', []) + target_profile_result.get('sources', [])}

        except Exception as e:
            logger.error(f"Critical error in cultural analysis: {e}")

    logger.warning("Qloo API unavailable or returned no data. Falling back to web-search-based cultural analysis.")
    return await _web_search_cultural_fallback(acquirer_brand_name, target_brand_name, acquirer_profile_result, target_profile_result)
    
async def _web_search_cultural_fallback(acquirer_brand: str, target_brand: str, acquirer_profile: dict, target_profile: dict) -> Dict[str, Any]:
    """Fallback cultural analysis using only web search data when Qloo API fails."""
    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
        prompt = f"""
        Based on the following information about two companies, perform a cultural analysis for a potential acquisition.
        
        ACQUIRER: {acquirer_brand}
        Profile: {acquirer_profile.get('context_str', 'No data available')}
        
        TARGET: {target_brand}  
        Profile: {target_profile.get('context_str', 'No data available')}
        
        Provide a JSON response with:
        1. "affinity_overlap_score": A number from 0-100 representing how well you estimate the brands' cultures and target audiences align.
        2. "shared_affinities_top_5": A list of 5 shared cultural elements, values, or audience characteristics.
        3. "acquirer_unique_tastes_top_5": A list of 5 unique aspects of the acquirer's culture or audience.
        4. "target_unique_tastes_top_5": A list of 5 unique aspects of the target's culture or audience.
        5. "analysis_method": A string with the value "Web Search Fallback".
        
        Focus on cultural values, audience demographics, brand positioning, and market presence.
        """
        response = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
        analysis_data = json.loads(response.text)
        
        shared = analysis_data.get("shared_affinities_top_5", [])
        acquirer_unique = analysis_data.get("acquirer_unique_tastes_top_5", [])
        target_unique = analysis_data.get("target_unique_tastes_top_5", [])
        
        culture_clashes = [{"topic": item, "description": f"Unique cultural aspect of {acquirer_brand}", "severity": "MEDIUM"} for item in acquirer_unique[:3]] + \
                          [{"topic": item, "description": f"Unique cultural aspect of {target_brand}", "severity": "HIGH"} for item in target_unique[:3]]
        untapped_growths = [{"description": f"Both brands share '{item}' as a cultural element", "potential_impact_score": 7} for item in shared[:3]]
        
        return {
            "context_str": json.dumps(analysis_data),
            "qloo_insights_for_stream": {"shared": shared, "acquirer_unique": acquirer_unique, "target_unique": target_unique},
            "culture_clashes": culture_clashes,
            "untapped_growths": untapped_growths,
            "sources": acquirer_profile.get('sources', []) + target_profile.get('sources', [])
        }
    except Exception as e:
        logger.error(f"Web search fallback analysis failed: {e}")
        return {"context_str": json.dumps({"error": "Cultural analysis unavailable", "affinity_overlap_score": 0, "analysis_method": "Failed Fallback"}), "culture_clashes": [], "untapped_growths": [], "sources": []}

async def _persona_expansion_fallback(acquirer_brand: str, target_brand: str, acquirer_profile: dict, target_profile: dict) -> Dict[str, Any]:
    """Fallback for persona expansion using only web search data."""
    logger.warning("Qloo Persona analysis unavailable. Falling back to web-search-based expansion analysis.")
    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
        prompt = f"""
        Based on the provided company profiles, analyze the potential for audience expansion if the acquirer buys the target.

        ACQUIRER: {acquirer_brand}
        Profile: {acquirer_profile.get('context_str', 'No data available')}
        
        TARGET: {target_brand}  
        Profile: {target_profile.get('context_str', 'No data available')}

        Provide a JSON response with:
        1. "expansion_score": An estimated score (0-100) of how well the target's audience and products could be adopted by the acquirer's audience.
        2. "latent_synergies": A list of the top 3-5 specific products, services, or brand attributes from the target that are most likely to appeal to the acquirer's audience.
        3. "analysis": A brief text summary explaining your reasoning for the score and synergies.
        """
        response = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
        return {"context_str": response.text}
    except Exception as e:
        logger.error(f"Persona expansion fallback analysis failed: {e}")
        return {"context_str": json.dumps({"error": "Persona expansion analysis unavailable.", "expansion_score": 0, "latent_synergies": []})}

async def persona_expansion_tool(acquirer_brand_name: str, target_brand_name: str) -> Dict[str, Any]:
    logger.info(f"AGENT TOOL: PERSONA EXPANSION for '{acquirer_brand_name}' vs '{target_brand_name}'")

    timeout_config = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=30.0)
    async with httpx.AsyncClient(timeout=timeout_config) as client:
        acquirer_profile, target_profile = await asyncio.gather(
            _web_search_tool(f"famous products and cultural properties of {acquirer_brand_name}"),
            _web_search_tool(f"famous products and cultural properties of {target_brand_name}")
        )
        
        try:
            acquirer_proxies, target_proxies = await asyncio.gather(
                _extract_cultural_proxies(acquirer_profile['context_str'], acquirer_brand_name),
                _extract_cultural_proxies(target_profile['context_str'], target_brand_name)
            )
            acquirer_search_terms = list(set([acquirer_brand_name] + acquirer_proxies))
            target_search_terms = list(set([target_brand_name] + target_proxies))

            semaphore = asyncio.Semaphore(3)
            async def _get_id_with_semaphore(term: str):
                async with semaphore:
                    await asyncio.sleep(0.5)
                    return await _find_qloo_id(client, term)
            async def _get_tastes_with_semaphore(term: str):
                async with semaphore:
                    await asyncio.sleep(0.5)
                    return await _get_tastes_for_term(client, term)

            acquirer_id_tasks = [_get_id_with_semaphore(term) for term in acquirer_search_terms]
            target_taste_tasks = [_get_tastes_with_semaphore(term) for term in target_search_terms]

            acquirer_ids_list, target_tastes_list = await asyncio.gather(
                asyncio.gather(*acquirer_id_tasks), asyncio.gather(*target_taste_tasks)
            )
            acquirer_ids = [id for id in acquirer_ids_list if id]
            target_actual_tastes = set().union(*target_tastes_list)

            if not acquirer_ids or not target_actual_tastes:
                logger.warning("Could not find necessary Qloo data for persona expansion. Using fallback.")
                return await _persona_expansion_fallback(acquirer_brand_name, target_brand_name, acquirer_profile, target_profile)
            
            logger.info(f"Building Acquirer Persona from IDs: {acquirer_ids}")
            
            headers = {"x-api-key": settings.QLOO_API_KEY}
            params = {
                "signal.interests.entities": ",".join(acquirer_ids),
                "filter.type": "urn:tag",
                "take": 100
            }
            resp = await client.get(f"{QLOO_HACKATHON_BASE_URL}/v2/insights", params=params, headers=headers, timeout=30.0)
            
            if resp.status_code != 200:
                logger.warning(f"Persona insights call failed with status {resp.status_code}, using fallback.")
                return await _persona_expansion_fallback(acquirer_brand_name, target_brand_name, acquirer_profile, target_profile)

            persona_data = resp.json().get("results", {}).get("entities", [])
            acquirer_predicted_tastes = {item['name'] for item in persona_data if 'name' in item}
            
            latent_synergies = acquirer_predicted_tastes.intersection(target_actual_tastes)
            expansion_score = round((len(latent_synergies) / len(target_actual_tastes)) * 100, 1) if target_actual_tastes else 0
            
            result = {
                "expansion_score": expansion_score,
                "latent_synergies": list(latent_synergies)[:10],
                "analysis": f"The acquirer's audience shows a predicted affinity for {len(latent_synergies)} of the target's core cultural products, indicating a potential taste expansion score of {expansion_score}%.",
            }
            return {"context_str": json.dumps(result)}

        except Exception as e:
            logger.error(f"Critical error in persona expansion tool: {e}")
            return await _persona_expansion_fallback(acquirer_brand_name, target_brand_name, acquirer_profile, target_profile)


# --- The Stateful ReAct Agent ---
class AlloyReActAgent:
    PROMPT_TEMPLATE = """
    You are a sophisticated strategic analyst AI for a financial firm specializing in M&A cultural analysis.
    Your job is to execute a strategic sequence of tool calls to gather comprehensive data about two companies and their cultural overlap, synergies, and expansion potential.
    Do not synthesize or generate the final report yourself. Simply gather the data methodically and pass it to the 'finish' tool.

    **STRATEGIC ANALYSIS WORKFLOW:**
    1.  **Basic Profiling**: Use `web_search` for both the acquirer and target to get a general company profile.
    2.  **Corporate Culture**: Use `corporate_culture_tool` for both companies to understand their internal values and work environment.
    3.  **Financial Analysis**: Use `financial_and_market_tool` for both companies to assess their financial health and market position.
    4.  **Deep Cultural Analysis**: Use `intelligent_cultural_analysis_tool` once to perform a deep comparison using Qloo data. This is a critical step.
    5.  **Persona Expansion**: After the cultural analysis, use `persona_expansion_tool` once to analyze latent synergies and predictive growth.
    6.  **Finish**: Once all data is gathered, call the `finish` tool.

    **AVAILABLE TOOLS:**
    - `web_search(query: str)`: For general company profile research. Use a query like "Apple Inc. company profile".
    - `corporate_culture_tool(brand_name: str)`: To get specific information on a company's culture, values, and leadership.
    - `financial_and_market_tool(brand_name: str)`: To get specific information on a company's financial health and market position.
    - `intelligent_cultural_analysis_tool(acquirer_brand_name: str, target_brand_name: str)`: For deep cultural analysis.
    - `persona_expansion_tool(acquirer_brand_name: str, target_brand_name: str)`: For predictive analysis of latent synergies.
    - `finish(gathered_data: dict)`: Use this ONLY when all strategic analysis steps are complete.

    **RESPONSE FORMAT (JSON ONLY):**
    You MUST respond with a single JSON object containing a "thought" and an "action".
    
    Example:
    ```json
    {{
      "thought": "I have completed the basic profiling for the acquirer. Now I will do the same for the target.",
      "action": {{
        "tool_name": "web_search",
        "parameters": {{
          "query": "{target_brand} company profile"
        }}
      }}
    }}
    ```

    **CURRENT TASK:**
    Conduct a comprehensive strategic analysis for the acquisition of target **{target_brand}** by acquirer **{acquirer_brand}**.
    User-provided context: {user_context}

    **COMPLETED STEPS:**
    {completed_steps}
    
    **PREVIOUS ACTIONS LOG:**
    {scratchpad}

    Based on the completed steps and previous actions, what is the next logical strategic analysis action? Focus on completing the workflow systematically. Return ONLY the JSON object.
    """

    def __init__(self, acquirer_brand: str, target_brand: str, user_context: str | None = None):
        self.acquirer_brand = acquirer_brand
        self.target_brand = target_brand
        self.user_context = user_context or "None"
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
        self.completed_steps: Set[str] = set()
        self.scratchpad = "" 
        self.gathered_data = {} 
        self.final_data = None
        self.tools = {
            "web_search": _web_search_tool,
            "intelligent_cultural_analysis_tool": intelligent_cultural_analysis_tool,
            "persona_expansion_tool": persona_expansion_tool,
            "corporate_culture_tool": _corporate_culture_tool,
            "financial_and_market_tool": _financial_and_market_tool
        }
        self.all_sources: Dict[str, List[Dict[str, str]]] = {
            'acquirer_sources': [], 'target_sources': [], 'search_sources': [],
            'acquirer_culture_sources': [], 'target_culture_sources': [],
            'acquirer_financial_sources': [], 'target_financial_sources': []
        }

    def _build_prompt(self) -> str:
        completed_steps_str = "\n".join(f"- {step}" for step in sorted(list(self.completed_steps))) or "None"
        scratchpad_log = "\n".join(self.scratchpad.splitlines()[-10:])
        return self.PROMPT_TEMPLATE.format(
            acquirer_brand=self.acquirer_brand,
            target_brand=self.target_brand,
            user_context=self.user_context,
            completed_steps=completed_steps_str,
            scratchpad=scratchpad_log
        )

    async def run_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        max_turns = 12
        for i in range(max_turns):
            yield {"status": "thinking", "message": f"Strategic analysis step {i+1}/{max_turns}"}
            
            prompt = self._build_prompt()
            response_text = await self._get_llm_response(prompt)
            
            try:
                response_json = json.loads(response_text)
                thought = response_json.get("thought", "No thought provided.")
                action_json = response_json.get("action", {})
                yield {"status": "thought", "message": thought}
                yield {"status": "action", "payload": action_json}
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(f"Agent response was not valid JSON: {e}. Raw response: {response_text}")
                observation = f"Error: The previous response was not valid JSON. Correct the format. Error: {e}"
                self.scratchpad += f"\n**Observation**: {observation}"
                continue

            tool_name, params = action_json.get("tool_name"), action_json.get("parameters", {})
            
            if not tool_name:
                observation = "Error: Your action JSON is missing the 'tool_name' key."
            elif tool_name == "finish":
                self.final_data = self.gathered_data
                yield {"status": "complete"}
                return
            elif tool_name not in self.tools:
                observation = f"Error: Unknown tool '{tool_name}'."
            else:
                try:
                    tool_function = self.tools[tool_name]
                    tool_result = await tool_function(**params)
                    
                    observation = tool_result.get('context_str', f"Tool {tool_name} ran successfully.")
                    sources = tool_result.get('sources', [])

                    if tool_name == "intelligent_cultural_analysis_tool" and "qloo_insights_for_stream" in tool_result:
                        yield {"status": "qloo_insight", "payload": {"type": "cultural_analysis", **tool_result["qloo_insights_for_stream"]}}

                    # --- State and Data Management ---
                    query = params.get('query', '').lower()
                    brand_name_param = params.get('brand_name', '')
                    is_acquirer = self.acquirer_brand.lower() in query or self.acquirer_brand == brand_name_param
                    is_target = self.target_brand.lower() in query or self.target_brand == brand_name_param

                    if tool_name == "web_search":
                        if is_acquirer:
                            self.completed_steps.add("searched_acquirer_profile")
                            self.gathered_data['acquirer_profile'] = observation
                            self.all_sources['acquirer_sources'].extend(sources)
                        elif is_target:
                            self.completed_steps.add("searched_target_profile")
                            self.gathered_data['target_profile'] = observation
                            self.all_sources['target_sources'].extend(sources)
                    elif tool_name == "corporate_culture_tool":
                        if is_acquirer:
                            self.completed_steps.add("searched_acquirer_culture")
                            self.gathered_data['acquirer_culture_profile'] = observation
                            self.all_sources['acquirer_culture_sources'].extend(sources)
                        elif is_target:
                            self.completed_steps.add("searched_target_culture")
                            self.gathered_data['target_culture_profile'] = observation
                            self.all_sources['target_culture_sources'].extend(sources)
                    elif tool_name == "financial_and_market_tool":
                        if is_acquirer:
                            self.completed_steps.add("searched_acquirer_financial")
                            self.gathered_data['acquirer_financial_profile'] = observation
                            self.all_sources['acquirer_financial_sources'].extend(sources)
                        elif is_target:
                            self.completed_steps.add("searched_target_financial")
                            self.gathered_data['target_financial_profile'] = observation
                            self.all_sources['target_financial_sources'].extend(sources)
                    elif tool_name == "intelligent_cultural_analysis_tool":
                        self.completed_steps.add("performed_intelligent_qloo_analysis")
                        self.all_sources['search_sources'].extend(sources)
                        try:
                            self.gathered_data['qloo_analysis'] = json.loads(observation)
                            self.gathered_data['culture_clashes'] = tool_result.get('culture_clashes', [])
                            self.gathered_data['untapped_growths'] = tool_result.get('untapped_growths', [])
                        except (json.JSONDecodeError, TypeError): self.gathered_data['qloo_analysis'] = {"error": observation}
                    elif tool_name == "persona_expansion_tool":
                        self.completed_steps.add("performed_persona_expansion")
                        try: self.gathered_data['persona_expansion'] = json.loads(observation)
                        except (json.JSONDecodeError, TypeError): self.gathered_data['persona_expansion'] = {"error": observation}
                    
                    for source in sources: yield {"status": "source", "payload": source}

                except Exception as e:
                    logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
                    observation = f"Error: {e}"

            self.scratchpad += f"\nAction: {json.dumps(action_json)}\nObservation: {observation}"
            yield {"status": "observation", "message": f"Completed {tool_name}"}

        logger.warning("Agent exceeded maximum turns.")
        self.final_data = self.gathered_data
        yield {"status": "complete"}

    async def _get_llm_response(self, prompt) -> str:
        try:
            generation_config = {"response_mime_type": "application/json"}
            response = await self.model.generate_content_async(prompt, generation_config=generation_config)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return json.dumps({"thought": "A critical error occurred with the LLM. I must finish now.", "action": {"tool_name": "finish", "parameters": {"gathered_data": self.gathered_data}}})