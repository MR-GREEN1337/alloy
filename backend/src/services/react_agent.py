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
        # CORE FIX: Generalize the prompt to work for more than just media companies.
        prompt = f"""
        Based *only* on the following text about '{brand_name}', identify the 3 to 5 most famous and culturally significant properties, products, shows, or public figures associated with them.
        These items will be used as proxies to understand the brand's cultural footprint.

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
    """Finds the Qloo ID and canonical name for any cultural entity."""
    headers = {"x-api-key": settings.QLOO_API_KEY}
    entity_variations = list(set([
        entity_name,
        entity_name.title(),
        entity_name.capitalize(),
    ]))

    for variation in entity_variations:
        if not variation: continue
        try:
            # Search across multiple relevant categories
            search_payload = {"query": variation, "filter": {"type": ["urn:entity:movie", "urn:entity:tv_show", "urn:entity:brand", "urn:entity:person", "urn:entity:music_track"]}, "take": 1}
            search_url = "https://hackathon.api.qloo.com/v2/search"
            resp = await client.post(search_url, json=search_payload, headers=headers)
            if resp.status_code != 200: continue
            results = resp.json().get("data", [])
            if results:
                qloo_id, found_name = results[0].get("id"), results[0].get("name")
                logger.success(f"Found Qloo match for '{variation}': '{found_name}' (ID: {qloo_id})")
                return qloo_id, found_name
        except Exception:
            logger.warning(f"Qloo ID search failed for variation '{variation}'.")
    return None

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

# --- THE FIX: Create a helper function for concurrent execution ---
async def _get_tastes_for_term(client: httpx.AsyncClient, term: str) -> Set[str]:
    """Finds Qloo ID for a term and returns a set of its audience tastes."""
    qloo_info = await _find_qloo_id(client, term)
    if qloo_info:
        tastes = await _get_qloo_tastes(client, qloo_info[0])
        return {t['name'] for t in tastes if 'name' in t}
    return set()

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

    # CORE FIX: Create a hybrid search list. Always include the original brand name as a fallback.
    acquirer_search_terms = list(set([acquirer_brand_name] + acquirer_proxies))
    target_search_terms = list(set([target_brand_name] + target_proxies))
    
    logger.info(f"Acquirer search terms for Qloo: {acquirer_search_terms}")
    logger.info(f"Target search terms for Qloo: {target_search_terms}")

    # --- THE FIX: Execute all Qloo API calls concurrently ---
    async with httpx.AsyncClient(timeout=45.0) as client:
        # Create a list of tasks for all acquirer terms
        acquirer_tasks = [_get_tastes_for_term(client, term) for term in acquirer_search_terms]
        # Create a list of tasks for all target terms
        target_tasks = [_get_tastes_for_term(client, term) for term in target_search_terms]

        # Run all tasks in parallel
        logger.info(f"Running {len(acquirer_tasks) + len(target_tasks)} Qloo API calls concurrently...")
        acquirer_results, target_results = await asyncio.gather(
            asyncio.gather(*acquirer_tasks),
            asyncio.gather(*target_tasks)
        )
        logger.success("All Qloo API calls completed.")

    # Flatten the list of sets into a single set of tastes for each brand
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
    # CORE FIX: The logic here was bugged, subtracting a set from itself.
    unique_to_target = list(aggregated_target_tastes - aggregated_acquirer_tastes)

    culture_clashes = []
    for interest in unique_to_acquirer[:5]:
        culture_clashes.append({"topic": interest, "description": "The Acquirer's audience ecosystem shows a strong affinity for this, a taste not shared by the Target's.", "severity": "MEDIUM"})
    for interest in unique_to_target[:5]:
        culture_clashes.append({"topic": interest, "description": "The Target's audience ecosystem shows a strong affinity for this, a taste not shared by the Acquirer's.", "severity": "HIGH"})
        
    untapped_growths = []
    for interest in shared_tastes[:5]:
        untapped_growths.append({"description": f"Both audience ecosystems show a strong affinity for '{interest}'. This shared passion could be a key pillar for joint marketing campaigns.", "potential_impact_score": 8})

    # THE FIX: Add a new key to the return value specifically for streaming to the frontend.
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

# --- The Stateful ReAct Agent ---
class AlloyReActAgent:
    PROMPT_TEMPLATE = """
    You are a data-gathering AI assistant for a financial firm.
    Your only job is to execute a sequence of tool calls to gather information about two companies and their cultural overlap.
    Do not synthesize, analyze, or generate the final report yourself. Simply gather the data and pass it to the 'finish' tool.

    **TOOLS:**
    - `web_search(query: str)`: For general company profile research.
    - `corporate_culture_tool(brand_name: str)`: To get specific information on a company's culture, values, and leadership.
    - `financial_and_market_tool(brand_name: str)`: To get specific information on a company's financial health and market position.
    - `intelligent_cultural_analysis_tool(acquirer_brand_name: str, target_brand_name: str)`: For deep cultural analysis, finding clashes, and growth opportunities. THIS IS THE PRIMARY TOOL FOR CULTURAL DATA.
    - `finish(gathered_data: dict)`: Use this ONLY when all data gathering steps are complete. The `gathered_data` parameter must be a JSON object containing keys for acquirer/target profiles, culture profiles, financial profiles, and the qloo analysis.

    **RESPONSE FORMAT (JSON ONLY):**
    You MUST respond with a single JSON object containing a "thought" and an "action".
    The "action" MUST be an object with "tool_name" and "parameters".
    
    Example:
    ```json
    {{
      "thought": "I need to get the general company profile for the acquirer.",
      "action": {{
        "tool_name": "web_search",
        "parameters": {{
          "query": "{acquirer_brand} company profile"
        }}
      }}
    }}
    ```

    **CURRENT TASK:**
    Gather data for a report on the acquisition of target **{target_brand}** by acquirer **{acquirer_brand}**.
    User-provided context: {user_context}

    **COMPLETED STEPS:**
    {completed_steps}
    
    **PREVIOUS ACTIONS LOG:**
    {scratchpad}

    Based on the completed steps and previous actions, what is the next logical data-gathering action? Return ONLY the JSON object.
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
        max_turns = 10 
        for i in range(max_turns):
            yield {"status": "thinking", "message": f"Agent reasoning (Step {i+1}/{max_turns})"}
            
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
                # CORE FIX: The agent should pass its internally gathered data to the finish tool.
                self.final_data = self.gathered_data
                yield {"status": "complete"}
                return
            elif tool_name not in self.tools:
                observation = f"Error: Unknown tool '{tool_name}'."
            else:
                try:
                    tool_result = await self.tools[tool_name](**params)
                    observation = tool_result.get('context_str', f"Tool {tool_name} ran but provided no context.")
                    sources = tool_result.get('sources', [])
                    
                    # CORE FIX: Explicitly check params to determine the target and data key.
                    # This is far more robust than parsing the query string.
                    brand_name_param = params.get('brand_name') or params.get('acquirer_brand_name')
                    is_acquirer = brand_name_param == self.acquirer_brand
                    is_target = brand_name_param == self.target_brand
                    
                    if tool_name == "web_search":
                        if is_acquirer:
                            self.completed_steps.add("searched_acquirer_profile")
                            self.gathered_data['acquirer_profile'] = observation
                            self.all_sources['acquirer_sources'].extend(sources)
                        # The query could be for the target brand
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

                    elif tool_name == "intelligent_cultural_analysis_tool":
                        self.completed_steps.add("performed_intelligent_qloo_analysis")
                        self.all_sources['search_sources'].extend(sources) # Add sources from proxy search
                        
                        # THE FIX: If the tool provides specific insights for streaming, yield them now.
                        if 'qloo_insights_for_stream' in tool_result:
                            yield {
                                "status": "qloo_insight",
                                "payload": tool_result['qloo_insights_for_stream']
                            }
                        
                        try:
                            self.gathered_data['qloo_analysis'] = json.loads(observation)
                            self.gathered_data['culture_clashes'] = tool_result.get('culture_clashes', [])
                            self.gathered_data['untapped_growths'] = tool_result.get('untapped_growths', [])
                        except (json.JSONDecodeError, TypeError):
                            self.gathered_data['qloo_analysis'] = {"error": observation}
                            self.gathered_data['culture_clashes'] = []
                            self.gathered_data['untapped_growths'] = []

                    for source in sources:
                        yield {"status": "source", "payload": source}

                except Exception as e:
                    logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
                    observation = f"Error: {e}"

            self.scratchpad += f"\nAction: {json.dumps(action_json)}\nObservation: {observation}"
            yield {"status": "observation", "message": f"Observation from {tool_name}"}

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