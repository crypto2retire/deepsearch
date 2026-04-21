import json
import logging

logger = logging.getLogger("deepsearch.synthesizer")


async def call_synthesizer(
    query: str,
    research_bundles: list[dict],
    all_findings: list[dict],
    model: str,
    api_key: str,
    provider: str,
    system_prompt: str = None,
) -> dict:
    """
    Two-pass synthesis:
    Pass 1: Organize findings per sub-task into structured research sections
    Pass 2: Write the final prose report using the organized sections
    """
    from app.services.openrouter import call_llm, structured_call

    if not all_findings:
        logger.warning("Synthesizer received empty findings -- returning no-data response")
        return {
            "answer": "No research data was collected. This could be due to:\n\n1. **Search API returned no results** -- The search query may not have matched any web content.\n2. **LLM returned empty facts** -- The model may have failed to extract facts from the search results.\n3. **API key or model misconfiguration** -- Check your settings to ensure the model is valid for the provider.\n\nTry reformulating your query or switching to a different model/provider in settings.",
            "sources": [],
            "follow_up_questions": [
                "Try a more specific search query?",
                "Check if the Tavily API key is working?",
                "Try a different model in settings?",
            ],
        }

    if not system_prompt:
        system_prompt = (
            "You are a senior research writer. Given findings from multiple researchers, produce a detailed written report.\n"
            'Return ONLY valid JSON:\n'
            '{"answer": "Full markdown answer with [1][2] inline citations...", "sources": [{"number": 1, "title": "...", "url": "..."}], "follow_up_questions": ["Q1", "Q2", "Q3"]}\n'
            "- answer should be in markdown with numbered inline citations [1][2]\n"
            "- sources should list all cited sources with their numbers\n"
            "- Provide 3-5 follow-up questions that dig deeper into the topic"
        )

    # Build context for pass 1: include snippets for richer context
    context_parts = []
    for bundle in research_bundles:
        st = bundle.get("sub_task", "")
        facts = bundle.get("findings", [])
        snippets = bundle.get("search_snippets", [])
        context_parts.append(f"\n=== Sub-task: {st} ===\n")
        context_parts.append("--- Extracted Facts ---\n")
        for f in facts:
            context_parts.append(f"- {f.get('fact', '')} (source: {f.get('source', '')})\n")
        if snippets:
            context_parts.append("\n--- Raw Search Snippets ---\n")
            for s in snippets[:5]:
                context_parts.append(f"[{s.get('title', '?')}] {s.get('snippet', '')}\n")

    pass1_context = (
        f"Original research query: {query}\n"
        "Your job is to organize the findings below into a structured research outline.\n"
        "Return ONLY valid JSON:\n"
        '{"sections": [{"topic": "Section Title", "summary": "2-3 sentence summary of key findings", "key_points": ["point 1", "point 2", "point 3"], "supporting_evidence": ["evidence from sources", "..."], "gaps": "What information was missing or inconclusive"]}\n'
        "Group findings into 4-6 thematic sections. Each section should have:\n"
        "- topic: a descriptive title\n"
        "- summary: 2-3 sentences summarizing what the research found on this topic\n"
        "- key_points: 3-5 specific findings with citations\n"
        "- supporting_evidence: relevant quotes or data from the raw snippets\n"
        "- gaps: what was missing, unclear, or requires further research\n"
    ) + "\n".join(context_parts)

    logger.info(f"Synthesizer Pass 1: organizing {len(all_findings)} findings into sections")
    pass1_messages = [
        {"role": "system", "content": "You are a research organizer. Analyze findings and create a structured outline. Return ONLY valid JSON."},
        {"role": "user", "content": pass1_context},
    ]

    try:
        sections_data = await structured_call(model, pass1_messages, api_key, provider, temperature=0.3)
        sections = sections_data.get("sections", [])
        logger.info(f"Pass 1 organized into {len(sections)} sections")
    except Exception as e:
        logger.warning(f"Pass 1 failed: {e}, falling back to single-pass synthesis")
        sections = []

    # Build pass 2 context with organized sections (or raw findings as fallback)
    if sections:
        pass2_body = "## Research Report\n\n"
        for i, sec in enumerate(sections, 1):
            pass2_body += f"\n### {sec.get('topic', f'Section {i}')}\n\n"
            summary = sec.get("summary", "")
            if summary:
                pass2_body += summary + "\n\n"
            key_pts = sec.get("key_points", [])
            for pt in key_pts:
                pass2_body += f"- {pt}\n"
            gaps = sec.get("gaps", "")
            if gaps:
                pass2_body += f"\n*Note on gaps: {gaps}*\n"
    else:
        # Fallback: use raw findings
        pass2_body = "## Key Findings\n\n"
        for f in all_findings:
            pass2_body += f"- {f.get('fact', '')} (source: {f.get('source', '')})\n"

    # Build citations map from all findings
    citation_map = {}
    for f in all_findings:
        src = f.get("source", "")
        if src and src not in citation_map:
            num = len(citation_map) + 1
            citation_map[src] = {"number": num, "title": src, "url": src}

    pass2_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Original query: {query}\n\n=== Research organized by topic ===\n{pass2_body}\n\n=== All source citations ===\n" + "\n".join(f"[{v['number']}] {v['title']} -- {v['url']}" for v in citation_map.values())},
    ]

    logger.info(f"Synthesizer Pass 2: writing final report with {len(citation_map)} sources")
    return await structured_call(model, pass2_messages, api_key, provider, temperature=0.3)
