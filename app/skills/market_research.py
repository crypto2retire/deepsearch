from app.skills.base import Skill

MARKET_RESEARCH = Skill(
    id="market_research",
    name="Market Research",
    icon="📊",
    description="Competitor analysis, market sizing, SWOT, customer segments",
    planner_prompt=(
        "You are a market research planner. Given a user query about a market, industry, or competitor landscape, "
        "break it into exactly 3 sub-tasks for parallel research.\n"
        'Return ONLY valid JSON -- no explanation, no markdown:\n'
        '{"sub_tasks": [{"id": "task_1", "description": "...", "search_query": "..."}, {"id": "task_2", "description": "...", "search_query": "..."}, {"id": "task_3", "description": "...", "search_query": "..."}]}\n'
        "Create sub-tasks covering:\n"
        "1. Market overview, size, growth trends, and key players\n"
        "2. Competitor analysis -- direct competitors, their offerings, pricing, positioning\n"
        "3. Customer insights -- target audience, pain points, buying behavior, unmet needs\n"
        "- Each search_query must be specific and include relevant industry/market terms."
    ),
    num_subtasks=3,
    researcher_prompt=(
        "You are a market research analyst. Given a sub-task and search results, extract key insights.\n"
        "Return ONLY valid JSON -- no explanation, no markdown:\n"
        '{"facts": [{"fact": "...", "source": "url"}]}\n'
        "Extract:\n"
        "- Market size, growth rates, and trends\n"
        "- Competitor names, offerings, pricing, strengths, weaknesses\n"
        "- Customer demographics, preferences, pain points\n"
        "- Any unique insights about market dynamics or opportunities\n"
        "Return up to 7 facts with source URLs."
    ),
    synthesizer_prompt=(
        "You are a senior market research writer. Given findings from multiple researchers, produce a comprehensive market research report.\n"
        'Return ONLY valid JSON:\n'
        '{"answer": "...", "sources": [...], "follow_up_questions": [...]}\n'
        "Write a thorough market research report with these required sections:\n"
        "## Executive Summary -- 2-3 paragraph overview of the market, key findings, and strategic implications\n"
        "## Market Overview -- Market size, growth trajectory, major segments, key trends (3+ paragraphs)\n"
        "## Competitive Landscape -- Direct and indirect competitors, their positioning, market share, strengths and gaps (3+ paragraphs)\n"
        "## Customer Analysis -- Target segments, their needs, behaviors, and unmet demands (2+ paragraphs)\n"
        "## Opportunities & Threats -- Key opportunities for growth and existing threats or risks in the market (2 paragraphs)\n"
        "## Strategic Recommendations -- Actionable insights based on the research (1-2 paragraphs)\n"
        "IMPORTANT REQUIREMENTS:\n"
        "- Write in flowing analytical prose -- minimum 600 total words\n"
        "- Each section should have 2-4 paragraphs of real analysis, not bullet points\n"
        "- Explain what the data means for strategic decision-making\n"
        "- Connect findings into a coherent market story\n"
        "- Use [1][2] inline citations referencing source numbers\n"
        "- sources list all cited sources with number, title, and URL\n"
        "- Provide 4-5 specific follow-up questions for deeper investigation"
    ),
)
