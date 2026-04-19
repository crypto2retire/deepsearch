import json


PLANNER_SYSTEM = """You are a research planner. Given a user query, break it into exactly 2 sub-tasks for parallel research.
Return ONLY valid JSON — no explanation, no markdown — in this exact format:
{
  "sub_tasks": [
    {"id": "task_1", "description": "...", "search_query": "..."},
    {"id": "task_2", "description": "...", "search_query": "..."}
  ]
}
- search_query should be a Google-friendly web search query.
- Keep descriptions concise (1-2 sentences).
- Each sub-task should cover a distinct aspect of the user's query."""


def call_planner(query: str, api_key: str, model: str, provider: str) -> dict:
    from app.services.openrouter import structured_call

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": query},
    ]
    return structured_call(model, messages, api_key, provider, temperature=0.2)
