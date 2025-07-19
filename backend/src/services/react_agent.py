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


async def _find_qloo_id(client: httpx.AsyncClient, entity_name: str) -> Optional[Tuple[str, str]]:
    """Finds the Qloo ID and canonical name for any cultural entity with improved search categories and logging."""
    headers = {"x-api-key": settings.QLOO_API_KEY}
    entity_variations = list(set([
        entity_name,
        entity_name.title(),
        entity_name.capitalize(),
    ]))

    for variation in entity_variations:
        if not variation: continue
        try:
            # Broadened search categories for better match probability
            search_payload = {
                "query": variation, 
                "filter": {
                    "type": [
                        "urn:entity:movie", 
                        "urn:entity:tv_show", 
                        "urn:entity:brand", 
                        "urn:entity:person", 
                        "urn:entity:music_track", 
                        "urn:entity:music_artist", 
                        "urn:entity:podcast",
                        "urn:entity:video_game",
                        "urn:entity:book"
                    ]
                }, 
                "take": 1
            }
            search_url = "https://hackathon.api.qloo.com/v2/search"
            resp = await client.post(search_url, json=search_payload, headers=headers)
            
            if resp.status_code != 200:
                logger.warning(f"Qloo search for '{variation}' returned status {resp.status_code}.")
                continue

            results = resp.json().get("data", [])
            if results:
                qloo_id, found_name = results[0].get("id"), results[0].get("name")
                logger.success(f"Found Qloo match for '{variation}': '{found_name}' (ID: {qloo_id})")
                return qloo_id, found_name
        except Exception as e:
            logger.error(f"Qloo ID search failed for variation '{variation}': {e}")
            
    logger.warning(f"Could not find any Qloo entity for search term: '{entity_name}'")
    return None

async def _get_tastes_for_term(client: httpx.AsyncClient, term: str) -> Tuple[Optional[str], Set[str]]:
    """Finds Qloo ID for a term and returns a tuple of (ID, set of its audience tastes)."""
    qloo_info = await _find_qloo_id(client, term)
    if qloo_info:
        qloo_id = qloo_info[0]
        tastes = await _get_qloo_tastes(client, qloo_id)
        if tastes:
            logger.info(f"Found {len(tastes)} tastes for '{term}' (ID: {qloo_id})")
        else:
            logger.warning(f"Found Qloo ID for '{term}' but it has no taste data.")
        return qloo_id, {t['name'] for t in tastes if 'name' in t}
    return None, set()

async def _get_qloo_tastes(client: httpx.AsyncClient, qloo_id: str) -> List[Dict]:
    """Fetches the top 50 tastes for a given Qloo ID."""
    try:
        headers = {"x-api-key": settings.QLOO_API_KEY}
        insights_payload = {"id": [qloo_id], "take": 50}
        insights_url = "https://hackathon.api.qloo.com/v2/insights"
        resp = await client.post(insights_url, json=insights_payload, headers=headers)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception as e:
        logger.error(f"Failed to fetch Qloo tastes for ID {qloo_id}: {e}")
        return []


# --- Agent Tools ---

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
    """
    Performs a deep, intelligent cultural comparison by finding representative cultural products (proxies) for each brand,
    aggregating their audience tastes from Qloo, and then performing a comparative analysis.
    """
    logger.info(f"AGENT TOOL: INTELLIGENT Cultural Analysis for '{acquirer_brand_name}' vs '{target_brand_name}'")

    # 1. Get profiles to find proxies
    acquirer_profile_result = await _web_search_tool(f"What are the most famous and representative movies, characters, products, or public figures of the company or brand '{acquirer_brand_name}'?")
    target_profile_result = await _web_search_tool(f"What are the most famous and representative movies, shows, or public figures from the company or brand '{target_brand_name}'?")
    
    # 2. Extract proxies
    acquirer_proxies = await _extract_cultural_proxies(acquirer_profile_result['context_str'], acquirer_brand_name)
    target_proxies = await _extract_cultural_proxies(target_profile_result['context_str'], target_brand_name)

    # Always include the original brand name as a fallback - this integrates the fallback logic directly
    acquirer_search_terms = list(set([acquirer_brand_name] + acquirer_proxies))
    target_search_terms = list(set([target_brand_name] + target_proxies))
    
    logger.info(f"Acquirer search terms for Qloo: {acquirer_search_terms}")
    logger.info(f"Target search terms for Qloo: {target_search_terms}")

    async with httpx.AsyncClient(timeout=45.0) as client:
        semaphore = asyncio.Semaphore(3) # Limit to 3 concurrent requests at a time

        async def get_tastes_with_semaphore(term):
            async with semaphore:
                # Add a small delay to be even more respectful to the API
                await asyncio.sleep(0.1) 
                return await _get_tastes_for_term_set(client, term)

        async def _get_tastes_for_term_set(term: str) -> Set[str]:
            """Helper to find Qloo ID for a term and return a set of its audience tastes."""
            qloo_info = await _find_qloo_id(client, term)
            if qloo_info:
                tastes = await _get_qloo_tastes(client, qloo_info[0])
                return {t['name'] for t in tastes if 'name' in t}
            return set()

        acquirer_tasks = [get_tastes_with_semaphore(term) for term in acquirer_search_terms]
        target_tasks = [get_tastes_with_semaphore(term) for term in target_search_terms]

        logger.info(f"Running {len(acquirer_tasks) + len(target_tasks)} Qloo API calls concurrently...")
        acquirer_results, target_results = await asyncio.gather(
            asyncio.gather(*acquirer_tasks),
            asyncio.gather(*target_tasks)
        )
        logger.success("All Qloo API calls completed.")

    aggregated_acquirer_tastes = set().union(*acquirer_results)
    aggregated_target_tastes = set().union(*target_results)

    if not aggregated_acquirer_tastes or not aggregated_target_tastes:
        error_msg = "Error: Could not retrieve any taste data from Qloo for the brands or their cultural products."
        logger.error(error_msg)
        return {"context_str": error_msg, "culture_clashes": [], "untapped_growths": []}
    
    # 4. Perform comparison on aggregated sets
    shared_tastes = list(aggregated_acquirer_tastes.intersection(aggregated_target_tastes))
    union_size = len(aggregated_acquirer_tastes.union(aggregated_target_tastes))
    unique_to_acquirer = list(aggregated_acquirer_tastes - aggregated_target_tastes)
    # Fixed bug: correctly calculate unique_to_target
    unique_to_target = list(aggregated_target_tastes - aggregated_acquirer_tastes)

    culture_clashes = []
    for interest in unique_to_acquirer[:5]:
        culture_clashes.append({"topic": interest, "description": "The Acquirer's audience ecosystem shows a strong affinity for this, a taste not shared by the Target's.", "severity": "MEDIUM"})
    for interest in unique_to_target[:5]:
        culture_clashes.append({"topic": interest, "description": "The Target's audience ecosystem shows a strong affinity for this, a taste not shared by the Acquirer's.", "severity": "HIGH"})
        
    untapped_growths = []
    for interest in shared_tastes[:5]:
        untapped_growths.append({"description": f"Both audience ecosystems show a strong affinity for '{interest}'. This shared passion could be a key pillar for joint marketing campaigns.", "potential_impact_score": 8})

    # New key for streaming granular insights to the frontend
    qloo_insights_for_stream = {
        "shared": shared_tastes[:5],
        "acquirer_unique": unique_to_acquirer[:5],
        "target_unique": unique_to_target[:5]
    }

    # 5. Return the full analysis object
    return {
        "context_str": json.dumps({
            "affinity_overlap_score": round((len(shared_tastes) / union_size * 100), 2) if union_size > 0 else 0,
            "shared_affinities_top_5": shared_tastes[:5],
            "acquirer_unique_tastes_top_5": unique_to_acquirer[:5],
            "target_unique_tastes_top_5": unique_to_target[:5],
            "analysis_proxies": {"acquirer": acquirer_search_terms, "target": target_search_terms}
        }),
        "qloo_insights_for_stream": qloo_insights_for_stream,
        "culture_clashes": culture_clashes,
        "untapped_growths": untapped_growths,
        "sources": acquirer_profile_result.get('sources', []) + target_profile_result.get('sources', [])
    }

async def persona_expansion_tool(acquirer_brand_name: str, target_brand_name: str) -> Dict[str, Any]:
    """
    NEW TOOL: Analyzes the latent synergy between two brands using Qloo's Persona API.
    It predicts what the acquirer's audience might like and sees if the target already offers it.
    This finds latent synergies by comparing predicted tastes against actual target tastes.
    """
    logger.info(f"AGENT TOOL: PERSONA EXPANSION for '{acquirer_brand_name}' vs '{target_brand_name}'")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Get cultural proxies and their Qloo IDs for both brands
        acquirer_profile = await _web_search_tool(f"famous products and cultural properties of {acquirer_brand_name}")
        acquirer_proxies = await _extract_cultural_proxies(acquirer_profile['context_str'], acquirer_brand_name)
        acquirer_search_terms = list(set([acquirer_brand_name] + acquirer_proxies))

        target_profile = await _web_search_tool(f"famous products and cultural properties of {target_brand_name}")
        target_proxies = await _extract_cultural_proxies(target_profile['context_str'], target_brand_name)
        target_search_terms = list(set([target_brand_name] + target_proxies))

        # Concurrently find IDs and actual tastes for both
        acquirer_tasks = [_get_tastes_for_term(client, term) for term in acquirer_search_terms]
        target_tasks = [_get_tastes_for_term(client, term) for term in target_search_terms]
        
        acquirer_results, target_results = await asyncio.gather(
            asyncio.gather(*acquirer_tasks),
            asyncio.gather(*target_tasks)
        )

        acquirer_ids = [res[0] for res in acquirer_results if res[0]]
        target_actual_tastes = set().union(*(res[1] for res in target_results))
        
        if not acquirer_ids or not target_actual_tastes:
            return {"context_str": json.dumps({
                "error": "Could not build a core persona or get target tastes for expansion analysis.",
                "expansion_score": 0,
                "latent_synergies": []
            })}

        # Step 2: Use Acquirer IDs to get predicted tastes from Persona API
        logger.info(f"Building Acquirer Persona from IDs: {acquirer_ids}")
        persona_payload = {
            "include": {"id": acquirer_ids}, 
            "category": ["tv_show", "movie", "brand", "person", "music_artist", "video_game"], 
            "take": 100
        }
        headers = {"x-api-key": settings.QLOO_API_KEY}
        persona_url = "https://hackathon.api.qloo.com/v2/persona/tastes"
        
        try:
            resp = await client.post(persona_url, json=persona_payload, headers=headers)
            resp.raise_for_status()
            persona_tastes = resp.json().get("data", [])
            acquirer_predicted_tastes = {t['name'] for t in persona_tastes if 'name' in t}
            logger.success(f"Successfully fetched {len(acquirer_predicted_tastes)} predicted tastes for acquirer persona.")
        except Exception as e:
            logger.error(f"Persona API call failed: {e}")
            return {"context_str": json.dumps({
                "error": "Failed to get predicted tastes from Qloo Persona API.",
                "expansion_score": 0,
                "latent_synergies": []
            })}
        
        # Step 3: Find the latent synergy
        latent_synergy = acquirer_predicted_tastes.intersection(target_actual_tastes)
        
        # Step 4: Calculate the score and formulate the result
        expansion_score = round((len(latent_synergy) / len(target_actual_tastes)) * 100, 2) if target_actual_tastes else 0
        
        result = {
            "expansion_score": expansion_score,
            "latent_synergies": list(latent_synergy)[:10],
            "analysis": (
                f"The acquirer's audience shows a strong predicted affinity for {len(latent_synergy)} of the target's core cultural products. "
                f"This indicates an expansion potential of {expansion_score}%, suggesting {'high' if expansion_score > 15 else 'moderate' if expansion_score > 5 else 'low'} probability of successful audience adoption and cross-promotion."
            ),
            "acquirer_predicted_tastes_count": len(acquirer_predicted_tastes),
            "target_actual_tastes_count": len(target_actual_tastes),
            "synergy_count": len(latent_synergy)
        }

        return {"context_str": json.dumps(result)}

# --- The Stateful ReAct Agent ---
class AlloyReActAgent:
    PROMPT_TEMPLATE = """
    You are a sophisticated strategic analyst AI for a financial firm specializing in M&A cultural analysis.
    Your job is to execute a strategic sequence of tool calls to gather comprehensive data about two companies and their cultural overlap, synergies, and expansion potential.
    Do not synthesize or generate the final report yourself. Simply gather the data methodically and pass it to the 'finish' tool.

    **STRATEGIC ANALYSIS WORKFLOW:**
    1. Basic company profiling (web search for both companies)
    2. Corporate culture analysis (for both companies)
    3. Financial and market analysis (for both companies)
    4. Deep cultural analysis using Qloo data (intelligent_cultural_analysis_tool)
    5. Predictive expansion analysis using Persona API (persona_expansion_tool)

    **AVAILABLE TOOLS:**
    - `web_search(query: str)`: For general company profile research.
    - `corporate_culture_tool(brand_name: str)`: To get specific information on a company's culture, values, and leadership.
    - `financial_and_market_tool(brand_name: str)`: To get specific information on a company's financial health and market position.
    - `intelligent_cultural_analysis_tool(acquirer_brand_name: str, target_brand_name: str)`: For deep cultural analysis, finding clashes, and growth opportunities using Qloo data.
    - `persona_expansion_tool(acquirer_brand_name: str, target_brand_name: str)`: For predictive analysis of latent synergies using Qloo's Persona API. Use this AFTER cultural analysis.
    - `finish(gathered_data: dict)`: Use this ONLY when all strategic analysis steps are complete. The `gathered_data` parameter must be a JSON object containing keys for all previous analysis steps.

    **RESPONSE FORMAT (JSON ONLY):**
    You MUST respond with a single JSON object containing a "thought" and an "action".
    
    Example:
    ```json
    {{
      "thought": "I have completed the cultural analysis and found significant overlap. Now I should perform the persona expansion analysis to identify latent synergies and predictive growth opportunities.",
      "action": {{
        "tool_name": "persona_expansion_tool",
        "parameters": {{
          "acquirer_brand_name": "{acquirer_brand}",
          "target_brand_name": "{target_brand}"
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
        """Builds the prompt with the current state of completed steps."""
        completed_steps_str = "\n".join(f"- {step}" for step in sorted(list(self.completed_steps))) or "None"
        # Truncate scratchpad to keep the prompt within reasonable size limits
        scratchpad_log = "\n".join(self.scratchpad.splitlines()[-10:])
        return self.PROMPT_TEMPLATE.format(
            acquirer_brand=self.acquirer_brand,
            target_brand=self.target_brand,
            user_context=self.user_context,
            completed_steps=completed_steps_str,
            scratchpad=scratchpad_log
        )

    async def run_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        max_turns = 12  # Increased to accommodate the new tool
        for i in range(max_turns):
            yield {"status": "thinking", "message": f"Strategic analysis step {i+1}/{max_turns}"}
            
            prompt = self._build_prompt()
            response_text = await self._get_llm_response(prompt)
            
            try:
                # Parse the entire response as a JSON object
                response_json = json.loads(response_text)
                thought = response_json.get("thought", "No thought provided.")
                action_json = response_json.get("action", {})
                yield {"status": "thought", "message": thought}
                yield {"status": "action", "payload": action_json}
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(f"Agent response was not valid JSON: {e}. Raw response: {response_text}")
                yield {"status": "error", "message": f"Agent produced an invalid response: {e}"}
                observation = f"Error: The previous response was not a valid JSON object with 'thought' and 'action' keys. Please correct the format. The error was: {e}"
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
                    
                    observation = tool_result.get('context_str', f"Tool {tool_name} ran but provided no context.")
                    sources = tool_result.get('sources', [])

                    # Enhanced data flow: yield qloo_insight events for frontend
                    if tool_name == "intelligent_cultural_analysis_tool" and "qloo_insights_for_stream" in tool_result:
                        qloo_insights = tool_result["qloo_insights_for_stream"]
                        yield {
                            "status": "qloo_insight", 
                            "payload": {
                                "type": "cultural_analysis",
                                "shared_tastes": qloo_insights.get("shared", []),
                                "acquirer_unique_tastes": qloo_insights.get("acquirer_unique", []),
                                "target_unique_tastes": qloo_insights.get("target_unique", [])
                            }
                        }

                    brand_name_param = params.get('brand_name') or params.get('acquirer_brand_name')
                    is_acquirer = brand_name_param == self.acquirer_brand
                    is_target = brand_name_param == self.target_brand
                    
                    if tool_name == "intelligent_cultural_analysis_tool":
                        self.completed_steps.add("performed_intelligent_qloo_analysis")
                        self.all_sources['search_sources'].extend(sources)
                        try:
                            self.gathered_data['qloo_analysis'] = json.loads(observation)
                            self.gathered_data['culture_clashes'] = tool_result.get('culture_clashes', [])
                            self.gathered_data['untapped_growths'] = tool_result.get('untapped_growths', [])
                        except (json.JSONDecodeError, TypeError):
                            self.gathered_data['qloo_analysis'] = {"error": observation}
                    
                    elif tool_name == "persona_expansion_tool":
                        self.completed_steps.add("performed_persona_expansion")
                        try:
                             self.gathered_data['persona_expansion'] = json.loads(observation)
                        except (json.JSONDecodeError, TypeError):
                            self.gathered_data['persona_expansion'] = {"error": observation}
                    
                    elif tool_name == "web_search":
                        if is_acquirer:
                            self.completed_steps.add("searched_acquirer_profile")
                            self.gathered_data['acquirer_profile'] = observation
                            self.all_sources['acquirer_sources'].extend(sources)
                        elif self.target_brand in params.get('query', ''):
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

                    for source in sources:
                        yield {"status": "source", "payload": source}

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
            # Enforce JSON output from the model
            generation_config = {"response_mime_type": "application/json"}
            response = await self.model.generate_content_async(prompt, generation_config=generation_config)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            # Fallback to a finish action if the LLM fails
            finish_action = {
                "thought": "A critical error occurred with the LLM. I must finish now.",
                "action": {
                    "tool_name": "finish",
                    "parameters": {"gathered_data": self.gathered_data}
                }
            }
            return json.dumps(finish_action)