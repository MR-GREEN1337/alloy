import httpx
import google.generativeai as genai
from typing import List, Dict, Any, AsyncGenerator, Optional, Tuple, Set
from loguru import logger
import json

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
    """Performs a deep cultural comparison and returns a structured dictionary."""
    logger.info(f"AGENT TOOL: Qloo Comparative Analysis for '{acquirer_brand_name}' vs '{target_brand_name}'")
    async with httpx.AsyncClient(timeout=45.0) as client:
        acquirer_info = await _find_qloo_id(client, acquirer_brand_name)
        target_info = await _find_qloo_id(client, target_brand_name)
        if not acquirer_info: return {"context_str": f"Error: Could not find acquirer '{acquirer_brand_name}' in Qloo database."}
        if not target_info: return {"context_str": f"Error: Could not find target '{target_brand_name}' in Qloo database."}
        acquirer_tastes = await _get_qloo_tastes(client, acquirer_info[0])
        target_tastes = await _get_qloo_tastes(client, target_info[0])
    if not acquirer_tastes or not target_tastes: return {"context_str": "Error: Could not retrieve taste data."}
    acquirer_set, target_set = {t['name'] for t in acquirer_tastes}, {t['name'] for t in target_tastes}
    shared_tastes, union_size = list(acquirer_set.intersection(target_set)), len(acquirer_set.union(target_set))
    # CORE FIX: Always return a dictionary with a 'context_str' key.
    return {"context_str": json.dumps({
        "affinity_overlap_score": round((len(shared_tastes) / union_size * 100), 2) if union_size > 0 else 0,
        "shared_affinities_top_5": shared_tastes[:5],
        "acquirer_unique_tastes_top_5": list(acquirer_set - target_set)[:5],
        "target_unique_tastes_top_5": list(target_set - acquirer_set)[:5],
    })}

# --- The Stateful ReAct Agent ---
class AlloyReActAgent:
    PROMPT_TEMPLATE = """
    You are a data-gathering AI assistant for a financial firm.
    Your only job is to execute a sequence of tool calls to gather information about two companies and their cultural overlap.
    Do not synthesize, analyze, or generate the final report yourself. Simply gather the data and pass it to the 'finish' tool.

    **TOOLS:**
    - `web_search(query: str)`: For company profile research.
    - `qloo_comparative_analysis(acquirer_brand_name: str, target_brand_name: str)`: For cultural data.
    - `finish(gathered_data: dict)`: Use this ONLY when all data gathering steps are complete. The `gathered_data` parameter must be a JSON object containing keys 'acquirer_profile', 'target_profile', and 'qloo_analysis'.

    **RESPONSE FORMAT:**
    You MUST respond with a "Thought" and an "Action" in this exact format. The Action MUST be a valid JSON object.
    **Thought**: [Your reasoning for the next action]
    **Action**: [A single JSON object for the tool call]

    **EXAMPLE ACTION:**
    **Action**: {{"tool_name": "web_search", "parameters": {{"query": "Example Inc. company profile"}}}}

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
        self.tools = {"web_search": _web_search_tool, "qloo_comparative_analysis": _qloo_comparative_analysis_tool}
        self.all_sources: Dict[str, List[Dict[str, str]]] = {'acquirer_sources': [], 'target_sources': [], 'search_sources': []}

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
        max_turns = 6
        for i in range(max_turns):
            yield {"status": "thinking", "message": f"Agent reasoning (Step {i+1}/{max_turns})"}
            
            prompt = self._build_prompt()
            response_text = await self._get_llm_response(prompt)
            
            if "**Action**:" not in response_text:
                yield {"status": "thought", "message": response_text.replace("**Thought**:", "").strip()}
                logger.warning("Agent produced a thought but no action. Ending turn.")
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
                observation = f"Error: The provided Action was not valid JSON. Please ensure your Action is a single, correctly formatted JSON object with 'tool_name' and 'parameters' keys. The error was: {e}"
                self.scratchpad += f"\n**Thought**: {thought}\n**Action**: {action_str}\n**Observation**: {observation}"
                continue

            tool_name, params = action_json.get("tool_name"), action_json.get("parameters", {})
            
            if not tool_name:
                observation = "Error: Your action JSON is missing the 'tool_name' key."
            elif tool_name == "finish":
                self.final_data = params.get("gathered_data", {})
                yield {"status": "complete"}
                return
            elif tool_name not in self.tools:
                observation = f"Error: Unknown tool '{tool_name}'."
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
                        
                        sources = tool_result.get('sources', [])
                        for source in sources:
                            yield {"status": "source", "payload": source}

                    elif tool_name == "qloo_comparative_analysis":
                        self.completed_steps.add("performed_qloo_analysis")
                        # This can fail if the observation is an error string.
                        try:
                            self.gathered_data['qloo_analysis'] = json.loads(observation)
                        except json.JSONDecodeError:
                            # Observation is an error message, pass it on.
                            self.gathered_data['qloo_analysis'] = {"error": observation}

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