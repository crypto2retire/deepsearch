import json


async def call_planner(query: str, api_key: str, model: str, provider: str, system_prompt: str = None) -> dict:
    from app.services.openrouter import structured_call

    if not system_prompt:
        system_prompt = (
            "You are a research planner. Given a user query, break it into exactly 2 sub-tasks for parallel research.\n"
            'Return ONLY valid JSON — no explanation, no markdown — in this exact format:\n'
            '{"sub_tasks": [{"id": "task_1", "description": "...", "search_query": "..."}, {"id": "task_2", "description": "...", "search_query": "..."}]}\n'
            "- search_query should be a Google-friendly web search query.\n"
            "- Keep descriptions concise (1-2 sentences).\n"
            "- Each sub-task should cover a distinct aspect of the user's query."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]
    return await structured_call(model, messages, api_key, provider, temperature=0.2)
