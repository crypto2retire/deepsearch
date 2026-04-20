import json
import re
import logging
from app.services.tavily import search_tavily

logger = logging.getLogger("deepsearch.researcher")


async def call_researcher(sub_task_desc: str, search_query: str, model: str, api_key: str, provider: str, system_prompt: str = None) -> dict:
    from app.services.openrouter import call_llm

    if not system_prompt:
        system_prompt = (
            "You are a research analyst. Given a sub-task description and Tavily search results, extract the 5 most important facts.\n"
            'Return ONLY valid JSON — no explanation, no markdown:\n'
            '{"facts": [{"fact": "...", "source": "url or \'general knowledge\'"}]}\n'
            "- Each fact should be concise and directly relevant to the sub-task.\n"
            "- Cite the source URL for each fact where available."
        )

    logger.info(f"Researcher searching: {search_query[:80]}")
    search_results = await search_tavily(search_query, top_k=10)
    logger.info(f"Tavily returned {len(search_results)} results for: {search_query[:50]}")

    if not search_results:
        return {
            "search_query": search_query,
            "search_results": [],
            "findings": [{"fact": f"No search results found for: {search_query}", "source": "tavily"}],
            "sub_task": sub_task_desc,
            "model": model,
        }

    context = f"Sub-task: {sub_task_desc}\n\nSearch results:\n"
    for i, r in enumerate(search_results, 1):
        context += f"[{i}] {r['title']}\n  URL: {r['url']}\n  Snippet: {r['snippet']}\n\n"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]
    logger.info(f"Researcher calling LLM: provider={provider} model={model}")
    raw = await call_llm(model, messages, api_key, provider, temperature=0.2)
    logger.info(f"Researcher LLM response: {raw[:200]}")

    raw = raw.strip()
    m = re.search(r"```(?:json)?(.*?)```", raw, re.DOTALL)
    if m:
        raw = m.group(1).strip()

    try:
        data = json.loads(raw)
        facts = data.get("facts", [])
        logger.info(f"Researcher extracted {len(facts)} facts")
        return {
            "search_query": search_query,
            "search_results": search_results,
            "findings": facts,
            "sub_task": sub_task_desc,
            "model": model,
        }
    except json.JSONDecodeError as e:
        logger.error(f"Researcher JSON parse failed: {e} raw={raw[:300]}")
        return {
            "search_query": search_query,
            "search_results": search_results,
            "findings": [{"fact": f"Failed to parse research results: {raw[:200]}", "source": "error"}],
            "sub_task": sub_task_desc,
            "model": model,
        }
