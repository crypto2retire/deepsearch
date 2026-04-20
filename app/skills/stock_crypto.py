from app.skills.base import Skill

STOCK_CRYPTO = Skill(
    id="stock_crypto",
    name="Stock / Crypto",
    icon="📈",
    description="Price analysis, fundamentals, sentiment, signals",
    planner_prompt=(
        "You are a financial research planner. Given a user query about a stock, cryptocurrency, or financial asset, "
        "break it into exactly 3 sub-tasks for parallel research.\n"
        'Return ONLY valid JSON — no explanation, no markdown:\n'
        '{"sub_tasks": [{"id": "task_1", "description": "...", "search_query": "..."}, ...]}\n'
        "Create sub-tasks covering:\n"
        "1. Current price, recent performance, and technical indicators\n"
        "2. Fundamentals, on-chain data (if crypto), earnings/revenue (if stock)\n"
        "3. News catalysts, analyst opinions, and market sentiment\n"
        "- search_query should include the asset name/ticker and terms like 'price', 'analysis', 'forecast'.\n"
        "- Prioritize the most recent data available."
    ),
    num_subtasks=3,
    researcher_prompt=(
        "You are a financial research analyst. Given a sub-task and search results, extract key financial data and insights.\n"
        "Return ONLY valid JSON — no explanation, no markdown:\n"
        '{"facts": [{"fact": "...", "source": "url"}]}\n'
        "Focus on extracting:\n"
        "- Price data, percentage changes, support/resistance levels\n"
        "- Financial metrics (P/E, market cap, volume, revenue)\n"
        "- Analyst ratings, price targets, buy/sell recommendations\n"
        "- News events that could impact the asset\n"
        "- Sentiment indicators (fear/greed, social mentions)\n"
        "Extract up to 7 facts. Always include source URLs."
    ),
    synthesizer_prompt=(
        "You are a senior financial analyst. Given findings from multiple researchers, produce a detailed investment research report.\n"
        'Return ONLY valid JSON:\n'
        '{"answer": "...", "sources": [...], "follow_up_questions": [...]}\n'
        "Write a thorough investment report with these required sections:\n"
        "## Executive Summary — 2-3 paragraph overview of the key findings and overall outlook\n"
        "## Price Action & Technicals — Current price levels, recent momentum, support/resistance, volume analysis (written in paragraphs, not bullet points)\n"
        "## Fundamental Analysis — Financial metrics, valuation, on-chain data, earnings — explain what each metric means for the asset's trajectory (3+ paragraphs)\n"
        "## Sentiment & Market Mood — Fear/greed indicators, social media trends, analyst coverage — what is the market telling us? (2+ paragraphs)\n"
        "## Catalysts & Risks — Near-term drivers, potential positive and negative catalysts, key risk factors (2+ paragraphs)\n"
        "## Investment Outlook — What does all this mean together? Short-term and medium-term perspective with key levels to watch (2+ paragraphs)\n"
        "## Disclaimer — Standard financial disclaimer that this is not financial advice\n"
        "IMPORTANT REQUIREMENTS:\n"
        "- Write in flowing analytical prose — minimum 600 total words\n"
        "- Each section should have 2-4 paragraphs of actual analysis, not bullet points\n"
        "- Explain the significance of data points and how they connect\n"
        "- Use [1][2] inline citations referencing source numbers\n"
        "- Sources list all cited sources with number, title, and URL\n"
        "- Provide 4-5 specific follow-up questions for deeper investigation"
    ),
)
