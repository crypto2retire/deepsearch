import json


async def call_synthesizer(
    query: str,
    all_findings: list[dict],
    model: str,
    api_key: str,
    provider: str,
    system_prompt: str = None,
) -> dict:
    from app.services.openrouter import structured_call

    if not system_prompt:
        system_prompt = (
            "You are a research synthesizer. Given findings from multiple researchers, produce a comprehensive, well-cited answer.\n"
            'Return ONLY valid JSON:\n'
            '{"answer": "Full markdown answer with [1][2] inline citations...", "sources": [{"number": 1, "title": "...", "url": "..."}], "follow_up_questions": ["Q1", "Q2", "Q3"]}\n'
            "- answer should be in markdown with numbered inline citations [1][2]\n"
            "- sources should list all cited sources with their numbers\n"
            "- Provide 3-5 follow-up questions that dig deeper into the topic"
        )

    context = f"Original query: {query}\n\n=== RESEARCH FINDINGS ===\n"
    for i, finding in enumerate(all_findings, 1):
        context += f"\n--- Researcher {i} ---\n"
        context += f"Task: {finding.get('sub_task', 'N/A')}\n"
        for fact in finding.get("findings", []):
            context += f"  - {fact.get('fact', '')} (source: {fact.get('source', '')}\n"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]
    return await structured_call(model, messages, api_key, provider, temperature=0.3)
