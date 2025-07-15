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

# --- Agent Tools ---

async def _tavily_search_tool(query: str) -> Dict[str, Any]:
    """
    Performs a Tavily search and returns the context string and sources.
    Returns a dictionary: {"context_str": "...", "sources": [...]}
    """
    logger.info(f"AGENT TOOL: Tavily Search with query: '{query}'")
    result = await tavily_search(query)
    # The tavily_search service already returns the correct format.
    return result

async def _qloo_brand_insights_tool(brand_name: str) -> str:
    """
    Gets cultural taste insights for a specific brand from Qloo.
    This tool first searches for the brand to find its Qloo ID, then fetches insights.
    Returns a string summary of the top tastes.
    """
    logger.info(f"AGENT TOOL: Qloo Insights for brand: '{brand_name}'")
    headers = {"x-api-key": settings.QLOO_API_KEY}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Step 1: Fuzzy search for the brand to get its Qloo ID
            logger.info(f"Qloo searching for brand: '{brand_name}'")
            qloo_search_payload = {"query": brand_name, "filter": {"type": "urn:entity:brand"}, "take": 1}
            qloo_search_url = "https://hackathon.api.qloo.com/v2/search"
            search_resp = await client.post(qloo_search_url, json=qloo_search_payload, headers=headers)
            search_resp.raise_for_status()
            
            search_results = search_resp.json().get("data", [])
            if not search_results:
                return f"Error: Could not find a matching brand for '{brand_name}' in Qloo's database."
            
            best_match = search_results[0]
            qloo_id = best_match.get("id")
            found_name = best_match.get("name")
            logger.success(f"Found Qloo match for '{brand_name}': '{found_name}' (ID: {qloo_id})")

            # Step 2: Get insights for the found Qloo ID
            insights_payload = {"id": [qloo_id], "take": 50}
            insights_url = "https://hackathon.api.qloo.com/v2/insights"
            insights_resp = await client.post(insights_url, json=insights_payload, headers=headers)
            insights_resp.raise_for_status()
            
            tastes = insights_resp.json().get("data", [])
            if not tastes:
                return f"No significant cultural tastes found for '{found_name}'."
            
            taste_summary = ", ".join([item['name'] for item in tastes[:20]])
            return f"The audience of '{found_name}' shows affinity for: {taste_summary}"

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            logger.error(f"Qloo API error for '{brand_name}': {error_body}")
            return f"Error: Qloo API returned status {e.response.status_code}. Details: {error_body}"
        except Exception as e:
            logger.error(f"Error in Qloo tool for '{brand_name}': {e}", exc_info=True)
            return f"An unexpected error occurred while fetching data for '{brand_name}'."


class AlloyReActAgent:
    """A ReAct agent for generating cultural due diligence reports."""

    PROMPT_TEMPLATE = """
    You are Alloy, an expert M&A brand strategist. Your goal is to generate a cultural due diligence report comparing two companies.
    
    You have access to the following tools:
    - tavily_search(query: str): Use for broad research on a company's profile, history, target audience, or recent news. Returns a JSON object with 'context_str' for your reasoning and 'sources' for citation.
    - qloo_brand_insights(brand_name: str): Use to get specific cultural taste data (movies, music, books, etc.) for a brand's audience. This is your primary data source for cultural analysis.
    - finish(report_json: str): Use this ONLY when you have gathered all necessary information and are ready to generate the final report.

    Follow this process:
    1.  **Thought**: Reason about the task and decide your next step. Be concise.
    2.  **Action**: Output a JSON object with "tool_name" and "parameters".
    
    Example:
    **Thought**: I need to understand the acquirer's business first.
    **Action**: { "tool_name": "tavily_search", "parameters": { "query": "Corporate profile and brand identity of The Walt Disney Company" } }
    
    You will be given the result of your action as an **Observation**. Use it to inform your next thought.
    
    RULES:
    - Start by researching each company's profile using `tavily_search`.
    - Then, use `qloo_brand_insights` for BOTH the acquirer and target to get their cultural profiles. This is mandatory.
    - If a tool fails, especially `qloo_brand_insights`, think about why it might have failed (e.g., brand name typo) and try again with a variation. If it consistently fails and you cannot proceed, you MUST use the `finish` tool with an empty report and explain the failure in the `strategic_summary`.
    - Synthesize all information to identify clashes, growth opportunities, and brand archetypes.
    - Once you have a clear picture, use the `finish` tool. The `report_json` parameter MUST be a single, valid JSON string containing the complete report with these exact keys: "cultural_compatibility_score", "affinity_overlap_score", "brand_archetype_summary", "strategic_summary", "culture_clashes", "untapped_growths".
    - `brand_archetype_summary` must be a stringified JSON object with keys "acquirer_archetype" and "target_archetype".
    - `culture_clashes` must be a list of objects, each with "topic", "description", and "severity" ("LOW", "MEDIUM", or "HIGH").
    - `untapped_growths` must be a list of objects, each with "description" and "potential_impact_score" (1-10).

    Here is your task:
    """

    def __init__(self, acquirer_brand: str, target_brand: str, user_context: str | None = None):
        self.acquirer_brand = acquirer_brand
        self.target_brand = target_brand
        self.user_context = user_context
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
        self.scratchpad = self.PROMPT_TEMPLATE + (
            f"Generate a cultural due diligence report for the acquisition of **{target_brand}** by **{acquirer_brand}**."
            f"\nUser-provided context to consider: {user_context}" if user_context else ""
        )
        self.final_report = None
        self.tools = {
            "tavily_search": _tavily_search_tool,
            "qloo_brand_insights": _qloo_brand_insights_tool
        }

    async def run_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        max_turns = 10 
        for i in range(max_turns):
            yield {"status": "thinking", "message": f"Turn {i+1}/{max_turns}: Agent is reasoning..."}
            
            response_text = await self._get_llm_response()

            thought = ""
            action_json = {}
            try:
                if "**Action**:" not in response_text:
                    thought = response_text.replace("**Thought**:", "").strip()
                    yield {"status": "thought", "message": thought}
                    yield {"status": "error", "message": f"Agent finished without a final action. Concluding thought: {thought}"}
                    return

                thought = response_text.split("**Action**:")[0].replace("**Thought**:", "").strip()
                action_str = response_text.split("**Action**:")[1].strip().replace("```json", "").replace("```", "")
                action_json = json.loads(action_str)
            except (IndexError, json.JSONDecodeError) as e:
                yield {"status": "error", "message": f"Agent parsing error: {e}. The agent responded: '{response_text}'"}
                return

            yield {"status": "thought", "message": thought}
            yield {"status": "action", "payload": action_json}
            
            tool_name = action_json.get("tool_name")
            parameters = action_json.get("parameters", {})

            if tool_name == "finish":
                report_payload = parameters.get("report_json", "{}")
                if isinstance(report_payload, str):
                    self.final_report = json.loads(report_payload)
                else:
                    self.final_report = report_payload
                
                yield {"status": "complete", "message": "Agent has finished the report."}
                return

            if tool_name not in self.tools:
                observation = f"Error: Unknown tool '{tool_name}'."
                observation_for_llm = observation
            else:
                try:
                    tool_result = await self.tools[tool_name](**parameters)
                    
                    # CORE FIX: Check if the tool is tavily_search and handle its structured output
                    if tool_name == "tavily_search":
                        observation_for_llm = tool_result['context_str']
                        # Stream individual sources to the frontend
                        for source in tool_result.get('sources', []):
                            yield {"status": "source", "payload": source}
                    else:
                        observation_for_llm = str(tool_result)

                    observation = observation_for_llm

                except Exception as e:
                    observation = f"Error executing tool '{tool_name}': {e}"
                    observation_for_llm = observation
            
            yield {"status": "observation", "message": f"Observation from {tool_name}: {observation}"}
            self.scratchpad += f"\n**Thought**: {thought}\n**Action**: {json.dumps(action_json)}\n**Observation**: {observation_for_llm}"

        yield {"status": "error", "message": "Agent exceeded maximum turns."}

    async def _get_llm_response(self) -> str:
        try:
            response = await self.model.generate_content_async(self.scratchpad)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API call failed in agent: {e}")
            error_report = {
                "strategic_summary": f"Could not complete analysis due to a critical LLM error: {e}",
                "cultural_compatibility_score": 0,
                "affinity_overlap_score": 0,
                "brand_archetype_summary": {},
                "culture_clashes": [],
                "untapped_growths": []
            }
            return f"**Thought**: A critical error occurred. I must stop and report the failure.\n**Action**: {{ \"tool_name\": \"finish\", \"parameters\": {{ \"report_json\": {json.dumps(json.dumps(error_report))} }} }}"