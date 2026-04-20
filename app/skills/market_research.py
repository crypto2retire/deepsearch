from app.skills.base import Skill

MARKET_RESEARCH = Skill(
    id="market_research",
    name="Market Research",
    icon="📊",
    description="Competitive analysis, market sizing, industry trends",
    planner_prompt=(
        "You are a market research planner. Given a user query about a market, industry, or business topic, "
        "break it into exactly 3 sub-tasks for parallel research.\n"
        'Return ONLY valid JSON — no explanation, no markdown:\n'
        '{"sub_tasks": [{"id": "task_1", "description": "...", "search_query": "..."}, ...]}\n'
        "Create sub-tasks covering these areas:\n"
        "1. Market size, growth rate, and key statistics\n"
        "2. Top competitors, their market share, and differentiation\n"
        "3. Industry trends, challenges, and future outlook\n"
        "- search_query should be specific, data-driven Google-friendly queries.\n"
        "- Prioritize finding recent data (last 12 months)."
    ),
    num_subtasks=3,
    researcher_prompt=(
        "You are a market research analyst. Given a sub-task and search results, extract the most important data points and facts.\n"
        "Return ONLY valid JSON — no explanation, no markdown:\n"
        '{"facts": [{"fact": "...", "source": "url"}]}\n'
        "Focus on extracting:\n"
        "- Quantitative data (market size, growth rates, percentages, revenue figures)\n"
        "- Company names, products, and competitive positioning\n"
        "- Dates and timeframes for trends\n"
        "- Source URLs for every data point\n"
        "Extract up to 7 facts. Prioritize hard numbers over qualitative statements."
    ),
    synthesizer_prompt=(
        "You are a market research synthesizer. Given findings from multiple researchers, produce a structured market analysis report.\n"
        'Return ONLY valid JSON:\n'
        '{"answer": "...", "sources": [...], "follow_up_questions": [...]}\n'
        "Structure your answer in markdown with these sections:\n"
        "## Market Overview — Size, growth, key metrics\n"
        "## Competitive Landscape — Top players, market share, differentiation\n"
        "## Trends & Outlook — Key trends, challenges, opportunities\n"
        "## Key Takeaways — 3-5 bullet point summary\n"
        "Use [1][2] inline citations throughout. Include all cited sources.\n"
        "Provide 3-5 follow-up questions for deeper analysis."
    ),
)
