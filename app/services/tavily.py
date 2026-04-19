import httpx
from app.config import get_settings

settings = get_settings()


def search_tavily(query: str, top_k: int = 10) -> list[dict]:
    """Search Tavily and return structured results."""
    payload = {
        "query": query,
        "top_k": top_k,
        "include_answer": False,
        "include_raw_content": False,
    }
    headers = {"Authorization": f"Bearer {settings.TAVILY_API_KEY}"}
    response = httpx.post(
        "https://api.tavily.com/search",
        json=payload,
        headers=headers,
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
        }
        for r in results
    ]
