from app.skills.base import Skill

MARKET_RESEARCH = Skill(
    id="market_research",
    name="Market Research",
    icon="📊",
    description="Competitor analysis, market sizing, SWOT, customer segments",
    planner_prompt=(
        "You are a market research planner. Given a user query about a local business, market, or industry, "
        "break it into exactly 4 sub-tasks for parallel research.\n"
        'Return ONLY valid JSON -- no explanation, no markdown:\n'
        '{"sub_tasks": [{"id": "task_1", "description": "...", "search_query": "..."}, {"id": "task_2", "description": "...", "search_query": "..."}, {"id": "task_3", "description": "...", "search_query": "..."}, {"id": "task_4", "description": "...", "search_query": "..."}]}\n'
        "IMPORTANT SEARCH QUERY RULES:\n"
        "- ALWAYS include location terms (city, state, zip code) in every search query -- e.g. 'Oshkosh WI', 'Fox Valley Wisconsin', '54901'\n"
        "- ALWAYS include the specific business type -- e.g. 'junk removal', 'hauling service', 'decluttering', 'estate cleanout'\n"
        "- Search queries must sound like what someone would type into Google to find this type of business\n"
        "- NEVER use generic industry terms like 'market analysis', 'competitors', 'industry overview' as search queries -- they return no useful results\n"
        "Create 4 distinct sub-tasks covering:\n"
        "1. Business/Service research -- Find the main business name, what they do, their reviews, their website, their service area\n"
        "2. Local competitors -- Find other junk removal / hauling / cleanout services in the same city and surrounding area\n"
        "3. Pricing and services -- Find typical pricing for junk removal services in the area, what services competitors offer\n"
        "4. Customer insights -- Find customer reviews, complaints, what customers are looking for, local market demand\n"
        "Example search queries for a junk removal business in Oshkosh WI:\n"
        '- "Clear the Clutter Junk Removal Oshkosh" -- to find the business itself\n'
        '- "junk removal Oshkosh WI" or "hauling service Oshkosh Wisconsin" -- to find competitors\n'
        '- "junk removal cost Oshkosh" or "estate cleanout service Fox Valley Wisconsin" -- to find pricing\n'
        '- "junk removal reviews Oshkosh Wisconsin" -- to find customer insights\n'
    ),
    num_subtasks=4,
    researcher_prompt=(
        "You are a market research analyst. Given a sub-task and search results, extract key insights.\n"
        "Return ONLY valid JSON -- no explanation, no markdown:\n"
        '{"facts": [{"fact": "...", "source": "url"}]}\n'
        "Extract:\n"
        "- Business names, locations, websites, services offered\n"
        "- Competitor names, services, pricing if available\n"
        "- Customer reviews, ratings, common praise and complaints\n"
        "- Market insights, trends specific to the local area\n"
        "IMPORTANT: Only extract facts that appear in the search results. Do NOT make up business names, prices, or other details. If the search results do not contain specific information, say so in the fact.\n"
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
        "- Only write about competitors and businesses that appear in the research findings -- do NOT invent or assume competitor names\n"
        "- If research did not find specific competitors, say so clearly and focus on what was found\n"
        "- Explain what the data means for strategic decision-making\n"
        "- Connect findings into a coherent market story\n"
        "- Use [1][2] inline citations referencing source numbers\n"
        "- sources list all cited sources with number, title, and URL\n"
        "- Provide 4-5 specific follow-up questions for deeper investigation"
    ),
)
