import json
import logging

logger = logging.getLogger("deepsearch.synthesizer")


async def call_synthesizer(
    query: str,
    all_findings: list[dict],
    model: str,
    api_key: str,
    provider: str,
    system_prompt: str = None,
) -> dict:
    from app.services.openrouter import structured_call

    if not all_findings or all(len(f.get("findings", [])) == 0 for f in all_findings):
        logger.warning("Synthesizer received empty findings — returning no-data response")
        return {
            "answer": "No research data was collected. This could be due to:\n\n1. **Search API returned no results** — The search query may not have matched any web content.\n2. **LLM returned empty facts** — The model may have failed to extract facts from the search results.\n3. **API key or model misconfiguration** — Check your settings to ensure the model is valid for the provider.\n\nTry reformulating your query or switching to a different model/provider in settings.",
            "sources": [],
            "follow_up_questions": [
                "Try a more specific search query?",
                "Check if the Tavily API key is working?",
                "Try a different model in settings?",
            ],
        }

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

    logger.info(f"Synthesizer calling LLM: provider={provider} model={model}")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]
    return await structured_call(model, messages, api_key, provider, temperature=0.3)
