import httpx
import logging
from app.services.prefs import get_tavily_api_key

logger = logging.getLogger("deepsearch.tavily")

async def search_tavily(query: str, top_k: int = 10) -> list[dict]:
    api_key = get_tavily_api_key()
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY not set in Railway environment variables")
    payload = {
        "api_key": api_key,
        "query": query,
        "top_k": top_k,
        "include_answer": False,
        "include_raw_content": False,
    }
    headers = {"Content-Type": "application/json"}
    logger.info(f"Tavily search: query={query[:80]} top_k={top_k}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json=payload,
                headers=headers,
                timeout=30.0,
            )
        response.raise_for_status()
        data = response.json()
        results = [
            {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
            for r in data.get("results", [])
        ]
        logger.info(f"Tavily search success: {len(results)} results for query={query[:50]}")
        return results
    except Exception as e:
        logger.error(f"Tavily search failed: query={query[:80]} error={e}")
        raise
