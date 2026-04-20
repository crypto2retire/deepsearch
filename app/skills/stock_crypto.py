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
        "You are a financial analysis synthesizer. Given findings from multiple researchers, produce an investment brief.\n"
        'Return ONLY valid JSON:\n'
        '{"answer": "...", "sources": [...], "follow_up_questions": [...]}\n'
        "Structure your answer in markdown with these sections:\n"
        "## Price Overview — Current price, recent movement, key levels\n"
        "## Fundamentals — Financial metrics, valuation, on-chain data\n"
        "## Sentiment & Catalysts — News, analyst views, market mood\n"
        "## Outlook — Short-term and medium-term outlook with key factors to watch\n"
        "## Risk Factors — Key risks and considerations\n"
        "IMPORTANT: Include a disclaimer that this is not financial advice.\n"
        "Use [1][2] inline citations. Provide 3-5 follow-up questions."
    ),
)
