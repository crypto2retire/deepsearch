import json
import re
from app.services.tavily import search_tavily


RESEARCHER_SYSTEM = """You are a research analyst. Given a sub-task description and Tavily search results, extract the 5 most important facts.
Return ONLY valid JSON — no explanation, no markdown:
{
  "facts": [
    {"fact": "...", "source": "url or 'general knowledge'"}
  ]
}
- Each fact should be concise and directly relevant to the sub-task.
- Cite the source URL for each fact where available."""


async def call_researcher(sub_task_desc: str, search_query: str, model: str, api_key: str, provider: str) -> dict:
    from app.services.openrouter import call_llm

    search_results = await search_tavily(search_query, top_k=10)

    context = f"Sub-task: {sub_task_desc}\n\nSearch results:\n"
    for i, r in enumerate(search_results, 1):
        context += f"[{i}] {r['title']}\n  URL: {r['url']}\n  Snippet: {r['snippet']}\n\n"

    messages = [
        {"role": "system", "content": RESEARCHER_SYSTEM},
        {"role": "user", "content": context},
    ]
    raw = await call_llm(model, messages, api_key, provider, temperature=0.2)

    raw = raw.strip()
    m = re.search(r"```(?:json)?(.*?)```", raw, re.DOTALL)
    if m:
        raw = m.group(1)
    findings = json.loads(raw)

    return {
        "search_query": search_query,
        "search_results": search_results,
        "findings": findings.get("facts", []),
        "sub_task": sub_task_desc,
        "model": model,
    }
