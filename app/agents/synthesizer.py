import json


SYNTHESIZER_SYSTEM = """You are a research synthesizer. Given findings from multiple researchers, produce a comprehensive, well-cited answer.
Return ONLY valid JSON:
{
  "answer": "Full markdown answer with [1][2] inline citations...",
  "sources": [{"number": 1, "title": "...", "url": "..."}],
  "follow_up_questions": ["Q1", "Q2", "Q3"]
}
- answer should be in markdown with numbered inline citations [1][2]
- sources should list all cited sources with their numbers
- Provide 3-5 follow-up questions that dig deeper into the topic"""


def call_synthesizer(
    query: str,
    all_findings: list[dict],
    model: str,
    api_key: str,
    provider: str,
) -> dict:
    from app.services.openrouter import structured_call

    context = f"Original query: {query}\n\n=== RESEARCH FINDINGS ===\n"
    for i, finding in enumerate(all_findings, 1):
        context += f"\n--- Researcher {i} ---\n"
        context += f"Task: {finding.get('sub_task', 'N/A')}\n"
        for fact in finding.get("findings", []):
            context += f"  - {fact.get('fact', '')} (source: {fact.get('source', '')}\n"

    messages = [
        {"role": "system", "content": SYNTHESIZER_SYSTEM},
        {"role": "user", "content": context},
    ]
    return structured_call(model, messages, api_key, provider, temperature=0.3)
