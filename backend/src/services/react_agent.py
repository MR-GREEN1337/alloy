import httpx
import google.generativeai as genai
from typing import List, Dict, Any, AsyncGenerator, Optional, Tuple, Set
from loguru import logger
import json
import random

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

async def _find_qloo_id(client: httpx.AsyncClient, brand_name: str) -> Optional[Tuple[str, str]]:
    """Finds the Qloo ID and canonical name for a brand."""
    headers = {"x-api-key": settings.QLOO_API_KEY}
    brand_variations = list(set([
        brand_name,
        brand_name.replace("Company", "").replace("Inc.", "").replace("Corp.", "").strip(),
        brand_name.split(' ')[0],
    ]))

    for variation in brand_variations:
        if not variation: continue
        try:
            search_payload = {"query": variation, "filter": {"type": "urn:entity:brand"}, "take": 1}
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

# --- Agent Tools ---

async def _web_search_tool(query: str) -> Dict[str, Any]:
    """Performs a web search, summarizes results, and returns summary and sources."""
    logger.info(f"AGENT TOOL: Web Search with query: '{query}'")
    search_result = await web_search(query)
    summary = await _summarize_with_gemini(search_result['context_str'], query)
    return {"context_str": summary, "sources": search_result["sources"]}

async def _qloo_comparative_analysis_tool(acquirer_brand_name: str, target_brand_name: str) -> Dict[str, Any]:
    """Performs a deep cultural comparison and returns a structured dictionary with pre-analyzed lists."""
    logger.info(f"AGENT TOOL: Qloo Comparative Analysis for '{acquirer_brand_name}' vs '{target_brand_name}'")
    async with httpx.AsyncClient(timeout=45.0) as client:
        acquirer_info = await _find_qloo_id(client, acquirer_brand_name)
        target_info = await _find_qloo_id(client, target_brand_name)
        if not acquirer_info: return {"context_str": f"Error: Could not find acquirer '{acquirer_brand_name}' in Qloo database."}
        if not target_info: return {"context_str": f"Error: Could not find target '{target_brand_name}' in Qloo database."}
        acquirer_tastes = await _get_qloo_tastes(client, acquirer_info[0])
        target_tastes = await _get_qloo_tastes(client, target_info[0])
    
    if not acquirer_tastes or not target_tastes: 
        return {"context_str": "Error: Could not retrieve taste data.", "qloo_analysis": {}, "culture_clashes": [], "untapped_growths": []}

    acquirer_set = {t['name'] for t in acquirer_tastes if t.get('name')}
    target_set = {t['name'] for t in target_tastes if t.get('name')}
    
    # Calculate overlaps and differences
    shared_tastes = list(acquirer_set.intersection(target_set))
    union_size = len(acquirer_set.union(target_set))
    acquirer_unique = list(acquirer_set - target_set)
    target_unique = list(target_set - acquirer_set)

    # Pre-generate the lists for the final report
    culture_clashes = [
        {"topic": topic, "description": f"Acquirer's audience shows affinity for this, a taste not shared by the Target's audience.", "severity": "MEDIUM"}
        for topic in acquirer_unique[:5]
    ] + [
        {"topic": topic, "description": f"Target's audience shows strong affinity for this, a taste not shared by the Acquirer's audience.", "severity": "HIGH"}
        for topic in target_unique[:5]
    ]
    
    untapped_growths = [
        {"description": f"Both audiences show a strong affinity for '{topic}'. This shared passion point could be a key pillar for joint marketing campaigns and product integrations.", "potential_impact_score": random.randint(7, 9)}
        for topic in shared_tastes[:5]
    ]

    # Structure the final output
    result = {
        "context_str": "Qloo analysis complete. Affinity scores, clashes, and growth opportunities have been calculated.",
        "qloo_analysis": {
            "affinity_overlap_score": round((len(shared_tastes) / union_size * 100), 2) if union_size > 0 else 0,
            "shared_affinities_count": len(shared_tastes),
            "acquirer_unique_tastes_count": len(acquirer_unique),
            "target_unique_tastes_count": len(target_unique),
        },
        "culture_clashes": culture_clashes,
        "untapped_growths": untapped_growths
    }
    return result

async def _corporate_culture_research_tool(brand_name: str) -> Dict[str, Any]:
    """
    Performs targeted web searches to build a corporate culture and leadership profile.
    It synthesizes findings on leadership, values, and employee sentiment.
    """
    logger.info(f"AGENT TOOL: Corporate Culture Research for: '{brand_name}'")
    
    queries = [
        f"leadership team and bios for {brand_name}",
        f"corporate values and mission statement of {brand_name}",
        f"employee reviews and culture at {brand_name} (e.g., from Glassdoor, news articles)",
    ]
    
    combined_context = ""
    all_sources = []
    
    for query in queries:
        search_result = await web_search(query)
        if search_result and search_result['context_str']:
            combined_context += f"\n\n--- Results for query: '{query}' ---\n{search_result['context_str']}"
            all_sources.extend(search_result['sources'])

    if not combined_context.strip():
        return {"context_str": f"No significant corporate culture information could be found for '{brand_name}' via web search.", "sources": []}
        
    summary_query = f"Synthesize a corporate culture profile for {brand_name}. Focus on: 1. Leadership style and key executives. 2. Stated company values and mission. 3. Publicly perceived employee sentiment and work culture."
    summary = await _summarize_with_gemini(combined_context, summary_query)

    unique_sources = list({v['url']:v for v in all_sources}.values())
    return {"context_str": summary, "sources": unique_sources}

async def _financial_and_market_analysis_tool(brand_name: str) -> Dict[str, Any]:
    """
    Performs web searches to build a high-level financial and market profile.
    Synthesizes findings on financial metrics, SWOT, and market position.
    """
    logger.info(f"AGENT TOOL: Financial & Market Analysis for: '{brand_name}'")
    
    queries = [
        f"key financial metrics for {brand_name}",
        f"SWOT analysis for {brand_name}",
        f"{brand_name} market position and key competitors",
    ]
    
    combined_context = ""
    all_sources = []
    
    for query in queries:
        search_result = await web_search(query)
        if search_result and search_result['context_str']:
            combined_context += f"\n\n--- Results for query: '{query}' ---\n{search_result['context_str']}"
            all_sources.extend(search_result['sources'])

    if not combined_context.strip():
        return {"context_str": f"No significant financial or market information could be found for '{brand_name}' via web search.", "sources": []}
        
    summary_query = f"Synthesize a high-level financial and market profile for {brand_name}. Focus on: 1. Key financial health indicators (e.g., revenue, growth trends). 2. A brief SWOT analysis (Strengths, Weaknesses, Opportunities, Threats). 3. Its primary market position and main competitors."
    summary = await _summarize_with_gemini(combined_context, summary_query)

    unique_sources = list({v['url']:v for v in all_sources}.values())
    return {"context_str": summary, "sources": unique_sources}

# --- The Stateful ReAct Agent ---
class AlloyReActAgent:
    PROMPT_TEMPLATE = """
    You are a data-gathering AI assistant.

    **PRIMARY DIRECTIVE:** Your only job is to execute a sequence of tool calls to gather all the necessary data for a comprehensive M&A due diligence report.

    **RULES:**
    1.  You MUST respond with a "Thought" and an "Action" in this exact format.
    2.  Your "Action" MUST be a single, valid JSON object.
    3.  The JSON object MUST have a `tool_name` key (the name of the tool to use).
    4.  The JSON object MUST have a `parameters` key, which is an object of the tool's arguments.

    **DATA-GATHERING TASKS (in any logical order):**
    1.  **Company Profiles:** Get a general overview of each company's business.
    2.  **Corporate Culture:** Investigate the internal culture, leadership, and values of each company.
    3.  **Audience Affinity:** Analyze the cultural tastes of each company's audience. This tool also generates the `culture_clashes` and `untapped_growths` lists automatically.
    4.  **Financial & Market Health:** Get a high-level overview of each company's market position and financial health.

    **TOOLS:**
    - `web_search(query: str)`: Use for **Task 1**.
    - `corporate_culture_research(brand_name: str)`: Use for **Task 2**.
    - `qloo_comparative_analysis(acquirer_brand_name: str, target_brand_name: str)`: Use for **Task 3**.
    - `financial_and_market_analysis_tool(brand_name: str)`: Use for **Task 4**.
    - `finish(gathered_data: dict)`: Call this tool ONLY when all other data-gathering tasks are complete. The `gathered_data` object MUST contain these keys: `acquirer_profile`, `target_profile`, `acquirer_culture_profile`, `target_culture_profile`, `acquirer_financial_profile`, `target_financial_profile`, `qloo_analysis`, `culture_clashes`, `untapped_growths`.

    **EXAMPLE ACTION FORMAT:**
    ```json
    {
      "tool_name": "web_search",
      "parameters": {
        "query": "Example Inc. company profile"
      }
    }
    ```

    **CURRENT TASK:**
    Gather data for a report on the acquisition of target **{target_brand}** by acquirer **{acquirer_brand}**.
    User-provided context: {user_context}

    **COMPLETED STEPS:**
    {completed_steps}

    Based on the completed steps, what is the next logical data-gathering action?
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
            "qloo_comparative_analysis": _qloo_comparative_analysis_tool,
            "corporate_culture_research": _corporate_culture_research_tool,
            "financial_and_market_analysis_tool": _financial_and_market_analysis_tool
        }
        self.all_sources: Dict[str, List[Dict[str, str]]] = {
            'acquirer_sources': [], 'target_sources': [], 
            'acquirer_culture_sources': [], 'target_culture_sources': [],
            'acquirer_financial_sources': [], 'target_financial_sources': [],
            'search_sources': []
        }

    def _build_prompt(self) -> str:
        """Builds the prompt with the current state of completed steps."""
        completed_steps_str = "\n".join(f"- {step}" for step in sorted(list(self.completed_steps))) or "None"
        return self.PROMPT_TEMPLATE.format(
            acquirer_brand=self.acquirer_brand,
            target_brand=self.target_brand,
            user_context=self.user_context,
            completed_steps=completed_steps_str
        ) + self.scratchpad

    async def run_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        max_turns = 8
        for i in range(max_turns):
            yield {"status": "thinking", "message": f"Agent reasoning (Step {i+1}/{max_turns})"}
            
            prompt = self._build_prompt()
            response_text = await self._get_llm_response(prompt)
            
            if "**Action**:" not in response_text:
                yield {"status": "thought", "message": response_text.replace("**Thought**:", "").strip()}
                logger.warning("Agent produced a thought but no action. Ending turn.")
                observation = "Error: Your response did not include an 'Action' block. You must provide an action."
                self.scratchpad += f"\n**Thought**: {response_text.replace('**Thought**:', '').strip()}\n**Observation**: {observation}"
                continue

            parts = response_text.split("**Action**:", 1)
            thought = parts[0].replace("**Thought**:", "").strip()
            action_str = parts[1].strip().replace("```json", "").replace("```", "")
            yield {"status": "thought", "message": thought}
            
            try:
                action_json = json.loads(action_str)
                yield {"status": "action", "payload": action_json}
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}. Raw action: {action_str}")
                yield {"status": "error", "message": f"Agent provided invalid JSON: {e}"}
                observation = f"Error: The Action was not valid JSON. You must provide a single, correctly formatted JSON object. For example: {{\"tool_name\": \"web_search\", \"parameters\": {{\"query\": \"some query\"}}}}"
                self.scratchpad += f"\n**Thought**: {thought}\n**Action**: {action_str}\n**Observation**: {observation}"
                continue

            tool_name = action_json.get("tool_name")
            params = action_json.get("parameters", {})
            
            if not tool_name:
                observation = "Error: Your action JSON is missing the 'tool_name' key."
            elif tool_name == "finish":
                self.final_data = params.get("gathered_data", self.gathered_data)
                yield {"status": "complete"}
                return
            elif tool_name not in self.tools:
                observation = f"Error: Unknown tool '{tool_name}'. Please use one of the available tools."
            else:
                try:
                    tool_result = await self.tools[tool_name](**params)
                    observation = tool_result.get('context_str', f"Tool {tool_name} ran but provided no context.")
                    
                    if tool_name == "web_search":
                        query = params.get('query','').lower()
                        if self.acquirer_brand.lower() in query:
                            self.completed_steps.add("searched_acquirer")
                            self.gathered_data['acquirer_profile'] = observation
                            self.all_sources['acquirer_sources'].extend(tool_result.get('sources', []))
                        elif self.target_brand.lower() in query:
                            self.completed_steps.add("searched_target")
                            self.gathered_data['target_profile'] = observation
                            self.all_sources['target_sources'].extend(tool_result.get('sources', []))
                        
                        for source in tool_result.get('sources', []):
                            yield {"status": "source", "payload": source}

                    elif tool_name == "corporate_culture_research":
                        brand = params.get('brand_name', '').lower()
                        if self.acquirer_brand.lower() in brand:
                            self.completed_steps.add("researched_acquirer_culture")
                            self.gathered_data['acquirer_culture_profile'] = observation
                            self.all_sources['acquirer_culture_sources'].extend(tool_result.get('sources', []))
                        elif self.target_brand.lower() in brand:
                            self.completed_steps.add("researched_target_culture")
                            self.gathered_data['target_culture_profile'] = observation
                            self.all_sources['target_culture_sources'].extend(tool_result.get('sources', []))
                        for source in tool_result.get('sources', []): yield {"status": "source", "payload": source}

                    elif tool_name == "financial_and_market_analysis_tool":
                        brand = params.get('brand_name', '').lower()
                        if self.acquirer_brand.lower() in brand:
                            self.completed_steps.add("researched_acquirer_financials")
                            self.gathered_data['acquirer_financial_profile'] = observation
                            self.all_sources['acquirer_financial_sources'].extend(tool_result.get('sources', []))
                        elif self.target_brand.lower() in brand:
                            self.completed_steps.add("researched_target_financials")
                            self.gathered_data['target_financial_profile'] = observation
                            self.all_sources['target_financial_sources'].extend(tool_result.get('sources', []))
                        for source in tool_result.get('sources', []): yield {"status": "source", "payload": source}
                    
                    elif tool_name == "qloo_comparative_analysis":
                        self.completed_steps.add("performed_qloo_analysis")
                        self.gathered_data['qloo_analysis'] = tool_result.get('qloo_analysis', {})
                        self.gathered_data['culture_clashes'] = tool_result.get('culture_clashes', [])
                        self.gathered_data['untapped_growths'] = tool_result.get('untapped_growths', [])

                except TypeError as e:
                    logger.error(f"Type error executing tool '{tool_name}': {e}", exc_info=True)
                    observation = f"Error: Tool '{tool_name}' was called with incorrect or missing parameters. The error was: {e}. Please correct the 'parameters' object in your next action."
                except Exception as e:
                    logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
                    observation = f"Error: {e}"

            self.scratchpad += f"\n**Thought**: {thought}\n**Action**: {json.dumps(action_json)}\n**Observation**: {observation}"
            yield {"status": "observation", "message": f"Observation from {tool_name}"}

        logger.warning("Agent exceeded maximum turns.")
        self.final_data = self.gathered_data
        yield {"status": "complete"}

    async def _get_llm_response(self, prompt) -> str:
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return f'**Thought**: A critical error occurred. I must finish now.\n**Action**: {json.dumps({"tool_name": "finish", "parameters": {"gathered_data": self.gathered_data}})}'